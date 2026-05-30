"""harness_capture.py — Single-civ readiness capture driven by the harness socket.

CLI:
    python3 -m tools.aoe3_harness.harness_capture --civ ANWBritish

Flow:
    1. Launch AOE3DEHarness + game via harness_launch().
    2. wait_for_ready() — polls until the inner window is compositing.
    3. Wire both lobby_driver and in_game_driver to the socket backend.
    4. Dismiss the weekly reward popup (blind-click, harmless if absent).
    5. Navigate the lobby: Skirmish → select civ (socket-driven clicks).
       - Scroll still uses xdotool (no WHEEL socket command yet; see BLOCKER
         comment below).  A warning is logged for each scroll call.
    6. Capture full/01_lobby.png.
    7. Click PLAY.
    8. Capture full/02_loading.png (~13 s into loading screen).
    9. Quit harness and terminate the process.

Output:  artifacts/validation/visual_art/<CIV>/full/01_lobby.png
                                                      full/02_loading.png

BLOCKER (scroll):
    The AOE3DEHarness control socket has NO WHEEL command.  Civ selection
    via set_civ_by_token_fast() requires wheel-down to scroll the picker.
    Those scroll calls fall back to xdotool (which still works because the
    nested Xwayland window is reachable for scroll events).  If xdotool is
    unavailable in the run environment, only civs that appear in the top
    visible rows without any scrolling can be selected.

    TODO(harness): add ``WHEEL dx dy`` to harness_socket.cpp +
                   harness_input.h/cpp to make civ-selection fully socket-driven.
"""
from __future__ import annotations

import argparse
import logging
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ARTIFACTS_ROOT = Path(__file__).resolve().parents[2] / "artifacts" / "validation" / "visual_art"

# Seconds to sleep after click_play before capturing the loading screen.
# Targets the middle of the loading screen animation (~13 s in).
LOADING_SCREEN_SLEEP = 13.0

