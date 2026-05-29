#!/usr/bin/env python3
"""
AFKmodValidation full driver: optimized for 48 civs (22 base + 26 mod).
- Phase 1 only (civ picker screenshots)
- Each civ: dropdown → navigate Down i times → click → screenshot → back to main
- Every click verified by pixel diff
- Saves anchors, all setup screenshots, JSONL log
"""

import subprocess
import re
import sys
import time
import json
import os
import tempfile
from pathlib import Path
from io import BytesIO
from PIL import Image
import random

os.environ['YDOTOOL_SOCKET'] = os.environ.get('YDOTOOL_SOCKET', '/tmp/.ydotool_socket')

# ============ CONFIG ============
ARTIFACT_DIR = Path("/tmp/aoe_test/afk_run_v2")
PHASE1_DIR = ARTIFACT_DIR / "phase1_civ_picker"
LOGS_DIR = ARTIFACT_DIR / "logs"
ANCHORS_DIR = ARTIFACT_DIR / "anchors"
JSONL_LOG = ARTIFACT_DIR / "run.jsonl"

# Create dirs
PHASE1_DIR.mkdir(parents=True, exist_ok=True)
ANCHORS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

SCREENSHOT_TIMEOUT = 5
CLICK_VERIFY_RETRIES = 1
CLICK_VERIFY_WAIT = 0.4
SCREENSHOT_WAIT = 0.2

# ============ LOGGING ============
def log_error(msg):
    print(f"[ERROR] {msg}", file=sys.stderr)

def log_jsonl(entry):
    with open(JSONL_LOG, 'a') as f:
        f.write(json.dumps(entry) + '\n')

def save_screenshot(png_bytes, path):
    if png_bytes:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'wb') as f:
            f.write(png_bytes)

# ============ WINDOW GEOMETRY ============
def get_aoe3_window():
    try:
        out = subprocess.check_output(["wmctrl", "-lG"], text=True)
        m = re.search(
            r'(0x[0-9a-f]+)\s+\d+\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+\S+\s+Age of Empires III',
            out
        )
        if not m:
            return None
        wid, wx, wy, ww, wh = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))
        return {'wid': wid, 'x': wx, 'y': wy, 'w': ww, 'h': wh}
    except Exception as e:
        log_error(f"wmctrl failed: {e}")
        return None

def verify_window_size(win, expected_w=1920, expected_h=1080):
    if (win['w'], win['h']) != (expected_w, expected_h):
        sys.exit(f"FATAL: window {win['w']}x{win['h']}, expected {expected_w}x{expected_h}")

# ============ SCREENSHOT & DIFF ============
def screenshot_bytes():
    try:
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_path = tmp.name
        result = subprocess.run(
            ["spectacle", "-b", "-n", "-o", tmp_path],
            capture_output=True,
            timeout=SCREENSHOT_TIMEOUT
        )
        if result.returncode != 0 or not os.path.exists(tmp_path):
            return None
        with open(tmp_path, 'rb') as f:
            png_bytes = f.read()
        os.unlink(tmp_path)
        return png_bytes
    except Exception as e:
        log_error(f"screenshot_bytes: {e}")
        return None

def pixel_diff_pct(before_bytes, after_bytes):
    try:
        before = Image.open(BytesIO(before_bytes)).convert("RGB")
        after = Image.open(BytesIO(after_bytes)).convert("RGB")
        if before.size != after.size:
            return 100.0
        changed = 0
        for _ in range(200):
            x = random.randint(0, before.size[0] - 1)
            y = random.randint(0, before.size[1] - 1)
            b_rgb = before.getpixel((x, y))
            a_rgb = after.getpixel((x, y))
            if any(abs(b_rgb[i] - a_rgb[i]) > 20 for i in range(3)):
                changed += 1
        return (changed / 200.0) * 100.0
    except Exception as e:
        log_error(f"pixel_diff_pct: {e}")
        return -1.0

# ============ INPUT ============
def ydotool_click(abs_x, abs_y):
    try:
        subprocess.run(["ydotool", "mousemove", str(abs_x), str(abs_y)], check=True, capture_output=True)
        subprocess.run(["ydotool", "click", "1"], check=True, capture_output=True)
    except Exception as e:
        log_error(f"ydotool_click({abs_x}, {abs_y}): {e}")
        raise

