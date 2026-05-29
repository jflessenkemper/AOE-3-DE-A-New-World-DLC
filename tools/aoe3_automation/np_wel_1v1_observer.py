#!/usr/bin/env python3
"""1v1 observer: me idle (Napoleonic France) vs Wellington AI (British).
Accepts all defaults (Deathmatch/Post-Imperial/Extreme/Alaska). Only UI change:
reduce 4 players to 2 via iterative Y-offset click on player-count dropdown.
"""
from __future__ import annotations
import os, subprocess, time
from pathlib import Path
from PIL import Image, ImageFile, ImageChops

ImageFile.LOAD_TRUNCATED_IMAGES = True
os.environ["GAMESCOPE_WAYLAND_DISPLAY"] = "gamescope-0"
os.environ["WAYLAND_DISPLAY"] = "gamescope-0"
XDO = {**os.environ, "DISPLAY": ":1"}

# 2026-05-11: was hardcoded under AOE-3-DE-Legendary-Leaders-AI worktree.
REPO = Path(__file__).resolve().parents[2]
ART = REPO / "artifacts" / "napoleon_vs_wellington_1v1"
ART.mkdir(parents=True, exist_ok=True)
LOG = ART / "run.log"


def log(msg):
    s = f"[{time.strftime('%H:%M:%S')}] {msg}"
    with LOG.open("a") as f: f.write(s + "\n")
    print(s, flush=True)


def shot(path):
    path = str(path)
    for _ in range(4):
        try: Path(path).unlink()
        except FileNotFoundError: pass
        subprocess.run(["gamescopectl","screenshot",path], timeout=20, capture_output=True)
        time.sleep(1.2)
        if Path(path).exists() and Path(path).stat().st_size > 100_000:
            try:
                with Image.open(path) as img: img.verify()
                return True
            except Exception: continue
    return False


def click(x, y):
    subprocess.run(["xdotool","mousemove",str(x),str(y)], env=XDO)
    time.sleep(0.2)
    subprocess.run(["xdotool","click","1"], env=XDO)


def press(key, n=1, delay=0.15):
    for _ in range(n):
        subprocess.run(["xdotool","key",key], env=XDO)
        time.sleep(delay)


def type_text(text):
    subprocess.run(["xdotool","type","--delay","30",text], env=XDO)


def imdiff(a, b):
    try:
        ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
        return sum(ImageChops.difference(ia, ib).getbbox() or (0,0,0,0))
    except Exception: return 0


def pixel_sum(path, x, y):
    p = Image.open(path).convert("RGB").getpixel((x,y))
    return p[0]+p[1]+p[2]


# Proven coords
SKIRMISH_BTN = (80, 490)
PLAYER_DROPDOWN = (1800, 25)
P1_CIV = (585, 176)
P2_CIV = (585, 282)
P3_ROW_PIXEL = (585, 388)   # Check: if P3 row is dark/empty → reduction worked
PICKER_OK = (240, 976)
PLAY_BTN = (1646, 1030)


def select_civ(flag, idx):
    click(*flag); time.sleep(2.0)
    press("Up", n=60, delay=0.03); time.sleep(0.4)
    press("Down", n=idx, delay=0.04); time.sleep(0.4)
    click(*PICKER_OK); time.sleep(2.5)


