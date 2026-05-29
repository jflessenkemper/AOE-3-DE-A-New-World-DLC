#!/usr/bin/env python3
"""Build vanilla_revolution_art_map.json — per-ANW-civ borrowable vanilla art.

Walks the canonical vanilla bar inventory dump at /tmp/vanilla_bar_inventory.txt
and groups assets by category, then maps them to ANW civ tokens via a
hand-curated keyword table.

Output: tools/vanilla_revolution_art_map.json with shape:
    {
      "ANWArgentines": {
        "ui_flags": [...png paths...],
        "postgame_flags": [...ddt paths...],
        "world_flags": [...flag-object stems...],
        "revolution_portraits": [...png paths...],
        "buntings": [...ddt paths...],
        "homecity_scene": [...gr2 paths...]
      },
      ...
    }
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

INVENTORY = Path("/tmp/vanilla_bar_inventory.txt")
OUT = Path(__file__).resolve().parent / "vanilla_revolution_art_map.json"

# Each ANW civ -> list of token aliases that should match path substrings.
# Order matters for disambiguation: more-specific tokens go first.
CIV_KEYWORDS = {
    "ANWArgentines":       ["argentin", "_argent.", "argent_", "granadero", "san_martin", "pampas", "patagonia"],
    "ANWBarbary":          ["barbary", "moroccan", "moros", "spc_barbary", "omani", "af_saharan", "africa", "african_villager", "african_military"],
    "ANWBrazil":           ["brazil", "amazonia", "orinoco"],
    "ANWCanadians":        ["canadian", "metis_pathfinder", "spc_canadian", "saguenay", "yukon", "northwest_territory", "great_lakes"],
    "ANWChileans":         ["chilean"],
    "ANWColumbians":       ["colombian", "columbia", "coumbia", "orinoco"],
    "ANWEgyptians":        ["egyptian", "egypt", "africa", "african_villager", "af_saharan"],
    "ANWFinnish":          ["finnish", "karelian", "siberia"],
    "ANWHaitians":         ["haitian", "haiti", "padre_revolution", "hispaniola"],
    "ANWHungarians":       ["hungarian", "hungar", "hajduk", "hungarian_hussar", "eu_eurasian_steppe"],
    "ANWIndonesians":      ["indonesian", "indones", "cetbang", "java_spearman", "indochina", "ceylon"],
    "ANWMayans":           ["mayan", "cruzob", "mx_mayan", "yucatan", "everglades"],
    "ANWNapoleonicFrance": ["french_revolution_ne", "revolution_ne", "noble_class_french"],
    "ANWPeruvians":        ["peruvian", "peru", "inca", "inca_parade", "inca_llama"],
    "ANWRevFrance":        ["french_revolution", "noble_class_french"],
    "ANWRomanians":        ["romanian", "dorobant", "rosior", "wallachian", "death_hussar", "eu_eurasian_steppe"],
    "ANWSouthAfricans":    ["south_african", "south_afric", "africa", "african_villager", "african_military"],
    "ANWTexians":          ["texan", "texas", "texian", "great_plains", "carolina"],
}

# Buckets a single entry falls into.
def classify(path_lower: str) -> str | None:
    if "resources\\images\\icons\\flags\\flag_hc_" in path_lower and path_lower.endswith(".png"):
        return "ui_flags"
    if "ui\\ingame\\ingame_ui_postgame_flag_" in path_lower and path_lower.endswith(".ddt"):
        return "postgame_flags"
    if "objects\\flags\\" in path_lower:
        return "world_flags"
    if "resources\\art\\units\\revolution\\" in path_lower and path_lower.endswith(".png"):
        return "revolution_portraits"
    if "homecity\\revolution\\bunting_" in path_lower or \
       "homecity\\revolution\\revolution_hall\\textures\\bunting_" in path_lower:
        return "buntings"
    if "homecity\\revolution\\" in path_lower and path_lower.endswith((".gr2", ".ddt")):
        return "homecity_scene"
    if "homecity\\homecity_units\\" in path_lower and path_lower.endswith((".gr2", ".ddt", ".xml")):
        return "hc_units"
    if "resources\\images\\icons\\random_map\\" in path_lower and path_lower.endswith(".png"):
        return "random_map_graphics"
    return None


def main() -> int:
    if not INVENTORY.exists():
        print(f"ERROR: {INVENTORY} not found. Run tools/bar_inventory.py first.", file=sys.stderr)
        return 1

    # Pre-bucket every relevant entry once, then match to civs.
    classified: dict[str, list[str]] = {
        "ui_flags": [],
        "postgame_flags": [],
        "world_flags": [],
        "revolution_portraits": [],
        "buntings": [],
        "homecity_scene": [],
        "hc_units": [],
        "random_map_graphics": [],
    }
    seen: set[str] = set()
    with INVENTORY.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t", 1)
            if len(parts) != 2:
                continue
            entry = parts[1]
            cat = classify(entry.lower())
            if cat and entry not in seen:
                classified[cat].append(entry)
                seen.add(entry)

    # Dedup + sort.
    for k in classified:
        classified[k] = sorted(set(classified[k]))

    # Shared revolution-scene assets (no per-country variant) — every revolution
    # civ can use these.
    shared_scene = [
        e for e in classified["homecity_scene"]
        if not any(country in e.lower() for country in
                   ("argent", "brazil", "chile", "columbia", "coumbia",
                    "haiti", "mexico", "peru", "usa"))
    ]

    out: dict[str, dict] = {}
    for civ, keywords in CIV_KEYWORDS.items():
        per_civ: dict[str, list[str]] = {k: [] for k in classified}
        for cat, entries in classified.items():
            if cat == "homecity_scene":
                # match country variants in entry paths
                for e in entries:
                    el = e.lower()
                    if any(kw in el for kw in keywords):
                        per_civ[cat].append(e)
                continue
            for e in entries:
                el = e.lower()
                if any(kw in el for kw in keywords):
                    per_civ[cat].append(e)
        # Always offer the shared revolution scene to ANW civs (they're all
        # revolution-era).
        per_civ["homecity_scene_shared"] = shared_scene
        out[civ] = per_civ

    OUT.write_text(json.dumps(out, indent=2) + "\n")

    # Summary printout
    print(f"Wrote {OUT}")
    print(f"Total catalogued entries by category:")
    for k, v in classified.items():
        print(f"  {k}: {len(v)}")
    print(f"  homecity_scene_shared (offered to all): {len(shared_scene)}")
    print()
    print("Per-ANW-civ asset counts (ui / postgame / world / portraits / buntings / hc_scene / hc_units / rand_map):")
    for civ, d in out.items():
        c = (len(d["ui_flags"]), len(d["postgame_flags"]), len(d["world_flags"]),
             len(d["revolution_portraits"]), len(d["buntings"]), len(d["homecity_scene"]),
             len(d.get("hc_units", [])), len(d.get("random_map_graphics", [])))
        total = sum(c)
        flag = "" if total else "  ← NO MATCHES"
        print(f"  {civ:24s} {c[0]:3d}/{c[1]:3d}/{c[2]:3d}/{c[3]:3d}/{c[4]:3d}/{c[5]:3d}/{c[6]:4d}/{c[7]:3d}  total={total}{flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
