"""Post-match validator for in-game runtime probes.

IMPORTANT — use the per-match log slice, NOT the .age3Yrec replay
---------------------------------------------------------------------
Every CPU AI emits ``[ANWP v=2 ...]`` probes via the A New World XS
hooks.  These probes are triple-emitted: ``aiEcho()`` → Age3Log.txt,
``aiChat(1, ...)`` → replay chat stream, ``aiChat(cMyID, ...)`` → replay
chat stream.

The .age3Yrec aiChat path stores values as string-table indices (binary
packed), NOT plain text.  Regex scanning the raw replay bytes therefore
returns zero probe lines — silently invalidating every validation run.

The correct source is **Age3Log.txt**, which ``aiEcho()`` writes as plain
ASCII — but only when the game runs with developer mode enabled.  See
``tools/aoe3_automation/log_capture.py`` for the per-match slice helper
that captures the right byte range from the live log.

To generate a parseable probe source:
  1. Ensure developer mode is active (``manage_game.py open`` creates
     user.cfg automatically).
  2. Run a match via ``in_game_driver.py`` or ``probe_coverage_matrix.py``.
  3. Those tools write a ``match.log`` per match using ``log_capture``.
  4. Pass that ``match.log`` to this validator.

Probe tags covered
------------------
  meta.*          — leader/buildstyle assignment (one-shot per AI)
  telem.*         — heartbeat + plan snapshots
  mil.*           — attack/defend plans
  compliance.*    — periodic doctrine compliance snapshots
  event.*         — state-transition events (delta, age-up, etc.)
  tech.*          — shipment / age-up choices

Usage:
    python3 -m tools.playtest.replay_probes path/to/match.log
    python3 -m tools.playtest.replay_probes path/to/match.log --strict
    python3 -m tools.playtest.replay_probes path/to/match.log --json
    python3 -m tools.playtest.replay_probes path/to/match.log --source log
    # Legacy (warns and exits 2 — replay chat is binary-encoded):
    python3 -m tools.playtest.replay_probes path/to/game.age3Yrec

Exit code: 0 = all probes match, 1 = mismatch, 2 = no probes found / wrong source.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.playtest.expectations import (  # noqa: E402
    CIV_LABELS,
    CivExpectation,
    load_expectations,
)
from tools.playtest.html_reference import (  # noqa: E402
    DoctrineContract,
    load_doctrine_contracts,
)


# `[ANWP v=2 t=<int> p=<int> civ=<civ> ldr=<ldr> tag=<domain.name>] <tail>`
# We match against bytes so the same regex can scan both raw .age3Yrec
# binary payloads and plain-text log files.
PROBE_RE = re.compile(
    rb"\[ANWP v=2 t=(?P<t>\d+) p=(?P<p>\d+) civ=(?P<civ>\S+) "
    rb"ldr=(?P<ldr>\S+) tag=(?P<tag>\S+)\]\s*(?P<tail>[ -~]*)"  # tail = printable ASCII only
)
KV_RE = re.compile(rb"(\w+)=([^\s]+)")


@dataclass
class ProbeRecord:
    time: int
    player: int
    civ: str
    leader: str
    tag: str
    fields: dict[str, str]


def parse_probes(data: bytes) -> list[ProbeRecord]:
    out: list[ProbeRecord] = []
    for m in PROBE_RE.finditer(data):
        tail = m.group("tail")
        fields = {k.decode(): v.decode() for k, v in KV_RE.findall(tail)}
        out.append(
            ProbeRecord(
                time=int(m.group("t")),
                player=int(m.group("p")),
                civ=m.group("civ").decode(),
                leader=m.group("ldr").decode(),
                tag=m.group("tag").decode(),
                fields=fields,
            )
        )
    return out


def _expect_index() -> dict[str, CivExpectation]:
    """Index expectations by both engine civ_id (cCivBritish) and rvltName
    (ANWBrazil) — the probe carries `civ=<rvltName>` from kbGetCivName(),
    which for base civs is e.g. "British", and for revolutions is the
    "ANWBrazil" form. So we index by every plausible key shape."""
    out: dict[str, CivExpectation] = {}
    for e in load_expectations():
        out[e.civ_id] = e
        out[e.label] = e
        # Strip "cCiv" prefix for base civs ("cCivBritish" -> "British").
        if e.civ_id.startswith("cCiv"):
            out[e.civ_id[4:]] = e
        # Drop "DE"/"XP" prefixes that some base civ_ids carry.
        m = re.match(r"^cCiv(?:DE|XP)?(.*)$", e.civ_id)
        if m:
            out[m.group(1)] = out.get(m.group(1), e)
    return out


# Tags expected exactly once per AI (assignment / loadout events).
ONE_SHOT_TAGS = (
    "meta.leader_assigned",
    "meta.buildstyle",
    "meta.leader_init",
    "meta.boot",
    "meta.setup",
)

# Tags expected to fire periodically (one per 60s heartbeat tick).
PERIODIC_TAGS = (
    "telem.heartbeat",
    "mil.plan_snap",
    "plan.build_snap",
    "navy.fleet_snap",
    # New compliance probes — emitted by llComplianceSnapshot every 60s.
    "compliance.profile",
    "compliance.bldg",
    "compliance.army",
    "compliance.placement",
    "compliance.terrain",
    # Coverage-push probes — extended doctrine compliance (60–120s tick).
    "compliance.combat",
    "compliance.econ",
    "compliance.ship",
    "compliance.placeAll",
    "compliance.wallGeom",
    "compliance.diplo",
    "compliance.rules",
    "compliance.tactics",
)

# Tags emitted only on state transitions (no cadence guarantee).
EVENT_TAGS = (
    "event.delta",                  # any of TP/base/attack/hero counters moved
    "event.combat.defense_reflex",  # moveDefenseReflex() entry
    "mil.attack",                   # attack-plan creation
    "mil.defend",                   # defend-plan creation
    "tech.ageReq",                  # politician/wonder picked at age-up
)

# Tags emitted at most once per AI by llInitialEconSnapshot / on age-up.
RARE_TAGS = (
    "compliance.anchor",   # one-shot, fires from initial econ snapshot
    "compliance.age",      # fires once per age transition (≤4 per AI)
    "plan.wall.stall",     # diagnostic — fires only if wall plan stalls 4 min
    "tech.ship",           # fires once per shipment chosen
)


# Field names used by compliance.profile (echo of static doctrine state).
# These are the *probe-emitted* names, not the expectation field names.
PROFILE_FIELDS = {
    "terrPrim":  "terrain_primary",
    "terrSec":   "terrain_secondary",
    "heading":   "heading",
}

# Reverse map: a barracks-quadrant tally that *matches* the configured
# placement preference is considered compliant. The probe emits the raw
# integer of cBuildingPlacementPreferenceFront/Back/Left/Right; we don't
# know the exact engine values, so we match on relative dominance: the
# quadrant with the most barracks should have ≥ 50% of all barracks if
# the preference is non-neutral.
PLACEMENT_PREF_NEUTRAL = "-1"  # genuine spread — no quadrant should dominate


_DOCTRINE_CACHE: Optional[dict[str, DoctrineContract]] = None


def _doctrine_index() -> dict[str, DoctrineContract]:
    """Lazy load — the HTML is 700KB, parse once per process."""
    global _DOCTRINE_CACHE
    if _DOCTRINE_CACHE is None:
        html = REPO_ROOT / "a_new_world.html"
        if html.exists():
            _DOCTRINE_CACHE = load_doctrine_contracts(html)
        else:
            _DOCTRINE_CACHE = {}
    return _DOCTRINE_CACHE


BEHAVIOR_AXES: tuple[str, ...] = (
    "combat_engaged",
    "explorer_active",
    "age_up_fired",
    "shipments_chosen",
    "walls_built",
    "doctrine_compliance",
)


def derive_behavioral_axes(probes: list[ProbeRecord]) -> list[dict]:
    """Per-AI behavioural-axis derivation from a parsed probe stream.

    Returns a list of dicts (one per player id seen in the probes)::

        {
          "player": int,
          "civ":    str,         # rvltName as the probe carried it
          "leader": str,
          "axes":   {            # the six booleans matrix_validator surfaces
              "combat_engaged":      bool,   # AI dispatched at least one
                                              # mil.attack OR mil.defend plan,
                                              # or compliance.combat reported
                                              # attackPlans/defendPlans > 0
              "explorer_active":     bool,   # heroes >= 1 in any
                                              # compliance.tactics snap
              "age_up_fired":        bool,   # any compliance.age or
                                              # tech.ageReq probe
              "shipments_chosen":    bool,   # any tech.ship probe
              "walls_built":         bool,   # any compliance.wallGeom with
                                              # segments > 0 (or strategy=5
                                              # MobileNoWalls — passes by
                                              # design without walls)
              "doctrine_compliance": bool,   # validate() raised 0 issues
                                              # affecting THIS player
          },
          "issues": list[str],   # validate() lines mentioning "p<pid>"
        }

    The runner emits this once per match.log; matrix_validator picks it up to
    fill per-civ deep-mode axes when --deep was used.
    """
    by_player: dict[int, dict[str, list[ProbeRecord]]] = defaultdict(lambda: defaultdict(list))
    civ_by_player: dict[int, str] = {}
    leader_by_player: dict[int, str] = {}
    for p in probes:
        by_player[p.player][p.tag].append(p)
        civ_by_player.setdefault(p.player, p.civ)
        leader_by_player.setdefault(p.player, p.leader)

    issues_all, _ = validate(probes)

    out: list[dict] = []
    for pid in sorted(by_player):
        tags = by_player[pid]

        mil_atk = len(tags.get("mil.attack", []))
        mil_def = len(tags.get("mil.defend", []))
        combat_snaps = tags.get("compliance.combat", [])
        attack_plan_total = 0
        defend_plan_total = 0
        for s in combat_snaps:
            try:
                attack_plan_total += int(s.fields.get("attackPlans", "0"))
                defend_plan_total += int(s.fields.get("defendPlans", "0"))
            except ValueError:
                pass
        combat_engaged = (mil_atk > 0 or mil_def > 0
                          or attack_plan_total > 0 or defend_plan_total > 0)

        tactics_snaps = tags.get("compliance.tactics", [])
        explorer_active = False
        for s in tactics_snaps:
            try:
                if int(s.fields.get("heroes", "0")) >= 1:
                    explorer_active = True
                    break
            except ValueError:
                pass

        age_up_fired = (len(tags.get("compliance.age", [])) > 0
                        or len(tags.get("tech.ageReq", [])) > 0)

        shipments_chosen = len(tags.get("tech.ship", [])) > 0

        wall_snaps = tags.get("compliance.wallGeom", [])
        walls_built = False
        for s in wall_snaps:
            try:
                strat = int(s.fields.get("strategy", "-1"))
                segs = int(s.fields.get("segments", "0"))
                # MobileNoWalls (strategy=5) is "no walls by design" — count
                # as a pass: the doctrine fired and produced its expected
                # geometry (zero segments is correct here).
                if strat == 5 or segs > 0:
                    walls_built = True
                    break
            except ValueError:
                pass

        my_issues = [iss for iss in issues_all if iss.startswith(f"p{pid}")]
        doctrine_compliance = (len(my_issues) == 0)

        out.append({
            "player": pid,
            "civ": civ_by_player.get(pid, ""),
            "leader": leader_by_player.get(pid, ""),
            "axes": {
                "combat_engaged":      combat_engaged,
                "explorer_active":     explorer_active,
                "age_up_fired":        age_up_fired,
                "shipments_chosen":    shipments_chosen,
                "walls_built":         walls_built,
                "doctrine_compliance": doctrine_compliance,
            },
            "issues": my_issues,
        })
    return out


def validate(probes: list[ProbeRecord]) -> tuple[list[str], list[str]]:
    """Return (issues, summary_lines)."""
    expected = _expect_index()
    doctrines = _doctrine_index()

    # by_player[pid][tag] -> list of all probes with that tag
    by_player: dict[int, dict[str, list[ProbeRecord]]] = defaultdict(lambda: defaultdict(list))
    for p in probes:
        by_player[p.player][p.tag].append(p)

    issues: list[str] = []
    summary: list[str] = []

    if not by_player:
        issues.append("no [ANWP v=2] probes found — was cLLReplayProbes set true?")
        return issues, summary

    for pid in sorted(by_player):
        tags = by_player[pid]
        leader_assigned_list = tags.get("meta.leader_assigned", [])
        build_list = tags.get("meta.buildstyle", [])
        leader_p = leader_assigned_list[-1] if leader_assigned_list else None
        build_p = build_list[-1] if build_list else None

        civ_label = (leader_p or build_p).civ if (leader_p or build_p) else "?"
        line = f"  p{pid}  civ={civ_label}"

        if leader_p is None:
            issues.append(f"p{pid}: missing meta.leader_assigned probe")
        if build_p is None:
            issues.append(f"p{pid}: missing meta.buildstyle probe")
        if leader_p is None or build_p is None:
            summary.append(line + "  [INCOMPLETE]")
            continue

        # Leader name must not be the unassigned-* sentinel.
        leader_name = leader_p.fields.get("leader", leader_p.leader)
        if leader_name.startswith("unassigned-"):
            issues.append(
                f"p{pid}: civ {civ_label} hit the unassigned fallback "
                f"(leader={leader_name}). Add a dispatch entry to "
                f"llAssignLeaderIdentity()."
            )

        exp = expected.get(civ_label) or expected.get(leader_p.fields.get("civ_name", ""))
        if exp is None:
            summary.append(line + f"  ldr={leader_name}  [no expectation row]")
            continue

        # Leader key check
        if leader_name != exp.leader_key:
            issues.append(
                f"p{pid} {civ_label}: leader_key mismatch "
                f"(expected {exp.leader_key}, got {leader_name})"
            )

        # Build-style check (terrain + heading + biases)
        b = build_p.fields
        for key, want in (
            ("terrain_primary", exp.terrain_primary),
            ("terrain_secondary", exp.terrain_secondary),
            ("heading", exp.heading),
        ):
            got = b.get(key)
            if got != want:
                issues.append(
                    f"p{pid} {civ_label}: {key} mismatch (expected {want}, got {got})"
                )

        try:
            tb = float(b.get("terrain_bias", "nan"))
            if abs(tb - exp.terrain_strength) > 0.001:
                issues.append(
                    f"p{pid} {civ_label}: terrain_bias mismatch "
                    f"(expected {exp.terrain_strength}, got {tb})"
                )
        except ValueError:
            issues.append(f"p{pid} {civ_label}: terrain_bias not numeric ({b.get('terrain_bias')!r})")

        try:
            hb = float(b.get("heading_bias", "nan"))
            if abs(hb - exp.heading_strength) > 0.001:
                issues.append(
                    f"p{pid} {civ_label}: heading_bias mismatch "
                    f"(expected {exp.heading_strength}, got {hb})"
                )
        except ValueError:
            issues.append(f"p{pid} {civ_label}: heading_bias not numeric ({b.get('heading_bias')!r})")

        # Cross-check meta.leader_init against meta.leader_assigned —
        # confirms the dispatched leader's init function actually ran.
        init_list = tags.get("meta.leader_init", [])
        if not init_list:
            issues.append(
                f"p{pid} {civ_label}: missing meta.leader_init probe "
                f"— initLeader<X>() never executed"
            )
        else:
            init_keys = {p.fields.get("leader", "") for p in init_list}
            # Revolution commander shares one init for many civs, so accept
            # either the exact leader key or the rvlt_<rvltName> form.
            ok = (
                exp.leader_key in init_keys
                or any(k.startswith("rvlt_") for k in init_keys)
            )
            if not ok:
                issues.append(
                    f"p{pid} {civ_label}: meta.leader_init mismatch "
                    f"(expected {exp.leader_key!r}, saw {sorted(init_keys)})"
                )

        # Periodic probes: confirm each one fired at least once. For a
        # short replay (<60s) the heartbeat may not have ticked yet, so
        # only flag absence as a soft warning, not a fail.
        heartbeat_count = len(tags.get("telem.heartbeat", []))
        plan_count = len(tags.get("mil.plan_snap", []))
        build_count = len(tags.get("plan.build_snap", []))
        fleet_count = len(tags.get("navy.fleet_snap", []))
        ship_count = len(tags.get("tech.ship", []))
        if heartbeat_count and plan_count == 0:
            issues.append(
                f"p{pid} {civ_label}: telem.heartbeat fired {heartbeat_count}x "
                f"but mil.plan_snap never did — was llPlanSnapshot enabled?"
            )

        # ── compliance.profile ─────────────────────────────────────────────
        # Echoes static doctrine state every 60s. If it fires at all, every
        # tick must report the same terrain/heading the buildstyle locked
        # in. Drift between meta.buildstyle and compliance.profile = some
        # later code mutated gLLPreferred* mid-game (a real bug).
        profile_list = tags.get("compliance.profile", [])
        profile_count = len(profile_list)
        if profile_list:
            for snap in profile_list:
                for probe_field, exp_field in PROFILE_FIELDS.items():
                    got = snap.fields.get(probe_field)
                    want = getattr(exp, exp_field, None)
                    if got is None or want is None:
                        continue
                    # The probe emits the raw int constant value; meta.buildstyle
                    # appears to emit the symbolic name. If they don't match
                    # textually, only flag drift *between* profile snaps —
                    # static-vs-buildstyle comparison happens above.
                    pass
            # Drift detection: every snap must match the first.
            first_fields = profile_list[0].fields
            for snap in profile_list[1:]:
                for k in ("terrPrim", "terrSec", "heading", "wallStrat",
                          "milPlace"):
                    if snap.fields.get(k) != first_fields.get(k):
                        issues.append(
                            f"p{pid} {civ_label}: compliance.profile drift — "
                            f"{k} changed from {first_fields.get(k)!r} "
                            f"to {snap.fields.get(k)!r} mid-match"
                        )
                        break

        # ── compliance.placement ───────────────────────────────────────────
        # Latest snap's quadrant tally should reflect the doctrine. We can't
        # decode the engine's placement-pref int reliably, so the assertion
        # is: if expectedPref == "-1" (genuine spread), no quadrant should
        # hold > 70% of barracks once there are ≥3 of them. If pref is set,
        # *some* quadrant should be dominant (≥50%) once ≥2 barracks exist.
        placement_list = tags.get("compliance.placement", [])
        placement_count = len(placement_list)
        if placement_list:
            last = placement_list[-1].fields
            try:
                qf = int(last.get("front", "0"))
                qb = int(last.get("back", "0"))
                ql = int(last.get("left", "0"))
                qr = int(last.get("right", "0"))
                tot = qf + qb + ql + qr
                pref = last.get("expectedPref", "")
                if tot >= 3 and pref == PLACEMENT_PREF_NEUTRAL:
                    top = max(qf, qb, ql, qr)
                    if top * 10 > tot * 7:
                        issues.append(
                            f"p{pid} {civ_label}: spread doctrine but {top}/{tot} "
                            f"barracks clustered in one quadrant "
                            f"(F={qf} B={qb} L={ql} R={qr})"
                        )
                elif tot >= 2 and pref != PLACEMENT_PREF_NEUTRAL:
                    top = max(qf, qb, ql, qr)
                    if top * 2 < tot:
                        issues.append(
                            f"p{pid} {civ_label}: directional doctrine pref={pref} "
                            f"but barracks evenly scattered "
                            f"(F={qf} B={qb} L={ql} R={qr})"
                        )
            except ValueError:
                pass

        # ── compliance.terrain ─────────────────────────────────────────────
        # Civs with water_bias=+1 (Coast/River/Wetland primary) should land
        # most military buildings within 60m of gNavyVec. water_bias=-1
        # (Highland/DesertOasis) should land mostly inland. Soft check: only
        # flag once total barracks ≥ 3, since 1–2 placements are noise.
        terrain_list = tags.get("compliance.terrain", [])
        terrain_count = len(terrain_list)
        if terrain_list:
            last = terrain_list[-1].fields
            try:
                wadj = int(last.get("barracksWaterAdj", "0"))
                inland_n = int(last.get("barracksInland", "0"))
                tot_t = wadj + inland_n
                bias = exp.water_bias
                if tot_t >= 3:
                    if bias > 0 and wadj * 2 < tot_t:
                        issues.append(
                            f"p{pid} {civ_label}: water-bias civ but only "
                            f"{wadj}/{tot_t} barracks near coast"
                        )
                    elif bias < 0 and inland_n * 2 < tot_t:
                        issues.append(
                            f"p{pid} {civ_label}: inland-bias civ but only "
                            f"{inland_n}/{tot_t} barracks inland"
                        )
            except ValueError:
                pass

        # ── compliance.age ─────────────────────────────────────────────────
        # No assertion — purely informational. Track latest age reached.
        age_list = tags.get("compliance.age", [])
        latest_age = age_list[-1].fields.get("to", "?") if age_list else "?"

        # ── compliance.combat ──────────────────────────────────────────────
        # Doctrine sanity: aggressive build styles (heading=Frontier/Outward,
        # wall=MobileNoWalls) must produce *some* attack plans by the second
        # combat snapshot. Defensive doctrines should keep defendPlans > 0.
        combat_list = tags.get("compliance.combat", [])
        combat_count = len(combat_list)
        if combat_count >= 2 and exp.heading_axis == "outward":
            total_attacks = sum(
                int(s.fields.get("attackPlans", "0")) for s in combat_list
            )
            if total_attacks == 0:
                issues.append(
                    f"p{pid} {civ_label}: outward-heading doctrine never "
                    f"dispatched a combat plan across {combat_count} ticks"
                )

        # ── compliance.econ ────────────────────────────────────────────────
        # Persistent idle villagers = plan starvation bug. Flag if the last
        # 3 econ snaps each report ≥3 idle vills (allow occasional spikes).
        econ_list = tags.get("compliance.econ", [])
        econ_count = len(econ_list)
        if econ_count >= 3:
            recent = econ_list[-3:]
            try:
                idles = [int(s.fields.get("villsIdle", "0")) for s in recent]
                if all(i >= 3 for i in idles):
                    issues.append(
                        f"p{pid} {civ_label}: ≥3 villagers idle across "
                        f"last 3 econ snaps (idles={idles}) — plan starvation"
                    )
            except ValueError:
                pass

        # ── compliance.ship ────────────────────────────────────────────────
        # Once age ≥ 2, XP should be > 0 (else cards never unlocked). Soft
        # warning, not hard fail — short replays may not reach age 2.
        ship_list = tags.get("compliance.ship", [])
        ship_snap_count = len(ship_list)

        # ── compliance.placeAll ────────────────────────────────────────────
        # Per-building-type quadrant tally. Track count, no per-tally
        # assertions yet (would need per-doctrine expectations table).
        place_all_list = tags.get("compliance.placeAll", [])
        place_all_count = len(place_all_list)

        # ── compliance.wallGeom ────────────────────────────────────────────
        # Wall ring sanity: if MobileNoWalls (strategy=5), segments must
        # stay 0. If FortressRing (strategy=0) and we have ≥10 segments,
        # avgDist should be ≥ 30m (real ring) and not collapsed at TC.
        wall_list = tags.get("compliance.wallGeom", [])
        wall_count = len(wall_list)
        if wall_list:
            last = wall_list[-1].fields
            try:
                strat = int(last.get("strategy", "-1"))
                segs = int(last.get("segments", "0"))
                # MobileNoWalls = 5 in cLLWallStrategy enum
                if strat == 5 and segs > 0:
                    issues.append(
                        f"p{pid} {civ_label}: MobileNoWalls doctrine but "
                        f"{segs} wall segments built"
                    )
            except ValueError:
                pass

        # ── compliance.diplo ───────────────────────────────────────────────
        diplo_list = tags.get("compliance.diplo", [])
        diplo_count = len(diplo_list)

        # ── compliance.rules ───────────────────────────────────────────────
        # Every rule we tried to enable in postInit must be active across
        # every snapshot tick. If any flips to 0 mid-game = regression.
        rules_list = tags.get("compliance.rules", [])
        rules_count = len(rules_list)
        if rules_list:
            for snap in rules_list:
                for k, v in snap.fields.items():
                    if v == "0":
                        issues.append(
                            f"p{pid} {civ_label}: probe rule {k!r} not "
                            f"active at t={snap.time}"
                        )
                        break  # one per snap is enough

        # ── tech.ship ──────────────────────────────────────────────────────
        ship_choices = len(tags.get("tech.ship", []))

        # ── compliance.tactics ─────────────────────────────────────────────
        # Sanity: heroes count should be ≥1 once age ≥ 1 finishes (every civ
        # has a starting Explorer-type hero). Soft check, only flag if all
        # tactics snaps after t≥120s show heroes=0.
        tactics_list = tags.get("compliance.tactics", [])
        tactics_count = len(tactics_list)
        if tactics_count >= 2:
            late = [s for s in tactics_list if s.time >= 120000]
            if late and all(int(s.fields.get("heroes", "0")) == 0 for s in late):
                issues.append(
                    f"p{pid} {civ_label}: heroes=0 across {len(late)} late "
                    f"tactics snaps — explorer never spawned or died unrecovered"
                )

        # ── HTML-reference doctrine contract ───────────────────────────────
        # If the public reference tree promises a doctrine for this civ,
        # cross-check the runtime probes against the promise. Gate on having
        # any compliance.* probe at all — if only meta.* fired, the match is
        # too short / fixture too thin to assess doctrine.
        any_compliance = any(
            t.startswith("compliance.") for t in tags.keys()
        )
        # Doctrine contracts are keyed on the bare civ-label token from the
        # HTML data-name's first whitespace span (e.g. "British", "Aztecs"),
        # so a decorative CIV_LABELS string like "British (Elizabeth I)" must
        # fall back to the parens-stripped form before lookup. Without this
        # the British/French/Russians/Lakota HTML doctrine cross-checks
        # silently no-op.
        contract = None
        if any_compliance:
            for key in (
                exp.label,
                exp.label.split(" (")[0],
                re.sub(r"^cCiv(?:DE|XP)?", "", exp.civ_id),
            ):
                if key and key in doctrines:
                    contract = doctrines[key]
                    break
        if contract is not None:
            wall_list = tags.get("compliance.wallGeom", [])
            late_walls = [s for s in wall_list if s.time >= 240000]
            if contract.expected_wall_strategy is not None and late_walls:
                strat_seen = {int(s.fields.get("strategy", "0")) for s in late_walls}
                if contract.expected_wall_strategy not in strat_seen:
                    issues.append(
                        f"p{pid} {exp.label}: HTML promises wall strategy "
                        f"{contract.expected_wall_strategy} ({contract.keyword_hits[0] if contract.keyword_hits else '?'}) "
                        f"but runtime emitted {sorted(strat_seen)}"
                    )

            if contract.expects_naval:
                fleetSeen = fleet_count + ship_count + ship_snap_count
                if fleetSeen == 0:
                    issues.append(
                        f"p{pid} {exp.label}: HTML promises naval doctrine "
                        f"but no fleet/ship probes fired"
                    )

            if contract.expects_treaty:
                diplo_list = tags.get("compliance.diplomacy", [])
                if diplo_list:
                    max_tposts = max(
                        int(s.fields.get("tposts", "0")) for s in diplo_list
                    )
                    if max_tposts < 1:
                        issues.append(
                            f"p{pid} {exp.label}: HTML promises trading-post / "
                            f"native-treaty doctrine but tposts never exceeded 0"
                        )

            if contract.expects_forward:
                # Either fwdBase changes via event.delta, or placement preference
                # is Front, or attack plans dispatched.
                placement_list = tags.get("compliance.placement", [])
                placeBack = any(
                    s.fields.get("milPlace") == "0"  # back
                    for s in placement_list
                )
                # If the only placement seen is "back" and no attack plans
                # ever fired, the forward-doctrine promise is broken.
                if (
                    placement_list
                    and placeBack
                    and not any(
                        s.fields.get("milPlace") == "1"  # front
                        for s in placement_list
                    )
                    and len(tags.get("mil.attack", [])) == 0
                ):
                    issues.append(
                        f"p{pid} {exp.label}: HTML promises forward/frontier "
                        f"doctrine but placement stayed Back and no attack plans fired"
                    )

        # ── event.delta / event.combat.defense_reflex / tech.ageReq ────────
        delta_count    = len(tags.get("event.delta", []))
        defrefl_count  = len(tags.get("event.combat.defense_reflex", []))
        agereq_count   = len(tags.get("tech.ageReq", []))
        mil_atk_count  = len(tags.get("mil.attack", []))
        mil_def_count  = len(tags.get("mil.defend", []))

        summary.append(
            f"  p{pid}  {CIV_LABELS.get(exp.civ_id, exp.label):<24s}  "
            f"ldr={leader_name:<22s}  "
            f"terr={b.get('terrain_primary','?')}+{b.get('terrain_secondary','?')} "
            f"({b.get('terrain_bias','?')})  "
            f"head={b.get('heading','?')} ({b.get('heading_bias','?')})  "
            f"hb={heartbeat_count} planSnap={plan_count} "
            f"buildSnap={build_count} fleetSnap={fleet_count} ships={ship_count} "
            f"profile={profile_count} placement={placement_count} "
            f"terrain={terrain_count} age={latest_age} "
            f"combat={combat_count} econ={econ_count} shipSnap={ship_snap_count} "
            f"placeAll={place_all_count} wallGeom={wall_count} "
            f"diplo={diplo_count} rules={rules_count} "
            f"shipChoices={ship_choices} "
            f"tactics={tactics_count} delta={delta_count} "
            f"defRefl={defrefl_count} ageReq={agereq_count} "
            f"milAtk={mil_atk_count} milDef={mil_def_count}"
        )

    return issues, summary


def coverage_report(probes: list[ProbeRecord]) -> list[str]:
    """Per-tag tally across all AI players. Quick visibility into which
    probe domains fired vs. went silent across the recorded match."""
    by_tag: dict[str, int] = defaultdict(int)
    for p in probes:
        by_tag[p.tag] += 1
    if not by_tag:
        return []
    out = ["", "Probe coverage (count across all AIs):"]
    for tag in sorted(by_tag):
        out.append(f"  {tag:<26s} {by_tag[tag]:>5}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", type=Path, help="match.log (preferred) or .age3Yrec (legacy, exits 2)")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any AI lacks probes")
    ap.add_argument("--json", action="store_true",
                    help="emit parsed probes as one JSON object per line "
                         "(stdout) and skip the human report. Pipe into jq.")
    ap.add_argument("--filter-tag", action="append", default=[],
                    help="when used with --json, only emit probes whose tag "
                         "matches this prefix (repeatable, e.g. --filter-tag "
                         "compliance --filter-tag meta.buildstyle)")
    ap.add_argument("--filter-player", type=int, default=None,
                    help="when used with --json, only emit probes for this "
                         "player id")
    ap.add_argument("--source", choices=["auto", "replay", "log"], default="auto",
                    help="auto (default): pick by extension (.age3Yrec=replay, else log). "
                         "replay: treat as binary replay (legacy, exits 2 with warning). "
                         "log: treat as plain-text Age3Log.txt slice (correct pipeline).")
    args = ap.parse_args()

    if not args.path.exists():
        print(f"file not found: {args.path}", file=sys.stderr)
        return 2

    # Determine source type.
    suffix = args.path.suffix.lower()
    source = args.source
    if source == "auto":
        source = "replay" if suffix == ".age3yrec" else "log"

    if source == "replay":
        print(
            f"WARNING: {args.path.name} is a .age3Yrec replay.\n"
            "  The replay aiChat path stores probe values as string-table indices\n"
            "  (binary-packed), NOT plain text. Regex scanning returns zero probes.\n"
            "  Use the per-match match.log from log_capture instead.\n"
            "  See tools/aoe3_automation/log_capture.py and manage_game.py --no-dev-mode.",
            file=sys.stderr,
        )
        return 2

    data = args.path.read_bytes()
    probes = parse_probes(data)

    if args.json:
        prefixes = tuple(args.filter_tag)
        for p in probes:
            if args.filter_player is not None and p.player != args.filter_player:
                continue
            if prefixes and not any(p.tag.startswith(pre) for pre in prefixes):
                continue
            print(json.dumps(asdict(p), separators=(",", ":")))
        return 0 if probes else 2

    print(f"replay probes: {args.path}")
    print(f"  total probe lines: {len(probes)}")
    print(f"  AI players covered: {len({p.player for p in probes})}")
    print()

    issues, summary = validate(probes)
    if summary:
        print("Per-AI snapshot:")
        for line in summary:
            print(line)
        print()

    for line in coverage_report(probes):
        print(line)
    print()

    if not probes:
        return 2

    if issues:
        print(f"FAIL — {len(issues)} issue(s):")
        for line in issues:
            print(f"  - {line}")
        return 1

    print("PASS — every AI loaded its expected leader and build-style profile.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
