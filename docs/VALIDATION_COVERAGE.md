# A New World — Validation Coverage Matrix

This document maps every claim the HTML reference (`a_new_world.html`) makes about
how each of the 46 ANW civilizations should play, to the runtime probe that
proves the AI is actually doing it.

The validation pipeline is:

```
┌──────────────────┐    ┌────────────────────┐    ┌─────────────────────────┐
│ a_new_world.html │───▶│ playstyle_spec.json│───▶│ enriched_reference.json │
│   (source of     │    │   (per-civ claims) │    │  (validator-ready spec) │
│    truth)        │    │                    │    │                         │
└──────────────────┘    └────────────────────┘    └─────────────────────────┘
       │                                                       │
       │ data-search blob                            ┌──────────▼──────────┐
       │ (units, cards, bonuses)                     │ validate_civ_       │
       │                                             │ behavior.py         │
       │                                             │  (1058 assertions)  │
       │                                             └──────────▲──────────┘
       ▼                                                        │
┌──────────────────┐    ┌────────────────────┐    ┌─────────────┴───────────┐
│ data/decks_anw.  │───▶│ enriched_reference │    │ parse_match_log.py      │
│      json        │    │ .civs[X].          │    │  (Age3Log.txt → probes) │
│  (per-civ deck)  │    │   expected_deck    │    └─────────────▲───────────┘
└──────────────────┘    └────────────────────┘                  │
                                                                │
                            ┌───────────────────────────────────┴───┐
                            │ Real game match (skirmish 1v7)        │
                            │ AI emits [LLP v=2 ...] probes via     │
                            │ aiUtilities.xs:llProbe()              │
                            └───────────────────────────────────────┘
```

## Coverage matrix per civ (23 distinct checks)

| Check ID | Source | Probe(s) consumed | What it validates |
|----------|--------|-------------------|-------------------|
| `civ.identity` | log presence | any probe | civ name surfaces in log |
| `civ.doctrine_label` | playstyle_spec | (reference-only) | name match for diagnostics |
| `milestone.first_military_building` | universal | `milestone.first_barracks/stable` | every civ trains land army |
| `milestone.first_dock` | claims.first_military_building / expects_naval | `milestone.first_dock` | naval-doctrine civs build a dock |
| `milestone.first_wall_segment` | claims.first_wall_before_ms | `milestone.first_wall_segment` | walling civs actually wall |
| `milestone.first_forward_base` | claims.expects_forward | `milestone.first_forward_base` | forward-line doctrine expands |
| `milestone.first_trading_post` | doctrine label contains 'trade'/'mercantile' | `milestone.first_trading_post` | trade civs claim trade routes |
| `milestone.first_fort` | universal late-game | `milestone.first_fort` | civ reaches fort timing |
| `milestone.first_artillery` | universal late-game | `milestone.first_artillery` | civ trains artillery |
| `doctrine.wall_strategy` | claims.wall_strategy (0-5) | `posture.snapshot.ws` | wall enum matches reference |
| `doctrine.build_style` | playstyle_spec.doctrine_label → 1-14 | `posture.snapshot.bs` | build-style enum matches doctrine |
| `doctrine.military_distance` | claims.military_distance_band | `posture.snapshot.mdist` | mdist multiplier in [lo, hi] |
| `comp.unit_composition` | spec.expected_unit_composition | `comp.snapshot.{inf,cav,arty}` | unit class ratios within tolerance |
| `age.progression` | universal | `posture.snapshot.age` | reaches age 2+ |
| `meta.boot.fired` | engine | `meta.boot` | AI loader bootstrap fired |
| `meta.boot.wall_strategy` | claims.wall_strategy | `meta.boot.wallStrategy` | leader-doctrine binding correct |
| `meta.setup` | engine | `meta.setup` | game mode/difficulty/players logged |
| `meta.gameover` | engine | `meta.gameover` | match end probe (final age + score) |
| `compliance.profile.build_style` | playstyle_spec | `compliance.profile.style` | doctrine knob runtime check |
| `compliance.profile.wall_strat` | claims.wall_strategy | `compliance.profile.wallStrat` | doctrine knob runtime check |
| `chat.quote` | aiLeaderQuotes.xs | `chat.quote` | leader quote (opening) fires |
| `event.age_up` | aiCore.xs | `event.age_up` | per-age transition events |
| `card_deck` | data/decks_anw.json | `compliance.ship.card` | shipments are from expected deck |

