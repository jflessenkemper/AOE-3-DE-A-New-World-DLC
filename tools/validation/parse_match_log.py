#!/usr/bin/env python3
"""Parse [LLP v=2 ...] probe markers from Age3Log.txt and aiChat output.

The mod's `llProbe()` XS helper (game/ai/core/aiUtilities.xs:261) emits lines
in the format:

    [LLP v=2 t=<game_ms> p=<player_id> civ=<civ_name> ldr=<leader_key> tag=<dotted.tag>] [detail kv pairs...]

This parser extracts all probe lines from a log, groups by civ + tag, and
returns a structured dict suitable for downstream validation.

Usage as library:
    from parse_match_log import parse_log
    probes = parse_log(Path("Age3Log.txt"))
    # probes = {civ_token: {tag: [probe_record, ...]}}

Usage as CLI:
    python3 parse_match_log.py <path/to/Age3Log.txt> [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# [LLP v=2 t=234567 p=1 civ=ANWBritish ldr=wellington tag=milestone.first_barracks] atMs=234567 count=1 age=1
_PROBE_RE = re.compile(
    r"\[LLP v=2 "
    r"t=(?P<t>-?\d+) "
    r"p=(?P<p>-?\d+) "
    r"civ=(?P<civ>\S+) "
    r"ldr=(?P<ldr>\S+) "
    r"tag=(?P<tag>[^\]]+)\]"
    r"(?P<detail>.*)"
)

# detail format: " key=value key=value ..." (space-separated)
_KV_RE = re.compile(r"(?P<k>[A-Za-z_][A-Za-z0-9_.]*)=(?P<v>\S+)")


def _parse_kv(detail: str) -> dict[str, Any]:
    """Parse detail kv pairs; coerce numeric values."""
    out: dict[str, Any] = {}
    for m in _KV_RE.finditer(detail):
        k, v = m.group("k"), m.group("v")
        # Try numeric coercion
        try:
            if "." in v:
                out[k] = float(v)
            else:
                out[k] = int(v)
        except ValueError:
            out[k] = v
    return out


def parse_log(path: Path) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Parse a log file. Returns {civ_token: {tag: [probe_record, ...]}}.

    Each probe_record has:
      - t: int (game milliseconds)
      - p: int (player id)
      - civ: str
      - ldr: str (leader key)
      - tag: str (dotted tag)
      - **details (kv pairs from the detail portion)
    """
    if not path.exists():
        raise FileNotFoundError(path)
    civs: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = _PROBE_RE.search(line)
            if not m:
                continue
            rec: dict[str, Any] = {
                "t": int(m.group("t")),
                "p": int(m.group("p")),
                "civ": m.group("civ"),
                "ldr": m.group("ldr"),
                "tag": m.group("tag"),
            }
            rec.update(_parse_kv(m.group("detail")))
            civs[rec["civ"]][rec["tag"]].append(rec)
    return {c: dict(t) for c, t in civs.items()}


def summarize(probes: dict[str, dict[str, list[dict[str, Any]]]]) -> dict[str, Any]:
    """Top-level stats: which civs, which tags, counts."""
    out: dict[str, Any] = {
        "civs_seen": sorted(probes.keys()),
        "civ_count": len(probes),
        "per_civ_tags": {},
    }
    all_tags: set[str] = set()
    for civ, tagmap in probes.items():
        out["per_civ_tags"][civ] = {
            tag: len(records) for tag, records in tagmap.items()
        }
        all_tags.update(tagmap.keys())
    out["all_tags"] = sorted(all_tags)
    out["unique_tag_count"] = len(all_tags)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("log_path", type=Path, help="Age3Log.txt or match.log")
    ap.add_argument(
        "--json",
        type=Path,
        help="Write parsed data as JSON to this path",
    )
    ap.add_argument(
        "--summary",
        action="store_true",
        help="Print only the summary",
    )
    ap.add_argument(
        "--civ",
        action="append",
        default=[],
        help="Filter to specific civ (repeatable)",
    )
    ap.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Filter to specific tag (repeatable)",
    )
    args = ap.parse_args()

    probes = parse_log(args.log_path)

    # Apply filters
    if args.civ:
        probes = {c: t for c, t in probes.items() if c in args.civ}
    if args.tag:
        probes = {
            c: {tag: recs for tag, recs in tagmap.items() if tag in args.tag}
            for c, tagmap in probes.items()
        }

    summary = summarize(probes)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        out_data = {"summary": summary, "probes": probes}
        with open(args.json, "w") as f:
            json.dump(out_data, f, indent=2)
        print(f"Wrote {args.json}", file=sys.stderr)

    print("=" * 70)
    print("MATCH LOG SUMMARY")
    print("=" * 70)
    print(f"Source: {args.log_path}")
    print(f"Civs seen: {summary['civ_count']}")
    print(f"Unique tags: {summary['unique_tag_count']}")
    print()
    print("Per-civ tag counts:")
    for civ in summary["civs_seen"]:
        tags = summary["per_civ_tags"][civ]
        total = sum(tags.values())
        print(f"  {civ}: {total} probes across {len(tags)} tags")
        if not args.summary:
            for tag, n in sorted(tags.items()):
                print(f"    {tag}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
