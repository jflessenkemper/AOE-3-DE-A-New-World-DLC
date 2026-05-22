# Legendary Leaders AI Test Scenario

The `.age3Yscn` file in this folder is a binary AoE3DE scenario file, so it is not practical to author or review safely with normal repo tools. The reliable workflow is to edit it in the in-game Scenario Editor and keep this file as the source of truth for what the test map should contain.

## Goal

Build one small repeatable scenario that verifies the current mod behavior:

- AI non-elite units rout (fall back to their return point) at low health
- elite AI units do not auto-rout
- nearby elite support prevents ordinary AI units from routing
- AI assault shape keeps regular units in front, elites behind, explorer behind both
- if the AI explorer dies, the elite line disengages

## Recommended Map Setup

- Map size: small
- Terrain: flat, open, minimal obstacles
- Trade route: none
- Native settlements: none
- Treasures: none
- Starting resources: high enough to ignore economy during testing
- Player 1: human
- Player 2: AI

This scenario path remains the right tool when you need exact player-triggered interactions, but it can still be run mostly as an observer map: let the pre-placed lanes fight on their own, and only intervene when you specifically need to test rout, support removal, or forced explorer death.

## Core Layout

Use two lanes across the same scenario so one load can test several behaviors.

### Lane A: AI Rout Test

- Put Player 1 Town Center on the west side.
- Put Player 2 Town Center on the east side.
- Place 8 ordinary Player 2 (AI) land units in the center at roughly 30% health.
- Place 8 ordinary Player 1 land units opposite them at full health.

Expected result:

- when combat starts, damaged ordinary AI units rout at about 25% health
- routed AI units fall back toward the AI return point and disengage
- elite AI units in the same lane do not auto-rout
- when elite support is added beside damaged AI ordinaries, those ordinaries no longer rout

### Lane B: AI Formation and Explorer Test

- Place a larger Player 2 force south of center:
- 12 ordinary land units
- 4 elite units
- 1 explorer
- Place a smaller but durable Player 1 defending force nearby.
- Give the AI enough space to form up before first contact.

Expected result:

- regular AI units should advance as the first line
- elite AI units should trail as the second line
- the AI explorer should remain behind the fighting line
- if you kill the AI explorer during the attack, the elite line should disengage

## Recommended Unit Choice

Pick one civ pair you can identify quickly in the editor and use one clearly ordinary unit plus one clearly elite unit from the README tables.

Safe pattern:

- ordinary unit: a common infantry or cavalry unit that is not listed as elite for that nation
- elite unit: a unit explicitly listed in the README elite column for that nation

If you want the cleanest first pass, use only one nation pair for the whole scenario and duplicate the same test geometry in both lanes.

## Editor Steps

1. Open `Scenario/ANEWWORLD.age3Yscn` in the AoE3DE Scenario Editor.
2. Set Player 1 to human and Player 2 to AI.
3. Place one Town Center for each player first.
4. Place explorers before placing combat groups so their behavior is easy to observe.
5. Build the two lanes above with wide spacing so tests do not interfere with each other.
6. Lower the health of the rout-test units so they reach the threshold almost immediately.
7. Save the scenario and run it with the mod enabled.

## Fast Trigger Ideas

If you want to make repeated testing faster in the editor, add these optional triggers:

- Intro message trigger that labels each lane so you can mostly spectate.
- One-button unit heal trigger to reset a lane without rebuilding it.
- One-button respawn trigger for each lane.
- AI explorer kill trigger for the elite-retreat test.
- Observer-only trigger pads near the Player 1 Town Center so you can fire each lane reset without walking across the map.

Recommended observer-first pad set:

- `Lane A Reset`
- `Lane B Reset`
- `Kill AI Explorer`

That keeps the scenario useful for the exact interactions the RMS cannot assert precisely, while still avoiding normal macro play.

## Pass Checklist

- Lane A: damaged ordinary AI units rout and path back to their return point.
- Lane A: elite AI units in the same lane do not auto-rout.
- Lane A: nearby elite support blocks ordinary AI rout.
- Lane B: AI regulars lead, elites follow, explorer stays behind.
- Lane B: killing the AI explorer causes the elite line to back off.

## Limits

- This repo can store the scenario file, but it cannot reliably perform structured edits to `.age3Yscn` content from text tools.
- If you want automation beyond this, the viable next step is to build the scenario in the in-game editor and then keep a written spec plus screenshots in the repo.

## Map Picker Notes

- `ANEWWORLD.age3Yscn` is the Custom Maps or Scenario version and should appear in the in-game `Custom Maps` list. The canonical staged copy lives at
  `~/.local/share/Steam/userdata/209941315/933110/remote/scenario@ANEWWORLD.age3Yscn`
  (Steam Cloud); the repo holds an identical-md5 copy at `Scenario/ANEWWORLD.age3Yscn`.
- The legacy `Legendary Leaders Test.{age3Yscn,xs}` randmap was retired
  on 2026-05-11. Use the ANEWWORLD scenario or any stock random map.
- If the scenario entry itself still shows as `Unknown`, the remaining metadata is inside the binary `.age3Yscn` payload and must be refreshed by opening and re-saving that scenario in the AoE3DE Scenario Editor.
