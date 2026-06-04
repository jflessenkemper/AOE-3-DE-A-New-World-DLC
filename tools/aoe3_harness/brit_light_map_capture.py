#!/usr/bin/env python3
"""British age-up capture on a light standard 1v1 skirmish map.

Strategy:
- STOCK map: open map picker, Up×60 to top, pick first tile (alphabetically
  first stock map, e.g. "Amazon" or similar).  NOT anwHubTest/anwAgeCaptureTest.
- 1 AI opponent only.
- Staging dir: artifacts/validation/visual_art/ANWBritish/_staging/
- Only copies to full/ after 16x16 avg-hash distinctness verification (Hamming >15).
- Freeze detection: two consecutive identical screenshots ~20s apart => STOP.

Input: ONLY harness socket (HarnessClient). No xdotool/gamescopectl.
Verified coords from british_hubtest_capture.py (2026-05-31).
"""
from __future__ import annotations

import hashlib
import shutil
import sys
import time
from pathlib import Path

REPO = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World")
sys.path.insert(0, str(REPO))

from PIL import Image
from tools.aoe3_harness.harness_client import HarnessClient

SOCK   = "/tmp/AOE3DEHarness.sock"
STAGE  = REPO / "artifacts/validation/visual_art/ANWBritish/_staging"
FULL   = REPO / "artifacts/validation/visual_art/ANWBritish/full"
TMP    = Path("/tmp/brit_light_cap")

STAGE.mkdir(parents=True, exist_ok=True)
FULL.mkdir(parents=True, exist_ok=True)
TMP.mkdir(parents=True, exist_ok=True)

# VK codes
VK_ESC    = 0x1B
VK_RETURN = 0x0D
VK_END    = 0x23
VK_UP     = 0x26
VK_DOWN   = 0x28
VK_SPACE  = 0x20
VK_H      = 0x48

# UI coords — verified from british_hubtest_capture.py (2026-05-31)
SKIRMISH_BTN   = (130, 482)
MAP_BTN        = (1637, 425)
PLAY_BTN       = (1650, 1037)  # verified from lobby screenshot 2026-06-02
P1_CIV_FLAG    = (630, 170)
PICKER_OK      = (215, 962)     # civ picker OK button
MAP_OK         = (240, 976)     # map picker OK (from in_game_driver)
# AGE_UP_BTN: task spec says (57,895) — bottom-LEFT action panel, not bottom-right
# Standard AoE3 action panel is at x=0-390, y=880-1080 (bottom-left)
AGE_UP_BTN     = (57, 895)
POLITICIAN_1   = (220, 540)     # politician dialog first card (verified from good backup: x≈170-270)
ACCEPT_BTN     = (760, 978)   # Age-up accept button — verified from good backup: y≈976-982
ESC_RESIGN     = (1830, 365)
RESIGN_YES     = (760, 605)
SPEED_TICK5    = (1895, 1058)
# TC building location on Alaska map (center of TC, from 02_in_game.png visual)
TC_CLICK       = (480, 390)

# British = picker idx 3 (0=Random, 1=Argentines, 2=Bourbon France, 3=British Empire)
BRITISH_CIV_IDX = 3

# Use "coinage" (food+coin) and "lumberjack" (wood) — proven to work in capture_final2.py
# "this is too hard" may have VK mapping issues
CHEATS_CYCLE = ["coinage", "coinage", "coinage", "lumberjack", "lumberjack", "lumberjack"]

AGE_TARGETS = [
    (2, "age2.png"),
    (3, "age3.png"),
    (4, "age4.png"),
    (5, "age5.png"),
]

# Existing good full/ files (PROTECTED — never overwrite with non-distinct shots)
GOOD_EXISTING = {
    "age2": FULL / "08_ageup_age2.png",
    "age3": FULL / "08_ageup_age3.png",
}

