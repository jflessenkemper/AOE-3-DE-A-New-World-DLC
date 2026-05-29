#!/usr/bin/env python3
"""Static validator: ``RandMaps/anwHubTest.xs`` trigger soundness.

The hub test map is the *random map script* the user uses to exercise
every wall + doctrine probe end-to-end. Its doctrine-capture triggers
are wired by name (e.g. ``hubtestDockDeadline360`` fires at T+360s)
and a single typo — a missing ``rmSetTriggerActive(true)``, a stale
``Param1`` after rename, an extended trigger that moved outside the
``gHubTestEndSeconds >= 1200`` gate — turns into a silently-dead
trigger that the user can't see when running the script.

This validator parses the map source and asserts three invariants:

  T-1 — TRIGGER WELL-FORMED
        Every ``rmCreateTrigger("name")`` block must contain
        ``rmSetTriggerActive(true)``, ``rmAddTriggerCondition(...)``,
        and ``rmAddTriggerEffect(...)``. A block missing any of those
        is a no-op trigger and will never fire.

  T-2 — TIMER MATCHES NAME
        If the trigger name ends with digits ``N``, its Timer condition
        ``rmSetTriggerConditionParamInt("Param1", N, ...)`` must equal
        ``N`` (seconds). Catches the rename-without-updating-param
        regression where ``hubtestArmyBoost60`` becomes
        ``hubtestArmyBoost120`` but its Param1 stays at 60.
        Triggers with no digits in their name are exempt.
        ``hubtestAutoEnd`` is exempt — it sets Param1 from the
        ``gHubTestEndSeconds`` variable, not a literal.

  T-3 — EXTENDED TRIGGERS INSIDE EXTENDED GATE
        Triggers whose name embeds a timer ``>= 240`` must be inside
        the ``if (gHubTestEndSeconds >= 1200)`` block. Otherwise the
        fast 120s cycle would silently fire them too (or rather, the
        T+240+ ones would never fire because the auto-end at T+120s
        defeats the player first — but the script would still attempt
        to create the triggers in init, which we want gated).

Run::

    python3 tools/validation/validate_hub_test_triggers.py
    python3 tools/validation/validate_hub_test_triggers.py \\
        --json artifacts/validation/hub_test_triggers.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
HUB_TEST_XS = REPO_ROOT / "RandMaps" / "anwHubTest.xs"

# Exempt names — these triggers are intentionally driven by a global
# variable (gHubTestEndSeconds) rather than a literal integer.
TIMER_NAME_EXEMPT = {"hubtestAutoEnd"}

# Threshold: triggers with names embedding a timer >= this number of
# seconds are expected to live inside the extended-cycle gate.
EXTENDED_GATE_THRESHOLD_S = 240
# Extended-cycle threshold value (matches the ``if (gHubTestEndSeconds >= N)``
# block in the map). Used to locate the gate.
EXTENDED_GATE_VALUE_S = 1200


def _strip_line_comments(text: str) -> str:
    """Strip ``// …`` line comments so a commented-out
    ``rmSetTriggerActive(true)`` doesn't fool the well-formed check.

    Doesn't touch string literals (which can't contain ``//`` in this
    map source — verified by inspection).
    """
    return re.sub(r"//[^\n]*", "", text)


def parse_triggers(text: str) -> list[dict]:
    """Walk the file and slice each rmCreateTrigger block."""
    text = _strip_line_comments(text)
    starts = [(m.start(), m.group(1))
              for m in re.finditer(r'rmCreateTrigger\s*\(\s*"([^"]+)"\s*\)', text)]
    out = []
    for i, (start, name) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        block = text[start:end]
        m_param1 = re.search(
            r'rmSetTriggerConditionParamInt\s*\(\s*"Param1"\s*,\s*(\d+)', block)
        out.append({
            "name": name,
            "start": start,
            "end": end,
            "block": block,
            "has_active_true": bool(re.search(
                r'rmSetTriggerActive\s*\(\s*true\s*\)', block)),
            "has_condition": bool(re.search(
                r'rmAddTriggerCondition\s*\(', block)),
            "has_effect": bool(re.search(
                r'rmAddTriggerEffect\s*\(', block)),
            "timer_param1": int(m_param1.group(1)) if m_param1 else None,
            "uses_variable_param1": bool(re.search(
                r'rmSetTriggerConditionParamInt\s*\(\s*"Param1"\s*,\s*[a-zA-Z]\w*',
                block)),
        })
    return out


def find_extended_gate_range(text: str) -> tuple[int, int] | None:
    """Locate the body span of ``if (gHubTestEndSeconds >= 1200) { ... }``.

    Strip line comments first so commented-out gate lines don't mislead.
    """
    text = _strip_line_comments(text)
    m = re.search(
        rf"if\s*\(\s*gHubTestEndSeconds\s*>=\s*{EXTENDED_GATE_VALUE_S}\s*\)\s*\{{",
        text)
    if not m:
        return None
    # Find matching close brace
    open_pos = m.end() - 1
    depth = 0
    i = open_pos
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return (m.start(), i + 1)
        i += 1
    return None


def check_t1_well_formed(triggers: list[dict]) -> list[dict]:
    """Every trigger must have active=true + condition + effect."""
    out = []
    for t in triggers:
        missing = []
        if not t["has_active_true"]:
            missing.append("rmSetTriggerActive(true)")
        if not t["has_condition"]:
            missing.append("rmAddTriggerCondition")
        if not t["has_effect"]:
            missing.append("rmAddTriggerEffect")
        if missing:
            out.append({"trigger": t["name"], "missing": missing,
                        "msg": "trigger block missing required calls"})
    return out


def check_t2_timer_matches_name(triggers: list[dict]) -> list[dict]:
    """If name ends in digits N, Param1 must be N (seconds)."""
    out = []
    for t in triggers:
        if t["name"] in TIMER_NAME_EXEMPT:
            continue
        m = re.search(r"(\d+)$", t["name"])
        if not m:
            continue
        expected = int(m.group(1))
        actual = t["timer_param1"]
        if actual is None:
            out.append({"trigger": t["name"], "expected_s": expected,
                        "actual_s": None,
                        "msg": f"name embeds {expected}s but no Param1 timer set"})
        elif actual != expected:
            out.append({"trigger": t["name"], "expected_s": expected,
                        "actual_s": actual,
                        "msg": f"name embeds {expected}s but Param1={actual}s"})
    return out


def check_t3_extended_gating(triggers: list[dict],
                             gate_range: tuple[int, int] | None) -> list[dict]:
    """Extended-cycle triggers (timer >= 240s) must be inside the
    ``if (gHubTestEndSeconds >= 1200)`` block."""
    out = []
    if gate_range is None:
        # Can't enforce — report as a separate diagnostic, not a per-trigger fail.
        return [{"trigger": "<gate>", "msg": "could not locate "
                 f"`if (gHubTestEndSeconds >= {EXTENDED_GATE_VALUE_S})` block"}]
    gate_start, gate_end = gate_range
    for t in triggers:
        if t["name"] in TIMER_NAME_EXEMPT:
            continue
        m = re.search(r"(\d+)$", t["name"])
        if not m:
            continue
        timer_s = int(m.group(1))
        if timer_s < EXTENDED_GATE_THRESHOLD_S:
            continue
        inside_gate = gate_start <= t["start"] < gate_end
        if not inside_gate:
            out.append({"trigger": t["name"], "timer_s": timer_s,
                        "msg": f"timer {timer_s}s is >= "
                               f"{EXTENDED_GATE_THRESHOLD_S}s but trigger lives "
                               f"OUTSIDE the `gHubTestEndSeconds >= "
                               f"{EXTENDED_GATE_VALUE_S}` gate"})
    return out


INVARIANTS = [
    ("T-1", "Every trigger has active=true + condition + effect",
     check_t1_well_formed),
    ("T-2", "Trigger name ending in N seconds matches Param1 timer",
     check_t2_timer_matches_name),
    # T-3 takes the gate range, handled below
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--map", type=Path, default=HUB_TEST_XS)
    ap.add_argument("--json", type=Path, dest="json_out")
    args = ap.parse_args()

    print("=" * 60)
    print("HUB TEST TRIGGER SOUNDNESS")
    print("=" * 60)

    if not args.map.exists():
        print(f"  ERROR: map file not found: {args.map}")
        return 2

    text = args.map.read_text(encoding="utf-8", errors="replace")
    triggers = parse_triggers(text)
    gate_range = find_extended_gate_range(text)
    print(f"  Triggers parsed: {len(triggers)}")
    print(f"  Extended gate range: {gate_range}")
    print()

    all_results: dict[str, dict] = {}

    for code, desc, fn in INVARIANTS:
        violations = fn(triggers)
        all_results[code] = {"desc": desc, "violations": violations,
                             "passed": not violations}
        status = "PASS" if not violations else f"FAIL ({len(violations)})"
        print(f"  {code}  {status:10s}  {desc}")
        for v in violations[:6]:
            print(f"          - {v['trigger']}: {v['msg']}")

    # T-3 — needs the gate range
    t3_violations = check_t3_extended_gating(triggers, gate_range)
    all_results["T-3"] = {
        "desc": f"Extended triggers (>= {EXTENDED_GATE_THRESHOLD_S}s) "
                f"inside `gHubTestEndSeconds >= {EXTENDED_GATE_VALUE_S}` gate",
        "violations": t3_violations,
        "passed": not t3_violations,
    }
    status = "PASS" if not t3_violations else f"FAIL ({len(t3_violations)})"
    print(f"  T-3  {status:10s}  Extended triggers inside "
          f"`gHubTestEndSeconds >= {EXTENDED_GATE_VALUE_S}` gate")
    for v in t3_violations[:6]:
        print(f"          - {v['trigger']}: {v['msg']}")

    total_violations = sum(len(r["violations"]) for r in all_results.values())
    overall_pass = total_violations == 0
    print()
    if overall_pass:
        print(f"PASS — all {len(all_results)} hub-test trigger invariants honored "
              f"({len(triggers)} triggers)")
    else:
        print(f"FAIL — {total_violations} violations across "
              f"{sum(1 for r in all_results.values() if not r['passed'])} invariants")

    report = {
        "map_path": str(args.map.relative_to(REPO_ROOT)) if args.map.is_relative_to(REPO_ROOT) else str(args.map),
        "trigger_count": len(triggers),
        "trigger_names": [t["name"] for t in triggers],
        "gate_located": gate_range is not None,
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


if __name__ == "__main__":
    sys.exit(main())
