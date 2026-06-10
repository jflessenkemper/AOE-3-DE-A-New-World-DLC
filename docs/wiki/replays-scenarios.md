# Replays and scenarios (`.age3Yrec` / `.age3Yscn`)

> Both formats are `l33t`-wrapped zlib-compressed Ensemble structured
> streams. After unwrap, they contain different inner schemas — replays
> hold a frame-by-frame command log; scenarios hold map data and
> triggers.

## Outer wrapper

Both formats share the [l33t wrapper](file-formats/l33t.md):

```
4 bytes  "l33t" or "L33t" magic
4 bytes  uncompressed size (uint32 LE)
N bytes  zlib-deflate stream
```

## `.age3Yrec` — replay records

Inner stream sections (community-observed):

| Section | Notes |
|---|---|
| Header | Magic, file version, build number, replay duration |
| Lobby setup | Player slots: name, color, civ, team, AI personality (if any), is-ESO-account |
| Mod manifest | Mod name(s), version(s), checksum (DE additions) |
| Map metadata | Map name, RM seed, victory conditions |
| Command frames | Per-tick / per-action structured records: `BuildBuilding`, `TrainUnit`, `ResearchTech`, `MoveUnit`, `AttackTarget`, `Chat`, `Taunt`, etc. |
| Footer | End-of-game stats |

### Verified examples

| File | Compressed | Decompressed |
|---|---|---|
| `Record Game 2026-04-17 14-40-35.age3Yrec` | 9.5 MB | 67.4 MB |

The [`@canyougiant/aoe3de-replay-parser`](https://www.npmjs.com/package/@canyougiant/aoe3de-replay-parser)
npm package source enumerates many of the command opcodes.

## `.age3Yscn` — scenarios

Inner stream sections (community-observed):

| Section | Notes |
|---|---|
| Header | Format version, scenario name (`_locID`), description (`_locID`), author, date. Starts with `BG;` magic |
| World metadata | Map size, terrain type set, lighting, water type |
| Heightmap | Grid of terrain heights |
| Terrain layer(s) | Per-tile texture + decal indices |
| Unit placements | Per-unit: proto name, owner, position, rotation, initial state |
| Player slots | Per-slot: civ, team, AI personality, starting resources, victory conditions |
| Triggers | Trigger graph: conditions + effects (XS-like) |
| Scripts | Embedded XS / trigger-script payloads |

### Verified example

| File | Compressed | Decompressed | Inner first bytes |
|---|---|---|---|
| `age3ycc5a.age3Yscn` (Wonders campaign) | 92 KB | 1.8 MB | `BG;` magic + version + UTF-16 metadata |

The Scenario Editor is the authoritative authoring path; raw binary
edits are not a community pattern.

## File path conventions

- Replays: `My Games/Age of Empires 3 DE/<steamid>/Savegame/...` or
  Documents tree (varies by OS / Proton mapping).
- Scenarios: `My Games/Age of Empires 3 DE/<steamid>/Scenario/...` or
  in the mod tree at `<mod>/Scenario/`.

## Cross-references

- [l33t wrapper](file-formats/l33t.md) — outer container.
- [XS scripts](ai-layer/xs-scripts.md) — scenario triggers can include
  XS payloads.
- [stringmods.xml](data-layer/stringmods.md) — scenario name /
  description loc-IDs.
- [Mod folder structure](mod-folder-structure.md) — `Scenario/`
  directory placement.

## Tools

| Path | Purpose |
|---|---|
| [`tools/cardextract/l33t_codec.py`](../../tools/cardextract/l33t_codec.py) | Pure-Python wrapper decompressor + compressor |
| [`tools/validation/scenario_emitter.py`](../../tools/validation/scenario_emitter.py) | This repo's scenario emitter (validation tier) |
| [`tools/validation/validate_scenario_binary.py`](../../tools/validation/validate_scenario_binary.py) | `.age3Yscn` binary checks |
| [`tools/validation/replay_determinism_validator.py`](../../tools/validation/replay_determinism_validator.py) | Replay determinism |
| [`@canyougiant/aoe3de-replay-parser`](https://www.npmjs.com/package/@canyougiant/aoe3de-replay-parser) | npm replay parser |
| [ESOCommunity Replay Manager v0.07](https://forums.ageofempires.com/t/v-0-07-replay-manager-tool-to-viewing-age-of-empires-iii-definitive-edition-records/197220) | Community replay viewer |
| [AoE3:DE Replay Launcher](https://eso-community.net/viewtopic.php?t=22050) | Cross-patch replay playback |

## Known issues

- **Cross-patch replay incompatibility**: replays recorded under one
  patch can fail to play back under a later patch. The Replay Launcher
  addresses this by swapping in old binaries.
- **Mod replay reproducibility**: a replay made with mods enabled
  requires the same mod set (and version) to play back
  deterministically.
- **Scenario-editor crash recovery**: scenarios that crash the editor
  can be unrecoverable; keep frequent backups.
- **Trigger-script portability**: a scenario authored under one mod
  may fail when loaded without the mod (missing protos, missing
  techs, missing strings).
- **No external scenario validator** known publicly.
- **No authoritative byte-level command opcode list** — only
  community parsers' source code expresses it.

## Open questions

- Authoritative byte-level layout of the inner Ensemble streams.
- Complete list of replay command opcodes and their argument layouts.
- Whether replays carry mod-asset hashes or only mod names/versions.
- Whether `.age3Yscn` is byte-identical to `.scn` from legacy AoE3
  (community-suspected: no).
- Whether replays can be programmatically used as a regression-test
  harness for mods.

## Sources

- [`@canyougiant/aoe3de-replay-parser`](https://www.npmjs.com/package/@canyougiant/aoe3de-replay-parser) — practical reference parser.
- [forums.ageofempires.com — Replay Manager](https://forums.ageofempires.com/t/v-0-07-replay-manager-tool-to-viewing-age-of-empires-iii-definitive-edition-records/197220).
- [eso-community.net — Replay Launcher](https://eso-community.net/viewtopic.php?t=22050).
- [AOE3 Modding Council AI guide](https://aoe3mc.github.io/ai-guide/getting-started/) — scenario editor flow as fast-iteration path.
- This repo: empirical decompression of 4 sample files (2026-05-09 session).