def ydotool_key(key_name):
    try:
        subprocess.run(["ydotool", "key", key_name], check=True, capture_output=True)
    except Exception as e:
        log_error(f"ydotool_key({key_name}): {e}")
        raise

# ============ CLICK VERIFICATION ============
def click_verified(win, game_x, game_y, expected_change=True, retries=CLICK_VERIFY_RETRIES):
    abs_x = win['x'] + game_x
    abs_y = win['y'] + game_y
    before = screenshot_bytes()
    if before is None:
        return False, -1.0, None, None
    diff = -1.0
    after = None
    for attempt in range(retries + 1):
        try:
            ydotool_click(abs_x, abs_y)
        except Exception:
            continue
        time.sleep(CLICK_VERIFY_WAIT)
        after = screenshot_bytes()
        if after is None:
            return False, -1.0, before, None
        diff = pixel_diff_pct(before, after)
        if diff < 0:
            return False, -1.0, before, after
        if expected_change:
            if diff > 0.5:
                return True, diff, before, after
        else:
            if diff < 0.1:
                return True, diff, before, after
        if attempt < retries:
            time.sleep(SCREENSHOT_WAIT)
    return False, diff, before, after

# ============ LOAD CIVS ============
def load_all_civs():
    """Load 22 base civs + 26 mod civs."""
    base_civs = [
        "French", "British", "Spanish", "Dutch", "German", "Portuguese", "Russian", "Ottoman",
        "Chinese", "Indian", "Japanese", "Korean", "Aztec", "Sioux", "Inca", "Haudenosaunee",
        "Swede", "Polish", "Italian", "Ethiopians", "Persians", "Maltese"
    ]

    # Load mod civs from XML (try from current dir or from repo root)
    mod_civs = []
    try:
        # Try to find civmods.xml from current working directory
        import os
        cwd = os.getcwd()
        xml_path = Path(cwd) / "data" / "civmods.xml"
        if not xml_path.exists():
            # Try going up to parent directories
            for parent in Path(cwd).parents:
                test_path = parent / "data" / "civmods.xml"
                if test_path.exists():
                    xml_path = test_path
                    break

        if xml_path.exists():
            with open(xml_path, 'r') as f:
                content = f.read()
            # Extract all <Name> tags
            import re
            names = re.findall(r'<Name>([^<]+)</Name>', content)
            for name in names:
                if name not in base_civs and name.startswith('ANW'):
                    mod_civs.append(name)
        else:
            log_error(f"civmods.xml not found at {xml_path}")
    except Exception as e:
        log_error(f"load mod civs: {e}")

    # Return max 22 base + max 26 mod
    return base_civs[:22] + mod_civs[:26]

# ============ ANCHOR ESTABLISHMENT ============
def establish_anchors(win):
    print("[ANCHOR] Starting...")
    success, diff, before, after = click_verified(win, 960, 800, expected_change=True, retries=1)
    if not success:
        print(f"[FATAL] Skirmish click failed (diff={diff:.1f}%)")
        if before: save_screenshot(before, ANCHORS_DIR / "FAIL_before_skirmish.png")
        if after: save_screenshot(after, ANCHORS_DIR / "FAIL_after_skirmish.png")
        sys.exit(1)
    save_screenshot(before, ANCHORS_DIR / "00_main_menu.png")
    save_screenshot(after, ANCHORS_DIR / "01_skirmish_opened.png")
    print(f"  [OK] Skirmish (diff={diff:.1f}%)")
    time.sleep(0.3)

    success, diff, _, after = click_verified(win, 400, 350, expected_change=True, retries=1)
    if not success:
        print(f"[FATAL] Dropdown click failed (diff={diff:.1f}%)")
        sys.exit(1)
    save_screenshot(after, ANCHORS_DIR / "02_dropdown_open.png")
    print(f"  [OK] Dropdown (diff={diff:.1f}%)")
    time.sleep(0.3)

    # Take dropdown screenshot
    dropdown = screenshot_bytes()
    if dropdown:
        save_screenshot(dropdown, ANCHORS_DIR / "03_dropdown_list.png")

    # Click first row
    success, diff, _, after = click_verified(win, 400, 420, expected_change=True, retries=1)
    if not success:
        print(f"[FATAL] Row click failed (diff={diff:.1f}%)")
        sys.exit(1)
    save_screenshot(after, ANCHORS_DIR / "04_civ_selected.png")
    print(f"  [OK] Row click (diff={diff:.1f}%)")
    time.sleep(0.3)

    # Back to main
    ydotool_key("Escape")
    time.sleep(0.5)
    back = screenshot_bytes()
    if back:
        save_screenshot(back, ANCHORS_DIR / "05_back_main.png")

    # Save anchors JSON
    anchors = {
        "skirmish_btn": {"x": 960, "y": 800},
        "civ_dropdown": {"x": 400, "y": 350},
        "first_row": {"x": 400, "y": 420}
    }
    with open(ANCHORS_DIR / "ui_anchors.json", 'w') as f:
        json.dump(anchors, f, indent=2)

    print("[ANCHOR] Complete")
    return anchors

