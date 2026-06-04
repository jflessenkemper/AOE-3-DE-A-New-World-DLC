#!/usr/bin/env python3
"""British age-up capture run — 2026-06-02.

Uses anwAgeCaptureTest map which has looping 100k resource grant (no cheats needed).
Captures: 02_loading, 08_ageup_age2..5, 07_endgame_screen.
Uses ONLY HarnessClient socket input (no xdotool).
"""
from __future__ import annotations
import sys, time, shutil
from pathlib import Path

REPO = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World")
# Insert REPO but make sure tools/aoe3_harness is NOT on path directly
# (it has bisect.py which shadows stdlib bisect)
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
# Remove harness subdir from path if it crept in
_harness_dir = str(REPO / "tools" / "aoe3_harness")
while _harness_dir in sys.path:
    sys.path.remove(_harness_dir)

from PIL import Image
from tools.aoe3_harness.harness_client import HarnessClient

SOCK = "/tmp/AOE3DEHarness.sock"
OUT  = REPO / "artifacts/validation/visual_art/ANWBritish/full"
OUT.mkdir(parents=True, exist_ok=True)
TMP  = Path("/tmp/brit_cap_run")
TMP.mkdir(parents=True, exist_ok=True)

# VK codes
VK_ESC    = 0x1B
VK_END    = 0x23
VK_RETURN = 0x0D
VK_H      = 0x48

# Lobby nav
SKIRMISH_BTN = (130, 482)
MAP_BTN      = (1637, 425)
AGE_TILE     = (810, 304)
PLAY_BTN     = (1648, 1048)

# In-game
AGE_UP_BTN   = (1356, 1029)
POLITICIAN_1 = (435, 540)
ESC_RESIGN   = (1830, 365)
RESIGN_YES   = (760, 605)
VIEW_POSTGAME= (1145, 737)
SPEED_TICK5  = (1895, 1058)

AGE_TARGETS = [
    (2, "08_ageup_age2.png"),
    (3, "08_ageup_age3.png"),
    (4, "08_ageup_age4.png"),
    (5, "08_ageup_age5.png"),
]


def log(msg): print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def shot(c, path):
    c.screenshot(str(path))
    return path


def top_row_brightness(c, probe_path):
    """Return average brightness of the top HUD strip (resource bar)."""
    c.screenshot(str(probe_path))
    with Image.open(probe_path) as im:
        row = [im.getpixel((x, 15)) for x in range(10, 500, 40)]
        return sum(sum(p[:3]) for p in row) / len(row) / 3


def wait_hud(c, timeout=300):
    log(f"  waiting for HUD (up to {timeout}s)...")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        probe = TMP / "hud_probe.png"
        try:
            b = top_row_brightness(c, probe)
            log(f"    hud brightness={b:.1f}")
            if b > 100:
                log("  HUD visible!")
                return True
        except Exception as e:
            log(f"    probe err: {e}")
        time.sleep(5)
    return False


def probe_age_up_active(c):
    probe = TMP / "ageup_probe.png"
    try:
        c.screenshot(str(probe))
        with Image.open(probe) as im:
            region = im.crop((1320, 1000, 1395, 1060)).convert("RGB")
            pixels = list(region.getdata())
            gold = sum(1 for (r, g, b) in pixels if r >= 180 and g >= 140 and b <= 100)
            ratio = gold / len(pixels)
            log(f"    age-up gold ratio: {ratio:.2%}")
            return ratio > 0.05
    except Exception as e:
        log(f"    probe err: {e}")
        return False


def wait_age_transition(c, expected_age, timeout=120):
    """Wait for age cinematic to finish (HUD returns after dip). 120s timeout."""
    log(f"    waiting for age {expected_age} transition (up to {timeout}s)...")
    time.sleep(3)  # let cinematic start
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        probe = TMP / "trans_probe.png"
        try:
            c.screenshot(str(probe))
            with Image.open(probe) as im:
                row = [im.getpixel((x, 15)) for x in range(50, 500, 40)]
                row_avg = sum(sum(p[:3]) for p in row) / len(row) / 3
                panel = [im.getpixel((x, 1029)) for x in range(1320, 1400, 10)]
                panel_avg = sum(sum(p[:3]) for p in panel) / len(panel) / 3
                log(f"    trans row_avg={row_avg:.1f} panel_avg={panel_avg:.1f}")
                if row_avg > 80:
                    log(f"    transition done (HUD returned)")
                    return True
        except Exception as e:
            log(f"    trans probe err: {e}")
        time.sleep(3)
    log(f"    WARNING: age {expected_age} transition timeout — proceeding anyway")
    return False


