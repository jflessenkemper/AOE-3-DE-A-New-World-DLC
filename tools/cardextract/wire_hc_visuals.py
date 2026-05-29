"""Replace the generic revolution\\revolution_* visuals in the 26 mod
revolution civ home city XMLs with thematically-matching base-game scenes.

Fix for user-reported "sky gap in home city backdrop" issue (2026-04-23) —
the stock revolution_background.xml has a plain skybox with visible seams
between building clusters; per-civ base-game backgrounds hide the skybox
with dense cityscape.

Mapping is historically/culturally approximate. Each mod civ is matched to
the base-game home city scene closest to its civilization root:
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"

# mod_homecity_filename → (visual_base, water_base, background_base)
# Each base is a folder like "british" → `british\british_homecity.xml`
MAPPING = {
    # North America
    "anwhomecityamericans":        "british",    # US is British-descended
    "anwhomecitycanada":           "british",    # Canadian Dominion
    "anwhomecityfrenchcanada":     "french",     # Québec
    "anwhomecitytexas":            "mexico",     # Texian uses Mexican architecture closer
    "anwhomecitycalifornia":       "mexico",     # Californio
    "anwhomecitybajacalifornians": "mexico",     # Baja Californio
    "anwhomecitycentralamericans": "spanish",    # Colonial Central America
    "anwhomecityriogrande":        "mexico",
    "anwhomecityyucatan":          "mexico",
    "anwhomecitymaya":             "mexico",
    # South America — Spanish/Portuguese colonial
    "anwhomecitybrazil":           "portuguese",
    "anwhomecityargentina":        "spanish",
    "anwhomecitychile":            "spanish",
    "anwhomecityperu":             "spanish",
    "anwhomecitycolumbia":         "spanish",
    "anwhomecityhaiti":            "french",     # French colonial Saint-Domingue
    # Europe East/North
    "anwhomecityromania":          "german",     # Mitteleuropa
    "anwhomecityhungary":          "german",
    "anwhomecityfinland":          "russian",    # Grand Duchy of Finland
    # Revolutionary France — use French visuals to match flag
    "anwhomecitynapoleon":            "french",
    "anwhomecityrevolutionaryfrance": "french",
    # Africa / MENA
    "anwhomecityegypt":            "ottoman",
    "anwhomecitybarbary":          "ottoman",
    "anwhomecitysouthafricans":    "dutch",      # Afrikaner / Dutch heritage
    # Asia / Indian Ocean
    "anwhomecityindonesians":      "dutch",      # Dutch East Indies
}


def rewire(stem: str, base: str) -> bool:
    path = DATA / f"{stem}.xml"
    if not path.exists():
        return False
    txt = path.read_text(encoding="utf-8")

    # Replace scene + TOP-LEVEL camera only. Nested <camera> tags inside
    # per-building blocks (Estate, Market, Dock) are left alone — they
    # reference building-specific shots that don't translate across civs,
    # and any revolution_market_camera references still render fine.
    # Camera must match the new visual — otherwise the view floats at the
    # old revolution-scene altitude (landing on rooftops of the new city).
    replacements = [
        (r"<visual>[^<]*</visual>",
         f"<visual>{base}\\\\{base}_homecity.xml</visual>"),
        (r"<watervisual>[^<]*</watervisual>",
         f"<watervisual>{base}\\\\{base}_homecity_water.xml</watervisual>"),
        (r"<backgroundvisual>[^<]*</backgroundvisual>",
         f"<backgroundvisual>{base}\\\\{base}_background.xml</backgroundvisual>"),
        # Only replace the top-level revolution camera (anchored to the
        # revolution homecity scene) — nested building cameras are preserved.
        (r"<camera>revolution\\+revolution_homecity_camera\.cam</camera>",
         f"<camera>{base}\\\\{base}_homecity_camera.cam</camera>"),
        (r"<widescreencamera>revolution\\+revolution_homecity_camera\.cam</widescreencamera>",
         f"<widescreencamera>{base}\\\\{base}_homecity_widescreencamera.cam</widescreencamera>"),
    ]

    changed = False
    for pat, repl in replacements:
        new, n = re.subn(pat, repl, txt)
        if n:
            txt = new
            changed = True

    if changed:
        path.write_text(txt, encoding="utf-8")
    return changed


def main():
    ok = 0
    for stem, base in MAPPING.items():
        if rewire(stem, base):
            print(f"  {stem}.xml → {base}")
            ok += 1
        else:
            print(f"  SKIP {stem}.xml")
    print(f"\nRewired {ok}/{len(MAPPING)} mod revolution civ home cities.")


if __name__ == "__main__":
    main()