## Verdict interpretation

| Verdict | Meaning |
|---------|---------|
| `PASS` | All required assertions hold; no FAIL or WARN |
| `WARN` | One or more assertions had soft issues (e.g., empty observation window, no military units in too-short match) |
| `FAIL` | At least one hard assertion failed (wrong wall_strategy, mdist out of band, missing required milestone) |
| `SKIP` | Assertion gracefully degraded (missing reference data, probe rule disabled) — NOT a failure |
| `NO_DATA` | Civ found in log but no recognised probe data |

## Running the full suite

```bash
# Synthetic-only verification (no game required, ~5 sec):
python3 tools/validation/run_full_validation.py --synthetic

# Real-game full 46-civ run (with test-mode auto-resign, ~30-60 min):
python3 tools/validation/run_full_validation.py --threshold-ms 60000

# Subset for debugging (specific civs):
python3 tools/validation/run_full_validation.py --synthetic --civs ANWBritish ANWAztecs
```

## Per-civ rich data sources

| Data file | Per-civ key shape | What it carries |
|-----------|-------------------|-----------------|
| `a_new_world.html` (data-search blobs) | `data-name="X Leader Y"` | units, cards, bonuses, prose, walling pattern |
| `playstyle_spec.json` | `civs[X Leader Y].claims.*` | wall_strategy, military_distance_band, first_military_building, expects_naval, expects_forward, first_dock_before_ms, first_wall_before_ms |
| `data/decks_anw.json` | `[ANWX][age]` → list[card_id] | full per-age card deck |
| `data/anw_civ_blurbs.json` | `[ANWX]` → string | display blurb |
| `reference_matrix.json` | `civs[ANWX]` | merged metadata (anw_token, display_name, data_name, playstyle_spec) |
| `enriched_reference.json` | `civs[ANWX]` | reference_matrix + claims + decks + blurbs (validator's input) |

## Failure modes the validator detects

These are real bugs the validator will catch and flag with `FAIL`:

1. **Wrong leader-doctrine binding** — `meta.boot.wallStrategy != claims.wall_strategy`. Means a leader was wired to the wrong doctrine in `leaderCommon.xs` or per-leader override.

2. **Doctrine knob drift** — `compliance.profile.style != expected build_style`. Means runtime override changed the value vs what the leader script set.

3. **Missing required milestone** — naval civ never built a dock; trade civ never claimed a trade route; forward-line civ never expanded.

4. **Wrong build order** — military distance multiplier outside the per-civ band (means the AI placed barracks somewhere unexpected).

5. **Card-deck divergence** — AI shipped a card not in `data/decks_anw.json[civ]`. Means either decks are out of sync with what the home city actually contains, or the home city has a card the deck spec doesn't list.

6. **AI never aged up** — `posture.snapshot.age` stuck at 1. Indicates AI didn't reach the strategic-decision phase.

7. **Loader silent failure** — `meta.boot` never fired. Means an XS error or missing extern stopped the loader before bootstrap.

## Source-of-truth precedence

When sources disagree, the order is:

1. `a_new_world.html` (data-search and prose) — **highest**, the document users read
2. `playstyle_spec.json` (claims) — extracted from HTML, machine-readable
3. `data/decks_anw.json` — the deck the home city actually uses at runtime
4. `data/civmods.xml` — the engine-readable civ definition
5. AI XS scripts (`aiHeader.xs`, leader files) — the runtime that actually runs

A FAIL in the validator means one of these layers diverges from what the HTML claims.
