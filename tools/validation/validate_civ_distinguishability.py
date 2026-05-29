#!/usr/bin/env python3
"""Verify each ANW civ's DisplayName resolves to a unique, correct string.

Bug class this catches (hit on 2026-05-08): the lobby rendered
"Friedrich the Great" for ANWDutch because two civs' DisplayNameIDs
pointed at the same _locID due to stringmods duplicates. The user
spotted it visually; pre-deploy validation should catch it.

For every ANW civ in civmods.xml, this validator:
  1. Reads its ``<DisplayNameID>`` value (a _locID integer).
  2. Resolves that _locID via ``data/strings/<lang>/stringmods*.xml``.
  3. Asserts the resolved text is non-empty.
  4. Asserts the resolved text contains the civ's expected display name
     token from ``anw_token_map.ANW_CIVS`` (loose case-insensitive match).
  5. Asserts no two ANW civs resolve to the *same* string (collision check).

Usage::

    python3 tools/validation/validate_civ_distinguishability.py
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

sys.path.insert(0, str(REPO_ROOT))
from tools.migration.anw_token_map import ANW_CIVS  # noqa: E402


# Match ``<String _locID="N" [attr="…"]*>…</String>`` — captures id and body.
# Tolerant of attributes between _locID and ``>`` (e.g. ``symbol="…"``) and of
# case variation (``_locID`` vs ``_locid`` since base game uses lowercase).
_STRING_RE = re.compile(
    r'<[Ss]tring\s+_loc[iI][dD]="(\d+)"[^>]*>\s*(.*?)\s*</[Ss]tring>',
    re.DOTALL,
)


def build_locid_to_text(strings_dir: Path,
                       prefer_lang: str = "en") -> dict[str, str]:
    """Build _locID → text mapping. English preferred for collision check."""
    out: dict[str, str] = {}
    # Walk only the preferred-lang dir if it exists; else everything.
    lang_dir = strings_dir / prefer_lang
    if lang_dir.exists():
        roots = [lang_dir]
    else:
        roots = [strings_dir]
    for root in roots:
        for f in root.rglob("stringmods*.xml"):
            text = f.read_text(encoding="utf-8", errors="replace")
            for locid, body in _STRING_RE.findall(text):
                # First-write-wins: stringmods dedup runs first; we want
                # the canonical resolution. Don't overwrite.
                out.setdefault(locid, body.strip())
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--civmods", type=Path,
                    default=REPO_ROOT / "data" / "civmods.xml")
    ap.add_argument("--strings-dir", type=Path,
                    default=REPO_ROOT / "data" / "strings")
    ap.add_argument("--lang", default="en",
                    help="preferred language subdir under strings (default: en)")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    if not args.civmods.exists():
        print(f"ERROR: {args.civmods} not found", file=sys.stderr)
        return 2

    locid_to_text = build_locid_to_text(args.strings_dir, args.lang)

    print("=" * 60)
    print("ANW CIV DISTINGUISHABILITY")
    print("=" * 60)
    print(f"Loaded {len(locid_to_text)} _locID → text mappings "
          f"from {args.strings_dir}/{args.lang}/")
    print()

    root = ET.parse(args.civmods).getroot()

    unresolved: list[tuple[str, str]] = []   # (token, locid)
    wrong_text: list[tuple[str, str, str]] = []  # (token, expected, actual)
    collisions: dict[str, list[str]] = {}    # text → [tokens]
    ok: list[tuple[str, str]] = []           # (token, text)

    for civ in root.findall("civ"):
        n = civ.find("name")
        token = n.text if n is not None else ""
        if not token or token not in ANW_CIVS:
            continue
        # Skip revolution-only suppression entries (main=0): they are not
        # shown in the lobby picker and don't need a display name.
        main_el = civ.find("main")
        if main_el is not None and (main_el.text or "").strip() == "0":
            continue
        d = civ.find("displaynameid")
        if d is None or not (d.text or "").strip():
            unresolved.append((token, ""))
            continue
        locid = d.text.strip()
        text = locid_to_text.get(locid, "")
        if not text:
            unresolved.append((token, locid))
            continue

        expected = ANW_CIVS[token].get("display", "")
        # Loose match: expected display name appears (case-insensitive)
        # somewhere in the resolved string. Allows engine-decorated text
        # like "British (ANW)" or just "British".
        if expected and expected.lower() not in text.lower():
            wrong_text.append((token, expected, text))
            continue

        ok.append((token, text))
        collisions.setdefault(text, []).append(token)

    real_collisions = {t: toks for t, toks in collisions.items() if len(toks) > 1}

    print(f"  ✓ Resolved + correct text:  {len(ok):>3}/{len(ANW_CIVS)}")
    print(f"  ✗ Unresolved DisplayNameID: {len(unresolved):>3}")
    print(f"  ✗ Wrong text (mismatch):    {len(wrong_text):>3}")
    print(f"  ✗ Display-name collisions:  {len(real_collisions):>3}")
    print()

    if unresolved:
        print("FAIL — DisplayNameID does not resolve in stringmods:")
        for token, locid in unresolved[:15]:
            print(f"    {token}  DisplayNameID={locid or '(missing)'}")
        if len(unresolved) > 15:
            print(f"    … +{len(unresolved) - 15} more")
        print()

    if wrong_text:
        print("FAIL — resolved text doesn't contain expected display name:")
        for token, expected, actual in wrong_text[:15]:
            actual_short = actual[:60] + ("…" if len(actual) > 60 else "")
            print(f"    {token}  expected '{expected}'  got '{actual_short}'")
        if len(wrong_text) > 15:
            print(f"    … +{len(wrong_text) - 15} more")
        print()

    if real_collisions:
        print("FAIL — multiple ANW civs resolve to same display string "
              "(picker can't tell them apart):")
        for text, tokens in list(real_collisions.items())[:10]:
            print(f"    '{text}'  ←  {', '.join(tokens)}")
        if len(real_collisions) > 10:
            print(f"    … +{len(real_collisions) - 10} more")
        print()

    fail_count = len(unresolved) + len(wrong_text) + len(real_collisions)

    if args.json:
        import json
        args.json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w") as f:
            json.dump({
                "total": len(ANW_CIVS),
                "ok_count": len(ok),
                "unresolved": unresolved,
                "wrong_text": wrong_text,
                "collisions": real_collisions,
                "fail_count": fail_count,
            }, f, indent=2)
        print(f"Report: {args.json}")

    print(f"OVERALL: {'FAIL' if fail_count else 'PASS'} "
          f"({len(ok)}/{len(ANW_CIVS)} distinguishable)")
    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