# Seconds to allow wait_for_ready() to detect the first composited frame.
HARNESS_READY_TIMEOUT = 90.0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_screenshot(label: str, out_path: Path, warnings: list) -> bool:
    """Take a screenshot; append any failure message to warnings. Returns True on success."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from tools.aoe3_automation.lobby_driver import screenshot as ldr_screenshot
        ldr_screenshot(out_path)
        if not out_path.exists() or out_path.stat().st_size < 1000:
            warnings.append(f"{label}:file_missing_or_empty")
            return False
        log.info("captured %s → %s", label, out_path)
        return True
    except Exception as exc:
        warnings.append(f"{label}:exception:{exc!r}")
        log.warning("screenshot failed for %s: %s", label, exc)
        return False


# ---------------------------------------------------------------------------
# Core capture routine
# ---------------------------------------------------------------------------


def run_capture(civ_token: str, *, skip_play: bool = False) -> int:
    """Launch harness, navigate lobby, capture readiness screenshots.

    Args:
        civ_token:  ANW civ token, e.g. ``"ANWBritish"``.
        skip_play:  If True, stop after capturing 01_lobby.png (no in-game).

    Returns:
        0 on full success, 1 if any captures failed, 2 on fatal launch error.
    """
    from tools.aoe3_harness.harness_launch import harness_launch
    from tools.aoe3_automation import lobby_driver as ldr
    from tools.aoe3_automation import in_game_driver as igd

    warnings: list[str] = []
    proc: Optional[subprocess.Popen] = None
    client = None

    civ_dir = ARTIFACTS_ROOT / civ_token
    full_dir = civ_dir / "full"
    full_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ── 1. Launch ─────────────────────────────────────────────────────────
        log.info("Launching AOE3DEHarness for civ %s …", civ_token)
        proc, client = harness_launch()

        # ── 2. Wait for game to reach the main menu ────────────────────────────
        log.info("Waiting for harness ready (timeout=%ss) …", HARNESS_READY_TIMEOUT)
        try:
            state = client.wait_for_ready(timeout=HARNESS_READY_TIMEOUT)
            log.info("Harness ready: pid=%d w=%d h=%d", state.pid, state.internal_w, state.internal_h)
        except Exception as exc:
            log.error("Harness never became ready: %s", exc)
            return 2

        # ── 3. Wire harness backend to both drivers ────────────────────────────
        ldr.set_harness_backend(client)
        igd.set_harness_backend(client)
        log.info("Harness backend wired to lobby_driver and in_game_driver.")

        # ── 4. Dismiss weekly reward popup (blind-click, harmless if absent) ───
        log.info("Dismissing weekly popup (if present) …")
        try:
            ldr.dismiss_weekly_popup(settle_pre=10.0, settle_inter=1.2, settle_post=1.0)
        except Exception as exc:
            warnings.append(f"dismiss_weekly_popup:{exc!r}")
            log.warning("dismiss_weekly_popup failed (non-fatal): %s", exc)

        # ── 5. Navigate to the Skirmish lobby and select civ ──────────────────
        coords = ldr.load_coords()

        log.info("Clicking Skirmish button …")
        try:
            ldr.click_skirmish(coords)
        except Exception as exc:
            warnings.append(f"click_skirmish:{exc!r}")
            log.error("click_skirmish failed: %s — aborting", exc)
            return 2

        log.info("Selecting civ %s via fast path …", civ_token)
        try:
            result = ldr.set_civ_by_token_fast(coords, civ_token)
            if not result.get("ok"):
                log.warning(
                    "set_civ_by_token_fast failed (%s); falling back to verified path.",
                    result.get("error"),
                )
                # Attempt the OCR-backed verified path as fallback.
                from tools.aoe3_automation.lobby_driver import set_civ_by_token_verified
                civ_order = ldr.get_civ_order()
                # build a minimal ref dict for OCR matching
                ref: dict = {"civ_names": civ_order}
                result = set_civ_by_token_verified(coords, civ_token, ref)
                if not result.get("ok"):
                    warnings.append(f"set_civ_both_paths_failed:{result!r}")
                    log.error("Both fast and verified civ-selection paths failed. Capturing lobby anyway.")
        except Exception as exc:
            warnings.append(f"set_civ:{exc!r}")
            log.error("Civ selection raised an exception: %s", exc)

        # ── 6. Capture 01_lobby ───────────────────────────────────────────────
        time.sleep(1.5)
        _safe_screenshot("01_lobby", full_dir / "01_lobby.png", warnings)

        if skip_play:
            log.info("--skip-play set; stopping after 01_lobby capture.")
            status = 0 if not warnings else 1
            _print_summary(civ_token, full_dir, warnings, status)
            return status

        # ── 7. Click PLAY ─────────────────────────────────────────────────────
        log.info("Clicking PLAY …")
        try:
            ldr.click_play(coords)
            time.sleep(2.0)
        except Exception as exc:
            warnings.append(f"click_play:{exc!r}")
            log.error("click_play failed: %s", exc)
            _print_summary(civ_token, full_dir, warnings, 1)
            return 1

        # ── 8. Capture 02_loading (~13 s into loading screen) ─────────────────
        log.info("Sleeping %ss for loading screen …", LOADING_SCREEN_SLEEP)
        time.sleep(LOADING_SCREEN_SLEEP)
        _safe_screenshot("02_loading", full_dir / "02_loading.png", warnings)

        status = 0 if not warnings else 1
        _print_summary(civ_token, full_dir, warnings, status)
        return status

    finally:
        # ── 9. Teardown ───────────────────────────────────────────────────────
        ldr.set_harness_backend(None)
        igd.set_harness_backend(None)
        if client is not None:
            try:
                client.quit()
            except Exception:
                pass
            client.close()
        if proc is not None and proc.poll() is None:
            log.info("Terminating AOE3DEHarness (PID %d) …", proc.pid)
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=8.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                log.warning("SIGKILL sent to PID %d", proc.pid)


def _print_summary(civ_token: str, full_dir: Path, warnings: list, status: int) -> None:
    log.info("=== Capture summary for %s ===", civ_token)
    for fn in ["01_lobby.png", "02_loading.png"]:
        p = full_dir / fn
        if p.exists():
            log.info("  OK  %s  (%d bytes)", fn, p.stat().st_size)
        else:
            log.info("  MISS %s", fn)
    if warnings:
        log.warning("Warnings (%d):", len(warnings))
        for w in warnings:
            log.warning("  %s", w)
    log.info("Exit status: %d", status)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python3 -m tools.aoe3_harness.harness_capture",
        description=(
            "Single-civ readiness capture driven by the AOE3DEHarness control socket. "
            "Launches the game, selects a civ in the lobby, and captures "
            "full/01_lobby.png (and optionally full/02_loading.png)."
        ),
    )
    p.add_argument(
        "--civ",
        required=True,
        metavar="CIV_TOKEN",
        help="ANW civ token to capture (e.g. ANWBritish, ANWAztecs).",
    )
    p.add_argument(
        "--skip-play",
        action="store_true",
        default=False,
        help="Stop after capturing 01_lobby.png (no in-game launch).",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    sys.exit(run_capture(args.civ, skip_play=args.skip_play))


if __name__ == "__main__":
    main()
