#!/usr/bin/env python3
"""Static validator: known non-existent data-overlay files must never be
presented inside a fenced code block in the wiki.

ANW does NOT ship several overlay files that the generic DE naming pattern
*could* imply:

  * data/stringmods.xml      — the real stringtable overlay is per-locale at
                               data/strings/<lang>/stringmods.xml
  * data/protoymods.xml      — no `protoy`-branch overlay ships
  * data/techtreeymods.xml   — no `techtreey`-branch overlay ships
  * data/civmodsy.xml        — no `civsy`-branch overlay ships

A wiki doc may legitimately MENTION these inline (in prose / backticks) to
say "there is no top-level data/stringmods.xml". What it must NOT do is list
them inside a ```fenced code block``` — a fence presents a path as a real,
copy-pasteable file, which is exactly the drift this catches: additive-data-
mods.md once listed `data/stringmods.xml`, `data/techtreeymods.xml`, and
`data/protoymods.xml` in a code block as if they shipped.

The fence/inline distinction is the rule:
  * inside a ``` ... ``` fence  -> treated as "this file exists" -> FAIL
  * inline backticks in prose    -> allowed (used for negative assertions)

Usage:
    python3 tools/validation/validate_wiki_phantom_data_files.py

Exit codes:
    0 — no phantom overlay file appears inside any wiki code fence (GREEN)
    1 — a phantom overlay file is presented as real in a code fence (RED)
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WIKI = REPO / "docs" / "wiki"

# Overlay filenames that do NOT exist in this repo. Each is double-checked at
# runtime: if one of these ever starts shipping, drop it from this set.
PHANTOM = [
    "data/stringmods.xml",
    "data/protoymods.xml",
    "data/techtreeymods.xml",
    "data/civmodsy.xml",
]


def code_fence_lines(text: str) -> list[tuple[int, str]]:
    """Return (lineno, line) for every line inside a ``` fenced block."""
    out: list[tuple[int, str]] = []
    in_fence = False
    for i, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            out.append((i, line))
    return out


def main() -> int:
    errors: list[str] = []

    # Sanity: confirm the phantom set really is phantom (guards against the
    # validator going stale if a file later starts shipping).
    for p in PHANTOM:
        if (REPO / p).is_file():
            errors.append(
                f"phantom set is stale: {p} now exists — remove it from PHANTOM")

    fences_scanned = 0
    for md in sorted(WIKI.rglob("*.md")):
        text = md.read_text(encoding="utf-8", errors="ignore")
        fence_lines = code_fence_lines(text)
        if fence_lines:
            fences_scanned += 1
        for lineno, line in fence_lines:
            for p in PHANTOM:
                if p in line:
                    rel = md.relative_to(REPO)
                    errors.append(
                        f"{rel}:{lineno}: phantom overlay file {p} presented "
                        f"inside a code fence (mention it inline in prose if you "
                        f"mean it does NOT ship)")

    print("Wiki phantom-data-file check (no non-existent overlay in a code fence)")
    print(f"  scanned {fences_scanned} wiki docs containing code fences")
    print(f"  phantom set: {', '.join(PHANTOM)}")
    print()

    if errors:
        print("FAIL — phantom overlay files presented as real:")
        for e in errors:
            print(f"  {e}")
        return 1

    print("PASS — no phantom overlay file appears inside any wiki code fence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
