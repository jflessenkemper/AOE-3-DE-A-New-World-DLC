#!/usr/bin/env python3
"""Validate that every ANW civ in civmods.xml is actually loadable in-game.

Catches the class of bug we hit on 2026-05-08: a civ entry exists in
``civmods.xml``, has valid XML and proper DisplayNameID, **but the AoE3 DE
engine doesn't add it to the lobby civ-picker**. The user assumes "46 civs
in civmods.xml = 46 civs in lobby"; reality is the engine has additional
gating (likely on StatsID format) that silently drops some entries.

Empirically: civs whose StatsID matches a 2-char base game pattern (AZ, CH,
FR, US, BR, ...) load fine — they REPLACE the base game civ at that slot.
Civs whose StatsID uses a "1X" digit-prefix format (1A, 1F, 1R, ...) get
dropped — they're not in the picker at all.

This validator runs in two modes:

1. **Static (no game)** — diffs civmods.xml against the cached picker walk
   at ``tools/aoe3_automation/picker_civ_order.json``. The cache was built
   from a live walk and reflects what the engine actually loads. Civs in
   civmods.xml that aren't in the cache are flagged as MISSING.

2. **Live (game running)** — walks the picker fresh, OCRs every row, then
   diffs. Slower but always-current.

Static mode is the default. Use ``--live`` to force a fresh walk.

Usage::

    python3 tools/validation/validate_civ_loadability.py
    python3 tools/validation/validate_civ_loadability.py --live
    python3 tools/validation/validate_civ_loadability.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))


# StatsID format heuristics ----------------------------------------------

# Base game civs use 2-char uppercase alpha StatsIDs (AZ, CH, FR, US, etc).
# ANW additions sometimes use a "1X" digit-prefix format (1A, 1F, 1R) which
# the engine appears NOT to load into the picker.
_ALPHA2_RE = re.compile(r"^[A-Z]{2}$")


def is_base_game_format_statsid(stats_id: str) -> bool:
    """True if the StatsID looks like a base-game-replacement format."""
    return bool(stats_id) and bool(_ALPHA2_RE.match(stats_id))


def classify_statsid(stats_id: str) -> str:
    """Classify a StatsID into a known bucket."""
    if not stats_id:
        return "EMPTY"
    if _ALPHA2_RE.match(stats_id):
        return "BASE_GAME_FORMAT"
    if re.match(r"^1[A-Z]$", stats_id):
        return "DIGIT_PREFIX_NEW"
    return "OTHER"


# civmods.xml parsing ----------------------------------------------------

def load_anw_civs_from_civmods(path: Path) -> list[dict]:
    """Return list of {token, statsid, statsid_class, display_name_id, ...}.

    Only ANW-prefixed civs are returned (skip base game definitions).
    """
    if not path.exists():
        raise FileNotFoundError(path)
    root = ET.parse(path).getroot()
    out: list[dict] = []
    for c in root.findall("civ"):
        n = c.find("name")
        if n is None or not (n.text or "").startswith("ANW"):
            continue
        # Skip revolution-only suppression entries (main=0): they are not
        # presented in the lobby picker, so loadability doesn't apply.
        main_el = c.find("main")
        if main_el is not None and (main_el.text or "").strip() == "0":
            continue
        token = n.text
        sid_e = c.find("statsid")
        did_e = c.find("displaynameid")
        sid = (sid_e.text or "").strip() if sid_e is not None else ""
        did = (did_e.text or "").strip() if did_e is not None else ""
        out.append({
            "token": token,
            "statsid": sid,
            "statsid_class": classify_statsid(sid),
            "display_name_id": did,
        })
    return out


# Cache lookup -----------------------------------------------------------

def load_picker_cache(path: Path) -> Optional[dict]:
    """Return the picker_civ_order.json content (None if missing)."""
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# Live walk (optional) ---------------------------------------------------

def walk_picker_live() -> dict:
    """Walk the live picker and return a token -> position dict.

    Imports lobby_driver lazily so the validator works without the game.
    """
    from tools.aoe3_automation.lobby_driver import (
        load_coords, reset_p1_to_random, open_civ_picker, cancel_civ_picker,
        scroll_down_fast, scroll_up_fast, _shot_lobby, HOME_CITY_TO_TOKEN,
    )
    from PIL import Image
    import pytesseract
    import time

    coords = load_coords()
    cp = coords["civ_picker"]
    crop = cp.get("leader_name_crop", {"x0": 80, "x1": 1100,
                                       "y0_off": -22, "y1_off": 22})

    try:
        cancel_civ_picker(coords); time.sleep(1)
    except Exception:
        pass
    reset_p1_to_random(coords); time.sleep(2)
    open_civ_picker(coords); time.sleep(1.5)
    scroll_up_fast(coords, n=80); time.sleep(0.5)

    seen: dict[str, dict] = {}
    last_sig = ""
    for s in range(80):
        shot = Path(f"/tmp/civ_loadability_walk_{s:02d}.png")
        _shot_lobby(shot)
        im = Image.open(shot)
        rows: list[str] = []
        for r in range(10):
            y = cp["row_y_start"] + r * cp["row_spacing"]
            box = (crop["x0"], y + crop["y0_off"],
                   crop["x1"], y + crop["y1_off"])
            sub = im.crop(box).convert("L")
            sub = sub.resize((sub.width * 3, sub.height * 3), Image.LANCZOS)
            txt = pytesseract.image_to_string(sub, config="--psm 7").strip()
            rows.append(txt)
        sig = "|".join(t[:8] for t in rows)
        if sig == last_sig:
            break
        last_sig = sig
        for r, t in enumerate(rows):
            if t and t not in seen:
                seen[t] = {"scroll": s, "row": r, "raw": t}
        scroll_down_fast(coords, n=1); time.sleep(0.3)
    cancel_civ_picker(coords)
    return seen


# Diff logic -------------------------------------------------------------

def diff_civs_against_cache(
    civs: list[dict],
    cache: dict,
) -> dict:
    """Compare civmods ANW civs vs cache entries; return per-civ verdict.

    Verdict logic (StatsID class is AUTHORITATIVE — we confirmed empirically
    on 2026-05-08 that digit-prefix StatsIDs don't load in the picker, no
    matter what the cache claims; the cache may have been built with a
    fuzzy OCR matcher that incorrectly attributed base-game-civ rows to
    ANW tokens):

      - DIGIT_PREFIX_NEW or OTHER → FAIL (engine drops these). Cache entry
        is treated as a false-positive from the cache builder.
      - BASE_GAME_FORMAT + in cache → PASS
      - BASE_GAME_FORMAT + NOT in cache → WARN (probably stale cache)
      - EMPTY → FAIL (malformed civmods entry)
    """
    cache_entries = (cache or {}).get("entries", {})
    results: list[dict] = []
    counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for civ in civs:
        tok = civ["token"]
        in_cache = tok in cache_entries
        sclass = civ["statsid_class"]

        if sclass == "EMPTY":
            verdict = "FAIL"
            why = "no <StatsID> element"
        elif sclass == "BASE_GAME_FORMAT":
            if in_cache:
                verdict = "PASS"
                why = (f"StatsID={civ['statsid']!r} replaces a base game "
                       f"slot and appears in picker cache")
            else:
                verdict = "WARN"
                why = (f"StatsID={civ['statsid']!r} is base-game-style but "
                       f"missing from cache; cache may be stale "
                       f"(run --live to refresh)")
        elif sclass == "DIGIT_PREFIX_NEW":
            verdict = "FAIL"
            why = (f"StatsID={civ['statsid']!r} is digit-prefix '1X' format. "
                   f"AoE3 DE's engine does NOT load civs with this StatsID "
                   f"format into the lobby picker. Empirically confirmed "
                   f"2026-05-08: 25 such civs were silently dropped from "
                   f"the picker. Use a 2-char alpha StatsID that replaces "
                   f"a base game slot, OR find the engine's civ-registry "
                   f"override mechanism.")
        else:  # OTHER
            verdict = "FAIL"
            why = (f"StatsID={civ['statsid']!r} class={sclass}. Engine's "
                   f"loadable-StatsID format is 2-char uppercase alpha "
                   f"(matches base game civ slot pattern).")
        counts[verdict] += 1
        results.append({
            "token": tok,
            "statsid": civ["statsid"],
            "statsid_class": sclass,
            "display_name_id": civ["display_name_id"],
            "in_cache": in_cache,
            "verdict": verdict,
            "why": why,
        })
    return {
        "counts": counts,
        "total": len(civs),
        "results": results,
    }


# Reporting --------------------------------------------------------------

def print_report(report: dict) -> None:
    c = report["counts"]
    n = report["total"]
    print("=" * 70)
    print("CIV LOADABILITY")
    print("=" * 70)
    print(f"Total ANW civs in civmods.xml: {n}")
    print(f"  PASS  (loadable in picker):  {c['PASS']:>3}")
    print(f"  WARN  (missing — cache stale?): {c['WARN']:>3}")
    print(f"  FAIL  (engine drops these):  {c['FAIL']:>3}")
    print()

    fails = [r for r in report["results"] if r["verdict"] == "FAIL"]
    warns = [r for r in report["results"] if r["verdict"] == "WARN"]
    if fails:
        print(f"FAIL ({len(fails)}):")
        for r in fails:
            print(f"  {r['token']:<28} StatsID={r['statsid']:<5} → {r['why']}")
        print()
    if warns:
        print(f"WARN ({len(warns)}):")
        for r in warns:
            print(f"  {r['token']:<28} StatsID={r['statsid']:<5} → {r['why']}")
        print()


# CLI --------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--civmods", type=Path,
                    default=REPO_ROOT / "data" / "civmods.xml")
    ap.add_argument("--cache", type=Path,
                    default=REPO_ROOT / "tools" / "aoe3_automation"
                    / "picker_civ_order.json")
    ap.add_argument("--live", action="store_true",
                    help="walk the live picker instead of using the cache "
                         "(slow; requires the game running at the lobby)")
    ap.add_argument("--json", type=Path,
                    help="write the full report as JSON")
    args = ap.parse_args()

    civs = load_anw_civs_from_civmods(args.civmods)

    if args.live:
        print("Walking live picker (this is slow)…", file=sys.stderr)
        live = walk_picker_live()
        # Convert raw OCR'd rows to a token cache via the same matcher logic
        # used by lobby_driver — for simplicity, treat any token whose
        # display_name appears in a live-walk raw_text as PASS.
        from tools.aoe3_automation.lobby_driver import _identify_civ_from_ocr
        # Need ref for _identify; load enriched_reference if present
        ref_path = REPO_ROOT / "enriched_reference.json"
        ref = json.loads(ref_path.read_text()) if ref_path.exists() else \
              {"civs": {c["token"]: {} for c in civs}}
        seen_tokens: set[str] = set()
        for raw, info in live.items():
            tok = _identify_civ_from_ocr(raw, ref)
            if tok:
                seen_tokens.add(tok)
        cache = {"entries": {t: {"scroll_count": 0, "click_row": 0,
                                  "raw_ocr": "live walk"}
                              for t in seen_tokens}}
    else:
        cache = load_picker_cache(args.cache)
        if cache is None:
            print(f"ERROR: cache not found at {args.cache}. "
                  f"Run lobby_driver.py --map-picker first or use --live.",
                  file=sys.stderr)
            return 2

    report = diff_civs_against_cache(civs, cache)
    print_report(report)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Report: {args.json}")

    return 1 if report["counts"]["FAIL"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
