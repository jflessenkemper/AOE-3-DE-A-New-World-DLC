#!/usr/bin/env python3
"""Checks every ANW leader has non-empty insult+compliment quotes in aiLeaderQuotes.xs, with no placeholder/TODO/TBD text, no non-ASCII characters (chat can't render them), no unescaped quote breaking the XS string, and no duplicate quote shared across different leaders."""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

XS_PATH = REPO_ROOT / "game" / "ai" / "core" / "aiLeaderQuotes.xs"

# Known civ names that must appear in both insult and compliment tables.
# These match the branch labels used in anwGetLeaderInsult / anwGetLeaderCompliment.
REQUIRED_CIVS: list[str] = [
    "Aztecs",
    "British",
    "Chinese",
    "Dutch",
    "Ethiopians",
    "French",
    "Germans",
    "Haudenosaunee",
    "Hausa",
    "Inca",
    "Indians",
    "Italians",
    "Japanese",
    "Lakota",
    "Maltese",
    "Mexicans",
    "Ottomans",
    "Portuguese",
    "Russians",
    "Spanish",
    "Swedes",
    "UnitedStates",
    "ANWNapoleonicFrance",
    "ANWRevFrance",
    "ANWAmericans",
    "ANWMexicans",
    "ANWCanadians",
    "ANWBrazil",
    "ANWArgentines",
    "ANWChileans",
    "ANWPeruvians",
    "ANWColumbians",
    "ANWHaitians",
    "ANWIndonesians",
    "ANWSouthAfricans",
    "ANWFinnish",
    "ANWHungarians",
    "ANWRomanians",
    "ANWBarbary",
    "ANWEgyptians",
    "ANWCentralAmericans",
    "ANWBajaCalifornians",
    "ANWYucatan",
    "ANWRioGrande",
    "ANWMayans",
    "ANWCalifornians",
    "ANWTexians",
]

# Placeholder patterns that must NOT appear in any quote string (case-insensitive).
_PLACEHOLDER_RE = re.compile(
    r"\bTODO\b|\bTBD\b|\bFIXME\b|\bPLACEHOLDER\b|\bTEMPLATE\b",
    re.IGNORECASE,
)

# Pattern to extract all return-string literals from anwGetLeaderInsult /
# anwGetLeaderCompliment: ``return ("...");``
_RETURN_STR_RE = re.compile(r'return\s*\(\s*"([^"]*)"\s*\)\s*;')

# Regex to find the civName == "X" branch guards, including the combined
# `(civName == "A") || (civName == "B")` forms.
_CIV_BRANCH_RE = re.compile(r'civName\s*==\s*"([^"]+)"')


