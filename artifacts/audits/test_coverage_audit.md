# Test Coverage Audit — Legendary Leaders Mod

Worktree: `hungry-banzai-e122dc` Date: 2026-04-28 Read-only audit.

## 1. Test inventory

`pytest` is not installed in the runtime, so functions were enumerated via grep
(`def test_`). All test files live under `tests/`; total = **17 test modules**,
**~110 test functions**.

### `tests/playtest/`

| File | Tests | Asserts | Subsystem |
|---|---|---|---|
| `test_replay_probes.py` | 41 | k=v parsing, leader-init match, profile drift, doctrine/placement/terrain/idle/walls/heroes rules, event tags, Aztec/British HTML cross-checks, coverage counters | Replay validator + probe matcher (`tools/playtest/replay_probes.py`) |
| `test_expectations.py` | 9 | terrain bias math, axis lookup, 48-civ load, label presence, strength range, heading/terrain constants, revolution/base deck naming | Expectations table (`tools/playtest/expectations.py`) |
| `test_minimap.py` | 7 | bearing detection N/E, no-pixel fallback, team-color routing, coast/inland building placement | Minimap analysis (`tools/playtest/minimap.py`) |

### `tests/validation/`

| File | Tests | Module under test |
|---|---|---|
| `test_validate_xs_scripts.py` | 13 | `validate_xs_scripts.py` — duplicate locals, unsupported builtins, loader-order, ASCII rules, `g_` var declaration |
| `test_validate_civ_homecities.py` | 5 | `validate_civ_homecities.py` — civmods⇄homecity binding, orphan files, lowercase tags |
| `test_validate_civ_crossrefs.py` | 5 | `validate_civ_crossrefs.py` — string locID + tech refs |
| `test_validate_civmods_ui.py` | 2 | `validate_civmods_ui.py` — UI fields, lowercase civ tags |
| `test_validate_homecity_cards.py` | 3 | `validate_homecity_cards.py` — prereq case, custom prereq techs |
| `test_validate_stringtables.py` | 2 | `validate_stringtables.py` — locid validity, empty strings |
| `test_validate_playstyle_modal.py` | 8 | `validate_playstyle_modal.py` — modal data⇄node consistency, jargon leaks, age keys |
| `test_validate_terrain_heading.py` | 4 | `validate_terrain_heading.py` — civ branch coverage, terrain constants, strength range |
| `test_validate_runtime_logs.py` | 5 | `validate_runtime_logs.py` — runtime marker order, regex spec, unknown suite |
| `test_validate_packaged_mod.py` | 1 | `validate_packaged_mod.py` — dev-only path exclusion |
| `test_validate_live_mod_install.py` | 2 | `validate_live_mod_install.py` — install diff, mismatched files |
| `test_run_staged_validation.py` | 5 | `run_staged_validation.py` — stage normalization, summary, runtime skip |
| `test_aoe3_ui_automation.py` | 3 | `tools/aoe3_automation/aoe3_ui_automation.py` — text-box matching, repeat indices |

No tests are `@skip`-marked or `xfail` — `grep -r "skip" tests/` returns zero.

## 2. Coverage status — per subsystem

### XS playstyles
- Note: there is **no `game/ai/playstyles/` directory** in this worktree.
  "Playstyle" is a UI/HTML concept, encoded as bullets in
  `a_new_world.html` and surfaced through
  `validate_playstyle_modal.py`. The XS implementation lives in the leader
  files plus `game/ai/core/`.
- Tested: modal⇄data⇄string-id consistency (`test_validate_playstyle_modal.py`).
- Untested: that the XS code path each playstyle promises (mobile-no-walls,
  naval, turtle, hero-late, etc.) is actually exercised in a probe replay for
  every leader. Today only Aztec and British have explicit HTML-vs-replay
  assertions (`test_replay_probes.py:548,564,575`).
- 100% = one HTML-promise → replay-violation test per playstyle tag, driven
  off the bullet list parsed from `a_new_world.html`.

