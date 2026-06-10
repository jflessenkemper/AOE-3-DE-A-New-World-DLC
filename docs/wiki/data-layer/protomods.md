# protomods.xml — additive prototype-unit table

> Plain XML at `data/protomods.xml`. Merges into base `proto.xml.xmb`
> (and `protoy.xml.xmb`). Modifies, adds, removes, or replaces specific
> `<unit>` records that define every unit, building, projectile, and
> special object in the game.

## Schema

The root element is `<protomods>` (not `<proto>`), and additive entries
merge into the base proto table **by `name`** — protomods units carry no
`id` attribute (verified: 0 `id=` attributes across all entries in
`data/protomods.xml`). The general base-proto `<unit>` field surface, for
reference, is:

```xml
<protomods>
  <unit name="UnitName">          <!-- merge key is name; no id attribute -->
    <displaynameid>...</displaynameid>
    <rolloverid>...</rolloverid>
    <initialhitpoints>...</initialhitpoints>
    <maxhitpoints>...</maxhitpoints>
    <maxvelocity>...</maxvelocity>
    <unittype>...</unittype>
    <protoaction>...</protoaction>
    <tactic>tactics\<unit>tactics.tactics</tactic>
    <icon>...</icon>
    <portraiticon>...</portraiticon>
    <unitaitype>...</unitaitype>
    <trainpoints>...</trainpoints>
    <cost resourcetype="Food">...</cost>
    <cost resourcetype="Wood">...</cost>
    <cost resourcetype="Gold">...</cost>
    <buildbounty>...</buildbounty>
    <killbounty>...</killbounty>
    <contain mergeMode='remove'>AbstractArtillery</contain>
    ...
  </unit>
</protomods>
```

### What ANW's `data/protomods.xml` actually contains

Despite the broad field surface above, ANW's protomods.xml is a **focused
single-purpose overlay**, not a stat-rebalance table. All 58 entries are the
**same** minimal override — each removes `AbstractArtillery` from a ship /
transport unit's `<contain>` list so artillery can no longer be garrisoned
aboard those naval units:

```xml
<unit name="Caravel">
  <contain mergeMode='remove' indelay="3.0" outdelay="0.0">AbstractArtillery</contain>
</unit>
```

(Verified against `data/protomods.xml`: 58 `<unit>` entries, every one a
single `<contain mergeMode='remove'>AbstractArtillery</contain>`, zero stat
or cost overrides.) Unit stats/costs for ANW civs are instead adjusted in
[techtreemods.xml](techtreemods.md) via `<Effect>` rows, not here.

### Field categories (community-reconstructed)

| Category | Example fields |
|---|---|
| Identity | `id`, `name`, `displaynameid`, `rolloverid`, `populationcount` |
| Stats | `initialhitpoints`, `maxhitpoints`, `maxvelocity`, `physicalsize`, `los` |
| Combat | `protoaction` (per-action stats), `tactic`, `armor` |
| Costs | `<cost resourcetype="...">` (Food/Wood/Gold) |
| Training | `trainpoints`, `populationcount`, `trainnotvisible` |
| Visuals | `<anim>`, `<sound>`, `<icon>`, `<portraiticon>` |
| Type tags | `<unittype>` (e.g. `AbstractInfantry`, `Military`, `LogicalTypeLandMilitary`) |
| AI hints | `<unitaitype>`, `<aiunitstance>` |

The `<unittype>` system is critical for matching: techs, cards, and AI
tactics target sets of `<unittype>` tags rather than individual proto
names. The `SetUnitType` effect in `techtreemods.xml` adds/removes type
tags at runtime.

## File paths

- Base: `proto.xml.xmb` inside base BARs.
- Additive overlay: `data/protomods.xml` (the one ANW ships). A
  `data/protoymods.xml` (`y`-variant, for the Asian `protoy.xml` table) is
  community-observed in other mods but **ANW does not ship one** (verified:
  no such file in `data/`).
- Tactics files: `data/tactics/<unit>tactics.tactics`.
- Animation/sound rigs are referenced by name and resolved against
  `anim.xml.xmb` and the sound libraries.

## Cross-references

- [techtreemods.xml](techtreemods.md) — `<Effect type='Data' subtype='Enable'>`
  and `SetUnitType` modify proto units.
- [civmods.xml](civmods.md) — `<startingunit>`, `<townstartingunit>`
  reference proto names.
- [Additive data mods](../additive-data-mods.md) — `mergeMode` controls
  how protomods entries merge.
- [Portrait rendering](../ui-layer/portrait-rendering.md) — `<icon>` /
  `<portraiticon>` reference DDT/PNG.

## Tools

| Path | Purpose |
|---|---|
| [`tools/validation/validate_protomods.py`](../../../tools/validation/validate_protomods.py) | Protomods structure |
| Engine `DebugOutputGameData` | Merged proto dumped to Temp dir |
| Resource Manager | XML/XMB/JSON conversion |

## Known issues

- **Patch breakage**: base `proto.xml` is patched frequently. Microsoft
  Additive Data Mods doc:
  > "Data mods from before the additive data mod implementation have to
  > be replaced after every official update."
- **Hidden cross-coupling**: protomods entries are referenced by
  techtree, anim, sound, tactics. Renaming a proto without updating
  refs causes silent runtime errors.
- **Case sensitivity** in proto names is community-suspected (matches
  with `<Target type='ProtoUnit'>` in techtree appear case-sensitive).

## Open questions

- Authoritative list of every legal `<unit>` field and their semantics.
- Whether `protoymods.xml` (with `y`) is a separate engine path or just
  a community filename convention.
- Whether DE supports `mergeMode="remove"` against a `<unit>` that other
  refs still target.
- Default values for omitted fields.

## Sources

- [Microsoft Additive Data Mods](https://support.ageofempires.com/hc/en-us/articles/360062106732-Additive-Data-Mods).
- [HeavenGames newciv tutorial](https://aoe3.heavengames.com/modding/tutorials/expert/newciv/index.shtml).
- This repo: `data/techtreemods.xml` for `<Target type='ProtoUnit'>` references.
