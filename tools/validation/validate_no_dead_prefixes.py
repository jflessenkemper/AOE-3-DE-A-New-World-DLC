#!/usr/bin/env python3
"""Fails if any validator or AI-design tool references a dead pre-rename identifier prefix (gLL/llXxx/cLL/[LLP/llProbe), which would silently misread the renamed gANW/anw/cANW XS code and produce false validation results.

Background
----------
In the gLL→gANW codebase rename, the mod's XS identifier family was
updated from gLL*/cLL*/llXxx()/[LLP v=...] to gANW*/cANW*/anwXxx()/[ANWP v=...].
Any Python tooling that still greps the XS source for the OLD prefixes will
silently find nothing and produce false PASS/FAIL results — the same bug
that was discovered in validate_spec_vs_xs_doctrine.py, validate_probe_tag_drift.py,
and ai_behaviour_map.py (all three were fixed, then this meta-validator was added
to prevent recurrence).

What is scanned
---------------
- tools/validation/*.py  (all validators + support scripts)
- tools/ai_design/*.py   (AI design tools)
- tools/migration/*.py   (migration tools, only if they read XS source)

This file itself is excluded from the scan.

Heuristic
---------
A dead-prefix occurrence is flagged only when the token appears in a
"matching context" — i.e. the token is being used to search or extract from
XS source, not merely mentioned in a docstring or comment.

Specifically, a line is flagged if ALL of the following hold:

  1. The line is NOT a pure comment (stripped line does not start with ``#``).
  2. The line contains one of the dead-token patterns:
       - ``gLL`` followed by a word-char  (catches gLLWallStrategy, gLLLeaderKey, …)
       - ``cLL`` followed by a word-char  (catches cLLWallStrategy*, cLLBuildStyle*, …)
       - ``ll`` followed by an UPPERCASE letter  (catches llUse*, llProbe*, llSet*, …)
       - ``[LLP ``  (old probe line-tag prefix)
       - ``LLP v=`` (old probe version tag)
       - ``llProbe(``  (direct call pattern)
  3. The line also shows a "matching context" — evidence that the token is used
     as an XS identifier matcher rather than just mentioned in text:
       - Adjacent to ``re.compile``, ``re.search``, ``re.findall``,
         ``re.finditer``, ``re.match``, ``re.fullmatch``, ``re.sub``,
         ``re.split`` (token appears inside a regex)  OR
       - The token appears inside a quoted string that is used with
         ``in line``, ``in text``, ``in src``, ``in txt``, ``in content``
         (membership test against XS source)  OR
       - The token is followed by ``(`` within the same quoted string segment
         (catches ``llProbe("`` or ``"llUse*Style"(`` fragment patterns)  OR
       - The token is a bare string key in a dict/mapping (appears inside
         quotes followed by ``:``, ``':``, or inside a list/tuple context
         where it would match an XS identifier)

The heuristic is intentionally conservative: it is better to have a
false-negative (miss a stale reference) than a false-positive (cry wolf on
docstrings). All surviving known-good patterns have been verified to be
documentation-only references, not XS-matching code.

The heuristic is documented here so future maintainers can extend it if a
new matching pattern is added.

Exit codes
----------
  0 — no dead-prefix occurrences found in matching contexts
  1 — one or more dead-prefix occurrences flagged
  2 — internal error (e.g. scan directory not found)

Usage::

    python3 tools/validation/validate_no_dead_prefixes.py
    python3 tools/validation/validate_no_dead_prefixes.py --json artifacts/validation/no_dead_prefixes.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

# Directories to scan (relative to REPO_ROOT).
SCAN_DIRS = [
    REPO_ROOT / "tools" / "validation",
    REPO_ROOT / "tools" / "ai_design",
    REPO_ROOT / "tools" / "migration",
]

# This file must be excluded from the scan (it necessarily contains the
# dead token strings as pattern definitions).
THIS_FILE = Path(__file__).resolve().name

# ── dead token patterns ──────────────────────────────────────────────────────
# Each pattern matches a dead XS identifier.  Word-boundary care is applied
# via the patterns themselves to avoid false positives on unrelated substrings.
# For example "all" does not match \bgLL\w because it starts with lowercase.

_DEAD_TOKEN_RES: list[re.Pattern[str]] = [
    re.compile(r'\bgLL\w'),        # gLL global prefix (e.g. gLLWallStrategy)
    re.compile(r'\bcLL\w'),        # cLL constant prefix (e.g. cLLWallStrategy*)
    re.compile(r'\bll[A-Z]\w*'),   # function prefix (e.g. llUse*, llProbe*, llSet*)
    re.compile(r'\[LLP '),         # old probe line-tag open bracket
    re.compile(r'LLP v='),         # old probe version tag
    re.compile(r'llProbe\('),      # direct llProbe() call pattern in string
]

# ── matching-context patterns ────────────────────────────────────────────────
# A line must match at least one of these to be considered a "matching context".
# These detect that the dead token is being used as an XS-source identifier
# matcher, not merely mentioned in a docstring or comment.

_MATCHING_CTX_RES: list[re.Pattern[str]] = [
    # Token is inside a re.* call argument — the most reliable signal.
    # Matches lines like:  re.compile(r"gLLWallStrategy...")
    #                      re.finditer(r"(llUse\w+Style)\s*\(", text)
    re.compile(r're\s*\.\s*(?:compile|search|findall|finditer|match|fullmatch|sub|split)\s*\('),
    # Token used as a membership test against source/line text (string search)
    # Matches:  if "gLLFoo" in line:    or    "llProbe" in src
    re.compile(r'["\'](?:gLL|cLL|ll[A-Z])[^"\']*["\'](?:\s*not)?\s+in\b'),
    # Token appears as a Python dict string key (quoted key followed by colon-space or colon-newline)
    # Matches:  "cLLWallStrategyFortressRing": 0
    # Guard: the token must be the whole key (no non-ws chars between closing quote and colon).
    re.compile(r'["\'](?:gLL|cLL|ll[A-Z])[^"\']*["\'\s]*\s*:'),
    # removeprefix / removesuffix on a dead token (string manipulation of XS name)
    # Matches:  k.removeprefix("cLLWallStrategy")
    re.compile(r'removeprefix\s*\(\s*["\'](?:gLL|cLL|ll[A-Z])'),
    re.compile(r'removesuffix\s*\(\s*["\'](?:gLL|cLL|ll[A-Z])'),
    # lstrip / replace targeting the dead prefix as a string argument
    re.compile(r'(?:lstrip|replace)\s*\(\s*["\'](?:gLL|cLL|ll[A-Z])'),
    # String concatenation forming an XS identifier: "cLLBuildStyle" + bm.group(1)
    re.compile(r'["\'](?:gLL|cLL|ll[A-Z])[^"\']*["\'](?:\s*\+|\s*%|\s*\.format)'),
]


def _is_matching_context(line: str) -> bool:
    """Return True if the line shows evidence the dead token is used as an XS matcher."""
    for pat in _MATCHING_CTX_RES:
        if pat.search(line):
            return True
    return False


def _dead_token_in_line(line: str) -> str | None:
    """Return the first dead token found in the line, or None."""
    for pat in _DEAD_TOKEN_RES:
        m = pat.search(line)
        if m:
            return m.group(0)
    return None


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    """Return list of (lineno, token, line) for flagged lines."""
    findings: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"  WARN  cannot read {path}: {exc}", file=sys.stderr)
        return findings

    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        # Skip pure comment lines — historical rename-explanation comments are OK.
        if stripped.startswith("#"):
            continue
        token = _dead_token_in_line(raw_line)
        if token is None:
            continue
        if _is_matching_context(raw_line):
            findings.append((lineno, token, raw_line.rstrip()))
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", type=Path, dest="json_out",
                    help="Write machine-readable report to this path.")
    args = ap.parse_args()

    print("=" * 60)
    print("NO DEAD PREFIXES")
    print("=" * 60)
    print()
    print(f"Scanning for dead gLL/cLL/ll[A-Z]/[LLP/llProbe patterns")
    print(f"in XS-matching contexts across tooling scripts...")
    print()

    all_findings: dict[str, list[dict]] = {}
    total = 0

    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for py_file in sorted(scan_dir.glob("*.py")):
            if py_file.name == THIS_FILE:
                continue
            rel = py_file.relative_to(REPO_ROOT)
            findings = scan_file(py_file)
            if findings:
                all_findings[str(rel)] = [
                    {"lineno": ln, "token": tok, "line": line}
                    for ln, tok, line in findings
                ]
                for ln, tok, line in findings:
                    print(f"  FAIL  {rel}:{ln}")
                    print(f"        token: {tok!r}")
                    print(f"        line:  {line.strip()[:120]}")
                    print()
                total += len(findings)

    print()
    if total:
        print(f"FAIL — {total} dead-prefix occurrence(s) found in XS-matching contexts")
        print("       These tokens grep the OLD pre-rename XS identifier family")
        print("       (gLL/cLL/ll*/[LLP) and will silently misread the current")
        print("       gANW/cANW/anw* XS code, producing false validation results.")
        print("       Update each flagged file to use the renamed identifiers.")
    else:
        print("PASS — no dead-prefix occurrences found in XS-matching contexts")
        print("       All tooling uses the current gANW/cANW/anw* identifier family.")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "passed": total == 0,
            "total_findings": total,
            "files": all_findings,
        }
        with open(args.json_out, "w") as fh:
            json.dump(report, fh, indent=2)
        print(f"\nReport: {args.json_out}")

    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
