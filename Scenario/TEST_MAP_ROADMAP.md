# Test Map Roadmap

This roadmap turns the Age of Pirates testing pattern into a concrete A New World plan.

## What Age of Pirates Appears To Do

Age of Pirates does not appear to use a modern end-to-end gameplay automation harness. Its repo leans on two things instead:

1. Strong structural validators for XML, proto, stringtables, and techtree.
2. In-game testing on special maps and map variants.

Relevant examples in that repo:

- `game/test/zptest.xs`: explicit test map script.
- `randmaps/performance_test.xs`: explicit stress or performance-oriented map.
- `randmaps/zpvenicecit_test.xs`: explicit test variant of a content map.
- many random maps contain commented `ZP Test Plr...` trigger blocks for fast tech grants and setup shortcuts.

That is a useful pattern for A New World because this repo already has stronger validators and runtime-log tooling than Age of Pirates. What it lacks is a wider set of targeted test surfaces.

## Recommended Map Set

### 1. Mechanics Lab Scenario

Status: already partially present.

Base this on `Scenario/ANEWWORLD.age3Yscn` and keep it focused on deterministic rule verification:

- AI non-elite rout threshold
- elite-support block
- AI rout fallback toward the return point
- elite retreat after explorer death

Required trigger actions:

- lane reset
- lane respawn
- AI explorer kill
- owner explorer teleport
- optional instant low-health setup

Why: this is the fastest path for objective runtime suites.

### 2. Commander Naval Stress Map

Create one dedicated map that pressures commander logic and naval behavior at the same time.

Detailed spec:

- `Scenario/COMMANDER_NAVAL_STRESS_MAP.md`
- `RandMaps/Commander Naval Stress Build.md`

Design intent:

- short readable center land corridor for commander tests
- one safer water economy lane
- one more contested naval combat or transport lane
- high starting resources and short travel distance so failures surface quickly

What to watch:

- commanderless-attack cancellation under multi-front pressure
- elite retreat and ransom behavior while naval tasks are active
- dock placement and fishing commitment during active land conflict
- fleet response, transport pressure, and plan thrash under combined load

Why: this is better than separate commander-only and naval-only maps because it exercises theater competition, which is closer to real failure conditions.

Implementation note:

- preferred first implementation is to evolve the ANEWWORLD scenario
  toward this combined profile rather than starting a separate RMS
  immediately. (The legacy `RandMaps/Legendary Leaders Test.xs` was
  retired 2026-05-11.)

### 3. Personality Contrast Arena

Create a map whose only job is to expose differences in doctrine between two or four civs.

Design:

- open symmetric lanes
- controlled resource clusters
- minimal terrain randomness
- optional pre-placed forward positions or forts

Best uses:

- Dutch vs Napoleon
- Russia vs Egypt
- any artillery-heavy vs positional pair

What to observe:

- who starts fights
- whether artillery is core or incidental
- whether explorer screening actually differs by personality
- whether the armies feel tactically distinct instead of statistically different only

Why: this is the subjective complement to the mechanics lab. It should stay observer-oriented, not over-automated.

### 4. Test Variants Of Real Content Maps

Follow the `*_test.xs` pattern from Age of Pirates.

Instead of only building generic labs, keep lightweight test variants of important real maps:

- one test variant of a land-heavy content map
- one test variant of a naval content map
- one test variant of a dense urban or chokepoint map if you add those later

What changes in the test variants:

- simplified resources
- clearer spawn geometry
- optional debug triggers
- optional pre-aged starts

Why: real map behavior often diverges from clean-lab behavior.

## Recommended Build Order

1. Finish the current Mechanics Lab Scenario.
2. Add the Commander Naval Stress Map.
3. Add one Personality Contrast Arena for the most important matchup set.
4. Only then start making `*_test` variants of content maps.

## Trigger Philosophy

Borrow the spirit, not the exact implementation, from Age of Pirates.

For A New World, the better model is:

- Scenario Editor GUI triggers for the binary scenario
- runtime log markers for machine-checkable assertions
- optional RMS-side trigger prototypes for maps that are easier to maintain in text

Avoid burying essential test behavior only in commented trigger snippets inside many unrelated maps. Keep the test intent explicit in a small number of maintained test surfaces.