### XS leaders
- 26 leader files in `game/ai/leaders/leader_*.xs` plus `leaderCommon.xs`,
  `leader_revolution_commanders.xs`, `leader_revolution_support.xs`.
- Tested: the **shape** of every leader file via `validate_xs_scripts.py`
  (parse, builtins, loader order, ASCII, `g_` vars). Two leaders
  (Aztec/Montezuma, British/Wellington) have replay-driven behaviour assertions.
- Untested: 24 of 26 leaders have **no behavioural assertion**. There is no
  generic "leader X must call its init function and emit a `LEADER_INIT_OK`
  probe" parametrised test.
- 100% = one parametrised test per leader that loads its expectations row
  (already in `tools/playtest/expectations.py`) and confirms a fixture replay
  contains the matching `LEADER_INIT`/`PERSONALITY_APPLIED`/`STYLE_APPLIED`
  probes. Drive it via `pytest.mark.parametrize("leader", LEADERS)`.

### Civ definitions
- `data/civmods.xml` ⇄ homecity binding: covered (`test_validate_civ_homecities.py`).
- `data/civmods.xml` UI/string refs: covered (`test_validate_civmods_ui.py`,
  `test_validate_civ_crossrefs.py`).
- `data/playercolors.xml`: **not validated by any test**. No
  `validate_playercolors.py` exists. Label/flag/leader consistency between
  `playercolors.xml`, `civmods.xml`, and the avatar PNGs in
  `resources/images/icons/singleplayer/cpai_avatar_*.png` is unchecked.
- 100% = a `validate_playercolors.py` plus a test that asserts every civ in
  `civmods.xml` has a matching colour entry, and every `cpai_avatar_<civ>_<leader>.png`
  asset is referenced from at least one civ/leader binding (the recent
  `british_elizabeth`, `lakota_gall`, `napoleonic_france_napoleon`,
  `russians_ivan` PNGs landed without a coverage net).

### Home-city scenes — **THE `pathdata` BUG IS UNGUARDED**
- 25 `data/anwhomecity*.xml` files contain `<visual>` /
  `<watervisual>` / `<backgroundvisual>` / `<pathdata>` / `<camera>` paths.
- `validate_civ_homecities.py` only checks **filename binding from
  `civmods.xml`**, not the *contents* of the home-city XML. `grep -c
  "pathdata\|<visual>" tools/validation/validate_civ_homecities.py` = **0**.
- The recently-fixed regression (25 files where
  `<pathdata>revolution\pathable_area.gr2</pathdata>` was paired with a
  parent-civ `<visual>ottoman\…</visual>` / `dutch\…`) **has no test**.
  There is no regression net.
