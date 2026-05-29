#!/usr/bin/env python3
"""Print the Steam launch options that put AoE3 DE in an isolated 1920x1080
gamescope session, plus a verification one-liner.

The harness already auto-detects nested gamescope sockets via
``gamescope_detect.py``; you don't need to set DISPLAY by hand. All you do is
paste the printed launch options into the AoE3 DE Steam Properties page, then
run the verify command to confirm a new gamescope socket appeared.

Usage::

    python3 tools/aoe3_automation/print_isolated_launch_options.py
    python3 tools/aoe3_automation/print_isolated_launch_options.py --verify
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys

# Recommended Steam launch options for AoE3 DE (AppId 933110) on Bazzite/Proton.
#   -W / -H : nominal output mode the game sees (1920x1080).
#   -w / -h : the size of the gamescope compositor window on the host. Same
#             values keep aspect 1:1, so the nested session looks like a real
#             1920x1080 monitor rendered into a host window of equal size.
#   --steam : enables the Steam overlay + UI scaling tweaks.
#   --xwayland-count 1 : single nested Xwayland — the harness expects exactly
#             one new :N display to attach to.
# Env vars set BEFORE gamescope (e.g. via `env VAR=val gamescope ...`)
# propagate to the inner Proton+game process by default, so existing AoE3
# launch options like `WINEDEBUG=+file PROTON_LOG=1 PROTON_LOG_DIR=/home/USER`
# continue to work — paste them in front of `gamescope`, not after.
# The user can append further flags (e.g. ``-r 60`` to cap framerate, or
# ``-f`` to fullscreen the gamescope window onto a real second monitor if one
# is plugged in). %command% is Steam's placeholder for the actual game binary.
#
# IMPORTANT — `--steam` vs no `--steam`:
#   `--steam` puts gamescope into Steam-Deck Gaming-Mode lifecycle. On a real
#   SteamOS / Big Picture session it integrates the Steam overlay and the
#   shutdown chain. On a *desktop* KDE Plasma 6 (Wayland) session it can leave
#   gamescope rendering internally but never presenting a visible host surface —
#   the compositor exists, AoE3 runs inside it, but you see nothing on your
#   monitor (the symptom we hit on 2026-05-10). For desktop Plasma use
#   RECOMMENDED_DESKTOP below; only use RECOMMENDED_STEAM_MODE if you actually
#   boot into the Bazzite Gaming-Mode session.
RECOMMENDED_DESKTOP = (
    "gamescope -W 1920 -H 1080 -w 1920 -h 1080 "
    "--xwayland-count 1 -- %command%"
)
RECOMMENDED_STEAM_MODE = (
    "gamescope -W 1920 -H 1080 -w 1920 -h 1080 --steam "
    "--xwayland-count 1 -- %command%"
)
# Back-compat alias used by older callers / docs.
RECOMMENDED = RECOMMENDED_DESKTOP
# Variant that preserves the user's existing diagnostic env vars (Proton log
# directory, Wine file-trace) — paste this if your current launch options
# already include WINEDEBUG / PROTON_LOG.
RECOMMENDED_WITH_DIAGNOSTICS = (
    "env WINEDEBUG=+file PROTON_LOG=1 PROTON_LOG_DIR=/home/$USER "
    + RECOMMENDED_DESKTOP
)

# After launch this is what the verify step checks: a new socket appears in
# $XDG_RUNTIME_DIR named ``gamescope-N`` and ``gamescopectl status`` against
# it succeeds.
VERIFY_DESC = (
    "After AoE3 starts, a NEW socket should appear in $XDG_RUNTIME_DIR with "
    "name 'gamescope-N'. The harness's gamescope_detect.py finds it "
    "automatically; xdotool against the matching Xwayland :N targets ONLY "
    "the AoE3 window — your primary cursor on :0 is never touched."
)


def _existing_sockets() -> list[str]:
    """Real gamescope compositor sockets only — name pattern 'gamescope-N'.

    The framerate limiter creates 'gamescope-limiter-XX*' shared-memory
    sockets in the same directory; those are not compositors and must be
    excluded from this glob.
    """
    xdg = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    candidates = glob.glob(os.path.join(xdg, "gamescope-*"))
    return sorted(p for p in candidates
                  if os.path.basename(p).split("-", 1)[1].isdigit())


def _verify() -> int:
    if not shutil.which("gamescope"):
        print("FAIL: gamescope not on PATH. On Bazzite it should ship with the "
              "system; check with `rpm -q gamescope` or `which gamescope`.")
        return 1
    pre = _existing_sockets()
    print(f"gamescope binary: {shutil.which('gamescope')}")
    print(f"existing gamescope-* sockets BEFORE launch: {pre or '(none)'}")
    print()
    print("Action required:")
    print("  1. Open Steam → AoE3 DE → Properties → General → Launch Options.")
    print("  2. Paste the line printed by `--print` (run without --verify).")
    print("  3. Click Play and let the game reach the main menu.")
    print("  4. Re-run this script with --verify-after-launch to confirm a new")
    print("     gamescope-N socket appeared and gamescopectl can talk to it.")
    return 0


def _verify_after_launch() -> int:
    sockets = _existing_sockets()
    if not sockets:
        print("FAIL: no gamescope-* sockets in $XDG_RUNTIME_DIR. Either AoE3 "
              "is not running, or the launch options didn't take effect.")
        return 1
    print(f"Found gamescope sockets: {sockets}")
    ok = False
    for sock in sockets:
        name = os.path.basename(sock)
        env = {
            **os.environ,
            "GAMESCOPE_WAYLAND_DISPLAY": name,
            "WAYLAND_DISPLAY": name,
        }
        try:
            r = subprocess.run(
                ["gamescopectl", "status"],
                env=env, capture_output=True, text=True, timeout=5,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            print(f"  {name}: gamescopectl status FAILED — {exc}")
            continue
        if r.returncode == 0:
            print(f"  {name}: OK — gamescopectl reachable")
            ok = True
        else:
            print(f"  {name}: rc={r.returncode}, stderr={r.stderr.strip()[:120]}")
    if not ok:
        return 1
    print()
    print("Now run the harness as usual — gamescope_detect.py will pick up the "
          "new socket and target the isolated AoE3 session automatically.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--verify", action="store_true",
                     help="Pre-launch sanity check: gamescope on PATH, list "
                          "existing sockets.")
    grp.add_argument("--verify-after-launch", action="store_true",
                     help="Post-launch check: confirm new gamescope-N socket "
                          "is reachable.")
    args = ap.parse_args()

    if args.verify:
        return _verify()
    if args.verify_after_launch:
        return _verify_after_launch()

    print("Steam launch options for AoE3 DE (paste into Properties → Launch Options):")
    print()
    print("DESKTOP KDE Plasma session (recommended — no --steam):")
    print(f"    {RECOMMENDED_DESKTOP}")
    print()
    print("With Wine/Proton diagnostic logging (matches the user's existing setup):")
    print(f"    {RECOMMENDED_WITH_DIAGNOSTICS}")
    print()
    print("STEAM-DECK / Bazzite Gaming-Mode session only (with --steam):")
    print(f"    {RECOMMENDED_STEAM_MODE}")
    print("    Do NOT use this on a desktop Plasma session — gamescope will")
    print("    render but never present a visible host window.")
    print()
    print(VERIFY_DESC)
    print()
    print("Verify before launch:  python3 tools/aoe3_automation/"
          "print_isolated_launch_options.py --verify")
    print("Verify after launch:   python3 tools/aoe3_automation/"
          "print_isolated_launch_options.py --verify-after-launch")
    return 0


if __name__ == "__main__":
    sys.exit(main())
