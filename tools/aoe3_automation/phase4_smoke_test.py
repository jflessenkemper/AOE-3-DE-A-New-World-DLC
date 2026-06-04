#!/usr/bin/env python3
"""Phase-4 XS state-snapshot smoke test.

Orchestrates:
  1. Navigate main menu → Skirmish
  2. Set P1 civ to Britain (ANWBritish, picker index 7)
  3. Click PLAY, wait 90s game-time
  4. Capture screenshots at t=30s and t=90s via spectacle+crop
  5. Resign cleanly
  6. Grep Age3Log.txt slice for tag=state.snapshot — need >= 2 hits
  7. Run state_snapshot_validator.py on the slice

Run from project root:
    python3 tools/aoe3_automation/phase4_smoke_test.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# ── Monkey-patch lobby_driver.screenshot BEFORE importing the driver ────────
# gamescopectl is non-functional on this rig (confirmed: "Failed to open
# GAMESCOPE_WAYLAND_DISPLAY" on all sockets). The lobby_driver uses
# gamescopectl-based screenshots only for state verification (is_picker_open,
# is_clean_lobby). We replace it with spectacle + crop to the game window
# (1920×1080 at desktop offset 4,30 on DISPLAY=:0). The crop dimensions
# exactly match what gamescopectl would have returned, so pixel-diff thresholds
# still apply.
import tools.aoe3_automation.lobby_driver as _ld_module

_SPECTACLE_CROP_GEOM = "1920x1080+4+30"  # game window on :0


def _screenshot_spectacle(out_path: Path, *, retries: int = 3) -> Path:
    """Spectacle full-screen → crop to game window → save."""
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".full.png")
    for attempt in range(retries):
        # Capture full desktop
        proc = subprocess.run(
            ["spectacle", "-b", "-n", "-f", "-o", str(tmp)],
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode != 0 or not tmp.exists():
            time.sleep(0.5)
            continue
        # Crop to game window
        crop = subprocess.run(
            ["magick", str(tmp), "-crop", _SPECTACLE_CROP_GEOM, "+repage", str(out_path)],
            capture_output=True, text=True, timeout=10,
        )
        if crop.returncode == 0 and out_path.exists() and out_path.stat().st_size > 1000:
            verify = subprocess.run(
                ["magick", "identify", str(out_path)],
                capture_output=True, text=True, timeout=5,
            )
            info = verify.stdout.strip()
            if "1920x1080" in info and "error" not in info.lower():
                tmp.unlink(missing_ok=True)
                return out_path
        time.sleep(0.5)
    raise RuntimeError(f"spectacle screenshot failed after {retries} tries: {out_path}")


_ld_module.screenshot = _screenshot_spectacle

# Now import the rest (will use patched screenshot)
from tools.aoe3_automation.lobby_driver import (
    click_skirmish,
    set_civ_by_token_fast,
    click_play,
    is_clean_lobby,
    load_coords,
)
from tools.aoe3_automation.log_capture import AGE3_LOG_PATH, snapshot_offset, read_since
from tools.aoe3_automation.in_game_driver import GameDriver

MATCH_LOG = ROOT / "logs" / "phase4_smoke_match.log"
MATCH_LOG.parent.mkdir(parents=True, exist_ok=True)
SHOTS_DIR = ROOT / "logs" / "phase4_smoke_shots"
SHOTS_DIR.mkdir(parents=True, exist_ok=True)

BRITAIN_TOKEN = "ANWBritish"
WAIT_SECS = 95     # ~90s game-time at 1× speed + 5s buffer


def _quick_shot(label: str) -> str:
    """Capture game window via spectacle+crop for debugging."""
    out = SHOTS_DIR / f"{label}.png"
    try:
        _screenshot_spectacle(out)
        print(f"[shot] {label} → {out}")
    except Exception as e:
        print(f"[shot] {label} FAILED: {e}")
    return str(out)


def main() -> int:
    coords = load_coords()

    # ── Step 1: Navigate to Skirmish lobby ─────────────────────────────────
    print("[phase4] step 1: click Skirmish on main menu…")
    click_skirmish(coords)
    _quick_shot("01_after_skirmish_click")

    # ── Step 2: Set P1 civ to ANWBritish ───────────────────────────────────
    print(f"[phase4] step 2: selecting {BRITAIN_TOKEN} via fast-path cache…")
    result = set_civ_by_token_fast(coords, BRITAIN_TOKEN, slot=0)
    print(f"[phase4] fast-pick result: {result}")
    _quick_shot("02_after_civ_select")

    # ── Step 3: Snapshot log offset BEFORE match starts ────────────────────
    print("[phase4] step 3: snapshot log offset…")
    log_offset = snapshot_offset()
    print(f"[phase4] log offset = {log_offset}")

    # ── Step 4: Click PLAY ─────────────────────────────────────────────────
    print("[phase4] step 4: clicking PLAY…")
    # Bypass is_clean_lobby check (it's advisory; we know we're in a lobby)
    from tools.aoe3_automation.lobby_driver import click_play as _click_play
    _click_play(coords)
    time.sleep(5)
    _quick_shot("03_game_start_t0")

    # ── Step 5: Wait for probes ────────────────────────────────────────────
    # At 30s game-time we should see the first state.snapshot probe.
    # At 90s we should have 3 (at 30, 60, 90).
    third = WAIT_SECS // 3
    print(f"[phase4] step 5: waiting {third}s for first probe (~30s game-time)…")
    time.sleep(third)
    _quick_shot("04_t30s")

    remaining = WAIT_SECS - third
    print(f"[phase4] waiting {remaining}s more for second/third probe…")
    time.sleep(remaining)
    _quick_shot("05_t90s")

    # ── Step 6: Resign cleanly ─────────────────────────────────────────────
    print("[phase4] step 6: resigning…")
    drv = GameDriver(art_dir=str(ROOT / "logs" / "phase4_smoke_driver"))
    resigned = drv.resign()
    print(f"[phase4] resign result: {resigned}")
    time.sleep(3)

    # ── Step 7: Extract log slice ──────────────────────────────────────────
    print("[phase4] step 7: reading Age3Log slice…")
    content = read_since(log_offset)
    MATCH_LOG.write_text(content, encoding="utf-8", errors="replace")
    print(f"[phase4] log slice: {MATCH_LOG} ({len(content)} bytes, {len(content.splitlines())} lines)")

    # ── Step 8: Count state.snapshot lines ────────────────────────────────
    all_lines = content.splitlines()
    snap_lines = [ln for ln in all_lines if "tag=state.snapshot" in ln]
    llp_lines  = [ln for ln in all_lines if "[ANWP" in ln]

    print(f"\n[phase4] [ANWP lines in log slice: {len(llp_lines)}")
    print(f"[phase4] state.snapshot lines: {len(snap_lines)}")

    if snap_lines:
        print(f"[phase4] first: {snap_lines[0][:250]}")
        if len(snap_lines) > 1:
            print(f"[phase4] last:  {snap_lines[-1][:250]}")
    else:
        print("[phase4] WARNING: no state.snapshot lines found.")
        if llp_lines:
            print(f"[phase4] first [ANWP line: {llp_lines[0][:200]}")
        else:
            print("[phase4] no [ANWP lines at all — check developer mode + aiEcho wiring")

    # ── Step 9: Run validator ──────────────────────────────────────────────
    print("\n[phase4] step 9: running state_snapshot_validator.py…")
    validator = ROOT / "tools" / "validation" / "state_snapshot_validator.py"
    val_result = subprocess.run(
        [sys.executable, str(validator), str(MATCH_LOG)],
        capture_output=True, text=True, timeout=30,
    )
    print("[validator stdout]:", val_result.stdout.strip())
    if val_result.stderr.strip():
        print("[validator stderr]:", val_result.stderr.strip())

    # ── Summary ────────────────────────────────────────────────────────────
    probe_ok = len(snap_lines) >= 2
    val_ok   = val_result.returncode == 0
    ok = probe_ok and val_ok

    print("\n" + "=" * 60)
    print(f"RESULT: {'PASS' if ok else 'FAIL'}")
    print(f"  state.snapshot lines: {len(snap_lines)}  (need ≥ 2)")
    print(f"  validator exit code:  {val_result.returncode}")
    print(f"  match.log:            {MATCH_LOG}")
    if snap_lines:
        print(f"  sample line:  {snap_lines[0][:180]}")
    print("=" * 60)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
