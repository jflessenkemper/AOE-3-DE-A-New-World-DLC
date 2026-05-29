#!/usr/bin/env python3
"""Gate-wired wrapper around verified_input.py — fails the gate if no
working input backend can reach the gamescope-nested game.

Without a working input backend, we cannot:
  - Drive the lobby picker to verify all 46 ANW civs render
  - Run any matrix matches automatically
  - Self-test live UI flows

So this is a hard release-gate. It runs ``verified_input.py --probe``
under the hood and inherits its rc.

Usage::

    python3 tools/validation/validate_input_harness.py
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]


def _static_check_backends() -> list[tuple[str, bool, str]]:
    """Return (name, available, note) for each known input backend binary."""
    results = []

    # ydotool — uinput-based backend
    ydotool_found = shutil.which("ydotool") is not None
    results.append((
        "ydotool",
        ydotool_found,
        "uinput-based input injection; requires ydotoold daemon + udev seat assignment" if ydotool_found
        else "not found in PATH; install ydotool for uinput-based input injection",
    ))

    # xdotool — X11 input injection
    xdotool_found = shutil.which("xdotool") is not None
    results.append((
        "xdotool",
        xdotool_found,
        "X11 input injection (works on DISPLAY=:0/:1)" if xdotool_found
        else "not found in PATH; install xdotool for X11-based input injection",
    ))

    # gamescopectl — gamescope screenshot + control
    gamescopectl_found = shutil.which("gamescopectl") is not None
    results.append((
        "gamescopectl",
        gamescopectl_found,
        "gamescope frame capture + control tool" if gamescopectl_found
        else "not found in PATH; install gamescopectl for gamescope integration",
    ))

    # ei_inject — compiled libei binary in repo
    ei_inject_path = REPO_ROOT / "tools" / "aoe3_automation" / "ei_inject"
    ei_found = ei_inject_path.exists() and os.access(ei_inject_path, os.X_OK)
    results.append((
        "ei_inject",
        ei_found,
        f"libei binary present at {ei_inject_path.relative_to(REPO_ROOT)}" if ei_found
        else f"not built; run: gcc tools/aoe3_automation/ei_inject.c -lei -o tools/aoe3_automation/ei_inject",
    ))

    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--static-mode", action="store_true",
                    help=(
                        "Offline fallback: verify at least one input backend binary "
                        "is installed/available on this system without probing the "
                        "live game. PASS if ydotool, xdotool, gamescopectl, or "
                        "ei_inject is present. FAIL if none are available."
                    ))
    args = ap.parse_args()

    if args.static_mode:
        print("=" * 60)
        print("INPUT HARNESS VALIDATION (static-mode)")
        print("=" * 60)
        backends = _static_check_backends()
        available = [(name, note) for name, ok, note in backends if ok]
        missing = [(name, note) for name, ok, note in backends if not ok]

        for name, ok, note in backends:
            mark = "+" if ok else "-"
            print(f"  [{mark}] {name:<16}  {note}")

        print()
        if available:
            names = ", ".join(n for n, _ in available)
            print(
                f"static-mode: {len(available)} input backend(s) available: {names}. "
                "(Live reach-the-game verification requires the game running.)"
            )
            rc = 0
        else:
            print(
                "static-mode: FAIL — no input backend found on this system. "
                "Install at least one of: ydotool, xdotool, gamescopectl, "
                "or build ei_inject."
            )
            rc = 1

        if args.json:
            import json
            report = {
                "static_mode": True,
                "verdict": "pass" if rc == 0 else "fail",
                "backends": [
                    {"name": name, "available": ok, "note": note}
                    for name, ok, note in backends
                ],
            }
            args.json.parent.mkdir(parents=True, exist_ok=True)
            with open(args.json, "w") as f:
                json.dump(report, f, indent=2)
            print(f"Report: {args.json}")

        return rc

    probe_script = REPO_ROOT / "tools" / "aoe3_automation" / "verified_input.py"
    if not probe_script.exists():
        print(f"ERROR: verified_input.py not found at {probe_script}",
              file=sys.stderr)
        return 2

    cmd = [sys.executable, str(probe_script), "--probe"]
    if args.json:
        cmd.extend(["--json", str(args.json)])
    proc = subprocess.run(cmd, env={**os.environ}, timeout=60)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
