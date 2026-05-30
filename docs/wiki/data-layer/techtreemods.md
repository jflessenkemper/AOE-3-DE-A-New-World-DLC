# techtreemods.xml — additive techtree

> Plain XML at `data/techtreemods.xml`. Merges into base
> `techtree.xml.xmb` (and the patch-y variant `techtreey.xml.xmb`).
> Defines techs — the engine's universal unit-of-effect for buffs,
> unlocks, age-ups, politicians, home-city cards, and shipments.

## Schema

```xml
<techtree>
  <Tech name='ColonializeBritish' type='Normal'>
    <DBID>30001</DBID>
    <Status>UNOBTAINABLE</Status>
    <Flag>Shadow</Flag>
    <Prereqs>
      <AnyAllPrereq>
        <TechStatus status='ACTIVE'>OtherTech</TechStatus>
      </AnyAllPrereq>
    </Prereqs>
    <Effects>
      <Effect type='Data' amount='1.00' subtype='Enable' relativity='Absolute'>
        <Target type='ProtoUnit'>Explorer</Target>
      </Effect>
      <Effect type='SetName' proto='Coureur' culture='none'
        newName='125348' newRollover='125350' newShortRollover='125351' />
    </Effects>
    <Cost resourcetype='Food'>...</Cost>
    <ResearchPoints>...</ResearchPoints>
  </Tech>
</techtree>
```

### Per-`<Tech>` fields

| Field | Notes |
|---|---|
| `name` (attr) | Unique tech identifier, primary key for additive merge |
| `type` (attr) | `Normal`, `Building`, `Politician`, `Counter`, ... |
| `<DBID>` | Numeric ID; engine references the tech here in some paths |
| `<Status>` | `UNOBTAINABLE` (must be enabled by another tech) / `ACTIVE` |
| `<Flag>` | `Shadow` (auto-enabled) and others |
| `<Prereqs>` | `<AnyAllPrereq>` / `<AllPrereq>` blocks containing `<TechStatus>` |
| `<Effects>` | Ordered list of `<Effect>` records |
| `<Cost>` | Resource cost (Food/Wood/Gold) |
| `<ResearchPoints>` | Research time |

### `<Effect type='Data'>` (most common)

| Attr | Notes |
|---|---|
| `type` | `Data`, `SetName`, `Cost`, `BuildLimit`, `Reveal`, `Sound`, ... |
| `amount` | Float (Absolute) or multiplier (Percent/BasePercent) |
| `subtype` | `Enable`, `WorkRate`, `Damage`, `TrainBatchSize`, `SetUnitType`, `EnableAutoFormations`, `CopyUnitPortraitAndIcon`, ... |
| `action` | Sub-scope: `Build`, `VolleyRangedAttack`, `CrackshotAttack`, ... |
| `unittype` | Type filter, e.g. `TradingPost`, `AbstractInfantry`, `LogicalTypeLandMilitary` |
| `relativity` | `Absolute` (assign), `Assign`, `Percent`, `BasePercent` |
| `<Target>` | `type='ProtoUnit'` + value; or `type='TechAll'`, `type='Player'` |

### `<Effect type='SetName'>`

| Attr | Notes |
|---|---|
| `proto` | Proto unit name |
| `culture` | `none` or culture key |
| `newName` | `_locID` of new display name |
| `newRollover` | `_locID` of new tooltip |
| `newShortRollover` | `_locID` of short tooltip |

## File paths

- Base: `techtree.xml.xmb` and `techtreey.xml.xmb` inside base BARs.
- Mod overlay: `data/techtreemods.xml` (additive) and optionally
  `data/techtreeymods.xml` for the DE patch-y branch.
- Politician entries reference `politiciandata.xml` for portraits.

## Cross-references

- [civmods.xml](civmods.md) — `<agetech>`, `<postindustrialtech>`, etc.
  reference techs by name.
- [protomods.xml](protomods.md) — `<Target type='ProtoUnit'>` resolves
  into the proto tree.
- [stringmods.xml](stringmods.md) —
  `newName`/`newRollover`/`newShortRollover` are `_locID`s.
- [Additive data mods](../additive-data-mods.md) — merge semantics.

## Tools

| Path | Purpose |
|---|---|
| [`tools/validation/validate_techtree.py`](../../../tools/validation/validate_techtree.py) | Techtree structure |
| [`tools/validation/validate_civ_tech_resolution.py`](../../../tools/validation/validate_civ_tech_resolution.py) | All civmods tech refs resolve in mod or base |
| Engine `DebugOutputGameData` | Merged techtree dumped to Temp dir |
| Resource Manager | XML <-> XMB conversion |

## Known issues

- **Effect ordering matters.** Effects within a tech apply in declared
  order; reordering changes the resulting state.
- **`SetUnitType` is sticky.** Removing a type added by an effect
  requires a separate `Remove` effect (community-suspected).
- **DBID collisions** with base game can clobber base tech IDs. No
  published reserved range.
- **Patch breakage:** base techs change between patches; mods that
  depend on `<Status>` of a base tech can desync.

## Open questions

- Authoritative list of every legal `subtype`, `action`, `relativity`,
  and `type='...'` value.
- Whether `<Flag>Shadow</Flag>` is the only documented flag.
- Authoritative semantics of `culture='none'` vs a specific culture key
  in `SetName`.
- Whether `<DBID>` must be unique or can collide.

## Sources

- [Microsoft Additive Data Mods](https://support.ageofempires.com/hc/en-us/articles/360062106732-Additive-Data-Mods).
- [HeavenGames newciv tutorial](https://aoe3.heavengames.com/modding/tutorials/expert/newciv/index.shtml).
- This repo: `data/techtreemods.xml`, `artifacts/extracted_base_techtreey.xml`.
