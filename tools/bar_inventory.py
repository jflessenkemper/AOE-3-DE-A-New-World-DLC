#!/usr/bin/env python3
"""Walk every .bar in a directory tree, dump entry names to a text file.

One line per entry: `<bar_basename>\t<entry_name>`.
Use grep on the output to inventory assets by civ/surface.
"""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from bar_extract import parse_header, read_entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path, help="dir to walk for .bar files")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    bars = sorted(args.root.rglob("*.bar"))
    print(f"found {len(bars)} bars under {args.root}", file=sys.stderr)
    n_total = 0
    with args.out.open("w", encoding="utf-8") as fout:
        for bar in bars:
            try:
                with bar.open("rb") as f:
                    version, _n, tbl = parse_header(f)
                    _root, entries = read_entries(f, version, tbl)
                for e in entries:
                    fout.write(f"{bar.name}\t{e['name']}\n")
                n_total += len(entries)
                print(f"  {bar.name}: {len(entries)} entries", file=sys.stderr)
            except Exception as ex:
                print(f"  ERROR {bar.name}: {ex}", file=sys.stderr)
    print(f"wrote {n_total} entries to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
