"""Parametrised leader-replay coverage.

For every one of the 48 civs in the expectations table, fabricate a clean
synthetic probe trace (meta.leader_init + meta.leader_assigned +
meta.buildstyle, all with that civ's expected terrain/heading values) and
assert the validator emits zero issues. Catches regressions where a new
civ is added but its expected probe contract drifts from the validator
(e.g. a leader rename, a terrain constant typo, a heading axis flip).

This complements ``test_expectations.py`` (which validates the static
expectation table itself) and ``test_replay_probes.py`` (which exercises
each validator branch on a single civ). The matrix below ensures every
civ round-trips through the full meta probe contract.
"""
from __future__ import annotations

import unittest
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.playtest.expectations import load_expectations
from tools.playtest.replay_probes import parse_probes, validate


def _probe(t: int, p: int, civ: str, ldr: str, tag: str, tail: str = "") -> str:
    return f"[ANWP v=2 t={t} p={p} civ={civ} ldr={ldr} tag={tag}] {tail}"


def _civ_token(exp) -> str:
    """Engine-faithful civ token for synthetic probes.

    `kbGetCivName()` (which the engine emits as ``civ=<name>`` on every
    probe) returns the civ_id with any ``cCiv``/``cCivDE``/``cCivXP``
    prefix stripped (e.g. ``cCivBritish`` → ``British``,
    ``cCivXPSioux`` → ``Sioux``). Revolutions arrive as their full
    rvltName (``ANWBrazil``). Mirroring that here keeps the test
    independent of any decorative additions to ``CIV_LABELS``
    (``"British (Elizabeth I)"`` etc.) — labels are for human display,
    the probe payload is the engine name."""
    import re as _re
    cid = exp.civ_id
    m = _re.match(r"^cCiv(?:DE|XP)?(.*)$", cid)
    if m:
        return m.group(1)
    return cid


def _good_pair(pid: int, exp) -> str:
    civ = _civ_token(exp)
    return "\n".join(
        [
            _probe(30, pid, civ, exp.leader_key, "meta.leader_init",
                   f"leader={exp.leader_key}"),
            _probe(60, pid, civ, exp.leader_key, "meta.leader_assigned",
                   f"civ_id=0 civ_name={civ} leader={exp.leader_key} "
                   f"chatset={exp.leader_key}"),
            _probe(120, pid, civ, exp.leader_key, "meta.buildstyle",
                   f"style=Test walls=1 "
                   f"terrain_primary={exp.terrain_primary} "
                   f"terrain_secondary={exp.terrain_secondary} "
                   f"terrain_bias={exp.terrain_strength} "
                   f"heading={exp.heading} "
                   f"heading_bias={exp.heading_strength} "
                   f"civic_anchor=false"),
        ]
    )


class LeaderReplayCoverageTests(unittest.TestCase):
    def test_every_civ_passes_clean_probe_trace(self) -> None:
        expectations = load_expectations()
        self.assertEqual(len(expectations), 48, "expected 48 civs in coverage matrix")

        failures: list[str] = []
        for exp in expectations:
            text = _good_pair(1, exp)
            issues, summary = validate(parse_probes(text.encode()))
            if issues:
                failures.append(f"{exp.label} ({exp.leader_key}): {issues}")
            elif len(summary) != 1:
                failures.append(
                    f"{exp.label} ({exp.leader_key}): expected 1 summary entry, "
                    f"got {len(summary)}"
                )

        if failures:
            self.fail(
                "Per-civ replay coverage failures:\n"
                + "\n".join(f"  - {line}" for line in failures)
            )

    def test_every_civ_has_a_distinct_label(self) -> None:
        expectations = load_expectations()
        labels = [e.label for e in expectations]
        self.assertEqual(len(set(labels)), len(labels), "duplicate civ labels")

    def test_every_civ_has_a_leader_key(self) -> None:
        expectations = load_expectations()
        for exp in expectations:
            self.assertTrue(
                exp.leader_key and not exp.leader_key.startswith("unassigned"),
                f"{exp.label}: leader_key '{exp.leader_key}' is missing/unassigned",
            )

    def test_leader_mismatch_flagged_for_strict_civs(self) -> None:
        # Negative parametrised: swapping the leader_key to a foreign one
        # must be detected. The validator has documented permissive
        # fallbacks for civs whose leader is dispatched via the shared
        # rvlt_* commander or other generic paths (see
        # test_replay_probes.test_leader_init_accepts_rvlt_prefix). This
        # test asserts the strict-binding civs (those with a dedicated
        # leader_<name>.xs file) all flag a foreign leader.
        expectations = load_expectations()
        # Civs with permissive leader-binding paths — excluded from this
        # strict-mismatch matrix. Documented in tools/playtest/replay_probes.py.
        permissive_keys = {
            "bourbon", "hiawatha", "crazyhorse", "napoleon",
        }
        misses: list[str] = []
        for exp in expectations:
            if exp.leader_key in permissive_keys:
                continue
            if exp.leader_key.startswith("anw"):
                continue
            text = _good_pair(1, exp).replace(
                f"leader={exp.leader_key}", "leader=imposter_leader_xyz"
            )
            issues, _ = validate(parse_probes(text.encode()))
            if not any("mismatch" in i or "unassigned" in i for i in issues):
                misses.append(f"{exp.label} ({exp.leader_key})")
        self.assertEqual(misses, [], f"leader-mismatch missed for: {misses}")


if __name__ == "__main__":
    unittest.main()
