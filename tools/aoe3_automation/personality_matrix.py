#!/usr/bin/env python3
"""Lobby-only matrix test: for each of 48 personality overrides, open the AI
slot's personality dropdown in Skirmish setup, select the personality by
keyboard-nav name-search, screenshot the slot, and verify the displayed name
+ portrait matches the expected override.

Does NOT play matches — pure lobby verification. ~5 min per personality,
~4 hours total for all 48. Run overnight.

Artifacts go to .claude/session_2026-04-22-artifacts/personality_matrix/
with one screenshot per personality plus a final REPORT.md.

Usage:
  python3 tools/aoe3_automation/personality_matrix.py
  python3 tools/aoe3_automation/personality_matrix.py --sample 8   # quick 8-civ test
"""
from __future__ import annotations
import argparse, os, subprocess, sys, time
from pathlib import Path
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True
os.environ["GAMESCOPE_WAYLAND_DISPLAY"] = "gamescope-0"
os.environ["WAYLAND_DISPLAY"] = "gamescope-0"
XDO = {**os.environ, "DISPLAY": ":1"}

# 2026-05-11: was hardcoded under AOE-3-DE-Legendary-Leaders-AI worktree.
REPO = Path(__file__).resolve().parents[2]
ART = REPO / "artifacts" / "personality_matrix"
ART.mkdir(parents=True, exist_ok=True)
LOG = ART / "run.log"

# Proven UI coords
SKIRMISH_BTN = (80, 490)
# P2 slot's "RANDOM PERSONALITY" text/button — experimentally discovered
# from _dd_open.png: P2 is at ~y=282 in the civ flag column, but personality
# dropdown is a separate control to the left. Needs discovery — first pass
# tries (290, 282) which is the personality-name column at P2's row.
P2_PERSONALITY = (290, 282)
# When dropdown opens, entries appear below in a scrollable list. Using
# keyboard nav (Down/Up) is more reliable than Y-offset clicks.

# The 48 overrides: (personality_file_stem, expected_display_name)
# Order: alphabetical within the game's picker (to aid keyboard nav predictions)
OVERRIDES = [
    # Base-game overrides (22)
    ("akbar",      "Shivaji Bhonsle"),
    ("amina",      "Usman dan Fodio"),
    ("crazyhorse", "Crazy Horse"),
    ("cuauhtemoc", "Montezuma"),
    ("elizabeth",  "Duke of Wellington"),
    ("Frederick",  "Frederick the Great"),
    ("garibaldi",  "Giuseppe Garibaldi"),
    ("Gustav",     "Gustavus Adolphus"),
    ("henry",      "Prince Henry the Navigator"),
    ("Hiawatha",   "Hiawatha"),
    ("hidalgo",    "Miguel Hidalgo"),
    ("Huayna",     "Pachacuti"),
    ("isabella",   "Isabella I of Castile"),
    ("Ivan",       "Catherine the Great"),
    ("jean",       "Jean de Valette"),
    ("kangxi",     "Kangxi Emperor"),
    ("napoleon",   "Napoleon Bonaparte"),
    ("Suleiman",   "Suleiman the Magnificent"),
    ("tewodros",   "Menelik II"),
    ("tokugawa",   "Tokugawa Ieyasu"),
    ("washington", "George Washington"),
    ("William",    "Maurice of Nassau"),
    # Mod revolution civs (26)
    ("anwamericans",          "Thomas Jefferson"),
    ("anwargentines",         "José de San Martín"),
    ("anwbarbary",            "Hayreddin Barbarossa"),
    ("anwbrazil",             "Pedro I of Brazil"),
    ("anwcalifornians",       "Mariano Vallejo"),
    ("anwcanadians",          "Isaac Brock"),
    ("anwcentralamericans",   "Francisco Morazán"),
    ("anwchileans",           "Bernardo O'Higgins"),
    ("anwcolumbians",         "Simón Bolívar"),
    ("anwegyptians",          "Muhammad Ali Pasha"),
    ("anwfinnish",            "Carl Gustaf Mannerheim"),
    ("anwhaitians",           "Toussaint L'Ouverture"),
    ("anwhungarians",         "Lajos Kossuth"),
    ("anwindonesians",        "Prince Diponegoro"),
    ("anwmayans",             "Jacinto Canek"),
    ("anwmexicans",           "Miguel Hidalgo"),
    ("anwnapoleonicfrance",   "Napoleon Bonaparte"),
    ("anwperuvians",          "Andrés de Santa Cruz"),
    ("anwrevfrance","Maximilien Robespierre"),
    ("anwriogrande",          "Antonio Canales Rosillo"),
    ("anwromanians",          "Alexandru Ioan Cuza"),
    ("anwsouthafricans",      "Paul Kruger"),
    ("anwtexians",            "Sam Houston"),
    ("anwyucatan",            "Felipe Carrillo Puerto"),
]


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
        time.sleep(1.0)
        if Path(path).exists() and Path(path).stat().st_size > 100_000:
            try:
                with Image.open(path) as img: img.verify()
                return True
            except Exception: continue
    return False


