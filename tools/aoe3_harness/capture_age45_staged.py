#!/usr/bin/env python3
"""Staging-safe Age-Up IV/V (+ AI deck best-effort) capture for ANWBritish.

Writes ALL age-up dialogs to a STAGING dir (/tmp/anw_age45_staging), NEVER to
full/.  This makes the good, backed-up age2/age3 physically impossible to clobber.
Promotion into full/ happens in a SEPARATE manual step after visual/distinctness
verification.

Reuses proven helpers from british_recapture_2026 (navigation, probes).
Pure harness-socket input (no xdotool).  Hard self-imposed step budget.
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

REPO = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World")
sys.path.insert(0, str(REPO))

from PIL import Image  # noqa: E402

from tools.aoe3_harness.harness_client import HarnessClient  # noqa: E402
import tools.aoe3_harness.british_recapture_2026 as br  # noqa: E402
import tools.aoe3_automation.in_game_driver as gd  # noqa: E402

SOCK = "/tmp/AOE3DEHarness.sock"
STAGING = Path("/tmp/anw_age45_staging")
STAGING.mkdir(parents=True, exist_ok=True)

AGE_TARGETS = [
    (2, "stage_age2.png"),
    (3, "stage_age3.png"),
    (4, "stage_age4.png"),
    (5, "stage_age5.png"),
]


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main() -> int:
    log("=== STAGED Age-Up IV/V capture (full/ is write-protected) ===")
    c = HarnessClient(SOCK)
    c.connect(timeout=30)
    st = c.state()
    log(f"harness: pid={st.pid} ready={st.ready} {st.internal_w}x{st.internal_h}")
    if not st.ready:
        log("FATAL: harness not ready"); return 2

    gd.set_harness_backend(c)
    driver = gd.GameDriver(art_dir=STAGING)

    # Step 0: main menu
    log("--- Step 0: main menu ---")
    br.get_to_main_menu(c, driver)
    time.sleep(2)

    # Step 1: start age-capture-test map (looping resource trigger + pre-placed mil bldgs)
    log("--- Step 1: launch anwAgeCaptureTest ---")
    br.start_anw_age_capture_test(c)

    # Wait for HUD
    log("  waiting for in-game HUD (<=300s)...")
    hud_ok = False
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        p = STAGING / "hud_wait.png"
        try:
            c.screenshot(str(p))
            with Image.open(p) as im:
                row = [im.getpixel((x, 15)) for x in range(10, 500, 40)]
                avg = sum(sum(px[:3]) for px in row) / len(row) / 3
                log(f"    hud brightness={avg:.1f}")
                if avg > 100:
                    hud_ok = True; break
        except Exception as e:
            log(f"    probe err {e}")
        time.sleep(5)
    if not hud_ok:
        log("FATAL: HUD never appeared"); c.close(); return 3
    time.sleep(5)

    # Step 2: speed 5 + resources via socket cheat
    log("--- Step 2: speed5 + resources ---")
    c.click(*br.SPEED_TICK5); time.sleep(0.5)
    for _ in range(2):
        br.apply_cheat_harness(c, br.CHEAT_RESOURCES)
    time.sleep(2)

    # Step 3: age-up loop -> STAGING only
    log("--- Step 3: age-up loop (staging) ---")
    captured = {}
    for target_age, out_name in AGE_TARGETS:
        log(f"  -- Age {target_age} -> {out_name} --")
        br.apply_cheat_harness(c, br.CHEAT_RESOURCES); time.sleep(1.5)

        active = False
        for attempt in range(1, 6):
            log(f"    H select-TC attempt {attempt}/5")
            c.key(br.VK_H); time.sleep(1.0)
            if br.probe_age_up_active(c):
                active = True; log("    age-up ACTIVE"); break
            time.sleep(8)
        if not active:
            log(f"    WARN: age-up never active for age {target_age}; skip"); continue

        c.click(*br.AGE_UP_BTN); time.sleep(2.0)
        dlg = STAGING / out_name
        c.screenshot(str(dlg))
        sz = dlg.stat().st_size // 1024 if dlg.exists() else 0
        log(f"    captured {out_name} ({sz}KB)")
        captured[target_age] = dlg

        # pick first politician to advance
        c.click(*br.POLITICIAN_1); time.sleep(1.0)
        br.probe_age_transition_done(c, target_age)
        time.sleep(15)
        br.apply_cheat_harness(c, br.CHEAT_RESOURCES); time.sleep(2)

    # Step 4: distinctness across all staged shots
    log("--- Step 4: distinctness ---")
    files = [(f"age{a}", p) for a, p in captured.items() if p.exists()]
    if len(files) >= 2:
        for a, b, d in br.check_distinctness(files):
            log(f"    {a} vs {b}: Hamming={d} [{'DISTINCT' if d>8 else 'COLLAPSE'}]")

    log("=== DONE — staged files: ===")
    for a, p in captured.items():
        if p.exists():
            log(f"   age{a}: {p} ({p.stat().st_size//1024}KB)")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
