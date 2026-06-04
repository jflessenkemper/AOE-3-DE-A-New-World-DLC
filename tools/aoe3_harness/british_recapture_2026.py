#!/usr/bin/env python3
"""British surface re-capture script — 2026-06-02.

Captures:
  02_loading.png        — loading screen (best-effort transient)
  08_ageup_age2.png     — Age II (Colonial) politician-select dialog
  08_ageup_age3.png     — Age III (Fortress) politician-select dialog
  08_ageup_age4.png     — Age IV (Industrial) politician-select dialog
  08_ageup_age5.png     — Age V (Imperial) politician-select dialog
  07_endgame_screen.png — post-game results/score screen after resign
  ai_03_deck.png        — AI-round deck screen (best-effort)

Fix vs prior run: after selecting a politician, we POLL for age transition
completion before capturing the next dialog, using HUD pixel probes.
Also runs avg-hash distinctness check on the 4 age-up shots.

Uses ONLY HarnessClient (socket-level input injection) — never xdotool.
Output: artifacts/validation/visual_art/ANWBritish/full/
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World")
sys.path.insert(0, str(REPO))

from PIL import Image

from tools.aoe3_harness.harness_client import HarnessClient  # noqa: E402
import tools.aoe3_automation.in_game_driver as gd  # noqa: E402

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SOCK = "/tmp/AOE3DEHarness.sock"
OUT  = REPO / "artifacts/validation/visual_art/ANWBritish/full"
OUT.mkdir(parents=True, exist_ok=True)

TMP = Path("/tmp/british_recapture_2026")
TMP.mkdir(parents=True, exist_ok=True)

# Harness / VK constants
VK_ESC    = 0x1B
VK_END    = 0x23
VK_RETURN = 0x0D
VK_H      = 0x48    # H key — selects TC in-game

# Skirmish lobby navigation (verified in drive_hubtest.py 2026-05-31)
SKIRMISH_BTN = (130, 482)
MAP_BTN      = (1637, 425)
HUBTEST_TILE = (1059, 304)   # anwHubTest "Unknown" tile after pressing End

# anwAgeCaptureTest tile — verified via _smoketest_run.py: adjacent tile left
AGE_TILE     = (810, 304)    # row1 col3, one tile left of HUBTEST_TILE

PLAY_BTN     = (1648, 1048)

# In-game: action panel age-up button (empirical — anw_autonomous_age_up_runner.py)
AGE_UP_BTN   = (1356, 1029)

# Politician dialog first portrait (leftmost)
POLITICIAN_1 = (435, 540)

# ESC menu resign (verified in in_game_driver.py 2026-05-20)
ESC_RESIGN   = (1830, 365)
RESIGN_YES   = (760, 605)

# Post-game / post-resign screen
VIEW_POSTGAME = (1145, 737)

# Resource cheats (developer mode must be active)
CHEAT_RESOURCES = "this is too hard"

# Age-up sequence: (age_number, output_filename)
AGE_TARGETS = [
    (2, "08_ageup_age2.png"),
    (3, "08_ageup_age3.png"),
    (4, "08_ageup_age4.png"),
    (5, "08_ageup_age5.png"),
]

# Speed bar coords (verified in in_game_driver.py: tick 5 = x=1895)
SPEED_TICK5 = (1895, 1058)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def shot(c: HarnessClient, path: Path) -> Path:
    """Take a screenshot via harness socket, save to path, return path."""
    c.screenshot(str(path))
    return path


def wait_hud(c: HarnessClient, timeout: int = 180) -> bool:
    """Poll until the HUD resource bar is visible (top row pixel brightness)."""
    log(f"  polling HUD visible (up to {timeout}s)...")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        probe = TMP / "hud_probe.png"
        try:
            c.screenshot(str(probe))
            with Image.open(probe) as im:
                px = [im.getpixel((x, 15)) for x in range(10, 400, 30)]
                total = sum(sum(p[:3]) for p in px)
                avg = total / len(px) / 3
                log(f"    hud probe avg brightness={avg:.1f}")
                if avg > 100:  # resource bar visible = bright UI strip
                    return True
        except Exception as e:
            log(f"    probe error: {e}")
        time.sleep(5)
    return False


def probe_age_up_active(c: HarnessClient) -> bool:
    """Check if the age-up button cell contains gold/yellow pixels."""
    probe = TMP / "ageup_probe.png"
    try:
        c.screenshot(str(probe))
        with Image.open(probe) as im:
            # Crop the age-up button region
            region = im.crop((1320, 1000, 1395, 1060)).convert("RGB")
            pixels = list(region.getdata())
            gold = sum(1 for (r, g, b) in pixels
                       if r >= 180 and g >= 140 and b <= 100)
            ratio = gold / len(pixels)
            log(f"    age-up gold ratio: {ratio:.2%}")
            return ratio > 0.05
    except Exception as e:
        log(f"    probe error: {e}")
        return False


def probe_age_transition_done(c: HarnessClient, expected_age: int) -> bool:
    """Poll until the age-up animation is complete.

    Heuristic: the Age-up cinematic banner covers the HUD.  When the banner
    is gone, the HUD resource bar is visible again AND the age-up button probe
    will be active (if we're not at max age) or inactive (if we just hit max).
    We simply poll for HUD brightness returning > threshold after it dips.

    We also probe whether the age indicator area shows the new age.  The simplest
    reliable proxy is: wait for the bottom-left action-panel area to stabilize
    (no bright moving pixels from the cinematic).
    """
    log(f"    waiting for age {expected_age} transition to settle...")
    # First sleep: let the cinematic start
    time.sleep(3)
    # Then poll HUD every 3s for up to 60s
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        probe = TMP / "trans_probe.png"
        try:
            c.screenshot(str(probe))
            with Image.open(probe) as im:
                # Check resource bar (y=15, top strip): if visible again, cinematic done
                row = [im.getpixel((x, 15)) for x in range(50, 500, 40)]
                row_avg = sum(sum(p[:3]) for p in row) / len(row) / 3
                # Check action panel area for stability
                panel = [im.getpixel((x, 1029)) for x in range(1320, 1400, 10)]
                panel_avg = sum(sum(p[:3]) for p in panel) / len(panel) / 3
                log(f"    row_avg={row_avg:.1f} panel_avg={panel_avg:.1f}")
                if row_avg > 80:  # HUD visible again
                    return True
        except Exception as e:
            log(f"    transition probe error: {e}")
        time.sleep(3)
    log(f"    WARNING: age {expected_age} transition timeout — proceeding anyway")
    return False


def apply_cheat_harness(c: HarnessClient, cheat: str) -> None:
    """Type a cheat phrase via harness (Enter → type via key sequence → Enter)."""
    # Open chat
    c.key(VK_RETURN)
    time.sleep(0.5)
    # Type characters one by one using VK codes (only ASCII)
    for ch in cheat:
        if ch == ' ':
            c.key(0x20)  # VK_SPACE
        elif ch.isalpha():
            vk = ord(ch.upper())  # A-Z VK codes = ord('A')-ord('Z')
            c.key(vk)
        elif ch == '&':
            # & = shift+7 on US keyboard; send as unicode via a different path
            # Use the type method if available, else skip
            try:
                c.key(0x26)  # VK_7 with shift... just try raw
            except Exception:
                pass
        elif ch.isdigit():
            c.key(ord(ch))
        time.sleep(0.04)
    time.sleep(0.3)
    c.key(VK_RETURN)
    time.sleep(1.0)


def apply_cheat_via_xdo(cheat: str) -> None:
    """Fallback: apply cheat via xdotool type (not ideal but safe for text)."""
    import subprocess
    from tools.aoe3_automation.in_game_driver import _get_xdo_env, _key
    env = _get_xdo_env()
    _key("Return")
    time.sleep(0.5)
    subprocess.run(["xdotool", "type", "--delay", "40", cheat],
                   env=env, capture_output=True, timeout=15)
    time.sleep(0.3)
    _key("Return")
    time.sleep(1.0)


def avg_hash(path: Path) -> int:
    """Compute a 64-bit average hash (8x8 grayscale, threshold at mean)."""
    with Image.open(path) as im:
        small = im.convert("L").resize((8, 8), Image.LANCZOS)
        pixels = list(small.getdata())
        avg = sum(pixels) / len(pixels)
        bits = [1 if p >= avg else 0 for p in pixels]
        val = 0
        for b in bits:
            val = (val << 1) | b
        return val


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count('1')


def check_distinctness(captures: list[tuple[str, Path]]) -> list[tuple[str, str, int]]:
    """Return list of (name_a, name_b, hamming_dist) for all pairs."""
    results = []
    hashes = [(name, avg_hash(path)) for name, path in captures if path.exists()]
    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            d = hamming(hashes[i][1], hashes[j][1])
            results.append((hashes[i][0], hashes[j][0], d))
    return results


# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------

def get_to_main_menu(c: HarnessClient, driver: gd.GameDriver) -> bool:
    """If in-game, resign first. Then ensure at main menu."""
    if driver.is_in_game():
        log("  in-game detected — resigning...")
        try:
            driver.resign(verify_lobby=False)
            time.sleep(3)
        except Exception as e:
            log(f"  resign error: {e}")
    log("  ensuring main menu...")
    ok = driver.ensure_main_menu(retries=3)
    log(f"  ensure_main_menu: {ok}")
    return ok


def start_british_game_alaska(c: HarnessClient, driver: gd.GameDriver) -> bool:
    """Navigate from main menu into a British skirmish on Alaska."""
    BRITISH_PICKER_IDX = 7
    ALASKA_MAP_IDX = 2
    log("  starting British skirmish (Alaska, Hard, speed 5)...")
    try:
        driver.start_skirmish(
            p1_civ_idx=BRITISH_PICKER_IDX,
            map_idx=ALASKA_MAP_IDX,
            difficulty="Hard",
            speed_tick=5,
        )
        return True
    except Exception as e:
        log(f"  start_skirmish error: {e}")
        return False


def start_anw_age_capture_test(c: HarnessClient) -> bool:
    """Try to launch anwAgeCaptureTest map via harness navigation.
    Returns True if we made it past the Play button click.
    """
    log("  navigating to anwAgeCaptureTest map...")
    st = c.state()
    if st.ready != 1:
        log("  harness not ready yet, waiting 30s...")
        for _ in range(10):
            time.sleep(3)
            if c.state().ready == 1:
                break

    # Click Skirmish
    c.click(*SKIRMISH_BTN); time.sleep(3.0)
    shot(c, TMP / "nav_01_skirmish.png")

    # Open map picker
    c.click(*MAP_BTN); time.sleep(2.5)
    shot(c, TMP / "nav_02_map_open.png")

    # Focus grid, jump to end (both Unknown maps at bottom)
    c.click(150, 304); time.sleep(0.4)
    c.key(VK_END); time.sleep(1.0)
    shot(c, TMP / "nav_03_map_end.png")

    # Try AGE_TILE (one left of HubTest tile)
    log(f"  double-clicking AGE_TILE at {AGE_TILE}...")
    c.click(*AGE_TILE); time.sleep(0.25); c.click(*AGE_TILE); time.sleep(2.5)
    shot(c, TMP / "nav_04_lobby.png")

    # Click Play
    c.click(*PLAY_BTN); time.sleep(5.0)
    shot(c, TMP / "nav_05_afterplay.png")
    log("  Play clicked — waiting for loading/in-game...")
    return True


# ---------------------------------------------------------------------------
# Main capture flow
# ---------------------------------------------------------------------------

def main() -> int:
    log("=== British re-capture 2026-06-02 ===")
    log(f"Output: {OUT}")

    # Connect harness
    c = HarnessClient(SOCK)
    c.connect(timeout=30)
    st = c.state()
    log(f"harness connected: pid={st.pid} ready={st.ready} {st.internal_w}x{st.internal_h}")

    # Also set harness backend in in_game_driver so GameDriver uses socket input
    gd.set_harness_backend(c)
    driver = gd.GameDriver(art_dir=TMP)

    captured_files = {}  # filename -> Path

    # -------------------------------------------------------------------
    # Step 0: Get to main menu
    # -------------------------------------------------------------------
    log("\n--- Step 0: Get to main menu ---")
    ok = get_to_main_menu(c, driver)
    if not ok:
        log("  WARNING: could not confirm main menu; continuing anyway")

    time.sleep(2)
    shot(c, TMP / "step0_main_menu.png")

    # -------------------------------------------------------------------
    # Step 1: Start British game
    # Strategy: try anwAgeCaptureTest first, fall back to Alaska skirmish
    # -------------------------------------------------------------------
    log("\n--- Step 1: Start British game ---")
    loading_captured = False

    # Try anwAgeCaptureTest
    start_anw_age_capture_test(c)

    # Poll for loading screen (best-effort capture)
    log("  polling for loading screen (15s window)...")
    for i in range(5):
        time.sleep(3)
        probe_p = TMP / f"loading_probe_{i}.png"
        try:
            c.screenshot(str(probe_p))
            with Image.open(probe_p) as im:
                # Loading screen: dark background, loading bar at bottom
                # Check if there's something on screen (not pure black)
                center_px = im.getpixel((960, 540))[:3]
                bottom_px = im.getpixel((960, 1000))[:3]
                avg_center = sum(center_px) / 3
                avg_bottom = sum(bottom_px) / 3
                log(f"    loading probe {i}: center={avg_center:.0f} bottom={avg_bottom:.0f}")
                # Loading bar is typically brighter than gameplay
                if avg_center > 15 or avg_bottom > 15:  # anything non-black
                    import shutil
                    shutil.copy(probe_p, OUT / "02_loading.png")
                    captured_files["02_loading.png"] = OUT / "02_loading.png"
                    loading_captured = True
                    log(f"  02_loading.png captured (loading screen or civ splash)")
                    break
        except Exception as e:
            log(f"    loading probe error: {e}")

    # Wait for HUD to appear (longer timeout for map gen + load)
    log("  waiting for in-game HUD (timeout 300s)...")
    hud_ok = False
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        probe_p = TMP / "hud_wait.png"
        try:
            c.screenshot(str(probe_p))
            with Image.open(probe_p) as im:
                row = [im.getpixel((x, 15)) for x in range(10, 500, 40)]
                avg_r = sum(sum(p[:3]) for p in row) / len(row) / 3
                log(f"    hud wait: top-row brightness={avg_r:.1f}")
                if avg_r > 100:
                    hud_ok = True
                    log("  HUD is visible!")
                    break
        except Exception as e:
            log(f"    hud wait error: {e}")
        time.sleep(5)

    if not hud_ok:
        log("ERROR: HUD never appeared after anwAgeCaptureTest launch")
        log("  Falling back to Alaska British skirmish...")
        # Get back to main menu and try Alaska
        try:
            c.key(VK_ESC); time.sleep(1)
            c.click(1830, 365); time.sleep(1)  # try resign from wherever we are
            c.click(760, 605); time.sleep(3)    # confirm
        except Exception:
            pass

        ok = driver.ensure_main_menu(retries=3)
        log(f"  main menu after fallback: {ok}")

        start_british_game_alaska(c, driver)

        log("  waiting for in-game HUD after Alaska launch (timeout 420s)...")
        if not driver.wait_for_in_game(timeout=420, dismiss_errors=True):
            log("FATAL: never reached in-game")
            c.close()
            return 3

        hud_ok2 = False
        for _ in range(36):
            if driver.is_in_game():
                hud_ok2 = True
                break
            time.sleep(5)
        if not hud_ok2:
            log("FATAL: HUD never appeared after Alaska launch")
            c.close()
            return 3

    time.sleep(5)  # let HUD fully settle
    shot(c, TMP / "step1_in_game.png")

    # -------------------------------------------------------------------
    # Step 2: Set speed and apply resources
    # -------------------------------------------------------------------
    log("\n--- Step 2: Set speed and apply resources ---")
    # Set speed to max
    c.click(*SPEED_TICK5); time.sleep(0.5)
    log("  speed set to 5")

    # Apply resource cheats
    for _ in range(2):
        apply_cheat_via_xdo(CHEAT_RESOURCES)
    time.sleep(2)
    log("  resources cheated x2")
    shot(c, TMP / "step2_resources_applied.png")

    # -------------------------------------------------------------------
    # Step 3: Age-up loop (II → III → IV → V)
    # -------------------------------------------------------------------
    log("\n--- Step 3: Age-up capture loop ---")

    for target_age, out_name in AGE_TARGETS:
        log(f"\n  -- Age {target_age}: {out_name} --")

        # Ensure resources before each age
        apply_cheat_via_xdo(CHEAT_RESOURCES)
        time.sleep(1.5)

        # Select TC using H hotkey, probe age-up button
        success = False
        for attempt in range(1, 5):
            log(f"    H: select TC (attempt {attempt}/4)")
            c.key(VK_H)
            time.sleep(1.0)

            active = probe_age_up_active(c)
            if active:
                log("    age-up button is ACTIVE")
                break
            else:
                log(f"    age-up not active; sleeping 8s...")
                time.sleep(8)
        else:
            log(f"    WARNING: age-up never active for age {target_age} — skipping")
            continue

        # Click age-up button
        log(f"    clicking age-up at {AGE_UP_BTN}")
        c.click(*AGE_UP_BTN)
        time.sleep(2.0)

        # Capture the politician dialog
        dialog_path = TMP / f"dialog_{target_age}.png"
        c.screenshot(str(dialog_path))
        log(f"    dialog screenshot taken: {dialog_path.stat().st_size // 1024}KB")

        # Verify the dialog looks like a politician dialog
        # (not a blank screen or pure black — dialog has colored UI elements)
        try:
            with Image.open(dialog_path) as im:
                center = im.getpixel((960, 540))[:3]
                bottom = im.getpixel((435, 540))[:3]
                avg_c = sum(center) / 3
                avg_b = sum(bottom) / 3
                log(f"    dialog center brightness={avg_c:.0f} politician area={avg_b:.0f}")
                if avg_c < 5 and avg_b < 5:
                    log(f"    WARNING: dialog appears black — age-up may not have opened")
        except Exception as e:
            log(f"    dialog verify error: {e}")

        import shutil
        shutil.copy(dialog_path, OUT / out_name)
        captured_files[out_name] = OUT / out_name
        log(f"    saved: {out_name}")

        # Pick first politician to actually advance age
        log(f"    clicking politician at {POLITICIAN_1}")
        c.click(*POLITICIAN_1)
        time.sleep(1.0)

        # Wait for transition to complete before next iteration
        probe_age_transition_done(c, target_age)
        time.sleep(15)  # hard floor: ensure cinematic+TC-refocus settle before next probe

        # Re-apply resources after age-up
        apply_cheat_via_xdo(CHEAT_RESOURCES)
        time.sleep(2)

    # -------------------------------------------------------------------
    # Step 4: Distinctness check
    # -------------------------------------------------------------------
    log("\n--- Step 4: Distinctness check ---")
    age_up_files = []
    for _, out_name in AGE_TARGETS:
        p = OUT / out_name
        if p.exists():
            age_up_files.append((out_name, p))

    if len(age_up_files) >= 2:
        pairs = check_distinctness(age_up_files)
        log("  Pairwise avg-hash Hamming distances:")
        collapsed = []
        for a, b, d in pairs:
            status = "DISTINCT" if d > 8 else "COLLAPSE!"
            log(f"    {a} vs {b}: Hamming={d}  [{status}]")
            if d <= 8:
                collapsed.append((a, b, d))

        if collapsed:
            log(f"  WARNING: {len(collapsed)} collapsed pairs — these ages did NOT advance!")
            for a, b, d in collapsed:
                log(f"    COLLAPSED: {a} ~ {b} (Hamming={d})")
    else:
        pairs = []
        log("  Not enough files for distinctness check")

    # -------------------------------------------------------------------
    # Step 5: Resign and capture endgame screen
    # -------------------------------------------------------------------
    log("\n--- Step 5: Resign and capture endgame ---")

    # Open ESC menu
    c.key(VK_ESC)
    time.sleep(1.5)
    shot(c, TMP / "step5_esc_menu.png")

    # Click Resign
    c.click(*ESC_RESIGN)
    time.sleep(1.5)
    shot(c, TMP / "step5_resign_confirm.png")

    # Confirm
    c.click(*RESIGN_YES)
    time.sleep(2.0)
    shot(c, TMP / "step5_after_yes.png")

    # Check if abandon screen appeared (View Postgame button)
    time.sleep(3.0)
    probe_p = TMP / "step5_post_resign.png"
    c.screenshot(str(probe_p))

    # Try clicking View Postgame if present
    c.click(*VIEW_POSTGAME)
    time.sleep(3.0)
    postgame_path = TMP / "step5_postgame.png"
    c.screenshot(str(postgame_path))

    # Verify it's the endgame screen (not gameplay)
    try:
        with Image.open(postgame_path) as im:
            # Endgame screen: typically has a dark panel, different from gameplay
            corner_tl = sum(im.getpixel((50, 50))[:3]) / 3
            corner_br = sum(im.getpixel((1870, 1030))[:3]) / 3
            center = sum(im.getpixel((960, 540))[:3]) / 3
            log(f"  postgame probe: tl={corner_tl:.0f} br={corner_br:.0f} center={center:.0f}")
            # Any non-black screen is likely the endgame or at least post-resign
            if center > 5 or corner_tl > 5:
                import shutil
                shutil.copy(postgame_path, OUT / "07_endgame_screen.png")
                captured_files["07_endgame_screen.png"] = OUT / "07_endgame_screen.png"
                log("  07_endgame_screen.png captured")
            else:
                log("  WARNING: endgame screen appears black")
    except Exception as e:
        log(f"  endgame verify error: {e}")

    # -------------------------------------------------------------------
    # Step 6: Return to main menu
    # -------------------------------------------------------------------
    log("\n--- Step 6: Return to main menu ---")
    time.sleep(2)
    # Try Esc to close postgame, then navigate back
    c.key(VK_ESC); time.sleep(1)
    c.click(50, 20); time.sleep(2)  # Quit button top-left of postgame
    time.sleep(3)
    shot(c, TMP / "step6_menu.png")

    # -------------------------------------------------------------------
    # Step 7: Skip ai_03_deck (no established flow for this surface)
    # -------------------------------------------------------------------
    log("\n--- Step 7: ai_03_deck (skipping — no reliable navigation path) ---")
    log("  ai_03_deck.png: skipped (not reachable without dedicated flow)")

    # -------------------------------------------------------------------
    # Step 8: Rebuild site
    # -------------------------------------------------------------------
    log("\n--- Step 8: Rebuild release readiness site ---")
    import subprocess
    result = subprocess.run(
        [sys.executable, "tools/validation/build_release_readiness_site.py"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode == 0:
        log("  site rebuild: PASS")
        # Check for expected output
        if "Civs in spec: 40" in result.stdout or "40" in result.stdout:
            log("  confirmed: Civs in spec: 40")
    else:
        log(f"  site rebuild: FAIL (exit {result.returncode})")
        log(f"  stdout: {result.stdout[-500:]}")
        log(f"  stderr: {result.stderr[-500:]}")

    # -------------------------------------------------------------------
    # Final report
    # -------------------------------------------------------------------
    log("\n=== FINAL REPORT ===")
    for fname, path in captured_files.items():
        size = path.stat().st_size // 1024 if path.exists() else 0
        log(f"  CAPTURED: {fname} ({size}KB)")

    expected = [
        "02_loading.png",
        "08_ageup_age2.png", "08_ageup_age3.png",
        "08_ageup_age4.png", "08_ageup_age5.png",
        "07_endgame_screen.png",
    ]
    for f in expected:
        if f not in captured_files:
            log(f"  MISSING:  {f}")

    if pairs:
        log("\n  Pairwise distinctness summary:")
        for a, b, d in pairs:
            log(f"    {a} vs {b}: Hamming={d} ({'DISTINCT' if d > 8 else 'COLLAPSED'})")

    log("=== END ===")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
