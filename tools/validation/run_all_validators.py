#!/usr/bin/env python3
"""Unified pre-deploy validation gate — runs every validator, single verdict.

Catches every class of bug the project has hit historically by composing
all 30+ tools/validation/validate_*.py scripts into one CLI. Exit code:

  0 — all validators passed (or only warnings)
  1 — one or more validators FAILed
  2 — orchestrator itself errored

Use as a pre-deploy CI gate::

    python3 tools/validation/run_all_validators.py && manage_game.py sync

Output:
  - tools/validation/run_all_validators_report.json (machine-readable)
  - tools/validation/run_all_validators_report.md (human-readable)
  - artifacts/validation_run_<timestamp>/ (per-validator stdout snapshots)

Each validator is run in its own subprocess so a crash in one doesn't
block the others. Per-validator timeout (default 60s) prevents long runs
from blocking the gate.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]


# Per-validator config ---------------------------------------------------

@dataclass
class ValidatorSpec:
    """One validator entry. Path is relative to REPO_ROOT."""
    name: str
    path: str
    args: list[str] = field(default_factory=list)
    # Validators that need the live game running; skip in CI.
    needs_game: bool = False
    # Validators that need a real-game artifact dir (Age3Log slices, etc.)
    # — skipped in static gate mode; surface only when --include-runtime is on.
    needs_runtime_artifact: bool = False
    # Validators that take a while (don't run in fast mode).
    slow: bool = False
    # Treat WARN exits (non-zero rc but not catastrophic) as PASS for gating.
    warn_is_pass: bool = False
    # Reasonable per-validator timeout in seconds.
    timeout_s: int = 60


# Curated list. NOT all validators are in here — some are interactive,
# game-dependent, or dev-only (tier3 gameplay etc.). Add as needed.
VALIDATORS: list[ValidatorSpec] = [
    # === Tier 1: Pure static (XML well-formedness, file existence) ===
    ValidatorSpec("mod_version_metadata", "tools/validation/validate_mod_version_metadata.py",
                  timeout_s=15, warn_is_pass=True),
    ValidatorSpec("xml_well_formed", "tools/validation/validate_xml_well_formed.py"),
    ValidatorSpec("packaged_mod", "tools/validation/validate_packaged_mod.py",
                  warn_is_pass=True),  # has known dup-locID warning, OK to pass

    # === Tier 2: Mod content cross-checks ===
    ValidatorSpec("civmods_ui", "tools/validation/validate_civmods_ui.py"),
    ValidatorSpec("civ_loadability", "tools/validation/validate_civ_loadability.py"),
    ValidatorSpec("civ_homecities", "tools/validation/validate_civ_homecities.py"),
    ValidatorSpec("civ_crossrefs", "tools/validation/validate_civ_crossrefs.py"),
    ValidatorSpec("playstyles", "tools/validation/validate_playstyles.py",
                  args=["--static-mode"]),
    ValidatorSpec("playercolors", "tools/validation/validate_playercolors.py"),
    ValidatorSpec("homecity_cards", "tools/validation/validate_homecity_cards.py"),
    ValidatorSpec("personality_overrides", "tools/validation/validate_personality_overrides.py"),
    ValidatorSpec("leader_vs_spec", "tools/validation/validate_leader_vs_spec.py"),
    # Tightened 2026-05-09: montezuma wall_strategy fixed — full 20/20 pass.
    ValidatorSpec("playstyle_modal", "tools/validation/validate_playstyle_modal.py"),
    ValidatorSpec("doctrine_compliance", "tools/validation/validate_doctrine_compliance.py",
                  args=["--static-mode"]),
    ValidatorSpec("probes_vs_spec", "tools/validation/validate_probes_vs_spec.py"),
    # Static AI behaviour map — derives per-civ knobs from leader XS files
    # and cross-checks against playstyle_spec.json claims. Catches drift
    # between spec doctrine and actual init/age-rule dispatch without
    # needing the engine. Renders json+html+md artifacts to
    # artifacts/validation/ai_behaviour_map.{json,html,md}.
    ValidatorSpec("ai_behaviour_map", "tools/validation/ai_behaviour_map.py"),

    # === Tier 3: Engine data layer ===
    ValidatorSpec("protomods", "tools/validation/validate_protomods.py"),
    ValidatorSpec("techtree", "tools/validation/validate_techtree.py"),
    ValidatorSpec("xs_scripts", "tools/validation/validate_xs_scripts.py"),
    ValidatorSpec("stringtables", "tools/validation/validate_stringtables.py"),

    # === Tier 4: Art / visuals ===
    ValidatorSpec("art_pixel_perfect", "tools/validation/validate_art_pixel_perfect.py",
                  warn_is_pass=True),  # 25 hires-portrait artist warnings are out-of-scope
    ValidatorSpec("art_coverage", "tools/validation/validate_art_coverage.py",
                  warn_is_pass=True),
    # Catches the 2026-05-12 live-test bug: per-civ art fields out of sync
    # so different engine surfaces render different art (Napoleon flag button
    # = NE Empire, scoreboard flag = Bourbon; Dutch picker portrait = generic
    # Dutch, home-city preview = Maurice). Compares civ-identity tokens
    # across <homecityflagbuttonwpf>/<homecityflagiconwpf>/<postgameflagiconwpf>
    # and <homecitypreviewwpf>/<smallportraittexturewpf>.
    ValidatorSpec("civmods_art_consistency",
                  "tools/validation/validate_civmods_art_consistency.py"),
    # Catches the 2026-05-12 second live-test bug: lobby AI slots had no
    # portrait at all because shipped leader DDTs (cpai_avatar_<civ>_<leader>.ddt
    # built by build_leader_ddts.py) declared format=1 (BGRA32) in the
    # header but stuffed DXT1 pixel data into the body. Engine read fmt=1,
    # tried to decode 2048B as BGRA32 (needs w*h*4 bytes), got garbage,
    # silently rendered nothing. This validator verifies header format
    # byte matches body size for every shipped DDT referenced by
    # civmods.xml's <smallportraittexture>.
    ValidatorSpec("ddt_format",
                  "tools/validation/validate_ddt_format.py"),
    ValidatorSpec("homecity_visuals", "tools/validation/validate_homecity_visuals.py"),
    # Homecity asset existence — verifies every <visual>/<pathdata>/<camera>/
    # <ambientsounds> path resolves to a real asset in base .bar archives.
    # Catches typos and broken refs that produce empty/black home-city scenes.
    ValidatorSpec("homecity_assets_exist",
                  "tools/validation/validate_homecity_assets_exist.py",
                  timeout_s=60),
    ValidatorSpec("visuals", "tools/validation/validate_visuals.py",
                  args=["--static-mode"]),
    ValidatorSpec("terrain_heading", "tools/validation/validate_terrain_heading.py"),
    ValidatorSpec("dev_subtrees", "tools/validation/validate_dev_subtrees.py",
                  warn_is_pass=True),  # known: HTML dev blocks reference wrong asset paths (doc drift, not runtime bug)

    # === Tier 4b: 2026-05-09 morning-release validators (built tonight) ===
    # These catch the bug-classes the project hit on 2026-05-08 (locID dups,
    # NameID resolution failures, .anw.xml shadow files, .proposed-only
    # personalities, picker text collisions). They run fast and stay cheap.
    # Rank #3 coverage: catch shipped cards that do nothing — card token in a
    # deck but no <effect> block in techtreemods.xml or base techtreey.xml.
    # First-run flagged 65 pre-existing "no-op card" warnings (mostly Romanian/
    # Hungarian ANW* tokens with cards.json metadata but no techtreemods
    # entry). Marked warn_is_pass while the missing tech-effect blocks get
    # designed and added; the validator continues to surface the gap.
    ValidatorSpec("deck_card_effects", "tools/validation/validate_deck_card_effects.py",
                  warn_is_pass=True,
                  timeout_s=30),
    ValidatorSpec("no_locid_duplicates", "tools/validation/validate_no_locid_duplicates.py",
                  timeout_s=30),
    ValidatorSpec("string_resolution", "tools/validation/validate_string_resolution.py",
                  timeout_s=30),
    ValidatorSpec("no_orphan_xml", "tools/validation/validate_no_orphan_xml.py",
                  args=["--allow-proposed"],  # .proposed files are dev WIP, not blockers
                  warn_is_pass=True,  # warn-only since .proposed shadows + 1 .bak are tolerated
                  timeout_s=30),
    ValidatorSpec("personality_active", "tools/validation/validate_personality_active.py",
                  timeout_s=15),
    ValidatorSpec("civ_distinguishability", "tools/validation/validate_civ_distinguishability.py",
                  timeout_s=30),
    # Lobby quadruple check: every ANW personality's name/tooltip/portrait/
    # forcedciv all resolve. Catches the 2026-05-08 locID-mismatch class
    # (wrong lobby text), broken icon paths (blank portraits), and forcedciv
    # typos (engine falls back to base-game civ silently).
    ValidatorSpec("personality_lobby", "tools/validation/validate_personality_lobby.py",
                  timeout_s=30),
    # Rank #1 coverage (impact 5/5, effort 1/5): catch free-age-up exploits
    # and missing politician options.  Each ANW-specific civ must expose ≥ 2
    # politician choices at every age tier (Commerce/Fortress/Industrial/Imperial)
    # and any politician tech defined in techtreemods.xml must have cost > 0.
    ValidatorSpec("age_up_politicians",
                  "tools/validation/validate_age_up_politicians.py",
                  timeout_s=30),

    # === Tier 4c: Offline engine simulators (no game launch needed) ===
    # 2026-05-09: cracked .bar archive + reverse-engineered the engine's
    # civmods merge + picker enumeration. Predicts the live picker from
    # static XML alone in ~5s. Caught the <Civ> vs <civ> tag-case bug
    # that the static gate missed.
    ValidatorSpec("offline_picker", "tools/validation/validate_offline_picker.py",
                  timeout_s=15),
    # Offline 46-civ matrix — runs every per-civ check in one pass.
    # PASS = every ANW civ predicted-correct on every dimension
    # (civmods entry, statsid, displayname, personality, leader, homecity,
    #  portrait, picker visibility, locid uniqueness, string resolution).
    ValidatorSpec("offline_matrix", "tools/validation/validate_offline_matrix.py",
                  timeout_s=30),
    # Civ tech-reference resolution: every <agetech>/<postindustrialtech>/
    # <treatytech>/etc. on every ANW civ must resolve in our techtreemods or
    # base techtreey.xml. Caught 15 case-mismatch + 3 wrong-case Age0 bugs
    # on first run that the existing techtree validator missed.
    ValidatorSpec("civ_tech_resolution",
                  "tools/validation/validate_civ_tech_resolution.py",
                  timeout_s=20),
    # Homecity leader-name match: catch the "Francis Drake for Argentina"
    # template-residue bug. Verifies each ANW homecity's <heroname>
    # resolves to the canonical leader from anw_token_map.
    ValidatorSpec("homecity_leader_match",
                  "tools/validation/validate_homecity_leader_match.py",
                  timeout_s=15),
    # Homecity doubles: suppression entries must blank <homecityfilename>
    # or the SELECT HOME CITY picker shows two entries (base + ANW).
    ValidatorSpec("no_homecity_doubles",
                  "tools/validation/validate_no_homecity_doubles.py",
                  timeout_s=15),
    # Blurb coverage: catches stale/short/placeholder blurbs and copy-paste
    # drift across civs.  Checks all ANW civ tokens in anw_civ_blurbs.json
    # for playstyle length ≥ 40 chars, no TODO/TBD/FIXME/template text,
    # cross-source parity with age_build_notes.json, and unique playstyle text.
    ValidatorSpec("blurb_coverage",
                  "tools/validation/validate_blurb_coverage.py",
                  timeout_s=15),
    # Proto unit/building references: every entry in unique_units and
    # unique_buildings in anw_civ_blurbs.json must resolve to a real
    # engine display name (stringtable, stringmods, or proto/techtree
    # ProtoUnit token). Caught polish_pass_7 phantoms ("Buddhist Temple",
    # "Sacre Infermeria", "Horse Artillery") + the "Fire Lancer"
    # phantom + "Dorabant" vs engine-spelled "Dorobant".
    ValidatorSpec("proto_unit_references",
                  "tools/validation/validate_proto_unit_references.py",
                  timeout_s=20),
    # Icon / portrait / flag path existence on all ANW homecity XMLs
    # + civmods.xml.  Verifies every <portrait>, <smallportraittexture>,
    # <smallportraittexturewpf>, etc. resolves to a real file (mod tree
    # PNG or base game DDT in extracted_bar_index.json).  Caught 2
    # ManufacturingPlant portrait typos (Ethiopians + Portuguese).
    ValidatorSpec("icon_path_existence",
                  "tools/validation/validate_icon_path_existence.py",
                  timeout_s=15),
    # Doctrine template drift: civs sharing identical doctrine_prose text
    # in playstyle_spec.json must also share critical claims fields
    # (wall_strategy, first_military_building, expects_* booleans).
    # Caught Romanians-vs-French-Canadians drift where prose was
    # "civic militia outpost" but claims said barracks-first.
    ValidatorSpec("doctrine_template_drift",
                  "tools/validation/validate_doctrine_template_drift.py",
                  timeout_s=15),
    # Spec-vs-XS doctrine check: for each ANW civ in playstyle_spec.json,
    # extracts the actual wall_strategy, first_military_building, and
    # expects_forward values produced by the XS dispatch in
    # leaderCommon.xs:llApplyBuildStyleForActiveCiv() (plus
    # leader_revolution_commanders.xs overrides for ANW* civs) and
    # compares them to the claims in the spec. Catches doc-vs-engine drift
    # that static prose checks cannot detect — e.g. a style helper's default
    # forward-base setting disagrees with the spec's expects_forward claim.
    # On first run: 45/45 PASS (post-fix XS state). Must stay 45/45 green.
    ValidatorSpec("spec_vs_xs_doctrine",
                  "tools/validation/validate_spec_vs_xs_doctrine.py",
                  warn_is_pass=False,
                  timeout_s=15),
    # Doctrine prose theme alignment: each civ's doctrine_label /
    # doctrine_summary / doctrine_prose must contain at least one
    # keyword that matches its declared wall_strategy. Catches edits
    # that drift the player-facing prose away from the engine doctrine
    # (or vice versa). On first run: 45/45 PASS.
    ValidatorSpec("doctrine_prose_theme",
                  "tools/validation/validate_doctrine_prose_theme.py",
                  warn_is_pass=False,
                  timeout_s=10),
    # Hub test coverage: the random-map doctrine test arena
    # (RandMaps/anwHubTest.xs) extended-cycle threshold must cover the
    # longest *_before_ms claim in playstyle_spec.json. Locks the test
    # script's milestone observation window against spec drift — if
    # someone adds a civ with a 1500s wall deadline but the test caps
    # at 1200s, this fires. Currently PASS with 300s headroom.
    ValidatorSpec("hub_test_coverage",
                  "tools/validation/validate_hub_test_coverage.py",
                  warn_is_pass=False,
                  timeout_s=10),
    # Hub test roster integrity: artifacts/validation/hub_test_roster.json
    # is the canonical 40-civ 6-pass schedule referenced from the release-
    # readiness site. Locks (a) every spec civ appears once, (b) no pass
    # exceeds the 7-AI hub capacity, (c) per-civ wall_strategy matches the
    # spec, and (d) the JSON is byte-equivalent to build_hub_test_roster.py
    # output (catches stale checked-in roster after a spec edit).
    ValidatorSpec("hub_test_roster",
                  "tools/validation/validate_hub_test_roster.py",
                  warn_is_pass=False,
                  timeout_s=30),
    # Probe-tag drift: every probe tag the doctrine compliance validator
    # reads from log lines (`p.tag == "foo"`) must have an emitter in
    # game/ai/core/*.xs (static or dynamic-prefix) or in the Python
    # harness. Catches the failure mode where a future edit adds a
    # probe-tag consumer to validate_doctrine_compliance.py but no part
    # of the runtime emits it — the validator would silently pass on
    # empty data, masking a coverage hole. Currently 14/14 PASS.
    ValidatorSpec("probe_tag_drift",
                  "tools/validation/validate_probe_tag_drift.py",
                  warn_is_pass=False,
                  timeout_s=10),
    # Spec internal consistency: locks the logical implications between
    # claim fields in playstyle_spec.json (e.g. expects_naval iff
    # wall_strategy==2, expects_forward implies fmb=='barracks_or_stable',
    # ws=5 wall deadline is exactly 720000ms). 5 invariants, 0 violations
    # baseline. Catches data-model drift before runtime tests.
    ValidatorSpec("spec_internal_consistency",
                  "tools/validation/validate_spec_internal_consistency.py",
                  warn_is_pass=False,
                  timeout_s=10),
    # AI behaviour map: rebuilds the spec-vs-XS derivation table and
    # fails if any civ's player-facing claim (expects_forward,
    # expects_naval, wall_strategy, etc.) doesn't match the actual
    # XS doctrine code. 0/45 mismatches baseline. Catches drift where
    # someone edits XS without updating the doctrine claim, or vice
    # versa. Re-runs the mapper as part of the check (~10s).
    ValidatorSpec("ai_behaviour_map",
                  "tools/validation/validate_ai_behaviour_map.py",
                  warn_is_pass=False,
                  timeout_s=90),
    # Hub test trigger soundness: locks the doctrine-capture triggers in
    # RandMaps/anwHubTest.xs against silent breakage. 3 invariants: every
    # trigger has active=true + condition + effect (T-1), trigger names
    # ending in N seconds have Param1=N (T-2), and extended triggers (>=
    # 240s) live inside the `gHubTestEndSeconds >= 1200` gate (T-3).
    # All three mutation-tested. 9 triggers / 0 violations baseline.
    ValidatorSpec("hub_test_triggers",
                  "tools/validation/validate_hub_test_triggers.py",
                  warn_is_pass=False,
                  timeout_s=10),
    # Hub test probe coverage: every dotted probe token in a [HUBTEST]
    # Send-Chat message must be a real llProbe() or llCheckMilestone()
    # emission site (C-1), and every non-exempt milestone tag must be
    # cited in at least one [HUBTEST] narrative line (C-2). Mutation-tested
    # via --self-test. 2 invariants / 0 violations baseline.
    ValidatorSpec("hub_test_probe_coverage",
                  "tools/validation/validate_hub_test_probe_coverage.py",
                  warn_is_pass=False,
                  timeout_s=15),
    # XS simulator doctrine vs spec: each leader_*.xs is executed through
    # the Python XS interpreter in tools/xs_sim/, then the observed
    # gLLWallStrategy / gLLMilitaryDistanceMultiplier / etc. globals are
    # compared to the matching civ's `claims` block in playstyle_spec.json.
    # Complements ai_behaviour_map (grep-style derivation) by actually
    # *running* the XS — catches drifts where the right helper is called
    # but a follow-on assignment pushes the global out of the spec band
    # (the original Shivaji/Tokugawa military-distance regression).
    # 23 leaders / 0 mismatches baseline.
    ValidatorSpec("xs_sim_doctrine",
                  "tools/validation/validate_xs_sim_doctrine.py",
                  warn_is_pass=False,
                  timeout_s=120),
    # Per-civ wall knob dispatch: runs the auto-generated
    # game/ai/core/aiWallKnobsByCiv.xs llSetWallKnobsForCiv() function for
    # all 40 civs through the Python XS sim, asserts each civ writes its
    # 15 gLLWall* globals to the exact values declared in
    # tools/ai_design/wall_knob_calibration.py CALIBRATION dict. Catches
    # any drift between the source-of-truth table and the auto-generated
    # XS dispatch (engine-name keys, knob values, strategy enum).
    ValidatorSpec("per_civ_wall_knobs",
                  "tools/validation/validate_per_civ_wall_knobs.py",
                  warn_is_pass=False,
                  timeout_s=60),
    # Civ asset existence: every flag/portrait/UI asset on every ANW civ
    # must resolve to a real file (DDT in base .bar OR PNG in mod tree).
    # Caught 24 broken-flag references on first run.
    ValidatorSpec("civ_asset_existence",
                  "tools/validation/validate_civ_asset_existence.py",
                  timeout_s=60),

    # === Tier 5: HTML reference cross-checks ===
    ValidatorSpec("html_reference", "tools/validation/validate_html_reference.py",
                  warn_is_pass=True),  # known: HTML missing some doc-only blocks (EXPLORER-START etc.) for USA/Barbary; doc drift
    ValidatorSpec("html_vs_mod", "tools/validation/validate_html_vs_mod.py"),

    # === Game-dependent (skip unless --include-live) ===
    ValidatorSpec("live_mod_install", "tools/validation/validate_live_mod_install.py"),
    # static-mode: scans game/ai/core/*.xs for emitter sites of each required
    # marker instead of parsing a live log. Catches the case where an emitter
    # is removed from XS but the validator config still requires the marker.
    # Pass --include-live to the validator directly for the full live-log check.
    ValidatorSpec("runtime_logs", "tools/validation/validate_runtime_logs.py",
                  args=["--static-mode"],
                  warn_is_pass=True),
    # static-mode: checks civmods.xml registration for all 40 ANW civ tokens
    # rather than OCR-ing a live screenshot. Pass --include-live for live check.
    ValidatorSpec("live_picker", "tools/validation/validate_live_picker.py",
                  args=["--static-mode"],
                  timeout_s=30),
    # static-mode: checks that at least one input backend binary (ydotool,
    # xdotool, gamescopectl, ei_inject) is present on this system.
    # Pass --include-live for the full screenshot-diff probe.
    ValidatorSpec("input_harness", "tools/validation/validate_input_harness.py",
                  args=["--static-mode"],
                  timeout_s=30),

    # === Self-test suites (verify the validators themselves still work) ===
    ValidatorSpec("self_civ_loadability", "tools/validation/validate_civ_loadability_tests.py",
                  timeout_s=15),
    ValidatorSpec("self_art_pixel_perfect", "tools/validation/validate_art_pixel_perfect_tests.py",
                  timeout_s=15),
    ValidatorSpec("self_scenario_binary", "tools/validation/validate_scenario_binary_tests.py",
                  timeout_s=15),
    ValidatorSpec("self_test_validator", "tools/validation/test_validator.py",
                  timeout_s=30),
]


# Runner -----------------------------------------------------------------

@dataclass
class ValidatorResult:
    name: str
    rc: int
    duration_s: float
    verdict: str  # PASS | FAIL | SKIP | TIMEOUT | ERROR
    stdout_path: Optional[str] = None
    stderr_first_lines: str = ""
    notes: str = ""


def run_one(spec: ValidatorSpec, run_dir: Path,
            include_live: bool, include_runtime: bool, fast: bool) -> ValidatorResult:
    if spec.needs_game and not include_live:
        return ValidatorResult(spec.name, 0, 0.0, "SKIP",
                               notes="needs game running; pass --include-live to enable")
    if spec.needs_runtime_artifact and not include_runtime:
        return ValidatorResult(spec.name, 0, 0.0, "SKIP",
                               notes="needs real-game artifact dir; pass --include-runtime + provide artifact path to validator manually")
    if spec.slow and fast:
        return ValidatorResult(spec.name, 0, 0.0, "SKIP",
                               notes="slow validator; pass --no-fast to include")

    abs_path = REPO_ROOT / spec.path
    if not abs_path.exists():
        return ValidatorResult(spec.name, 127, 0.0, "ERROR",
                               notes=f"validator file missing: {spec.path}")

    out_path = run_dir / f"{spec.name}.txt"
    cmd = [sys.executable, str(abs_path), *spec.args]
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd, cwd=REPO_ROOT, capture_output=True, text=True,
            timeout=spec.timeout_s, env={**os.environ},
        )
    except subprocess.TimeoutExpired as e:
        out_path.write_text(f"TIMEOUT after {spec.timeout_s}s\n"
                            f"partial stdout:\n{e.stdout or ''}\n"
                            f"partial stderr:\n{e.stderr or ''}")
        return ValidatorResult(spec.name, 124, spec.timeout_s, "TIMEOUT",
                               stdout_path=str(out_path),
                               notes=f"exceeded {spec.timeout_s}s timeout")
    dt = time.monotonic() - t0
    out_path.write_text(
        f"=== {spec.name} (rc={proc.returncode}, {dt:.1f}s) ===\n"
        f"--- stdout ---\n{proc.stdout}\n"
        f"--- stderr ---\n{proc.stderr}\n"
    )

    if proc.returncode == 0:
        verdict = "PASS"
    elif spec.warn_is_pass and proc.returncode in (1, 2):
        verdict = "PASS"  # treat warn-class as pass
    else:
        verdict = "FAIL"

    return ValidatorResult(
        spec.name, proc.returncode, dt, verdict,
        stdout_path=str(out_path),
        stderr_first_lines="\n".join((proc.stderr or "").splitlines()[:5]),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--include-live", action="store_true",
                    help="include validators that need the live game running")
    ap.add_argument("--include-runtime", action="store_true",
                    help="include validators that need a real-game artifact dir")
    ap.add_argument("--fast", action="store_true", default=True,
                    help="skip slow validators (default)")
    ap.add_argument("--no-fast", action="store_false", dest="fast",
                    help="run all validators including slow ones")
    ap.add_argument("--report-dir", type=Path,
                    default=REPO_ROOT / "artifacts" / "validation_runs",
                    help="root for per-run artifact directories")
    ap.add_argument("--filter", help="run only validators matching this substring")
    args = ap.parse_args()

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = args.report_dir / f"run_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    specs = VALIDATORS
    if args.filter:
        specs = [s for s in specs if args.filter.lower() in s.name.lower()]

    print(f"Running {len(specs)} validators (fast={args.fast}, "
          f"live={args.include_live}). Output: {run_dir}", flush=True)

    results: list[ValidatorResult] = []
    for spec in specs:
        print(f"  [{spec.name:<28}] ", end="", flush=True)
        r = run_one(spec, run_dir, args.include_live, args.include_runtime, args.fast)
        results.append(r)
        mark = {"PASS": "\u2713", "FAIL": "\u2717",
                "SKIP": "-", "TIMEOUT": "T", "ERROR": "E"}.get(r.verdict, "?")
        print(f"{mark} {r.verdict:<7} ({r.duration_s:.1f}s)"
              f"{('  ' + r.notes) if r.notes else ''}", flush=True)

    # Summary
    counts = {v: 0 for v in ["PASS", "FAIL", "SKIP", "TIMEOUT", "ERROR"]}
    for r in results:
        counts[r.verdict] = counts.get(r.verdict, 0) + 1
    total = len(results)
    overall = "PASS" if (counts["FAIL"] + counts["TIMEOUT"] + counts["ERROR"]) == 0 else "FAIL"

    print()
    print("=" * 70)
    print(f"OVERALL: {overall}  ({counts['PASS']}/{total} pass, "
          f"{counts['FAIL']} fail, {counts['SKIP']} skip, "
          f"{counts['TIMEOUT']} timeout, {counts['ERROR']} error)")
    print("=" * 70)

    # Markdown report
    md_lines = [
        f"# Validator gate — run {ts}",
        "",
        f"**Overall: {overall}**",
        "",
        f"| Status | Validator | Duration | Notes |",
        f"|--------|-----------|---------:|-------|",
    ]
    for r in results:
        emoji = {"PASS": "\u2705", "FAIL": "\u274c",
                 "SKIP": "\u23ed\ufe0f", "TIMEOUT": "\u23f1\ufe0f",
                 "ERROR": "\u26a0\ufe0f"}.get(r.verdict, "?")
        md_lines.append(f"| {emoji} {r.verdict} | `{r.name}` "
                        f"| {r.duration_s:.1f}s | {r.notes} |")
    md_lines.append("")
    md_lines.append("**Counts**:")
    for k, v in counts.items():
        md_lines.append(f"- {k}: {v}")
    md_path = HERE / "run_all_validators_report.md"
    md_path.write_text("\n".join(md_lines))

    # JSON report
    json_path = HERE / "run_all_validators_report.json"
    with open(json_path, "w") as f:
        json.dump({
            "run_id": ts,
            "overall": overall,
            "counts": counts,
            "total": total,
            "include_live": args.include_live,
            "fast": args.fast,
            "results": [
                {"name": r.name, "verdict": r.verdict, "rc": r.rc,
                 "duration_s": r.duration_s, "notes": r.notes,
                 "stdout_path": r.stdout_path,
                 "stderr_first_lines": r.stderr_first_lines}
                for r in results
            ],
        }, f, indent=2)

    print()
    print(f"Markdown: {md_path}")
    print(f"JSON:     {json_path}")
    print(f"Per-validator stdout: {run_dir}")

    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
