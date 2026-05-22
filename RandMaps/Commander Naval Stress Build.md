# Commander Naval Stress Build

This is the concrete RMS-side build spec for the combined commander and naval stress surface.

The intent is not to create a second abstract plan. The intent is to
define a new dedicated naval-stress random map so land-command logic and
naval behavior are stressed in the same match. (Originally this spec
proposed evolving the `Legendary Leaders Test` random map, but that map
was retired on 2026-05-11 when ANEWWORLD became the canonical AI-testing
scenario. The geometry targets below are still valid for a fresh RMS.)

## Recommended Implementation Path

Author a new RMS from scratch using the geometry targets below — they
were validated against the legacy 2v2 west-vs-east layout and remain a
good starting point.

Reason:

- the west-vs-east 2v2 layout already exists
- the map already has north and south water lanes
- the map already has readable land corridors
- extending one maintained test map is better than creating multiple half-maintained labs

## Exact Geometry Targets

These are the target layout anchors for the RMS.

### Team Starts

- west south start: `(0.18, 0.33)`
- west north start: `(0.18, 0.67)`
- east south start: `(0.82, 0.33)`
- east north start: `(0.82, 0.67)`

These already match the current map structure and should stay fixed so slot order remains irrelevant in 2v2.

### Main Land Corridor

- center line anchor: `(0.50, 0.50)`
- desired corridor width: wide enough for clear regular-first and elite-second attack shape
- desired travel time: short enough that commander death changes the fight quickly

Use the current center lane as the main commander test corridor.

### North Water Economy Lane

- lane anchor: `(0.50, 0.86)`
- purpose: safe dock and fishing lane

Requirements:

- each side gets one clear near-shore dock pocket
- first fish cluster should be easy and obvious
- at least one whale pocket should exist but not be fully risk-free

### South Water Combat Lane

- lane anchor: `(0.50, 0.14)`
- purpose: contested warship and transport lane

Requirements:

- more exposed docking than the north lane
- clear ship-to-ship travel route
- at least one coastal landing path that can influence the south land flank

### Land Pressure Lanes

- north land corridor anchor: `(0.50, 0.72)`
- center land corridor anchor: `(0.50, 0.50)`
- south land corridor anchor: `(0.50, 0.28)`

Recommended roles:

- north lane: flank and reinforcement movement
- center lane: main commander stress lane
- south lane: land-to-naval interaction lane tied to the south water combat strip

## Resource Rules

### Starting Economy

Each player should have:

- one guaranteed Town Center start
- one near mine
- one second mine
- one close herd
- one second herd
- at least one livestock source
- enough wood access to support early dock and military branching

### Midfield Economy

Place extra resources to keep the test from ending before both theaters matter.

Use:

- neutral mines along north, center, and south land lanes
- extra herd pockets in each lane
- visible shoreline fish in both water lanes
- a stronger whale or deep-water pocket that rewards actual naval commitment

Do not use treasures or natives unless a specific regression requires them.

## Target Test Cases

This map should expose all of these in one run:

- commanderless major attacks stop instead of continuing blindly
- elite retreat and ransom still trigger during crowded land fights
- dock placement remains sensible while land pressure is active
- fishing is not abandoned just because land combat started
- naval patrol and engagement still happen while commander logic is busy
- transport or shoreline pressure can interfere with land timing in readable ways
- AI rout tracking does not stall when many units are in danger at once

## Recommended Matchups

Use these first because they stress different systems without being too noisy.

### Matchup Set A

- west: Dutch + British
- east: Napoleon + Egypt

Why:

- Dutch and British give you readable defensive or positional play plus water capability
- Napoleon and Egypt pressure artillery, escort behavior, and commander doctrine strongly

### Matchup Set B

- west: Russia + Portuguese
- east: Egypt + Ottomans

Why:

- Russia stresses mass and broad-front land pressure
- Portuguese test town center and dock economy overlap
- Egypt and Ottomans keep artillery and naval-adjacent pressure relevant

### Matchup Set C

- west: player + allied AI of choice
- east: two opposing AIs

Why:

- easiest setup when you need to observe one side carefully and still influence the run manually

## RMS Build Priorities

When implementing the new RMS, do the work in this order:

1. Keep the fixed west-east 2v2 placement unchanged.
2. Strengthen the difference between the north and south water lanes.
3. Make the south shoreline matter more to nearby land fights.
4. Ensure the center land corridor remains the clearest formation-reading space.
5. Increase resource clarity before increasing terrain complexity.

## Success Criteria

The build is good enough when one 2v2 run can reliably show all of these without forcing weird setups:

- one meaningful center-lane commander fight
- one visible dock and fishing phase
- one meaningful south-lane naval engagement or transport threat
- one moment where naval and land decisions clearly compete for attention

If a run only tests land or only tests water, the map is still too soft.