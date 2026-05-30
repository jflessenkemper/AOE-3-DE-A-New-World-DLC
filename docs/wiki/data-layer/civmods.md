# civmods.xml — civilization additive merge

> Plain XML file at `data/civmods.xml`. Merges into the base game's
> `civs.xml` (XMB-encoded inside `Game/Data/Data.bar`) at engine load.
> Adds new civs, overrides existing fields, suppresses base civs.

## Schema

Root: `<civmods>` containing `<civ>` children. Each `<civ>` has a
`<name>` (the civ token, must be unique) plus any subset of base civ
fields (the engine merges by field name).

```xml
<civmods>
    <civ>
        <name>British</name>
        <main>1</main>
        <statsid>BR</statsid>
        <portrait>objects\flags\british</portrait>
        <culture>WesternEurope</culture>
        <displaynameid>410100</displaynameid>
        <rollovernameid>410500</rollovernameid>
        <homecityfilename>anwhomecitybritish.xml</homecityfilename>
        <agetech><age>Age0</age><tech>BritishAge0</tech></agetech>
        <agetech><age>Age1</age><tech>ColonializeBritish</tech></agetech>
        <!-- … many more fields … -->
    </civ>
</civmods>
```

## Critical fields

| Field | Type | Purpose | Notes |
|---|---|---|---|
| `<name>` | string | Civ token, primary key | Must match across all references (homecity XML, personality, decks, playercolors). **Engine is case-sensitive on tag names.** |
| `<main>` | `0` or `1` | Picker visibility | `1` = appears in SELECT CIVILIZATION picker; `0` = hidden. Use `0` to suppress base civs. |
| `<statsid>` | 2-char alpha | Engine-internal civ ID | Must be exactly 2 alphabetic chars. `1X` digit-prefix StatsIDs are silently rejected. Must be unique across merged table. |
| `<homecityfilename>` | path | Default home city for civ | Picker iterates by this; **suppression entries must override to empty string** to remove from SELECT HOME CITY picker. |
| `<displaynameid>` | int | _locID for civ display name | Must resolve in stringmods or base stringtable (10670–230102). |
| `<rollovernameid>` | int | _locID for short tooltip | Often the displayed-on-hover short name. |

## Merge semantics

The engine's merge:
1. Reads base `civs.xml` from `Game/Data/Data.bar`.
2. Iterates `data/civmods.xml` `<civ>` entries.
3. For each `<civ>`, looks up base civ by `<name>` match.
4. If found: **modify** behavior — civmods fields override base field values.
5. If not found: **add** behavior — new civ inserted into the table.
6. Per-field merge: civmods value wins. Empty string overrides base value to empty.

### Case sensitivity ⚠

**Tag names ARE case-sensitive at the merge layer.** Base game uses
**lowercase**: `<civ>`, `<name>`, `<main>`, `<statsid>`. If our mod's
file uses Capital tags (`<Civ>`, `<Name>`, `<Main>`), the engine
**doesn't recognize them** and our entries are silently dropped.

Symptoms: picker shows base civs only, no error logged.

See [case-sensitivity pitfall](../modding-pitfalls/case-sensitivity.md)
for the full bug story.

## Cross-references

- [stringmods.xml](stringmods.md) — provides `_locID` resolutions for
  `<displaynameid>`, `<rollovernameid>`, etc.
- [techtreemods.xml](techtreemods.md) — tech names referenced by
  `<agetech>`, `<postindustrialtech>`, etc.
- [homecity XML](homecity.md) — file referenced by `<homecityfilename>`
- [personality files](personalities.md) — reference civ token via
  `<forcedciv>`
- [SELECT CIVILIZATION picker](../ui-layer/select-civilization.md) — reads `<main>` + display fields
- [SELECT HOME CITY picker](../ui-layer/select-home-city.md) — reads `<homecityfilename>`

## Tools

| Path | Purpose |
|---|---|
| [`tools/cardextract/offline_engine_sim.py`](../../../tools/cardextract/offline_engine_sim.py) | Reverse-engineered merge simulator. Predicts post-merge civ table from base + civmods in <1 sec |
| [`tools/validation/validate_civmods_ui.py`](../../../tools/validation/validate_civmods_ui.py) | Field-presence + structure |
| [`tools/validation/validate_civ_loadability.py`](../../../tools/validation/validate_civ_loadability.py) | StatsID / loadability checks |
| [`tools/validation/validate_civ_distinguishability.py`](../../../tools/validation/validate_civ_distinguishability.py) | DisplayName resolution + collision |
| [`tools/validation/validate_no_homecity_doubles.py`](../../../tools/validation/validate_no_homecity_doubles.py) | Suppression entries + empty homecityfilename check |
| [`tools/validation/validate_civ_tech_resolution.py`](../../../tools/validation/validate_civ_tech_resolution.py) | All tech refs resolve in mod or base |
| [`tools/validation/validate_offline_picker.py`](../../../tools/validation/validate_offline_picker.py) | Predicts picker contents from merged table |

## Known issues + fixes

| Bug | Symptom | Fix |
|---|---|---|
| Capital `<Civ>` tags | All ANW civs missing from picker | Lowercase all tags |
| `<main>0</main>` only | Base civ still in SELECT HOME CITY picker | Also add empty `<homecityfilename></homecityfilename>` |
| Bad StatsID (`1X`, etc.) | Civ doesn't load | Use 2-char alpha unique IDs |
| Forward-slash wpf paths | Some flag/portrait wpf paths fail | (open) Backslash style works for some, not all |

## Open questions

> ⚠ OPEN: Is the `mergeMode` attribute (`modify`/`add`/`remove`/`replace`)
> from the official additive-mod spec respected when set on `<civ>`
> entries? We've been using empty-field overrides instead, but
> `mergeMode="remove"` might be cleaner for suppression entries.
> Source: [Microsoft Additive Data Mods
> doc](https://support.ageofempires.com/hc/en-us/articles/360062106732).

> ⚠ OPEN: How does the picker disambiguate when civmods has both an
> `add` (new civ) and a `modify` (override base) for civs that share
> a base name (e.g. our `British` rename of base British)? We assume
> civmods replaces base via name match.

## Sources

- Schema: HeavenGames "New Civilizations" expert tutorial,
  [aoe3.heavengames.com/modding/tutorials/expert/newciv](https://aoe3.heavengames.com/modding/tutorials/expert/newciv/index.shtml).
- Merge semantics: empirically tested in this session. The `<Civ>` vs
  `<civ>` case-sensitivity bug was verified by extracting base
  `civs.xml` from Data.bar and observing 46 ANW civs dropped before
  the lowercase rewrite.
- Microsoft official: [Additive Data Mods](https://support.ageofempires.com/hc/en-us/articles/360062106732-Additive-Data-Mods).