FULL_NAMES = {
    "age2.png": "08_ageup_age2.png",
    "age3.png": "08_ageup_age3.png",
    "age4.png": "08_ageup_age4.png",
    "age5.png": "08_ageup_age5.png",
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def shot(c: HarnessClient, path: Path) -> Path:
    c.screenshot(str(path))
    return path


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def avg_hash_16(path: Path) -> int:
    """16x16 avg-hash (256 bits)."""
    with Image.open(path) as im:
        small = im.convert("L").resize((16, 16), Image.LANCZOS)
        pixels = list(small.getdata())
        avg = sum(pixels) / len(pixels)
        bits = [1 if p >= avg else 0 for p in pixels]
        val = 0
        for b in bits:
            val = (val << 1) | b
        return val


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count('1')


def is_politician_dialog(path: Path) -> bool:
    """Detect real politician dialog vs terrain/gameplay.

    The dialog overlays the game with a dark semi-transparent vignette.
    Key signals:
    1. The outer game area (e.g. x=50, y=200) becomes very DARK (vignette effect)
       — in real dialog: avg < 60; in terrain: avg > 80
    2. Title strip (y≈70, center strip) has bright gold "SELECT A ... POLITICIAN" text
       — in real dialog: avg > 100; in terrain: usually < 80 (sky or dark)
    3. Panel interior (y=540, x=200-800) is medium gray-brown panel background
       — in real dialog: avg 40-120; in terrain: varies widely
    Both signals must agree for reliable detection.
    """
    with Image.open(path) as im:
        # Signal 1: outer left edge darkened by vignette (real dialog → dark)
        edge_pixels = [im.getpixel((50, y))[:3] for y in range(180, 280, 10)]
        edge_avg = sum(sum(px) / 3 for px in edge_pixels) / len(edge_pixels)

        # Signal 2: title bar at top of dialog (bright gold text on dark background)
        # The title "SELECT A ... POLITICIAN" sits at y≈80 (verified from backup)
        title_pixels = [im.getpixel((x, 80))[:3] for x in range(400, 1500, 50)]
        title_avg = sum(sum(px) / 3 for px in title_pixels) / len(title_pixels)

        # Signal 3: panel header band (dark brownish wood panel at y=50-100, x=100-1800)
        header_pixels = [im.getpixel((x, 50))[:3] for x in range(100, 1800, 100)]
        header_avg = sum(sum(px) / 3 for px in header_pixels) / len(header_pixels)

        log(f"    dialog check: edge_avg={edge_avg:.0f} title_avg={title_avg:.0f} header_avg={header_avg:.0f}")

        # Real politician dialog: edge dark (<70), title VERY bright (>130, verified=156),
        # header dark (<50, verified=28)
        # QuickSave error: title=116 (fails >130 threshold), header=96 (fails <50 threshold)
        # Terrain: edge bright (>80, fails)
        edge_dark = edge_avg < 70
        title_very_bright = title_avg > 130
        header_very_dark = header_avg < 50

        # All 3 must agree for reliable detection (no 2/3 fallback — too many false positives)
        signals = sum([edge_dark, title_very_bright, header_very_dark])
        log(f"    dialog signals: edge_dark={edge_dark} title_bright={title_very_bright} header_dark={header_very_dark} -> {signals}/3")
        return signals >= 3


def detect_freeze(c: HarnessClient, wait_s: int = 20) -> bool:
    """Two screenshots wait_s apart; identical md5 = frozen."""
    p1 = TMP / "freeze_a.png"
    p2 = TMP / "freeze_b.png"
    c.screenshot(str(p1))
    time.sleep(wait_s)
    c.screenshot(str(p2))
    frozen = (md5(p1) == md5(p2))
    log(f"  freeze check: {'FROZEN' if frozen else 'alive'}")
    return frozen


def type_cheat(c: HarnessClient, cheat: str) -> None:
    """Type cheat phrase via harness only: Enter → chars → Enter.

    Uses longer pre/post delays to ensure chat box is open/closed.
    Mirrors british_hubtest_capture.py: key(VK_RETURN, 0.8); type_text; key(VK_RETURN, 1.5)
    """
    c.key(VK_RETURN)
    time.sleep(1.0)  # wait for chat to open
    for ch in cheat:
        if ch == ' ':
            c.key(VK_SPACE)
        elif ch.isalpha():
            c.key(ord(ch.upper()))
        elif ch.isdigit():
            c.key(ord(ch))
        time.sleep(0.05)
    time.sleep(0.5)
    c.key(VK_RETURN)
    time.sleep(2.0)  # wait for cheat to apply and chat to close


def apply_cheats(c: HarnessClient) -> None:
    """Apply coinage×3 + lumberjack×3 to give ample resources."""
    log("  applying cheats: coinage×3 + lumberjack×3")
    for cheat in ["coinage", "coinage", "coinage", "lumberjack", "lumberjack", "lumberjack"]:
        type_cheat(c, cheat)
    time.sleep(2)
    # Verify cheats by reading resource bar (top strip has resource numbers)
    p = TMP / "cheat_verify.png"
    c.screenshot(str(p))
    with Image.open(p) as im:
        # Resource area is at top y=5-25; numbers show when cheats work
        top_strip = [im.getpixel((x, 12))[:3] for x in range(50, 600, 20)]
        top_avg = sum(sum(px) / 3 for px in top_strip) / len(top_strip)
        log(f"  cheats applied; resource bar top_avg={top_avg:.0f}")
    shutil.copy(p, TMP / f"after_cheat_{int(time.time())%1000}.png")


def wait_hud(c: HarnessClient, timeout: int = 300) -> bool:
    """Wait for in-game HUD resource bar to appear.

    The in-game HUD has:
    - Top-left dark strip with resource icons at y=5-25
    - Top-center Age indicator strip (darker than menu)
    - Bottom-left action panel (dark)
    - The game TERRAIN visible at mid-screen y=200-600

    Main menu does NOT have terrain at y=300, x=500-1400 (has the dock/city background).
    In-game terrain: bright variable (grass, ground) at y=300, x=500-900.

    Wait for LOADING screen first (very dark), then game HUD.
    """
    log(f"  waiting for HUD (timeout {timeout}s)...")
    deadline = time.monotonic() + timeout
    loading_seen = False

    while time.monotonic() < deadline:
        p = TMP / "hud_probe.png"
        try:
            c.screenshot(str(p))
            with Image.open(p) as im:
                # Check for loading screen (very dark overall)
                center_row = [im.getpixel((x, 540))[:3] for x in range(200, 1800, 100)]
                center_avg = sum(sum(px) / 3 for px in center_row) / len(center_row)

                # Check for game terrain at mid-screen (y=350, x=400-900)
                terrain_row = [im.getpixel((x, 350))[:3] for x in range(400, 900, 50)]
                terrain_avg = sum(sum(px) / 3 for px in terrain_row) / len(terrain_row)

                # Check resource bar at y=10 (in-game: dark icons; menu: different)
                hud_row = [im.getpixel((x, 10))[:3] for x in range(10, 200, 20)]
                hud_avg = sum(sum(px) / 3 for px in hud_row) / len(hud_row)

                log(f"    hud probe: center={center_avg:.0f} terrain={terrain_avg:.0f} hud={hud_avg:.0f}")

                if center_avg < 20:
                    loading_seen = True
                    log("    loading screen detected")

                # In-game: terrain bright (>60) AND hud bar visible (>20) AND loading was seen
                # OR just terrain very bright with action panel at bottom
                if loading_seen and terrain_avg > 60 and hud_avg > 20:
                    log("    HUD confirmed (post-loading, terrain visible)")
                    return True

                # Also accept without loading_seen if terrain is clearly game-like
                # and we're well past the main menu (terrain >80, hud >40)
                if terrain_avg > 80 and hud_avg > 40:
                    log("    HUD confirmed (terrain+hud bright)")
                    return True

        except Exception as e:
            log(f"    hud probe error: {e}")
        time.sleep(6)
    return False


def wait_politician_dialog(c: HarnessClient, timeout: int = 30) -> bool:
    """Wait for politician dialog using same detection as is_politician_dialog()."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        p = TMP / "pol_probe.png"
        c.screenshot(str(p))
        if is_politician_dialog(p):
            return True
        time.sleep(3)
    return False


def wait_age_transition(c: HarnessClient, timeout: int = 120) -> bool:
    """Wait for age cinematic to finish: top strip row_avg > 80."""
    log(f"  waiting for age transition (timeout {timeout}s)...")
    time.sleep(5)  # let cinematic begin
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        p = TMP / "trans_probe.png"
        try:
            c.screenshot(str(p))
            with Image.open(p) as im:
                row = [im.getpixel((x, 15)) for x in range(50, 500, 40)]
                avg = sum(sum(px[:3]) for px in row) / len(row) / 3
                log(f"    trans hud_avg={avg:.1f}")
                if avg > 80:
                    return True
        except Exception as e:
            log(f"    trans probe error: {e}")
        time.sleep(4)
    log("  WARNING: transition timeout — proceeding anyway")
    return False


def click_tc(c: HarnessClient) -> None:
    """Select TC: H hotkey (centers camera) then click TC building.

    TC_CLICK = (480, 390) observed from 02_in_game.png on Alaska map.
    Also try grid scan y=430-490, x=430-550.
    """
    # H hotkey: centers camera on TC
    c.key(VK_H)
    time.sleep(1.5)

    # Click TC building directly
    c.move(*TC_CLICK)
    time.sleep(0.1)
    c.click(*TC_CLICK)
    time.sleep(1.0)

    # Also try a small grid scan around TC in case initial position differs
    for dx, dy in [(0, 0), (-20, 0), (20, 0), (0, -20), (0, 20)]:
        x, y = TC_CLICK[0] + dx, TC_CLICK[1] + dy
        c.click(x, y)
        time.sleep(0.3)
        p = TMP / "tc_scan.png"
        c.screenshot(str(p))
        # Quick check: if action panel appeared (bottom-left has icons)
        with Image.open(p) as im:
            panel_row = [im.getpixel((x2, 980))[:3] for x2 in range(10, 300, 20)]
            panel_avg = sum(sum(px) / 3 for px in panel_row) / len(panel_row)
        if panel_avg > 30:  # panel has content
            log(f"    TC selected at ({x},{y}), panel_avg={panel_avg:.0f}")
            break


def probe_age_up_active(c: HarnessClient) -> bool:
    """Check if age-up button is active in the bottom-left action panel.

    AGE_UP_BTN = (57, 895). Check a small region around it for gold pixels.
    Also check if the action panel itself is visible (not empty).
    """
    p = TMP / "ageup_probe.png"
    try:
        c.screenshot(str(p))
        with Image.open(p) as im:
            # Check age-up button region (57, 895) ± 30px
            region = im.crop((27, 865, 90, 928)).convert("RGB")
            pixels = list(region.getdata())
            gold = sum(1 for r, g, b in pixels if r >= 160 and g >= 120 and b <= 100)
            ratio = gold / len(pixels)
            log(f"    age-up gold ratio (action panel)={ratio:.2%}")

            # Also check overall action panel brightness (x=10-390, y=900-1040)
            panel_region = im.crop((10, 900, 390, 1040)).convert("RGB")
            panel_pixels = list(panel_region.getdata())
            panel_avg = sum(r + g + b for r, g, b in panel_pixels) / len(panel_pixels) / 3
            log(f"    action panel avg brightness={panel_avg:.1f}")

            return ratio > 0.03 or panel_avg > 20
    except Exception as e:
        log(f"    age-up probe error: {e}")
        return False


def detect_popup(path: Path) -> bool:
    """Return True if the Weekly Profile Picture popup is visible.

    The CLOSE button (gold/yellow at bottom-left of dialog) is at approximately
    y≈306-318, x≈130-270 and emits gold pixels (R>140, G>120, B<130).
    """
    with Image.open(path) as im:
        # Sample the gold CLOSE button region
        gold_count = 0
        for y in range(300, 325):
            for x in range(135, 280, 5):
                r, g, b = im.getpixel((x, y))[:3]
                if r > 140 and g > 120 and b < 130:
                    gold_count += 1
        log(f"  popup gold count in close-button region: {gold_count}")
        return gold_count > 60


def is_in_game_or_postgame(path: Path) -> bool:
    """Return True if we're in-game or post-game (not main menu).

    Key signal: In-game HUD has a dark top bar across the full width (y=0-30).
    - In-game: top-center (y=20, x=700-1200) is DARK (<60) — the dark HUD bar
    - Main menu: top-center (y=20, x=700-1200) is BRIGHT (>100) — city background

    Second signal: left sidebar.
    - Main menu: x=0-240 has a semi-transparent dark panel (avg ~30-70)
    - In-game resign screen: x=0-240 at y=200-400 is terrain (avg >60)
    """
    with Image.open(path) as im:
        # Signal 1: top-center dark bar (in-game HUD)
        hud_row = [im.getpixel((x, 20))[:3] for x in range(700, 1200, 50)]
        hud_avg = sum(sum(px) / 3 for px in hud_row) / len(hud_row)

        # Signal 2: left sidebar at y=200-400
        sidebar_pixels = [im.getpixel((x, y))[:3]
                          for x in range(20, 120, 20)
                          for y in range(200, 400, 40)]
        sidebar_avg = sum(sum(px) / 3 for px in sidebar_pixels) / len(sidebar_pixels)

        log(f"  state check: hud_top_avg={hud_avg:.0f} sidebar_avg={sidebar_avg:.0f}")
        # In-game: hud_top is dark (<60) — the HUD bar
        # In post-game resign: hud_top is also darkish (terrain/overlay ~50-80)
        # Main menu: hud_top is bright (>100) city background
        return hud_avg < 80


def escape_to_main_menu(c: HarnessClient) -> bool:
    """If in-game or post-game, click Quit from ESC menu to return to main menu.

    ESC menu top-right buttons (observed from resign_esc.png):
    - Resign ≈ (1856, 169)
    - Quit   ≈ (1856, 182)

    Post-game score panel top-right buttons (observed from resign_done.png):
    - View Postgame ≈ (1856, 75)
    - Restart ≈ (1856, 96)
    - Options ≈ (1856, 111)
    - Quit    ≈ (1856, 133)
    """
    p = TMP / "state_check.png"
    c.screenshot(str(p))

    if not is_in_game_or_postgame(p):
        log("  already at main menu")
        return True

    log("  in-game/post-game detected — attempting to quit to main menu")

    # Try ESC to open in-game ESC menu (works in active game)
    c.key(VK_ESC)
    time.sleep(2.0)
    shot(c, TMP / "esc_menu.png")

    # Click Quit in ESC menu (top-right, observed at ~y=182)
    c.click(1856, 182)
    time.sleep(2.0)
    shot(c, TMP / "after_quit_esc.png")

    # Check if quit-to-main-menu confirmation appeared — click Yes (center/OK)
    c.click(960, 600)  # typical confirm dialog Yes button
    time.sleep(3.0)
    shot(c, TMP / "after_quit_confirm.png")

    # If post-game resign screen was shown: the Quit button in score panel ≈ (1856, 133)
    c.click(1856, 133)
    time.sleep(2.0)
    shot(c, TMP / "after_score_quit.png")

    # Final ESC spam to return from any modal
    for _ in range(3):
        c.key(VK_ESC)
        time.sleep(1.5)

    # Final check
    p2 = TMP / "state_check2.png"
    c.screenshot(str(p2))
    still_in_game = is_in_game_or_postgame(p2)
    if still_in_game:
        log("  WARNING: still appears to be in-game after escape attempts")
    else:
        log("  successfully returned to main menu")
    return not still_in_game


def dismiss_popup_if_present(c: HarnessClient) -> None:
    """Dismiss 'Free Weekly Profile Picture' popup if present.

    ESC key dismisses it reliably (tested 2026-06-02).
    """
    p = TMP / "popup_check.png"
    c.screenshot(str(p))
    if detect_popup(p):
        log("  popup detected — pressing ESC to dismiss")
        c.key(VK_ESC)
        time.sleep(2.0)
        p2 = TMP / "popup_after.png"
        c.screenshot(str(p2))
        if detect_popup(p2):
            log("  still visible — pressing ESC again")
            c.key(VK_ESC)
            time.sleep(1.5)
        else:
            log("  popup dismissed successfully via ESC")
    else:
        log("  no popup detected")


def find_skirmish_y(c: HarnessClient) -> int:
    """Find the y-coordinate of the Skirmish button.

    When 'Continue' is present at top of menu, all buttons shift down by ~62px.
    Without Continue: Skirmish ≈ y=482.
    With Continue: Skirmish ≈ y=544.
    Detect by checking if y≈432-442 has a bright button (= Continue present).
    """
    p = TMP / "menu_scan.png"
    c.screenshot(str(p))
    with Image.open(p) as im:
        # Continue button text is at x≈50-80, y≈430-445
        b1 = sum(im.getpixel((60, 435))[:3]) / 3
        b2 = sum(im.getpixel((70, 437))[:3]) / 3
        continue_brightness = max(b1, b2)
        log(f"  Continue button brightness: {continue_brightness:.0f}")
        if continue_brightness > 100:
            # With Continue: Skirmish verified at y=500 (2026-06-02 pixel test)
            log("  Continue button present — Skirmish at y=500")
            return 500
        else:
            log("  No Continue — Skirmish at y=482")
            return 482


def is_skirmish_lobby(c: HarnessClient) -> bool:
    """Return True if current screen appears to be the Skirmish lobby (not Multiplayer).

    The Skirmish lobby has a British/civ flag at approx (630, 170) and a
    dark sidebar on the left.  Multiplayer shows a blue Online/LAN button.
    """
    p = TMP / "lobby_check.png"
    c.screenshot(str(p))
    with Image.open(p) as im:
        # Multiplayer screen has 'ONLINE' text button at top-right ~(1870, 47)
        # which is light-blue. Skirmish lobby does NOT have this.
        # Check: if pixel at (1850, 47) is blue-ish -> Multiplayer
        r, g, b = im.getpixel((1850, 47))[:3]
        is_mp = (b > r + 20 and b > 100)
        log(f"  lobby check: (1850,47)={r},{g},{b} is_multiplayer={is_mp}")
        return not is_mp


def navigate_to_stock_skirmish(c: HarnessClient) -> bool:
    """Navigate from main menu into a British skirmish on first stock map."""
    # Step A: Skirmish
    skirmish_y = find_skirmish_y(c)
    log(f"  A: clicking Skirmish at (130, {skirmish_y})...")
    c.move(130, skirmish_y)
    time.sleep(0.1)
    c.click(130, skirmish_y)
    time.sleep(3.5)
    shot(c, TMP / "nav_A_skirmish.png")

    # Verify we landed in Skirmish lobby (not Multiplayer)
    if not is_skirmish_lobby(c):
        log("  ERROR: did not land in Skirmish lobby — pressing ESC and retrying")
        c.key(VK_ESC)
        time.sleep(1.5)
        # Try again with a different y
        for y_try in [500, 495, 505, 508]:
            log(f"  retry Skirmish click at y={y_try}")
            c.move(130, y_try); time.sleep(0.1)
            c.click(130, y_try); time.sleep(3.0)
            if is_skirmish_lobby(c):
                log(f"  Skirmish lobby reached at y={y_try}")
                break
            c.key(VK_ESC); time.sleep(1.5)
        else:
            log("  ERROR: could not reach Skirmish lobby after retries")
            return False

    # Step B: Set P1 = British (civ picker)
    log(f"  B: setting P1 civ to British (idx={BRITISH_CIV_IDX})...")
    c.move(*P1_CIV_FLAG); time.sleep(0.05)
    c.click(*P1_CIV_FLAG)
    time.sleep(2.5)
    shot(c, TMP / "nav_B_picker.png")

    # Navigate: Up×60 to reset, then Down×3 for British Empire (London)
    for _ in range(60):
        c.key(VK_UP)
        time.sleep(0.03)
    time.sleep(0.5)
    for _ in range(BRITISH_CIV_IDX):
        c.key(VK_DOWN)
        time.sleep(0.06)
    time.sleep(0.5)
    shot(c, TMP / "nav_B_picker_british.png")
    c.move(*PICKER_OK); time.sleep(0.05)
    c.click(*PICKER_OK)
    time.sleep(2.5)
    shot(c, TMP / "nav_B_civ_set.png")

    # Step C: Select "Alaska" stock map directly
    # Alaska is visible at the bottom-right of the initial map picker grid (row 3, col 5)
    # Verified in nav_C_map_open.png: Alaska tile center ≈ (690, 357)
    ALASKA_TILE = (690, 357)
    MAP_OK_BTN  = (961, 995)   # OK button at very bottom of map picker modal

    log("  C: opening map picker...")
    c.move(*MAP_BTN); time.sleep(0.05)
    c.click(*MAP_BTN)
    time.sleep(2.5)
    shot(c, TMP / "nav_C_map_open.png")

    # Double-click Alaska to select and confirm (mirrors drive_hubtest.py pattern)
    log(f"  C: double-clicking Alaska tile at {ALASKA_TILE}...")
    c.move(*ALASKA_TILE); time.sleep(0.1)
    c.click(*ALASKA_TILE); time.sleep(0.3)
    c.click(*ALASKA_TILE)
    time.sleep(2.5)
    shot(c, TMP / "nav_C_lobby.png")

    # Step D: Play
    log(f"  D: clicking Play at {PLAY_BTN}...")
    c.move(*PLAY_BTN); time.sleep(0.05)
    c.click(*PLAY_BTN)
    time.sleep(5.0)
    shot(c, TMP / "nav_D_afterplay.png")
    log("  Play clicked")
    return True


def main() -> int:
    log("=== British light-map age-up capture (stock 1v1) ===")

    c = HarnessClient(SOCK)
    c.connect(timeout=30)
    st = c.state()
    log(f"harness: pid={st.pid} ready={st.ready} {st.internal_w}x{st.internal_h}")
    if st.ready != 1:
        log("ERROR: harness not ready")
        return 1

    shot(c, TMP / "00_initial.png")

    # If we're in-game or post-game from a prior session, escape to main menu first
    escape_to_main_menu(c)
    time.sleep(2.0)
    shot(c, TMP / "01_after_escape.png")

    # Dismiss any popup (weekly profile picture, etc.)
    dismiss_popup_if_present(c)

    # Handle QuickSaveGame error dialog if present
    # (appears when game loads with a corrupt/missing quick save)
    p_pre = TMP / "01b_pre_nav.png"
    c.screenshot(str(p_pre))
    with Image.open(p_pre) as im:
        # Error dialog OK button is at approximately (960, 500) center of screen
        # Check if dialog text region has bright text at y=440-490, x=500-1400
        dialog_text = [im.getpixel((x, 460))[:3] for x in range(500, 1400, 50)]
        dialog_avg = sum(sum(px) / 3 for px in dialog_text) / len(dialog_text)
        log(f"  pre-nav dialog check: dialog_avg={dialog_avg:.0f}")
        if dialog_avg > 150:
            # Possible error dialog — click center OK button
            log("  clicking center OK to dismiss possible error dialog")
            c.click(960, 500)
            time.sleep(1.5)
            c.key(VK_RETURN)
            time.sleep(1.5)

    shot(c, TMP / "01_after_popup.png")

    log("\n--- Step 1: Navigate to 1v1 British skirmish (stock map) ---")
    navigate_to_stock_skirmish(c)

    log("\n--- Step 2: Wait for in-game HUD ---")
    hud_ok = wait_hud(c, timeout=300)
    if not hud_ok:
        log("ERROR: HUD never appeared")
        shot(c, TMP / "error_no_hud.png")
        c.close()
        return 2

    log("HUD visible!")
    time.sleep(3)
    shot(c, TMP / "02_in_game.png")

    log("\n--- Step 3: Speed up + resources ---")
    c.click(*SPEED_TICK5)
    time.sleep(0.5)
    log("  speed set to 5")

    apply_cheats(c)
    shot(c, TMP / "03_resources.png")

    log("\n--- Step 4: Age-up capture loop ---")
    staged_shots: dict[str, Path] = {}
    freeze_at: str | None = None

    for target_age, staging_name in AGE_TARGETS:
        log(f"\n  *** Age {target_age} ({staging_name}) ***")

        # Apply cheats before each age-up attempt
        apply_cheats(c)

        # Select TC using both H hotkey AND direct click on TC area
        log("    selecting TC (H hotkey + direct click)...")
        click_tc(c)
        time.sleep(1.5)

        # Probe age-up button (gold check)
        age_up_seen = probe_age_up_active(c)
        if not age_up_seen:
            log("    age-up probe: not gold. Trying H again + TC click...")
            c.key(VK_H); time.sleep(1.0)
            c.click(800, 460); time.sleep(1.0)  # TC area direct click
            age_up_seen = probe_age_up_active(c)

        if not age_up_seen:
            log("    age-up probe still 0%. Attempting direct click anyway...")

        # Click age-up button
        log(f"    clicking age-up at {AGE_UP_BTN}")
        c.move(*AGE_UP_BTN); time.sleep(0.1)
        c.click(*AGE_UP_BTN)
        time.sleep(3.0)

        # Wait for politician dialog (may take up to 60s if cheats are slow to apply)
        dialog_shown = wait_politician_dialog(c, timeout=60)
        log(f"    politician dialog detected: {dialog_shown}")

        # Capture politician dialog
        dialog_path = STAGE / staging_name
        c.screenshot(str(dialog_path))
        size_kb = dialog_path.stat().st_size // 1024
        log(f"    staged: {dialog_path} ({size_kb}KB)")

        is_valid = is_politician_dialog(dialog_path)
        log(f"    is_valid_dialog={is_valid}")
        if is_valid:
            staged_shots[staging_name] = dialog_path
        else:
            log(f"    REJECTED: {staging_name} is terrain/garbage — skip")
            # Still try to advance age: try clicking politician area
            c.click(*POLITICIAN_1); time.sleep(1.5)
            continue

        # Select first politician and accept to advance age
        log(f"    clicking politician at {POLITICIAN_1}")
        c.click(*POLITICIAN_1)
        time.sleep(0.6)
        log(f"    clicking accept at {ACCEPT_BTN}")
        c.click(*ACCEPT_BTN)
        time.sleep(2.0)

        # Wait for age transition
        wait_age_transition(c, timeout=120)
        time.sleep(12)  # hard floor

        # Freeze check after age 3 and 4 (prior freeze points)
        if target_age in (3, 4):
            log(f"  [freeze check after age {target_age}]")
            frozen = detect_freeze(c, wait_s=20)
            if frozen:
                freeze_at = f"after age {target_age} transition"
                log(f"FREEZE DETECTED at: {freeze_at}")
                log("STOPPING — no copies made (freeze state)")
                break

        apply_cheats(c)

    # Resign
    log("\n--- Step 5: Resign ---")
    try:
        c.key(VK_ESC)
        time.sleep(1.5)
        shot(c, TMP / "resign_esc.png")
        c.click(*ESC_RESIGN)
        time.sleep(1.5)
        c.click(*RESIGN_YES)
        time.sleep(5.0)
        shot(c, TMP / "resign_done.png")
    except Exception as e:
        log(f"  resign error (ignoring): {e}")

    if freeze_at:
        log(f"\nFREEZE REPORT: frozen {freeze_at}")
        log(f"Staged before freeze: {list(staged_shots.keys())}")
        log("No shots copied to full/ (frozen game state).")
        try:
            c.close()
        except Exception:
            pass
        return 10

    log("\n--- Step 6: Hash analysis and staging -> full/ copy ---")

    # Compute hashes for all valid staged shots
    hashes: dict[str, int] = {}
    for name, path in staged_shots.items():
        h = avg_hash_16(path)
        hashes[name] = h
        log(f"  hash staged/{name}: {h}")

    # Hashes of good existing full/ files
    existing_hashes: dict[str, int] = {}
    for key_name, full_path in GOOD_EXISTING.items():
        if full_path.exists():
            h = avg_hash_16(full_path)
            existing_hashes[key_name] = h
            log(f"  hash full/{full_path.name}: {h}")

    # Pairwise distances among all staged shots
    names = list(staged_shots.keys())
    log("\n  Pairwise Hamming (staged shots):")
    all_pairs: list[tuple[str, str, int]] = []
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            d = hamming(hashes[names[i]], hashes[names[j]])
            all_pairs.append((names[i], names[j], d))
            log(f"    {names[i]} vs {names[j]}: Hamming={d} ({'DISTINCT' if d > 15 else 'SIMILAR'})")

    # Cross-check staged vs existing full/
    log("\n  Staged vs existing full/ Hamming:")
    for s_name, s_hash in hashes.items():
        for e_name, e_hash in existing_hashes.items():
            d = hamming(s_hash, e_hash)
            log(f"    staged/{s_name} vs full/08_ageup_{e_name}.png: Hamming={d}")

    # Decide copies
    log("\n  Copy decisions:")
    copied: list[str] = []
    skipped: list[str] = []

    for staging_name, staged_path in staged_shots.items():
        full_dest = FULL / FULL_NAMES[staging_name]
        s_hash = hashes[staging_name]
        age_key = staging_name.replace(".png", "")

        # Collect all other hashes to compare against
        other_hashes: list[tuple[str, int]] = []
        for other_name, other_hash in hashes.items():
            if other_name != staging_name:
                other_hashes.append((f"staged/{other_name}", other_hash))
        for e_name, e_hash in existing_hashes.items():
            if e_name != age_key:
                other_hashes.append((f"full/08_ageup_{e_name}.png", e_hash))

        if not other_hashes:
            min_dist = 999
        else:
            min_dist = min(hamming(s_hash, oh) for _, oh in other_hashes)
        log(f"  {staging_name}: min_hamming_from_others={min_dist}")

        if min_dist <= 15:
            log(f"  SKIP {staging_name} -> not distinct (min_hamming={min_dist} <= 15)")
            skipped.append(staging_name)
        else:
            shutil.copy(staged_path, full_dest)
            log(f"  COPY {staging_name} -> {full_dest}")
            copied.append(staging_name)

    # Rebuild site
    if copied:
        log("\n--- Step 7: Rebuild release readiness site ---")
        import subprocess
        result = subprocess.run(
            [sys.executable, "tools/validation/build_release_readiness_site.py"],
            cwd=str(REPO),
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            log("  site rebuild: PASS")
        else:
            log(f"  site rebuild: FAIL (exit {result.returncode})")
            log(f"  {result.stderr[-300:]}")
    else:
        log("  No shots copied — skipping rebuild")

    log("\n=== FINAL REPORT ===")
    log(f"  Map: stock (first in picker after Up×60, 1v1 British)")
    log(f"  Freeze: {freeze_at or 'NONE'}")
    log(f"  Valid staged dialogs: {list(staged_shots.keys())}")
    log(f"  Copied to full/: {copied}")
    log(f"  Skipped (not distinct): {skipped}")
    if all_pairs:
        log("  Pairwise Hamming:")
        for a, b, d in all_pairs:
            log(f"    {a} vs {b}: {d}")

    log("\n  full/ age-up state:")
    for s_name, full_name in FULL_NAMES.items():
        p = FULL / full_name
        status = f"{p.stat().st_size//1024}KB" if p.exists() else "MISSING"
        log(f"    {full_name}: {status}")

    try:
        c.close()
    except Exception:
        pass
    log("=== END ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
