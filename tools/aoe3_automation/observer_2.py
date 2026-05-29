#!/usr/bin/env python3
"""3-player observer match: P1 idle + British (Wellington auto) + French (Napoleon auto).
Keep it simple — accept Deathmatch/Alaska/Extreme defaults. Run 20 min, screenshot every 60s.
"""
from __future__ import annotations
import os, subprocess, time
from pathlib import Path
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True
GS_ENV = {**os.environ, 'GAMESCOPE_WAYLAND_DISPLAY': 'gamescope-0', 'WAYLAND_DISPLAY': 'gamescope-0', 'XDG_RUNTIME_DIR': '/run/user/1000'}
X_ENV = {**os.environ, 'DISPLAY': ':1'}

# 2026-05-11: was hardcoded under AOE-3-DE-Legendary-Leaders-AI worktree.
REPO = Path(__file__).resolve().parents[2]
ART = REPO / "artifacts" / "observer2"
ART.mkdir(parents=True, exist_ok=True)
LOG = ART / "run.log"


def log(m):
    s = f"[{time.strftime('%H:%M:%S')}] {m}"
    with LOG.open("a") as f: f.write(s+"\n")
    print(s, flush=True)


def shot(path):
    path = str(path)
    for _ in range(4):
        try: Path(path).unlink()
        except FileNotFoundError: pass
        subprocess.run(["gamescopectl","screenshot",path], env=GS_ENV, timeout=20, capture_output=True)
        time.sleep(4)
        if Path(path).exists() and Path(path).stat().st_size > 100_000:
            try:
                with Image.open(path) as img: img.verify()
                return True
            except Exception: pass
    return False


def click(x, y):
    subprocess.run(["xdotool","mousemove",str(x),str(y)], env=X_ENV)
    time.sleep(0.15)
    subprocess.run(["xdotool","click","1"], env=X_ENV)


def press(key, n=1, d=0.15):
    for _ in range(n):
        subprocess.run(["xdotool","key",key], env=X_ENV); time.sleep(d)


def type_text(t):
    subprocess.run(["xdotool","type","--delay","30",t], env=X_ENV)


def ocr_click(target_words, region=None, after_delay=2.0):
    """OCR-find target words and click. target_words is a list of strings; returns True on success."""
    import pytesseract
    p = str(ART / "_ocr.png")
    shot(p)
    img = Image.open(p)
    if region: img = img.crop(region)
    d = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config='--psm 6')
    ox, oy = region[:2] if region else (0, 0)
    for i, t in enumerate(d['text']):
        if any(w.lower() in t.lower() for w in target_words):
            x, y, w, h = d['left'][i], d['top'][i], d['width'][i], d['height'][i]
            click(ox + x + w//2, oy + y + h//2)
            time.sleep(after_delay)
            return True
    return False


def main():
    log("=== observer_2: Wellington vs Napoleon ===")
    # Assume main menu
    shot(str(ART/"00_menu.png"))

    # Skirmish
    click(80, 490); time.sleep(4)
    shot(str(ART/"01_setup.png"))

    # P2 civ flag → British
    click(585, 282); time.sleep(3)
    # Find + click British via OCR (British is row 6)
    shot(str(ART/"_p2_picker.png"))
    import pytesseract
    img = Image.open(str(ART/"_p2_picker.png"))
    d = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config='--psm 6')
    for i, t in enumerate(d['text']):
        if 'British' in t or 'BRITISH' in t:
            x, y, w, h = d['left'][i], d['top'][i], d['width'][i], d['height'][i]
            click(x + w//2, y + h//2); time.sleep(1)
            break
    click(216, 960); time.sleep(3)  # OK
    shot(str(ART/"02_p2_british.png"))

    # P3 civ flag → French
    click(585, 388); time.sleep(3)
    # scroll to French
    subprocess.run(["xdotool","mousemove","400","500"], env=X_ENV)
    for _ in range(10): subprocess.run(["xdotool","click","5"], env=X_ENV); time.sleep(0.1)
    time.sleep(2)
    shot(str(ART/"_p3_picker.png"))
    img = Image.open(str(ART/"_p3_picker.png"))
    d = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config='--psm 6')
    found = False
    for i, t in enumerate(d['text']):
        if t.strip() in ('French', 'FRENCH'):
            x, y, w, h = d['left'][i], d['top'][i], d['width'][i], d['height'][i]
            click(x + w//2, y + h//2); time.sleep(1)
            found = True
            break
    if not found:
        log("WARN French not found in OCR; picker may have scrolled past");
    click(216, 960); time.sleep(3)
    shot(str(ART/"03_p3_french.png"))

    # Play
    click(1646, 1030); time.sleep(5)

    # Wait for in-game
    for i in range(30):
        time.sleep(4)
        p = str(ART/"_wait.png")
        if shot(p):
            img = Image.open(p).convert("RGB")
            if sum(img.getpixel((200, 15))) > 280:
                log(f"in-game at {(i+1)*4}s")
                break
    else:
        log("TIMEOUT"); return 1

    match_start = time.time()
    shot(str(ART/"t00_ingame.png"))

    # Reveal + zoom
    time.sleep(3)
    press("Return"); time.sleep(0.8)
    type_text("x marks the spot"); time.sleep(0.5)
    press("Return"); time.sleep(2)
    shot(str(ART/"t00b_reveal.png"))
    for _ in range(20):
        subprocess.run(["xdotool","click","5"], env=X_ENV); time.sleep(0.08)
    time.sleep(1)
    press("Home"); time.sleep(1.5)
    shot(str(ART/"t00c_zoom.png"))

    # Observe 20 min
    for minute in range(1, 21):
        target = match_start + minute*60
        while time.time() < target: time.sleep(5)
        shot(str(ART/f"t{minute:02d}_min.png"))
        log(f"t+{minute}m captured")

    # Resign
    log("resigning")
    press("Escape"); time.sleep(1.5)
    press("Down", n=5, d=0.2); press("Return"); time.sleep(2)
    press("Left"); time.sleep(0.3); press("Return"); time.sleep(4)
    shot(str(ART/"t21_resigned.png"))
    press("Escape"); time.sleep(1.5)
    press("Down", n=3, d=0.2); press("Return"); time.sleep(3)
    shot(str(ART/"t22_menu.png"))

    log("DONE")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