def reduce_to_2_players():
    """Click dropdown, then try keyboard-nav first (Up+Return), then Y-offset iteration."""
    baseline = str(ART / "_dd_before.png")
    shot(baseline)
    p3_before = pixel_sum(baseline, *P3_ROW_PIXEL)
    log(f"P3 row pixel_sum before: {p3_before}")

    # Approach 1: keyboard nav after clicking dropdown
    click(*PLAYER_DROPDOWN); time.sleep(1.0)
    shot(str(ART / "_dd_open.png"))
    press("Up", n=5, delay=0.08); time.sleep(0.3)
    press("Return"); time.sleep(1.5)
    probe = str(ART / "_dd_kb.png")
    shot(probe)
    p3_after = pixel_sum(probe, *P3_ROW_PIXEL)
    log(f"P3 row pixel_sum after kb-nav: {p3_after}")
    if abs(p3_after - p3_before) > 40:
        log("  kb-nav appears to have changed player count")
        return True

    # Approach 2: iterate Y offsets
    for y in [60, 80, 100, 120, 140, 160, 180, 200]:
        click(*PLAYER_DROPDOWN); time.sleep(0.8)
        click(PLAYER_DROPDOWN[0], y); time.sleep(1.2)
        probe = str(ART / f"_dd_y{y}.png")
        shot(probe)
        p3_now = pixel_sum(probe, *P3_ROW_PIXEL)
        log(f"  y={y} P3 pixel={p3_now}")
        if abs(p3_now - p3_before) > 40:
            log(f"  SUCCESS at y={y}")
            return True
    log("  FAILED: could not reduce player count")
    return False


def ensure_menu():
    for _ in range(5):
        if shot(str(ART/"_probe.png")):
            if pixel_sum(str(ART/"_probe.png"), 80, 490) < 300:
                return True
        press("Escape"); time.sleep(2)
    return False


def main():
    log("=== np vs wellington 1v1 observer ===")
    if not ensure_menu():
        log("FAIL: not at main menu"); return 1
    log("at main menu")

    click(*SKIRMISH_BTN); time.sleep(3.5)
    shot(str(ART / "00_setup.png"))

    log("reducing to 2 players")
    reduced = reduce_to_2_players()
    shot(str(ART / "01_players.png"))
    if not reduced:
        log("WARN: player reduction failed; proceeding anyway (match will be 4-player FFA)")

    log("P1 = Napoleonic France (idx 33)")
    select_civ(P1_CIV, 33)
    shot(str(ART / "02_p1.png"))

    log("P2 = British (idx 5)")
    select_civ(P2_CIV, 5)
    shot(str(ART / "03_p2.png"))

    log("clicking PLAY")
    click(*PLAY_BTN); time.sleep(5)

    # wait for in-game
    for i in range(30):
        time.sleep(4)
        p = str(ART / "_wait.png")
        if shot(p) and pixel_sum(p, 200, 15) > 280:
            log(f"in-game at ~{(i+1)*4}s")
            break
    else:
        log("TIMEOUT waiting for in-game"); return 2

    match_start = time.time()
    shot(str(ART / "t00_in_game.png"))

    # map reveal
    time.sleep(3)
    log("applying map-reveal cheat")
    press("Return"); time.sleep(0.8)
    type_text("x marks the spot"); time.sleep(0.5)
    press("Return"); time.sleep(2.0)
    shot(str(ART / "t00b_after_cheat.png"))

    # zoom out (click 5 = wheel down)
    log("zooming out")
    for _ in range(20):
        subprocess.run(["xdotool","click","5"], env=XDO); time.sleep(0.08)
    time.sleep(1)
    press("Home"); time.sleep(1.5)
    shot(str(ART / "t00c_zoomed.png"))

    # observe
    for minute in range(1, 26):
        target = match_start + minute * 60
        while time.time() < target:
            time.sleep(5)
        p = str(ART / f"t{minute:02d}_min.png")
        shot(p)
        log(f"captured t+{minute}m")

    log("resigning")
    press("Escape"); time.sleep(1.5)
    press("Down", n=5, delay=0.2); press("Return"); time.sleep(2)
    press("Left"); time.sleep(0.3); press("Return"); time.sleep(4)
    shot(str(ART / "t26_post_resign.png"))

    press("Escape"); time.sleep(1.5)
    press("Down", n=3, delay=0.2); press("Return"); time.sleep(3)
    shot(str(ART / "t27_main_menu.png"))

    log("DONE")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
