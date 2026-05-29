"""Run layout verification across a folder of screenshots.

Expected layout:
    screenshots/
        british.png
        french.png
        napoleon.png
        ...

Filename stem (case-insensitive) must match either the civ id
(`cCivBritish`, `ANWNapoleonicFrance`) or one of the labels in
`expectations.CIV_LABELS` (or a unique prefix of it). Optional `_<seq>`
suffix is allowed for multiple shots of the same civ:
`british_8min.png`, `british_15min.png`.

Usage:
    python3 -m tools.playtest.spot_check screenshots/
    python3 -m tools.playtest.spot_check screenshots/ --team red
    python3 -m tools.playtest.spot_check screenshots/ --report .validation-reports/playtest.txt

Exit code: 0 if no FAILs, 1 if any FAIL, 4 if all readings INCONCLUSIVE.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.playtest.expectations import CivExpectation, load_expectations  # noqa: E402
from tools.playtest.layout_verify import (  # noqa: E402
    INLAND_TOLERANCE_DEG,
    WATER_TOLERANCE_DEG,
    Verdict,
    verify,
)
from tools.playtest.minimap import (  # noqa: E402
    DEFAULT_MINIMAP_RECT_1080P,
    analyze_minimap,
    parse_rect,
)


def _index_civs() -> dict[str, CivExpectation]:
    out: dict[str, CivExpectation] = {}
    for e in load_expectations():
        out[e.civ_id.lower()] = e
        out[e.label.lower()] = e
        # Add common shortened keys.
        out[e.label.lower().split(" (")[0]] = e
    return out


def _match_civ(stem: str, index: dict[str, CivExpectation]) -> CivExpectation | None:
    base = stem.lower()
    # Drop trailing `_NNN` or `_NNNmin` suffixes.
    while base and (base.rsplit("_", 1)[-1].rstrip("min").rstrip("sec").isdigit() or base.endswith("min") or base.endswith("sec")):
        if "_" not in base:
            break
        base = base.rsplit("_", 1)[0]
    if base in index:
        return index[base]
    matches = [e for k, e in index.items() if k.startswith(base)]
    matches = list({id(e): e for e in matches}.values())
    if len(matches) == 1:
        return matches[0]
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dir", type=Path, help="folder of screenshots")
    ap.add_argument("--team", default="blue")
    ap.add_argument("--minimap", type=parse_rect, default=None)
    ap.add_argument("--water-tol", type=float, default=WATER_TOLERANCE_DEG)
    ap.add_argument("--inland-tol", type=float, default=INLAND_TOLERANCE_DEG)
    ap.add_argument("--report", type=Path, default=None, help="write transcript to this path")
    args = ap.parse_args()

    if not args.dir.exists() or not args.dir.is_dir():
        print(f"not a directory: {args.dir}", file=sys.stderr)
        return 2

    rect = args.minimap or DEFAULT_MINIMAP_RECT_1080P
    index = _index_civs()

    shots = sorted(p for p in args.dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"})
    if not shots:
        print(f"no screenshots in {args.dir}", file=sys.stderr)
        return 2

    verdicts: list[Verdict] = []
    skipped: list[tuple[Path, str]] = []
    transcript: list[str] = []

    transcript.append(f"playtest spot-check :: {len(shots)} screenshots from {args.dir}")
    transcript.append(f"team={args.team}  minimap={rect}")
    transcript.append("")

    for path in shots:
        expectation = _match_civ(path.stem, index)
        if expectation is None:
            skipped.append((path, "no civ match"))
            transcript.append(f"  [SKIP] {path.name}: no civ match for stem '{path.stem}'")
            continue
        try:
            reading = analyze_minimap(path, team=args.team, rect=rect)
        except Exception as exc:  # pragma: no cover - I/O / decode errors
            skipped.append((path, f"read error: {exc}"))
            transcript.append(f"  [SKIP] {path.name}: {exc}")
            continue

        v = verify(
            expectation,
            reading,
            water_tol=args.water_tol,
            inland_tol=args.inland_tol,
        )
        verdicts.append(v)
        transcript.append(f"  -- {path.name} → {expectation.label} --")
        transcript.append(f"     {reading.summary()}")
        transcript.append(v.line())

    counts = Counter(v.status for v in verdicts)
    transcript.append("")
    transcript.append(
        f"summary: PASS={counts['PASS']}  FAIL={counts['FAIL']}  "
        f"INCONCLUSIVE={counts['INCONCLUSIVE']}  SKIPPED={len(skipped)}"
    )
    if any(v.status == "FAIL" for v in verdicts):
        transcript.append("")
        transcript.append("FAILURES:")
        for v in verdicts:
            if v.status == "FAIL":
                transcript.append(v.line())

    text = "\n".join(transcript)
    print(text)
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n", encoding="utf-8")

    if counts["FAIL"]:
        return 1
    if not verdicts or counts["INCONCLUSIVE"] == len(verdicts):
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
