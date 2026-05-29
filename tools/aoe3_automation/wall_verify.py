#!/usr/bin/env python3
"""Wall verification match. P2=Maltese (FortressRing), P3=Lakota (MobileNoWalls).
Map defaults to Alaska; walls should still differ per doctrine on any terrain.
"""
from __future__ import annotations
import os, subprocess, time
from pathlib import Path
from PIL import Image, ImageFile
import pytesseract

ImageFile.LOAD_TRUNCATED_IMAGES = True
GS_ENV = {**os.environ, 'GAMESCOPE_WAYLAND_DISPLAY': 'gamescope-0',
          'WAYLAND_DISPLAY': 'gamescope-0', 'XDG_RUNTIME_DIR': '/run/user/1000'}
X_ENV = {**os.environ, 'DISPLAY': ':1'}

# 2026-05-11: was a hardcoded April worktree path under the old
# AOE-3-DE-Legendary-Leaders-AI repo. Now resolves relative to this file.
ART = Path(__file__).resolve().parents[2] / "artifacts" / "wall_verify"
ART.mkdir(parents=True, exist_ok=True)
LOG = ART / "run.log"


def log(m):
    s = f"[{time.strftime('%H:%M:%S')}] {m}"
    with LOG.open("a") as f: f.write(s+"\n")
    print(s, flush=True)


def shot(path, retries=6):
    path = str(path)
    for _ in range(retries):
        try: Path(path).unlink()
        except FileNotFoundError: pass
        subprocess.run(["gamescopectl","screenshot",path], env=GS_ENV, timeout=20, capture_output=True)
        time.sleep(5)
        if Path(path).exists() and Path(path).stat().st_size > 100_000:
            try:
                with Image.open(path) as img: img.verify()
                return True
            except Exception: continue
    return False


def click(x, y):
    subprocess.run(["xdotool","mousemove",str(x),str(y)], env=X_ENV)
    time.sleep(0.2)
    subprocess.run(["xdotool","click","1"], env=X_ENV)


def press(key, n=1, d=0.15):
    for _ in range(n):
        subprocess.run(["xdotool","key",key], env=X_ENV); time.sleep(d)


def type_text(t):
    subprocess.run(["xdotool","type","--delay","30",t], env=X_ENV)


def pick_in_picker(target_word):
    """Scan picker, click row matching target_word via OCR. Returns True if found."""
    p = str(ART / f"_pick_{target_word}.png")
    if not shot(p): return False
    img = Image.open(p)
    d = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config='--psm 6')
    for i, t in enumerate(d['text']):
        if target_word.lower() in t.strip().lower():
            x,y,w,h = d['left'][i], d['top'][i], d['width'][i], d['height'][i]
            click(x+w//2, y+h//2); time.sleep(1)
            return True
    return False


def main():
    log("=== wall verify: Maltese (FortressRing) vs Lakota (MobileNoWalls) ===")
    shot(str(ART/"00_menu.png"))

    # Skirmish
    click(80, 490); time.sleep(5)
    shot(str(ART/"01_setup.png"))

    # P2 flag → Maltese
    click(585, 282); time.sleep(3)
    # Maltese should be in the M area; scroll down
    click(400, 500)
    for _ in range(20): subprocess.run(["xdotool","click","5"], env=X_ENV); time.sleep(0.1)
    time.sleep(2)
    ok = pick_in_picker("Maltese")
    if ok:
        click(216, 960); time.sleep(5)  # OK
        log("P2 Maltese selected")
    else:
        log("WARN: Maltese not found in picker")
        press("Escape"); time.sleep(2)
    shot(str(ART/"02_p2_maltese.png"))

    # P3 flag → Lakota
    click(585, 388); time.sleep(3)
    click(400, 500)
    for _ in range(18): subprocess.run(["xdotool","click","5"], env=X_ENV); time.sleep(0.1)
    time.sleep(2)
    ok = pick_in_picker("Lakota")
    if ok:
        click(216, 960); time.sleep(5)
        log("P3 Lakota selected")
    else:
        log("WARN: Lakota not found in picker")
        press("Escape"); time.sleep(2)
    shot(str(ART/"03_p3_lakota.png"))

    # PLAY
    click(1646, 1030); time.sleep(5)
    log("clicked PLAY")

    # wait for in-game
    for i in range(40):
        time.sleep(4)
        p = str(ART/"_wait.png")
        if shot(p):
            img = Image.open(p).convert("RGB")
            if sum(img.getpixel((200, 15))) > 280:
                log(f"in-game @ ~{(i+1)*4}s")
                break
    else:
        log("TIMEOUT"); return 1

    match_start = time.time()
    shot(str(ART/"t00_ingame.png"))

    # map reveal
    time.sleep(4)
    press("Return"); time.sleep(0.8)
    type_text("x marks the spot"); time.sleep(0.5)
    press("Return"); time.sleep(2.5)
    shot(str(ART/"t00b_reveal.png"))

    # zoom out
    for _ in range(20):
        subprocess.run(["xdotool","click","5"], env=X_ENV); time.sleep(0.08)
    time.sleep(1)
    press("Home"); time.sleep(1.5)

    # 10-minute observation, screenshot every 60s
    for minute in range(1, 11):
        target = match_start + minute*60
        while time.time() < target: time.sleep(5)
        shot(str(ART/f"t{minute:02d}_min.png"))
        log(f"t+{minute}m captured")

    # Focus maltese base (hotkey F2 or similar) + screenshot walls closeup
    # Then Lakota with F3
    log("capturing base zoom: P2 Maltese (team 2 color yellow)")
    press("F2"); time.sleep(1)
    shot(str(ART/"t11_maltese_base.png"))
    log("capturing base zoom: P3 Lakota")
    press("F3"); time.sleep(1)
    shot(str(ART/"t12_lakota_base.png"))

    # resign
    press("Escape"); time.sleep(1.5)
    press("Down", n=5, d=0.2); press("Return"); time.sleep(2)
    press("Left"); time.sleep(0.3); press("Return"); time.sleep(4)
    shot(str(ART/"t13_resign.png"))
    press("Escape"); time.sleep(1.5)
    press("Down", n=3, d=0.2); press("Return"); time.sleep(3)

    log("DONE")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