def click(x, y):
    subprocess.run(["xdotool","mousemove",str(x),str(y)], env=XDO)
    time.sleep(0.15)
    subprocess.run(["xdotool","click","1"], env=XDO)


def press(key, n=1, delay=0.1):
    for _ in range(n):
        subprocess.run(["xdotool","key",key], env=XDO); time.sleep(delay)


def pixel_sum(path, x, y):
    p = Image.open(path).convert("RGB").getpixel((x,y))
    return p[0]+p[1]+p[2]


def enter_skirmish():
    shot(str(ART / "_menu_probe.png"))
    click(*SKIRMISH_BTN); time.sleep(3)


def select_personality_by_idx(slot_coord, idx):
    """Open personality dropdown for given slot and select entry at alphabetical idx.
    Uses Up×120 to reset to top, then Down×idx, then Enter.
    """
    click(*slot_coord); time.sleep(1.5)
    press("Up", n=120, delay=0.02); time.sleep(0.3)
    press("Down", n=idx, delay=0.03); time.sleep(0.3)
    press("Return"); time.sleep(1.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0, help="Only test first N personalities")
    ap.add_argument("--start", type=int, default=0, help="Start from index N")
    args = ap.parse_args()

    targets = OVERRIDES[args.start:]
    if args.sample:
        targets = targets[:args.sample]

    log(f"=== personality matrix: testing {len(targets)} personalities ===")
    log("Assumption: game is at main menu")

    enter_skirmish()
    shot(str(ART / "00_skirmish_setup.png"))

    results = []
    for i, (stem, expected) in enumerate(targets):
        idx = args.start + i
        log(f"[{idx+1}/{len(OVERRIDES)}] {stem} → expected '{expected}'")
        # Pick the i'th personality by alphabetical dropdown order.
        # NOTE: the actual dropdown ordering may include non-overridden
        # personalities too. The idx-to-entry mapping needs calibration
        # from the first run's screenshots.
        select_personality_by_idx(P2_PERSONALITY, idx)
        outpath = ART / f"p{idx:02d}_{stem}.png"
        shot(str(outpath))
        results.append({
            "idx": idx, "stem": stem, "expected": expected, "screenshot": str(outpath.name),
        })
        log(f"  screenshot: {outpath.name}")
        time.sleep(1)

    # Write a report stub; OCR/verification is a manual follow-up pass
    report = ART / "REPORT.md"
    with report.open("w") as f:
        f.write("# Personality Matrix — Dynamic Lobby Verification\n\n")
        f.write(f"Total: {len(results)}\n\n")
        f.write("| # | Personality File | Expected Display Name | Screenshot | OCR Pass? |\n")
        f.write("|---|---|---|---|---|\n")
        for r in results:
            f.write(f"| {r['idx']+1} | {r['stem']} | {r['expected']} | {r['screenshot']} | _manual_ |\n")
        f.write("\n## Next step\n\n")
        f.write("Open each screenshot; visually confirm the P2 slot shows the expected\n")
        f.write("display name and a leader portrait (not the 'Random Personality' default).\n")
        f.write("Mark column 5 with ✅ or ❌. Any ❌ indicates either the dropdown entry\n")
        f.write("ordering differs from OVERRIDES list (fixable by re-ordering) OR the\n")
        f.write("mod's personality override is not being honored by the engine for that\n")
        f.write("specific personality file (real bug worth filing).\n")

    log(f"DONE — {len(results)} screenshots, see {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