# ============ PHASE 1: CIV PICKER ============
def phase1_all_civs(win, anchors, civs):
    print(f"\n[PHASE1] Testing {len(civs)} civs...")
    for i, civ in enumerate(civs):
        print(f"  [{i+1}/{len(civs)}] {civ}...", end='', flush=True)
        slug = civ.lower().replace(' ', '_').replace('/', '_')

        # Back to main, re-enter Skirmish
        ydotool_key("Escape")
        time.sleep(0.2)
        success, _, _, _ = click_verified(win, 960, 800, expected_change=True, retries=1)
        if not success:
            log_jsonl({"civ": civ, "phase": 1, "step": "skirmish", "verified": False})
            print(" [FAIL skirmish]")
            continue
        time.sleep(0.2)

        # Open dropdown
        success, diff, _, _ = click_verified(win, 400, 350, expected_change=True, retries=1)
        if not success:
            log_jsonl({"civ": civ, "phase": 1, "step": "dropdown", "verified": False})
            print(" [FAIL dropdown]")
            ydotool_key("Escape")
            time.sleep(0.2)
            continue
        time.sleep(0.1)

        # Navigate down i times
        for _ in range(i):
            ydotool_key("Down")
            time.sleep(0.05)
        time.sleep(0.1)

        # Click row
        success, diff, _, after = click_verified(win, 400, 420, expected_change=True, retries=1)
        if not success:
            log_jsonl({"civ": civ, "phase": 1, "step": "row_click", "verified": False, "diff_pct": diff})
            print(f" [FAIL click]")
            ydotool_key("Escape")
            time.sleep(0.2)
            continue

        # Screenshot setup
        time.sleep(0.2)
        setup = screenshot_bytes()
        if setup:
            save_screenshot(setup, PHASE1_DIR / f"{slug}_setup.png")

        log_jsonl({
            "civ": civ,
            "phase": 1,
            "step": "selected",
            "verified": True,
            "diff_pct": diff,
            "screenshot": f"{slug}_setup.png"
        })
        print(" [OK]")
        time.sleep(0.1)

# ============ MAIN ============
def main():
    print("=" * 70)
    print("AFKModValidation Driver v2 - Full 48-Civ Phase 1 Run")
    print("=" * 70)

    # Get window
    print("\n[INIT] Checking window...")
    win = get_aoe3_window()
    if not win:
        sys.exit("FATAL: AoE3 window not found")
    print(f"  Window: {win['w']}x{win['h']} @ ({win['x']}, {win['y']})")
    verify_window_size(win)

    # Load civs
    print("\n[INIT] Loading civs...")
    civs = load_all_civs()
    print(f"  Found {len(civs)} civs")

    # Anchors
    print("\n[STEP 1] Anchor Establishment")
    anchors = establish_anchors(win)

    # Phase 1
    print("\n[STEP 2] Phase 1 - Civ Picker")
    phase1_all_civs(win, anchors, civs)

    # Summary
    print("\n" + "=" * 70)
    with open(JSONL_LOG) as f:
        lines = f.readlines()
    print(f"Total entries logged: {len(lines)}")
    passed = sum(1 for line in lines if '"verified": true' in line)
    print(f"Verified: {passed}")
    print("=" * 70)

if __name__ == "__main__":
    main()