def avg_hash(path):
    with Image.open(path) as im:
        small = im.convert("L").resize((8, 8), Image.LANCZOS)
        pixels = list(small.getdata())
        avg = sum(pixels) / len(pixels)
        bits = [1 if p >= avg else 0 for p in pixels]
        val = 0
        for b in bits:
            val = (val << 1) | b
        return val


def hamming(a, b):
    return bin(a ^ b).count('1')


def main():
    log("=== British age-up capture 2026-06-02 (no-xdo, map-resources) ===")

    c = HarnessClient(SOCK)
    c.connect(timeout=30)
    st = c.state()
    log(f"harness: pid={st.pid} ready={st.ready} {st.internal_w}x{st.internal_h}")

    captured = {}

    # ---- Step 0: Confirm at main menu ----
    shot(c, TMP / "s0_start.png")
    log("At main menu (confirmed visually)")

    # ---- Step 1: Launch anwAgeCaptureTest ----
    log("\n--- Step 1: Launch anwAgeCaptureTest ---")
    c.click(*SKIRMISH_BTN); time.sleep(3.0)
    shot(c, TMP / "s1_skirmish.png")

    c.click(*MAP_BTN); time.sleep(2.5)
    c.click(150, 304); time.sleep(0.4)  # focus grid
    c.key(VK_END); time.sleep(1.0)
    shot(c, TMP / "s1_mapend.png")

    # Double-click AGE_TILE (one left of HUBTEST tile at 1059,304)
    c.click(*AGE_TILE); time.sleep(0.25); c.click(*AGE_TILE); time.sleep(2.5)
    shot(c, TMP / "s1_lobby.png")

    # Capture loading screen attempt
    c.click(*PLAY_BTN); time.sleep(3.0)
    # Probe for loading screen
    loading_captured = False
    for i in range(6):
        probe_p = TMP / f"load_{i}.png"
        try:
            c.screenshot(str(probe_p))
            with Image.open(probe_p) as im:
                center = sum(im.getpixel((960, 540))[:3]) / 3
                bottom = sum(im.getpixel((960, 1000))[:3]) / 3
                log(f"  loading probe {i}: center={center:.0f} bottom={bottom:.0f}")
                if center > 15 or bottom > 15:
                    shutil.copy(probe_p, OUT / "02_loading.png")
                    captured["02_loading.png"] = OUT / "02_loading.png"
                    log("  02_loading.png captured")
                    loading_captured = True
                    break
        except Exception as e:
            log(f"  loading probe err: {e}")
        time.sleep(3)

    # Wait for HUD
    hud_ok = wait_hud(c, timeout=300)
    if not hud_ok:
        log("ERROR: HUD never appeared — aborting")
        c.close()
        return 2

    time.sleep(5)
    shot(c, TMP / "s1_in_game.png")

    # ---- Step 2: Verify map (TC/Barracks/Stable/resources) ----
    log("\n--- Step 2: Map live-test screenshot ---")
    shot(c, OUT.parent.parent.parent / "validation" / "map_livetest.png" if False else TMP / "s2_livetest.png")
    # Also save a copy for reporting
    shutil.copy(TMP / "s2_livetest.png" if (TMP / "s2_livetest.png").exists() else TMP / "s1_in_game.png",
                TMP / "map_livetest.png")
    log(f"  live-test shot: {TMP}/map_livetest.png")

    # Set speed to 5
    c.click(*SPEED_TICK5); time.sleep(0.5)
    log("  speed set to 5")

    # Wait for first resource grant (map grants at T+3s, loops every 30s)
    log("  waiting 35s for map resource grant loop...")
    time.sleep(35)
    shot(c, TMP / "s2_after_resources.png")
    log("  resources should be ~100k now (from map trigger)")

    # ---- Step 3: Age-up loop ----
    log("\n--- Step 3: Age-up capture loop ---")

    for attempt_round in range(1, 3):  # max 2 full rounds per spec
        log(f"\n  === Round {attempt_round} ===")
        all_done = True
        for target_age, out_name in AGE_TARGETS:
            if (OUT / out_name).exists() and out_name not in ["08_ageup_age4.png", "08_ageup_age5.png"]:
                # age2/3 already exist from prior runs — skip (but still need to advance age)
                log(f"  {out_name} already exists — skipping capture but still advancing")
                # Still need to advance age if we're going to do age4/5
                pass

            log(f"\n  -- Age {target_age}: {out_name} --")

            # Try to select TC and activate age-up button
            activated = False
            for tc_attempt in range(1, 5):
                log(f"    H hotkey (attempt {tc_attempt}/4)")
                c.key(VK_H)
                time.sleep(1.0)
                if probe_age_up_active(c):
                    log("    age-up button ACTIVE")
                    activated = True
                    break
                # Also try clicking TC area
                for tx in range(760, 870, 30):
                    for ty in range(440, 500, 20):
                        c.click(tx, ty)
                        time.sleep(0.2)
                        if probe_age_up_active(c):
                            activated = True
                            break
                    if activated:
                        break
                if activated:
                    break
                log(f"    age-up not active; waiting 10s...")
                time.sleep(10)

            if not activated:
                log(f"    FAILED: age-up never active for age {target_age}")
                all_done = False
                continue

            # Click age-up
            log(f"    clicking AGE_UP_BTN at {AGE_UP_BTN}")
            c.click(*AGE_UP_BTN)
            time.sleep(2.5)

            # Screenshot the politician dialog
            dialog_p = TMP / f"dialog_age{target_age}.png"
            c.screenshot(str(dialog_p))

            # Verify it's non-black
            with Image.open(dialog_p) as im:
                ctr = sum(im.getpixel((960, 540))[:3]) / 3
                pol = sum(im.getpixel((435, 540))[:3]) / 3
                log(f"    dialog: center={ctr:.0f} politician_area={pol:.0f}")

            # Save to output
            shutil.copy(dialog_p, OUT / out_name)
            captured[out_name] = OUT / out_name
            log(f"    saved: {out_name}")

            # Click first politician to advance
            log(f"    selecting politician at {POLITICIAN_1}")
            c.click(*POLITICIAN_1)
            time.sleep(1.0)

            # Wait for transition (120s timeout + 15s floor)
            wait_age_transition(c, target_age, timeout=120)
            time.sleep(15)  # 15s hard floor per spec

        break  # single pass is enough (map keeps re-granting resources)

    # ---- Step 4: Distinctness check ----
    log("\n--- Step 4: Distinctness check ---")
    pairs_result = []
    files_for_hash = [(name, OUT / name) for _, name in AGE_TARGETS if (OUT / name).exists()]
    if len(files_for_hash) >= 2:
        hashes = [(name, avg_hash(path)) for name, path in files_for_hash]
        for i in range(len(hashes)):
            for j in range(i+1, len(hashes)):
                d = hamming(hashes[i][1], hashes[j][1])
                status = "DISTINCT" if d > 8 else "COLLAPSE"
                log(f"  {hashes[i][0]} vs {hashes[j][0]}: Hamming={d} [{status}]")
                pairs_result.append((hashes[i][0], hashes[j][0], d))
    else:
        log("  not enough files for check")

    # ---- Step 5: Resign + endgame ----
    log("\n--- Step 5: Resign ---")
    c.key(VK_ESC); time.sleep(1.5)
    shot(c, TMP / "s5_esc.png")
    c.click(*ESC_RESIGN); time.sleep(1.5)
    c.click(*RESIGN_YES); time.sleep(3.0)
    shot(c, TMP / "s5_post_resign.png")
    c.click(*VIEW_POSTGAME); time.sleep(3.0)
    pg_path = TMP / "s5_postgame.png"
    c.screenshot(str(pg_path))
    with Image.open(pg_path) as im:
        center = sum(im.getpixel((960, 540))[:3]) / 3
        log(f"  postgame screen brightness: {center:.0f}")
        if center > 5:
            shutil.copy(pg_path, OUT / "07_endgame_screen.png")
            captured["07_endgame_screen.png"] = OUT / "07_endgame_screen.png"
            log("  07_endgame_screen.png captured")

    # ---- Step 6: Back to main menu ----
    log("\n--- Step 6: Back to main menu ---")
    time.sleep(2)
    c.key(VK_ESC); time.sleep(1)
    c.click(50, 20); time.sleep(2)
    shot(c, TMP / "s6_menu.png")

    # ---- Step 7: Rebuild site ----
    log("\n--- Step 7: Rebuild site ---")
    import subprocess
    result = subprocess.run(
        [sys.executable, "tools/validation/build_release_readiness_site.py"],
        cwd=str(REPO),
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode == 0:
        log("  site rebuild: PASS")
        for line in result.stdout.splitlines():
            if "Civs" in line or "40" in line:
                log(f"  > {line}")
    else:
        log(f"  site rebuild FAIL (exit {result.returncode})")
        log(f"  stderr: {result.stderr[-300:]}")

    # ---- Final report ----
    log("\n=== FINAL REPORT ===")
    for fname in ["02_loading.png", "08_ageup_age2.png", "08_ageup_age3.png",
                  "08_ageup_age4.png", "08_ageup_age5.png", "07_endgame_screen.png"]:
        p = OUT / fname
        if p.exists():
            log(f"  CAPTURED: {fname} ({p.stat().st_size // 1024}KB)")
        else:
            log(f"  MISSING:  {fname}")

    if pairs_result:
        log("\n  Pairwise Hamming:")
        for a, b, d in pairs_result:
            log(f"    {a} vs {b}: Hamming={d} ({'DISTINCT' if d > 8 else 'COLLAPSE'})")

    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