- 100% = `validate_homecity_visuals.py` that asserts the *namespace prefix*
  (`ottoman\`, `dutch\`, `british\`, `revolution\`, …) of `<visual>`,
  `<watervisual>`, `<backgroundvisual>`, `<pathdata>`, `<camera>`,
  `<widescreencamera>` all agree, plus a parametrised test running it across
  all `anwhomecity*.xml`.

### Doctrine HTML reference (`a_new_world.html`)
- Helper module exists: `tools/playtest/html_reference.py` and
  `tools/validation/validate_html_vs_mod.py`.
- Tested indirectly: `test_replay_probes.py:548-589` reads HTML promises for
  Aztec/British and verifies replay compliance.
- Untested: `validate_html_vs_mod.py` itself has **no unit test**. There is no
  test that walks all `<civ>` cards in the HTML and asserts each promised
  bullet maps to an XS code path or an expectations-table flag.
- 100% = a parametrised test per civ × per bullet type asserting the bullet's
  keyword (e.g. "naval", "mobile", "walls", "elite") is present in the
  matching leader XS or expectations row.

### Probe coverage matrix
- `tools/aoe3_automation/probe_coverage_matrix.py` exists. **Zero test files
  reference it** (`grep -r probe_coverage_matrix tests/` empty).
- Replay-side parsing is well-tested (41 functions in
  `test_replay_probes.py`), but the in-engine driver that *produces* the
  matrix is untested.
- 100% = a unit test that feeds a synthetic probe stream into
  `probe_coverage_matrix.aggregate(...)` and asserts the per-tag counts. End-
  to-end (engine round-trip) coverage stays manual.

### String tables (`data/strings/english/stringmods.xml`)
- Tested: well-formedness + locID validity (`test_validate_stringtables.py`,
  2 tests).
- Untested: that **every locID referenced by `civmods.xml`,
  `homecity*.xml`, `protomods.xml`, `techtreemods.xml` and the leader XS
  files actually resolves**. `validate_civ_crossrefs.py` covers civmods only.
- 100% = extend cross-ref validator to scan all XML+XS for `$$N$$` tokens
  and assert presence in `stringmods.xml`; one test per source file type.

### Replay validator (`tools/playtest/replay_probes.py`)
- **Best-covered module in the repo** — 41 unit tests covering parser,
  doctrine rules, terrain bias, idle vil, walls, heroes, and HTML
  cross-checks.
- Gap: only Aztec and British have explicit HTML-cross-check tests; other 21
  base civs + 26 revolution civs have no per-civ replay-promise assertion.

## 3. Gaps — itemised

1. **No home-city visual/pathdata namespace test** — `tools/validation/`
   has no `validate_homecity_visuals.py`; `validate_civ_homecities.py:1-30`
   only walks `<HomeCityFilename>`. The 25-file regression that just landed
   has no guard. **Highest priority.**
2. **No `playercolors.xml` validator** — `tools/validation/` has no
   `validate_playercolors.py`; tests do not reference `playercolors.xml`.
3. **No avatar-PNG ↔ civ-leader binding test** — 4 new
   `cpai_avatar_<civ>_<leader>.png` files (Elizabeth, Gall, Napoleon, Ivan)
   are uncovered.
4. **No leader-behaviour parametrised test** — 24 of 26 leaders untested
   beyond `validate_xs_scripts.py` shape checks. Citations:
   `tests/playtest/test_replay_probes.py:548,575` (only Aztec, British).
5. **No tests for `validate_html_vs_mod.py`, `validate_protomods.py`,
   `validate_personality_overrides.py`, `validate_techtree.py`,
   `validate_xml_well_formed.py`** — five validator modules ship without unit
   tests. Verify with `ls tools/validation/validate_*.py | wc -l` (= 16) vs
   `ls tests/validation/test_validate_*.py | wc -l` (= 11).
6. **No tests for `tools/playtest/preflight.py`, `spot_check.py`,
   `layout_verify.py`, `html_reference.py`** — four playtest helpers
   uncovered.
7. **No tests for `tools/aoe3_automation/probe_coverage_matrix.py`**, nor
   for `personality_matrix.py`, `civ_matrix_*.py`, `np_wel_1v1_observer.py`,
   `observer_2.py`, `afk_driver*.py`, `generate_report.py`,
   `wall_verify.py`, `fast_test.py` — all untracked drivers added in this
   branch (see `git status`).
8. **No locID coverage test across all XML/XS sources** — only `civmods.xml`
   refs are cross-checked.
9. **Probe events** — `STYLE_APPLIED`, `PERSONALITY_APPLIED`,
   `ELITE_RETREAT_CORE`, `COMMANDER_RANSOM`, `BASE_INFLUENCE` parse
   tests exist (`test_replay_probes.py:474-511`) but no semantic assertion
   that each leader emits the expected style/personality probe.
10. **Pytest is not installed in dev shell** (`/usr/bin/python: No module
    named pytest`). CI likely runs it; locally the suite cannot be executed
    by `pytest` directly. Consider adding a `requirements-dev.txt` or
    documenting the venv in `TESTING.md`.

## 4. Recommendation — shortest path to 100%

Order by impact-per-line-of-test-code. The first three are cheap and would
catch the vast majority of recent and likely-future regressions.

### Tier 1 — write today

1. **`tests/validation/test_validate_homecity_visuals.py`** (would have
   caught the 25-file pathdata bug). Add `validate_homecity_visuals.py` that:
   - parses every `data/anwhomecity*.xml`,
   - extracts the directory prefix of `<visual>`, `<watervisual>`,
     `<backgroundvisual>`, `<pathdata>`, `<camera>`,
     `<widescreencamera>`,
   - asserts all six prefixes are equal (or all in a small allow-list per
     civ family).
   Test parametrises across the 25 files plus three synthetic fixtures
   (matching, mismatched-pathdata, mismatched-visual). **~80 lines, blocks
   the exact bug class just fixed.**

2. **`tests/validation/test_validate_playercolors.py`** + the missing
   validator. Asserts every `<civ>` in `civmods.xml` has a `<player>` entry
   in `playercolors.xml` and that every `cpai_avatar_<tag>_<leader>.png`
   asset under `resources/images/icons/singleplayer/` is referenced from a
   civ/leader binding. ~60 lines.

3. **Parametrised `tests/playtest/test_leader_replay.py`** that walks
   `expectations.LEADERS` (already 48 rows) and, given a fixture replay per
   leader, asserts the replay contains `LEADER_INIT`, `PERSONALITY_APPLIED`,
   and `STYLE_APPLIED` probes with the expected name. The fixture replays
   can be generated once and committed under `tests/fixtures/replays/`.
   This converts the existing two ad-hoc Aztec/British tests into a
   coverage-by-construction sweep. ~120 lines.

### Tier 2 — next sprint

4. **Cross-ref expansion**: extend `validate_civ_crossrefs.py` (or add
   `validate_locids.py`) to scan every `$$N$$` token across `*.xml` and
   `game/ai/**/*.xs`, assert it resolves in `stringmods.xml`. Single test,
   high ROI. ~50 lines.

5. **Validator-self-tests for the five orphans**: `validate_html_vs_mod`,
   `validate_protomods`, `validate_personality_overrides`,
   `validate_techtree`, `validate_xml_well_formed`. One test file per
   validator, modelled on the existing `test_validate_*.py` style (build
   tmp tree, run validator, assert exit code + messages). ~40 lines each.

### Tier 3 — when convenient

6. Tests for `tools/playtest/{preflight,spot_check,layout_verify,html_reference}.py`.
7. A unit test for `probe_coverage_matrix.aggregate` covering the per-tag
   counter logic (no engine round-trip).
8. Move untracked `tools/aoe3_automation/*.py` drivers into a documented
   "manual harness" subdir or add smoke tests for the importable entrypoints.

### Specific guard for the bug just fixed

```python
# tests/validation/test_validate_homecity_visuals.py
@pytest.mark.parametrize("xml_path", sorted(DATA.glob("anwhomecity*.xml")))
def test_visual_and_pathdata_share_prefix(xml_path):
    tree = ET.parse(xml_path)
    prefixes = {
        tag: tree.findtext(tag, "").split("\\", 1)[0]
        for tag in ("visual", "watervisual", "backgroundvisual",
                    "pathdata", "camera", "widescreencamera")
    }
    nonempty = {t: p for t, p in prefixes.items() if p}
    assert len(set(nonempty.values())) == 1, (
        f"{xml_path.name}: mismatched scene namespaces {nonempty}"
    )
```

That single parametrised test, ~15 lines, would have failed loudly on every
one of the 25 broken files before they were fixed.

## Coverage summary table

| Subsystem | State | Risk |
|---|---|---|
| Replay validator (`replay_probes.py`) | Strong (41 tests) | Low |
| Expectations table | Strong (9 tests) | Low |
| Per-validator unit tests (11/16) | Good | Medium — 5 validators uncovered |
| Civ definitions (civmods + crossrefs) | Good | Medium — playercolors uncovered |
| **Home-city visuals/pathdata** | **None** | **High — regression unguarded** |
| Per-leader behavioural assertions | 2/26 | High |
| HTML-vs-mod doctrine consistency | Partial (Aztec, British) | Medium |
| String table cross-refs (full coverage) | Partial (civmods only) | Medium |
| `tools/aoe3_automation/` drivers | None | Low (manual rigs) |
| Probe coverage matrix aggregator | None | Medium |

End of audit.
