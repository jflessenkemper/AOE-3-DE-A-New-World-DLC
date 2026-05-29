#!/usr/bin/env python3
"""Static validator: every probe tag read by validate_doctrine_compliance.py
has a corresponding emitter in XS code or the Python harness.

Catches the failure mode where a future edit to
``tools/validation/validate_doctrine_compliance.py`` references a new
probe tag (e.g. ``foo.bar``) that no part of the runtime ever emits —
the validator would silently pass on empty data, masking a coverage hole.

Detection strategy:

  1) Parse ``validate_doctrine_compliance.py`` for probe tags read from
     log lines, recognised by these access patterns::

         p.tag == "foo.bar"
         p.tag != "foo.bar"
         probe.tag == "foo.bar"
         _earliest_milestone(probes, "milestone.first_foo")

  2) Parse ``game/ai/core/*.xs`` and ``RandMaps/anwHubTest.xs`` for
     emitters::

         llProbe("foo.bar", …)                 (static)
         llProbe("foo." + tag, …)              (dynamic prefix)

  3) Parse ``tools/aoe3_automation/*.py`` for harness-emitted probes::

         "[LLP v=2 …tag=foo.bar"
         emit_probe("foo.bar", …)

  4) FAIL if any tag from (1) is not satisfied by (2) or (3) —
     either by exact static match, or by a dynamic XS prefix
     (e.g. ``milestone.first_barracks`` matches dyn prefix
     ``milestone.first_``).

Run::

    python3 tools/validation/validate_probe_tag_drift.py
    python3 tools/validation/validate_probe_tag_drift.py \\
        --json artifacts/validation/probe_tag_drift.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

VALIDATOR_PATH = REPO_ROOT / "tools" / "validation" / "validate_doctrine_compliance.py"
XS_DIRS = [REPO_ROOT / "game" / "ai" / "core"]
XS_EXTRA_FILES = [REPO_ROOT / "RandMaps" / "anwHubTest.xs"]
PY_HARNESS_DIR = REPO_ROOT / "tools" / "aoe3_automation"

# Patterns that read a probe tag from a log line — only these create a
# coverage requirement. (References purely in docstrings / comments /
# ClaimResult constructor args do NOT require an emitter.)
READ_PATTERNS = [
    re.compile(r'p\.tag\s*==\s*"([a-zA-Z][a-zA-Z0-9._]*)"'),
    re.compile(r'p\.tag\s*!=\s*"([a-zA-Z][a-zA-Z0-9._]*)"'),
    re.compile(r'probe\.tag\s*==\s*"([a-zA-Z][a-zA-Z0-9._]*)"'),
    re.compile(r'_earliest_milestone\([^,]+,\s*"([a-zA-Z][a-zA-Z0-9._]*)"'),
]
# Tag-in-tuple form: `p.tag in ("foo", "bar")`
READ_TUPLE_PATTERN = re.compile(r'\.tag\s+in\s+\(([^)]+)\)')


def collect_read_tags(validator_text: str) -> set[str]:
    """Tags that the validator reads from log probes."""
    tags: set[str] = set()
    for pat in READ_PATTERNS:
        for m in pat.finditer(validator_text):
            tags.add(m.group(1))
    for m in READ_TUPLE_PATTERN.finditer(validator_text):
        for inner in re.findall(r'"([a-zA-Z][a-zA-Z0-9._]*)"', m.group(1)):
            tags.add(inner)
    return tags


def collect_xs_emitters() -> tuple[set[str], set[str]]:
    """Return (static_tags, dynamic_prefixes) emitted by XS."""
    static: set[str] = set()
    dyn: set[str] = set()
    static_re = re.compile(r'llProbe\s*\(\s*"([a-zA-Z][a-zA-Z0-9._]*)"')
    dyn_re = re.compile(r'llProbe\s*\(\s*"([a-zA-Z][a-zA-Z0-9._]*)"\s*\+')
    xs_files: list[Path] = []
    for d in XS_DIRS:
        if d.exists():
            xs_files.extend(d.glob("*.xs"))
    xs_files.extend(f for f in XS_EXTRA_FILES if f.exists())
    for f in xs_files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in static_re.finditer(text):
            static.add(m.group(1))
        for m in dyn_re.finditer(text):
            dyn.add(m.group(1))
    return static, dyn


def collect_py_emitters() -> set[str]:
    """Tags emitted by the Python harness (test runners)."""
    out: set[str] = set()
    patterns = [
        re.compile(r'"\[LLP v=2[^"]*tag=([a-zA-Z][a-zA-Z0-9._]*)'),
        re.compile(r'emit_probe\s*\(\s*"([a-zA-Z][a-zA-Z0-9._]*)"'),
    ]
    if not PY_HARNESS_DIR.exists():
        return out
    for f in PY_HARNESS_DIR.glob("*.py"):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pat in patterns:
            for m in pat.finditer(text):
                out.add(m.group(1))
    return out


def find_emitter(tag: str, xs_static: set[str], xs_dyn: set[str],
                 py_emitted: set[str]) -> str | None:
    if tag in xs_static:
        return "XS-static"
    if tag in py_emitted:
        return "PY-harness"
    for pref in xs_dyn:
        if tag.startswith(pref):
            return f"XS-dynamic[{pref}]"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", type=Path, dest="json_out")
    args = ap.parse_args()

    print("=" * 60)
    print("PROBE TAG DRIFT")
    print("=" * 60)

    if not VALIDATOR_PATH.exists():
        print(f"  ERROR: validator not found: {VALIDATOR_PATH}")
        return 2

    val_text = VALIDATOR_PATH.read_text(encoding="utf-8")
    read_tags = collect_read_tags(val_text)
    xs_static, xs_dyn = collect_xs_emitters()
    py_emitted = collect_py_emitters()

    print(f"  Tags read from logs: {len(read_tags)}")
    print(f"  XS static emitters:  {len(xs_static)}")
    print(f"  XS dynamic prefixes: {sorted(xs_dyn)}")
    print(f"  PY harness emitters: {len(py_emitted)}")
    print()

    coverage: dict[str, str | None] = {}
    missing: list[str] = []
    for tag in sorted(read_tags):
        emitter = find_emitter(tag, xs_static, xs_dyn, py_emitted)
        coverage[tag] = emitter
        if emitter is None:
            missing.append(tag)
            print(f"  FAIL  {tag:40s} *** MISSING EMITTER ***")
        else:
            print(f"  PASS  {tag:40s} {emitter}")

    print()
    if missing:
        print(f"FAIL — {len(missing)}/{len(read_tags)} tags lack an emitter")
        print("       these probes will silently return no data, masking validation")
    else:
        print(f"PASS — all {len(read_tags)} log-read tags have an XS or PY emitter")

    report = {
        "tags_read": sorted(read_tags),
        "xs_static_emitters_count": len(xs_static),
        "xs_dynamic_prefixes": sorted(xs_dyn),
        "py_harness_emitters_count": len(py_emitted),
        "coverage": coverage,
        "missing": missing,
        "passed": len(missing) == 0,
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json_out, "w") as fh:
            json.dump(report, fh, indent=2)
        print(f"Report: {args.json_out}")

    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
