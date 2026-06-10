"""validate_xs_sim_parse_coverage.py — XS sim parser regression guard.

Parses every game .xs file under game/ai/ using tools.xs_sim.parser.parse()
and asserts that the number of successfully parsed files is at least BASELINE
(currently 66/66).  Exits non-zero and lists any failing file if coverage
drops below the baseline, so that future parser or .xs changes cannot silently
regress coverage.

Usage (from repo root):
    python tools/validation/validate_xs_sim_parse_coverage.py

Exit codes:
    0  All files parsed OK and coverage >= BASELINE.
    1  One or more files failed to parse or coverage < BASELINE.
"""
from __future__ import annotations

import glob
import os
import sys

# Minimum number of game/*.xs files that must parse without error.
# Raise this whenever parser improvements push coverage higher.
BASELINE: int = 66

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ensure the tools package is importable when the script is run directly.
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from xs_sim.parser import parse  # noqa: E402 — import after sys.path fixup


def main() -> int:
    pattern = os.path.join(REPO_ROOT, "game", "ai", "**", "*.xs")
    files = sorted(glob.glob(pattern, recursive=True))

    if not files:
        print(f"ERROR: no .xs files found under {os.path.join(REPO_ROOT, 'game', 'ai')}")
        return 1

    ok_count = 0
    failures: list[tuple[str, str]] = []

    for fpath in files:
        rel = os.path.relpath(fpath, REPO_ROOT)
        try:
            src = open(fpath, encoding="utf-8", errors="replace").read()
            parse(src, filename=rel)
            ok_count += 1
        except Exception as exc:
            first_line = str(exc).split("\n")[0]
            failures.append((rel, first_line))

    total = len(files)
    print(f"XS sim parse coverage: {ok_count}/{total} files OK")

    if failures:
        print(f"\nFAILED ({len(failures)} file(s)):")
        for path, err in failures:
            print(f"  FAIL  {path}")
            print(f"        {err}")

    if ok_count < BASELINE:
        print(
            f"\nCOVERAGE REGRESSION: {ok_count}/{total} < baseline {BASELINE}/{total}"
        )
        return 1

    print(f"PASS  coverage {ok_count}/{total} >= baseline {BASELINE}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