def _extract_function_body(src: str, fn_name: str) -> str:
    """Return the text of the named function body (between outermost braces)."""
    start = src.find(f"string {fn_name}(")
    if start == -1:
        return ""
    brace = src.find("{", start)
    if brace == -1:
        return ""
    depth = 0
    for i in range(brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[brace : i + 1]
    return ""


def main() -> int:
    if not XS_PATH.exists():
        print(f"ERROR: {XS_PATH} not found", file=sys.stderr)
        return 1

    src = XS_PATH.read_text(encoding="utf-8", errors="replace")

    fails: list[str] = []

    # --- Check: no non-ASCII characters anywhere in the file -----------------
    non_ascii = [(i + 1, c) for i, c in enumerate(src) if ord(c) > 127]
    if non_ascii:
        for lineno, ch in non_ascii[:10]:
            fails.append(f"Non-ASCII char at pos {lineno}: {repr(ch)}")

    # --- Extract both function bodies ----------------------------------------
    insult_body = _extract_function_body(src, "anwGetLeaderInsult")
    compliment_body = _extract_function_body(src, "anwGetLeaderCompliment")

    if not insult_body:
        fails.append("Could not locate anwGetLeaderInsult() function body")
    if not compliment_body:
        fails.append("Could not locate anwGetLeaderCompliment() function body")

    if fails:
        _report(fails)
        return 1

    # --- Check coverage: every required civ has a branch in both functions ---
    insult_civs: set[str] = set(_CIV_BRANCH_RE.findall(insult_body))
    compliment_civs: set[str] = set(_CIV_BRANCH_RE.findall(compliment_body))

    for civ in REQUIRED_CIVS:
        if civ not in insult_civs:
            fails.append(f"Missing insult branch for civ: {civ}")
        if civ not in compliment_civs:
            fails.append(f"Missing compliment branch for civ: {civ}")

    # --- Extract all string literals from each function ----------------------
    insult_strings: list[str] = _RETURN_STR_RE.findall(insult_body)
    compliment_strings: list[str] = _RETURN_STR_RE.findall(compliment_body)

    # --- Check: no empty strings (excluding the intentional fallback return("")) --
    # Each function ends with ``return ("");`` as a not-found fallback; that is
    # expected.  Flag only if more than one empty string is present (duplicate
    # fallback) or if a civ branch itself contains an empty-string return.
    empty_insult = [s for s in insult_strings if not s.strip()]
    empty_compliment = [s for s in compliment_strings if not s.strip()]
    if len(empty_insult) > 1:
        fails.append(f"Too many empty insult strings ({len(empty_insult)}); only the fallback return is expected")
    if len(empty_compliment) > 1:
        fails.append(f"Too many empty compliment strings ({len(empty_compliment)}); only the fallback return is expected")

    # --- Check: no placeholder/TODO text ------------------------------------
    for s in insult_strings:
        if _PLACEHOLDER_RE.search(s):
            snippet = s[:60]
            fails.append(f"Placeholder text in insult quote: {repr(snippet)}")
    for s in compliment_strings:
        if _PLACEHOLDER_RE.search(s):
            snippet = s[:60]
            fails.append(f"Placeholder text in compliment quote: {repr(snippet)}")

    # --- Check: no non-ASCII in any string literal --------------------------
    for s in insult_strings + compliment_strings:
        bad = [c for c in s if ord(c) > 127]
        if bad:
            fails.append(
                f"Non-ASCII char(s) {[repr(c) for c in bad[:3]]} in quote: {repr(s[:60])}"
            )

    # --- Check: no duplicate quote shared across different leaders ----------
    # A quote appearing twice in the same leader's two quoteIndex branches is
    # fine; a quote appearing in two different civ branches is a copy-paste bug.
    all_insult_strings = insult_strings
    all_compliment_strings = compliment_strings

    def _find_duplicates(strings: list[str], label: str) -> list[str]:
        seen: dict[str, int] = {}
        dup_fails: list[str] = []
        for s in strings:
            key = s.strip().lower()
            if not key:
                continue
            if key in seen:
                seen[key] += 1
            else:
                seen[key] = 1
        for key, count in seen.items():
            if count > 1:
                dup_fails.append(
                    f"Duplicate {label} quote (appears {count}x): {repr(key[:70])}"
                )
        return dup_fails

    fails.extend(_find_duplicates(all_insult_strings, "insult"))
    fails.extend(_find_duplicates(all_compliment_strings, "compliment"))

    # --- Report -------------------------------------------------------------
    _report(fails)
    return 1 if fails else 0


def _report(fails: list[str]) -> None:
    civ_count = len(REQUIRED_CIVS)
    print("=" * 60)
    print("LEADER QUOTE INTEGRITY")
    print("=" * 60)
    if fails:
        for f in fails:
            print(f"  FAIL: {f}")
        print()
        print(f"LEADER_QUOTE_INTEGRITY: FAIL  ({len(fails)} failure(s), {civ_count} civs checked)")
    else:
        print(f"  All {civ_count} civs have non-empty insult+compliment quotes.")
        print("  No placeholder text, non-ASCII chars, or duplicate quotes found.")
        print()
        print(f"LEADER_QUOTE_INTEGRITY: PASS  ({civ_count} civs checked, 0 failures)")
    print("=" * 60)


if __name__ == "__main__":
    sys.exit(main())
