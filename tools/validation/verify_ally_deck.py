#!/usr/bin/env python3
"""Cross-check ally home-city deck assignments for every ANW civ.

For each ANW civ:

  1. Locate the home-city XML (``data/anwhomecity<civ_lower>.xml`` —
     either declared via civmods.xml ``<homecityfilename>`` or by the
     conventional filename).
  2. Extract ``<deck><name>`` and ``<deck><cards>`` of the *default*
     deck (deck-0 = the first ``<deck>`` element, which carries the
     ``<default />`` marker on every ANW civ).
  3. Look up the expected deck card set in ``data/decks_anw.json`` (the
     canonical ANW deck source — keyed by civmods civ token; the HTML
     reference uses ``data/decks_anw.json['<civ>']`` everywhere).
     ``data/decks.json`` is checked as a fallback.
  4. Compare home-city XML deck-0 cards to the JSON deck (set-equal,
     ignoring order). Report any drift.
  5. If ``artifacts/validation/visual_art/<civ>/04_ally_homecity.png``
     exists, OCR it and verify the visible deck name ("A New World")
     matches what the XML declares.

Writes per-civ PASS / FAIL to:

  - ``artifacts/validation/ally_deck_compliance.json``
  - ``artifacts/validation/ally_deck_compliance.md``
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(REPO))
from tools.migration.anw_mapping import engine_token_for  # noqa: E402
INVENTORY = REPO / "tools" / "validation" / "art_inventory.json"
DECKS_ANW = REPO / "data" / "decks_anw.json"
DECKS = REPO / "data" / "decks.json"
VISUAL_DIR = REPO / "artifacts" / "validation" / "visual_art"
OUT_JSON = REPO / "artifacts" / "validation" / "ally_deck_compliance.json"
OUT_MD = REPO / "artifacts" / "validation" / "ally_deck_compliance.md"
# Spec-required alias output path (same content, different filename so the
# contact-sheet tooling can reference it without knowing the compliance name).
OUT_JSON_VERIFICATION = REPO / "artifacts" / "validation" / "ally_deck_verification.json"

# decks.json uses short, slightly different civ keys than civmods. Map
# civmods-civ → decks.json-key for fallback lookups. Civs not in this
# table fall back to a heuristic strip("ANW").
_DECKS_JSON_FALLBACK = {
    "ANWArgentines": "Argentines",
    "ANWBarbary": "Barbary",
    "ANWBrazil": "Brazilians",
    "ANWCanadians": "Canadians",
    "ANWChileans": "Chileans",
    "ANWColumbians": "Colombians",
    "ANWEgyptians": "Egyptians",
    "ANWFinnish": "Finns",
    "ANWHaitians": "Haitians",
    "ANWHungarians": "Hungarians",
    "ANWIndonesians": "Indonesians",
    "ANWMayans": "Mayans",
    "ANWMexicans": "Mexicans",
    "ANWNapoleonicFrance": "NapoleonicFrance",
    "ANWPeruvians": "Peruvians",
    "ANWRevFrance": "RevolutionaryFr",
    "ANWRomanians": "Romanians",
    "ANWSouthAfricans": "SouthAfricans",
    "ANWTexians": "Texians",
    "ANWUSA": "Americans",
}

_DEFAULT_DECK_RE = re.compile(
    r"<deck>\s*<name>([^<]+)</name>\s*<default\s*/>\s*<cards>(.*?)</cards>",
    re.DOTALL | re.IGNORECASE,
)
_FIRST_DECK_RE = re.compile(
    r"<deck>\s*<name>([^<]+)</name>.*?<cards>(.*?)</cards>",
    re.DOTALL | re.IGNORECASE,
)
_CARD_RE = re.compile(r"<card>([^<]+)</card>", re.IGNORECASE)


def _flatten_age_deck(entry) -> set[str]:
    """Convert decks_anw.json[civ] (age->cards) or decks.json[civ] same shape
    into a flat set of card names."""
    cards: set[str] = set()
    if isinstance(entry, dict):
        for v in entry.values():
            if isinstance(v, list):
                cards.update(str(c).strip() for c in v if c)
    elif isinstance(entry, list):
        cards.update(str(c).strip() for c in entry if c)
    return cards


def _parse_homecity_deck(xml_path: Path) -> tuple[str, set[str]]:
    """Return (deck_name, set_of_card_names) for the default deck.

    Falls back to the first <deck> if none is marked <default />.
    """
    text = xml_path.read_text(encoding="utf-8", errors="replace")
    m = _DEFAULT_DECK_RE.search(text)
    if not m:
        m = _FIRST_DECK_RE.search(text)
    if not m:
        return "", set()
    name = m.group(1).strip()
    cards = {c.strip() for c in _CARD_RE.findall(m.group(2))}
    return name, cards


def _resolve_homecity_path(civ: str, inv_civs: dict) -> Path | None:
    rec = inv_civs.get(civ, {})
    surfaces = rec.get("art_surfaces") or {}
    hc = surfaces.get("homecity_filename") or {}
    rel = hc.get("path")
    if rel:
        p = REPO / rel
        if p.exists():
            return p
    # Convention fallback: data/anwhomecity<lower>.xml
    stem = civ.replace("ANW", "").lower()
    cand = REPO / "data" / f"anwhomecity{stem}.xml"
    if cand.exists():
        return cand
    return None


def _ocr_check(civ: str) -> dict:
    """Best-effort OCR of 04_ally_homecity.png; SKIPPED if no file or OCR unavailable."""
    img = VISUAL_DIR / civ / "04_ally_homecity.png"
    if not img.exists():
        return {"status": "SKIPPED", "reason": "no 04_ally_homecity.png"}
    try:
        sys.path.insert(0, str(REPO / "tools" / "validation"))
        from ocr_validator import OCRValidator  # type: ignore
    except Exception as exc:
        return {"status": "SKIPPED", "reason": f"OCR import failed: {exc}"}
    ocr = OCRValidator()
    try:
        result = ocr.extract_text(img)
    except Exception as exc:
        return {"status": "ERROR", "reason": f"OCR raised: {exc}"}
    if result.get("status") != "OK":
        return {"status": "SKIPPED", "reason": result.get("error", "OCR not OK")}
    raw = (result.get("raw_text") or "").lower()
    visible_match = "a new world" in raw
    return {
        "status": "PASS" if visible_match else "FAIL",
        "expected_deck_name": "A New World",
        "saw_in_ocr": visible_match,
        "ocr_chars": len(raw),
    }


def verify_one(civ: str, inv_civs: dict, decks_anw: dict, decks: dict) -> dict:
    out = {
        "civ": civ,
        "homecity_xml": None,
        "homecity_deck_name": None,
        "homecity_card_count": 0,
        "json_deck_source": None,
        "json_card_count": 0,
        "extra_in_xml": [],
        "missing_in_xml": [],
        "static_check": "FAIL",
        "visual_check": "SKIPPED",
        "visual_reason": "",
        "notes": [],
    }
    hc_path = _resolve_homecity_path(civ, inv_civs)
    if not hc_path:
        out["static_check"] = "FAIL"
        out["notes"].append("home city XML not found")
        return out
    out["homecity_xml"] = str(hc_path.relative_to(REPO))
    deck_name, hc_cards = _parse_homecity_deck(hc_path)
    out["homecity_deck_name"] = deck_name
    out["homecity_card_count"] = len(hc_cards)

    # Resolve JSON deck: prefer decks_anw.json (canonical for ANW), else decks.json.
    # 22 legacy civs use engine-truth tokens in decks_anw.json (XPAztec, British,
    # DEAmericans, …). engine_token_for() bridges canonical → engine namespace.
    json_cards: set[str] = set()
    json_src: str | None = None
    engine_key = engine_token_for(civ)
    if civ in decks_anw:
        json_cards = _flatten_age_deck(decks_anw[civ])
        json_src = f"decks_anw.json[{civ!r}]"
    elif engine_key in decks_anw:
        json_cards = _flatten_age_deck(decks_anw[engine_key])
        json_src = f"decks_anw.json[{engine_key!r}]"
    else:
        # Try base-civ name (strip ANW prefix) — legacy fallback before
        # engine_token_for existed; keep for any decks_anw.json keys that
        # don't follow the engine-token convention.
        base = civ.replace("ANW", "", 1)
        if base in decks_anw:
            json_cards = _flatten_age_deck(decks_anw[base])
            json_src = f"decks_anw.json[{base!r}]"
        else:
            short = _DECKS_JSON_FALLBACK.get(civ)
            if short and short in decks:
                json_cards = _flatten_age_deck(decks[short])
                json_src = f"decks.json[{short!r}]"
    out["json_deck_source"] = json_src
    out["json_card_count"] = len(json_cards)

    if not json_cards:
        out["notes"].append("no JSON deck found for this civ")
    if hc_cards and json_cards:
        extra = sorted(hc_cards - json_cards)
        missing = sorted(json_cards - hc_cards)
        out["extra_in_xml"] = extra
        out["missing_in_xml"] = missing
        out["static_check"] = "PASS" if (not extra and not missing) else "FAIL"
    elif hc_cards and not json_cards:
        # Static check still useful: confirm there IS a deck named "A New World"
        out["static_check"] = "PASS" if "A New World" in (deck_name or "") else "FAIL"
        out["notes"].append("no JSON deck — fell back to deck-name presence check")
    else:
        out["static_check"] = "FAIL"
        out["notes"].append("home city XML has no <deck>")

    # OCR visual check (skipped when no screenshot has been captured yet)
    ocr_res = _ocr_check(civ)
    out["visual_check"] = ocr_res.get("status", "SKIPPED")
    out["visual_reason"] = ocr_res.get("reason", "") or ocr_res.get("saw_in_ocr", "")

    return out


def _markdown_report(records: list[dict]) -> str:
    total = len(records)
    static_pass = sum(1 for r in records if r["static_check"] == "PASS")
    visual_pass = sum(1 for r in records if r["visual_check"] == "PASS")
    visual_skipped = sum(1 for r in records if r["visual_check"] == "SKIPPED")
    lines = [
        "# ANW Ally-Deck Compliance Report",
        "",
        f"- Total civs checked: **{total}**",
        f"- Static XML-vs-JSON deck cross-check PASS: **{static_pass}/{total}**",
        f"- Visual (OCR of 04_ally_homecity.png) PASS: **{visual_pass}**, "
        f"SKIPPED: **{visual_skipped}**",
        "",
        "| civ | static | visual | XML deck | JSON src | XML cards | JSON cards | extra | missing |",
        "|-----|--------|--------|----------|----------|-----------|------------|-------|---------|",
    ]
    for r in sorted(records, key=lambda x: x["civ"]):
        lines.append(
            "| {civ} | {sc} | {vc} | {dn} | {js} | {xc} | {jc} | {ex} | {ms} |".format(
                civ=r["civ"],
                sc=r["static_check"],
                vc=r["visual_check"],
                dn=(r["homecity_deck_name"] or ""),
                js=(r["json_deck_source"] or "—"),
                xc=r["homecity_card_count"],
                jc=r["json_card_count"],
                ex=len(r["extra_in_xml"]),
                ms=len(r["missing_in_xml"]),
            )
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description=(
            "Cross-check ally home-city deck assignments for every ANW civ. "
            "For each civ: parses the home-city XML deck, compares card sets "
            "against decks_anw.json, and (if available) OCR-checks "
            "04_ally_homecity.png. "
            "Outputs artifacts/validation/ally_deck_compliance.json and .md."
        )
    )
    ap.add_argument(
        "--civ",
        metavar="TOKEN",
        help="Only check one civ (e.g. ANWBritish). Omit to check all 46.",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Also print the JSON report to stdout.",
    )
    args = ap.parse_args(argv)

    if not INVENTORY.exists():
        print(f"ERROR: missing {INVENTORY}", file=sys.stderr)
        return 1
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    inv_civs = inv.get("civs", {})
    decks_anw = json.loads(DECKS_ANW.read_text(encoding="utf-8")) if DECKS_ANW.exists() else {}
    decks = json.loads(DECKS.read_text(encoding="utf-8")) if DECKS.exists() else {}

    anw_all = sorted(c for c in inv_civs if c.startswith("ANW"))
    if args.civ:
        if args.civ not in anw_all:
            print(f"ERROR: unknown civ {args.civ!r}. Use one of: {', '.join(anw_all[:5])} …",
                  file=sys.stderr)
            return 2
        anw = [args.civ]
    else:
        anw = anw_all
    records = [verify_one(civ, inv_civs, decks_anw, decks) for civ in anw]

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(
            {
                "_meta": {
                    "total": len(records),
                    "static_pass": sum(1 for r in records if r["static_check"] == "PASS"),
                    "visual_pass": sum(1 for r in records if r["visual_check"] == "PASS"),
                    "visual_skipped": sum(1 for r in records if r["visual_check"] == "SKIPPED"),
                },
                "civs": records,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    OUT_MD.write_text(_markdown_report(records), encoding="utf-8")
    # Write spec-required alias (same content as OUT_JSON).
    OUT_JSON_VERIFICATION.write_text(OUT_JSON.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"wrote {OUT_JSON.relative_to(REPO)} ({OUT_JSON.stat().st_size:,} B)")
    print(f"wrote {OUT_JSON_VERIFICATION.relative_to(REPO)} ({OUT_JSON_VERIFICATION.stat().st_size:,} B)")
    print(f"wrote {OUT_MD.relative_to(REPO)} ({OUT_MD.stat().st_size:,} B)")
    static_pass = sum(1 for r in records if r["static_check"] == "PASS")
    static_fail = sum(1 for r in records if r["static_check"] == "FAIL")
    visual_pass = sum(1 for r in records if r["visual_check"] == "PASS")
    visual_skip = sum(1 for r in records if r["visual_check"] == "SKIPPED")
    print(
        f"  civs={len(records)}  static_pass={static_pass}  static_fail={static_fail}  "
        f"visual_pass={visual_pass}  visual_skipped={visual_skip}"
    )
    # Print final PASS/FAIL summary line
    if static_fail == 0:
        print("PASS — all static deck cross-checks passed")
    else:
        print(f"FAIL — {static_fail} civ(s) with deck mismatches:")
        for r in records:
            if r["static_check"] == "FAIL":
                notes = "; ".join(r.get("notes") or [])
                extra = len(r.get("extra_in_xml") or [])
                miss = len(r.get("missing_in_xml") or [])
                print(f"  {r['civ']}: extra={extra} missing={miss}"
                      + (f" ({notes})" if notes else ""))

    if args.json:
        report = {
            "_meta": {
                "total": len(records),
                "static_pass": static_pass,
                "visual_pass": visual_pass,
                "visual_skipped": visual_skip,
            },
            "civs": records,
        }
        print(json.dumps(report, indent=2))
    return 0 if static_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
