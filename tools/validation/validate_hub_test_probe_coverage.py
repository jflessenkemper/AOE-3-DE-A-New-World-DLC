#!/usr/bin/env python3
"""Static validator: hub-test narrative cites only real probe names.

Two invariants guard the relationship between the [HUBTEST] Send-Chat
messages in ``RandMaps/anwHubTest.xs`` and the actual probe emitters
in the AI XS scripts:

  C-1 — HUB TEST NARRATIVE CITES REAL PROBES
        Every ``[HUBTEST]`` Send-Chat message in ``RandMaps/anwHubTest.xs``
        that mentions a probe name (matched by regex
        ``\\b([a-z]+\\.[a-z_]+)\\b`` — dotted lowercase identifier) must
        reference a probe that exists, either as a literal
        ``llProbe("name"`` site in any AI XS file, or as a known dynamic
        emission (``llCheckMilestone(tag)`` → ``milestone.first_<tag>``).

  C-2 — MILESTONE TAG COVERAGE
        Each tag passed to ``llCheckMilestone("<tag>", ...)`` in
        ``game/ai/core/aiDoctrineProbes.xs`` must either (a) be cited by
        at least one ``[HUBTEST]`` narrative line, OR (b) be on the
        EXEMPT list below (with a justifying comment).

Run::

    python3 tools/validation/validate_hub_test_probe_coverage.py
    python3 tools/validation/validate_hub_test_probe_coverage.py --json artifacts/validation/hub_test_probe_coverage.json
    python3 tools/validation/validate_hub_test_probe_coverage.py --self-test
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
HUB_TEST_XS = REPO_ROOT / "RandMaps" / "anwHubTest.xs"
DOCTRINE_PROBES_XS = REPO_ROOT / "game" / "ai" / "core" / "aiDoctrineProbes.xs"
AI_DIR = REPO_ROOT / "game" / "ai"

# Milestone tags that ARE emitted by llCheckMilestone but are intentionally
# NOT cited in the hub-test narrative.  The hub test focuses on specific
# observable milestones tied to doctrine claims; the remaining building
# types (barracks, stable, fort, trading_post) are routine construction
# milestones that do not correspond to any time-boxed claim in
# playstyle_spec.json and would clutter the player-facing narrative.
MILESTONE_TAG_EXEMPT: set[str] = {
    "barracks",       # routine — all civs build one; no doctrine claim tied to it
    "stable",         # routine — cavalry civs build one; no time-boxed spec claim
    "fort",           # claimed by some civs but no specific hub-test window
    "trading_post",   # map-specific; not a doctrine claim in playstyle_spec.json
}

# Regex matching a dotted lowercase probe-name token in a string.
# Matches things like "wall.chokepoint", "elite.escort", "comp.snapshot",
# and three-segment names like "event.elite.doctrine" or "milestone.first_dock".
# The pattern allows an optional third segment (dot + word) so that
# "event.elite.doctrine" is captured as a single token rather than as
# the partial "event.elite".
_PROBE_TOKEN_RE = re.compile(
    r"\b([a-z][a-z_]*\.[a-z][a-z_]*(?:\.[a-z][a-z_]*)?)\b"
)

# Pattern that locates [HUBTEST] messages inside rmSetTriggerEffectParam
# "Message" calls.
_HUBTEST_MSG_RE = re.compile(
    r'rmSetTriggerEffectParam\s*\(\s*"Message"\s*,\s*"([^"]*\[HUBTEST\][^"]*)"',
)

# Pattern to find llProbe("name" literal sites.
_LLPROBE_LITERAL_RE = re.compile(r'llProbe\s*\(\s*"([^"]+)"')

# Pattern to find llCheckMilestone("<tag>", ...) calls.
_MILESTONE_TAG_RE = re.compile(r'llCheckMilestone\s*\(\s*"([^"]+)"')


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def collect_hubtest_messages(xs_text: str) -> list[str]:
    """Return the string content of every [HUBTEST] Send-Chat Message param."""
    return _HUBTEST_MSG_RE.findall(xs_text)


def collect_literal_probes(ai_dir: Path) -> set[str]:
    """Scan all XS files under *ai_dir* for ``llProbe("name"`` sites.

    Returns the set of literal probe name strings found.
    """
    found: set[str] = set()
    for xs_path in ai_dir.rglob("*.xs"):
        text = xs_path.read_text(encoding="utf-8", errors="replace")
        for m in _LLPROBE_LITERAL_RE.finditer(text):
            found.add(m.group(1))
    return found


def collect_milestone_tags(doctrine_xs_text: str) -> list[str]:
    """Extract all tag strings from ``llCheckMilestone("<tag>", ...)`` calls."""
    return _MILESTONE_TAG_RE.findall(doctrine_xs_text)


def build_all_probe_names(literal_probes: set[str],
                          milestone_tags: list[str]) -> set[str]:
    """Union of literal probes and dynamically-constructed milestone probes."""
    dynamic = {f"milestone.first_{tag}" for tag in milestone_tags}
    return literal_probes | dynamic


def extract_probe_tokens_from_message(message: str) -> list[str]:
    """Return all dotted-lowercase tokens from a [HUBTEST] message string."""
    return _PROBE_TOKEN_RE.findall(message)


# ---------------------------------------------------------------------------
# Invariant checks
# ---------------------------------------------------------------------------

def check_c1_narrative_cites_real_probes(
    hubtest_messages: list[str],
    all_probes: set[str],
) -> list[dict]:
    """C-1: every dotted token in a [HUBTEST] message must be a real probe."""
    violations: list[dict] = []
    for msg in hubtest_messages:
        tokens = extract_probe_tokens_from_message(msg)
        for tok in tokens:
            if tok not in all_probes:
                violations.append({
                    "message": msg,
                    "bad_token": tok,
                    "msg": (
                        f"[HUBTEST] message cites '{tok}' which is not emitted "
                        f"by any llProbe() or llCheckMilestone() in game/ai/"
                    ),
                })
    return violations


def check_c2_milestone_tag_coverage(
    milestone_tags: list[str],
    hubtest_messages: list[str],
) -> list[dict]:
    """C-2: every milestone tag must be cited in at least one [HUBTEST] message
    or be in the EXEMPT set."""
    # Build the set of probe tokens mentioned across all narrative lines.
    mentioned_probes: set[str] = set()
    for msg in hubtest_messages:
        mentioned_probes.update(extract_probe_tokens_from_message(msg))

    violations: list[dict] = []
    for tag in milestone_tags:
        if tag in MILESTONE_TAG_EXEMPT:
            continue
        milestone_probe = f"milestone.first_{tag}"
        if milestone_probe not in mentioned_probes:
            violations.append({
                "tag": tag,
                "probe": milestone_probe,
                "msg": (
                    f"llCheckMilestone(\"{tag}\") emits '{milestone_probe}' but "
                    f"no [HUBTEST] narrative line cites it, and it is not in "
                    f"MILESTONE_TAG_EXEMPT"
                ),
            })
    return violations


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--map", type=Path, default=HUB_TEST_XS,
                    help="Path to anwHubTest.xs (default: repo-relative)")
    ap.add_argument("--ai-dir", type=Path, default=AI_DIR,
                    help="Root of AI XS files to scan for llProbe() sites")
    ap.add_argument("--doctrine-xs", type=Path, default=DOCTRINE_PROBES_XS,
                    help="Path to aiDoctrineProbes.xs for milestone tags")
    ap.add_argument("--json", type=Path, dest="json_out",
                    help="Write machine-readable report to this path")
    ap.add_argument("--self-test", action="store_true",
                    help="Run internal mutation tests and exit")
    args = ap.parse_args(argv)

    if args.self_test:
        return _run_self_test()

    print("=" * 60)
    print("HUB TEST PROBE COVERAGE")
    print("=" * 60)

    # --- Load inputs --------------------------------------------------------
    if not args.map.exists():
        print(f"  ERROR: map file not found: {args.map}")
        return 2
    if not args.doctrine_xs.exists():
        print(f"  ERROR: aiDoctrineProbes.xs not found: {args.doctrine_xs}")
        return 2

    xs_text = args.map.read_text(encoding="utf-8", errors="replace")
    doctrine_text = args.doctrine_xs.read_text(encoding="utf-8", errors="replace")

    hubtest_messages = collect_hubtest_messages(xs_text)
    literal_probes = collect_literal_probes(args.ai_dir)
    milestone_tags = collect_milestone_tags(doctrine_text)
    all_probes = build_all_probe_names(literal_probes, milestone_tags)

    print(f"  [HUBTEST] messages found : {len(hubtest_messages)}")
    print(f"  Literal llProbe() sites  : {len(literal_probes)}")
    print(f"  llCheckMilestone tags    : {len(milestone_tags)} "
          f"({len(MILESTONE_TAG_EXEMPT)} exempt)")
    print(f"  Total known probe names  : {len(all_probes)}")
    print()

    # --- Run invariants -----------------------------------------------------
    all_results: dict[str, dict] = {}

    c1_violations = check_c1_narrative_cites_real_probes(hubtest_messages, all_probes)
    all_results["C-1"] = {
        "desc": "Every [HUBTEST] message probe token exists as a real emission site",
        "violations": c1_violations,
        "passed": not c1_violations,
    }
    status = "PASS" if not c1_violations else f"FAIL ({len(c1_violations)})"
    print(f"  C-1  {status:10s}  [HUBTEST] narrative cites only real probe names")
    for v in c1_violations[:6]:
        print(f"          - token '{v['bad_token']}': {v['msg'][:80]}")

    c2_violations = check_c2_milestone_tag_coverage(milestone_tags, hubtest_messages)
    all_results["C-2"] = {
        "desc": "Every non-exempt milestone tag is cited in a [HUBTEST] narrative line",
        "violations": c2_violations,
        "passed": not c2_violations,
    }
    status = "PASS" if not c2_violations else f"FAIL ({len(c2_violations)})"
    print(f"  C-2  {status:10s}  Non-exempt milestone tags cited in [HUBTEST] narrative")
    for v in c2_violations[:6]:
        print(f"          - tag '{v['tag']}': {v['msg'][:80]}")

    total_violations = sum(len(r["violations"]) for r in all_results.values())
    overall_pass = total_violations == 0
    print()
    if overall_pass:
        print(f"PASS — all {len(all_results)} hub-test probe coverage invariants honored")
    else:
        print(f"FAIL — {total_violations} violations across "
              f"{sum(1 for r in all_results.values() if not r['passed'])} invariants")

    report = {
        "map_path": (str(args.map.relative_to(REPO_ROOT))
                     if args.map.is_relative_to(REPO_ROOT) else str(args.map)),
        "hubtest_message_count": len(hubtest_messages),
        "literal_probe_count": len(literal_probes),
        "milestone_tag_count": len(milestone_tags),
        "milestone_tags_exempt": sorted(MILESTONE_TAG_EXEMPT),
        "all_probe_count": len(all_probes),
        "invariants": all_results,
        "total_violations": total_violations,
        "passed": overall_pass,
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json_out, "w") as fh:
            json.dump(report, fh, indent=2)
        print(f"Report: {args.json_out}")

    return 0 if overall_pass else 1


# ---------------------------------------------------------------------------
# Self-test (--self-test flag)
# ---------------------------------------------------------------------------

def _run_self_test() -> int:
    """Mutation-test the validator.

    Two mutations are applied to a temp copy of anwHubTest.xs:

    Mutation A — insert a [HUBTEST] message referencing a fictitious probe
    name "hero.march".  C-1 must FAIL.

    Mutation B — restore the original text (no bad probe) and also remove the
    "milestone.first_dock" token from every [HUBTEST] message so that the
    "dock" tag is no longer cited.  C-2 must FAIL.

    Finally, run the unmodified map file — both invariants must PASS.
    """
    script = str(HERE / "validate_hub_test_probe_coverage.py")

    original_text = HUB_TEST_XS.read_text(encoding="utf-8", errors="replace")

    results: list[tuple[str, bool, str]] = []  # (label, expected_pass, actual)

    with tempfile.NamedTemporaryFile(suffix=".xs", mode="w",
                                    encoding="utf-8", delete=False) as tf:
        tmp_path = Path(tf.name)

        # --- Mutation A: inject a bad probe token ---------------------------
        bad_msg = (
            'rmSetTriggerEffectParam("Message", '
            '"[HUBTEST] t=999s self_test: watch hero.march probe", false);'
        )
        mutant_a = original_text + "\n" + bad_msg + "\n"
        tf.write(mutant_a)
        tf.flush()

    rc_a = subprocess.run(
        [sys.executable, script, "--map", str(tmp_path)],
        capture_output=True,
    ).returncode
    results.append(("Mutation A (bad probe 'hero.march') → expect FAIL (rc=1)",
                    rc_a == 1,
                    f"rc={rc_a}"))

    # --- Mutation B: remove dock citation so C-2 fails ----------------------
    mutant_b = re.sub(
        r"milestone\.first_dock",
        "milestone.first_REMOVED",
        original_text,
    )
    tmp_path.write_text(mutant_b, encoding="utf-8")
    rc_b = subprocess.run(
        [sys.executable, script, "--map", str(tmp_path)],
        capture_output=True,
    ).returncode
    results.append(("Mutation B (dock citation removed) → expect FAIL (rc=1)",
                    rc_b == 1,
                    f"rc={rc_b}"))

    # --- Baseline: unmodified map should PASS --------------------------------
    rc_base = subprocess.run(
        [sys.executable, script, "--map", str(HUB_TEST_XS)],
        capture_output=True,
    ).returncode
    results.append(("Baseline (original map) → expect PASS (rc=0)",
                    rc_base == 0,
                    f"rc={rc_base}"))

    tmp_path.unlink(missing_ok=True)

    print("=" * 60)
    print("SELF-TEST: validate_hub_test_probe_coverage")
    print("=" * 60)
    all_ok = True
    for label, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        print(f"  {status}  {label}  [{detail}]")
        if not ok:
            all_ok = False
    print()
    if all_ok:
        print("SELF-TEST PASS — all mutations behaved as expected")
    else:
        print("SELF-TEST FAIL — one or more mutations did not produce the expected exit code")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
