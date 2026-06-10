#!/usr/bin/env python3
"""Static validator: every `tools/<...>.py` script AND every `artifacts/<...>`
file referenced in the wiki must point at a path that actually exists on disk.

Born from a recurring drift class: wiki "## Tools" tables, "Sources" sections,
and cross-reference links cite repo files by path, but those paths rot when a
file is renamed, moved, or regenerated under a new name. Live examples:

  * docs/wiki/replays-scenarios.md cited a phantom
    `tools/aoe3_automation/scenario_emitter.py` (the real one lives at
    `tools/validation/scenario_emitter.py`).
  * docs/wiki/file-formats/l33t.md linked the same dead path.

A dead link teaches a reader to run a command (or open an artifact) that does
not exist, and silently erodes trust in the whole section. This validator
walks every markdown file under docs/wiki/, extracts each `tools/....py` and
`artifacts/...<ext>` token (whether in a link target or inline code), and
asserts each path exists.

Note: `data/*.xml` overlay paths are deliberately NOT checked here — those
have legitimate "this file does NOT ship" negative mentions in prose and are
covered by validate_wiki_phantom_data_files.py instead.

Usage:
    python3 tools/validation/validate_wiki_tool_links.py

Exit codes:
    0 — every wiki-referenced tools/*.py and artifacts/* path resolves (GREEN)
    1 — at least one referenced path is missing (RED)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WIKI = REPO / "docs" / "wiki"

# Matches `tools/<segments>/<name>.py` with no whitespace, the canonical way
# the wiki references a repo script (in link targets or inline `code`).
TOOL_RE = re.compile(r"tools/[A-Za-z0-9_./-]+\.py")
# Matches `artifacts/<segments>/<name>.<ext>` — extracted dumps, JSON maps,
# checklists, etc. that docs cite as evidence/sources.
ARTIFACT_RE = re.compile(
    r"artifacts/[A-Za-z0-9_./-]+\.(?:xaml|xml|json|html|md|png|txt)")


def main() -> int:
    if not WIKI.is_dir():
        print(f"FAIL — wiki directory not found: {WIKI.relative_to(REPO)}")
        return 1

    missing: list[str] = []
    checked = 0
    docs = 0

    for md in sorted(WIKI.rglob("*.md")):
        text = md.read_text(encoding="utf-8", errors="ignore")
        refs = set(TOOL_RE.findall(text)) | set(ARTIFACT_RE.findall(text))
        if refs:
            docs += 1
        for ref in sorted(refs):
            checked += 1
            if not (REPO / ref).exists():
                rel = md.relative_to(REPO)
                kind = "tool" if ref.startswith("tools/") else "artifact"
                missing.append(f"{rel}: references missing {kind} {ref}")

    print("Wiki link check (every tools/*.py and artifacts/* reference must exist)")
    print(f"  scanned {docs} wiki docs, {checked} repo-path references")
    print()

    if missing:
        print("FAIL — wiki references dead repo paths:")
        for m in missing:
            print(f"  {m}")
        return 1

    print(f"PASS — all {checked} wiki-referenced tool/artifact paths resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
