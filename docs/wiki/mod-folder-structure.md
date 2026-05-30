# Mod folder structure

> Layout of an AoE3 DE mod: `modinfo.json` manifest, plus `data/`,
> `art/`, `sound/`, `Scenario/`, `game/ai/`, `resources/` modules that
> mirror the base data tree.

## Install location

Local mods live under:

```
<install>/Games/Age of Empires 3 DE/<steamid>/mods/local/<modname>/
```

Steam Workshop mods install to a sibling `subscribed/` directory.

## Canonical layout

```
mods/local/<modname>/
+-- modinfo.json          # DE manifest
+-- mod.xml               # legacy manifest (optional)
+-- data/                 # additive XML overlays
|   +-- civmods.xml
|   +-- stringmods.xml
|   +-- techtreemods.xml
|   +-- protomods.xml
|   +-- homecity*.xml     # one per civ
|   `-- ...
+-- art/                  # DDT, animation, model assets
+-- sound/                # WAV / OGG / sound XML
+-- Scenario/             # .age3Yscn scenarios
+-- game/
|   `-- ai/
|       +-- aiMain.xs
|       +-- aiHeader.xs
|       +-- aiLoaderStandard.xs
|       +-- *.personality
|       `-- *.xs
`-- resources/
    `-- images/
        `-- icons/
            +-- flags/    # WPF PNG flags
            `-- singleplayer/  # cpai_avatar_*.png
```

## `modinfo.json`

Ground-truth example (`modinfo.json` at repo root):

```json
{
  "name": "AOE 3 DE - A New World",
  "description": "...",
  "author": "A New World Team",
  "version": "1.0.0",
  "url": "https://github.com/...",
  "gameVersion": "100.15.x",
  "bigFileVersion": 9,
  "status": "release",
  "modules": [
    {"type": "game",      "sourcePath": "game"},
    {"type": "data",      "sourcePath": "data"},
    {"type": "art",       "sourcePath": "art"},
    {"type": "resources", "sourcePath": "resources"},
    {"type": "sound",     "sourcePath": "sound"}
  ]
}
```

| Field | Notes |
|---|---|
| `name` / `description` / `author` / `version` / `date` / `url` | Display metadata |
| `gameVersion` | Compatibility hint; not enforced |
| `bigFileVersion` | Encodes BAR-format epoch the mod was built against. Community-observed values 6-9 across DE patches. **Distinct from BAR header version field** (which is 6 for DE — see [BAR archives](file-formats/bar.md)) |
| `status` | `release` / `wip` / etc. — no published enum |
| `modules` | List of `{type, sourcePath}` mapping module roots |

`modules[].type` known values: `game`, `data`, `art`, `resources`,
`sound`. Other types may exist (`scenario`?). No authoritative list
published.

## `mod.xml` (legacy)

```xml
<mod>
  <name>...</name>
  <version>...</version>
  <description>...</description>
  <author>...</author>
  <website>...</website>
  <type>Mod</type>
  <folder>.</folder>
</mod>
```

Whether DE still consults `mod.xml` when `modinfo.json` is present is
undocumented; ANW ships both.

## Path conventions

- **Data files** under `data/` are loose XML; the engine merges them
  against the base XMB-decoded tree at load.
- **Art** under `art/` shadows base `.bar` paths by filename. A flag at
  `art/ui/flags/foo.ddt` overrides the base `ui/flags/foo.ddt` if the
  base file existed.
- **WPF PNG icons** live under `resources/images/icons/...` and are
  referenced from civmods/personality fields directly (not via the
  filename-override system).
- **AI scripts and personalities** under `game/ai/` are read by the
  engine's AI loader (see [XS scripts](ai-layer/xs-scripts.md) and
  [personality files](data-layer/personalities.md)).

## Cross-references

- [Additive data mods](additive-data-mods.md) — what `data/` does.
- [BAR archives](file-formats/bar.md) — optional packaging.
- [XS scripts](ai-layer/xs-scripts.md) — `game/ai/` placement.
- [Personality files](data-layer/personalities.md) — `.personality` files.
- [Flag rendering](ui-layer/flag-rendering.md) and
  [portrait rendering](ui-layer/portrait-rendering.md) —
  `resources/images/icons/...` paths.

## Known issues

- **Path case sensitivity on Linux/Proton.** Windows is case-insensitive
  but case-sensitive packaging tools (zip, git on case-sensitive FS) can
  trip mismatches.
- **`modinfo.json` schema is undocumented**, so unknown fields may
  silently no-op.
- **Slash direction in WPF paths.** Backslash vs forward slash matters
  in some fields — see [missing flags](modding-pitfalls/missing-flags.md).

## Open questions

- Authoritative schema for `modinfo.json`.
- Whether `bigFileVersion` is enforced by the loader or informational.
- Load order rule when multiple mods are enabled.
- Whether `mod.xml` is still honoured on DE.

## Sources

- [Steam Community modding guide](https://steamcommunity.com/app/933110/discussions/0/3037103480432201495/)
  (most-cited; full content gated behind Steam errors in our session).
- [Microsoft Additive Data Mods](https://support.ageofempires.com/hc/en-us/articles/360062106732-Additive-Data-Mods).
- This repo: `modinfo.json` and `mod.xml` are ground-truth examples.
