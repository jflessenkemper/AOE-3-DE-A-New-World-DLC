# stringmods.xml — additive stringtable

> Plain XML at `data/stringmods.xml`. Adds or overrides `_locID`-keyed
> entries in the base stringtable. Replaces the legacy
> `Mod/Data/Strings/<lang>/stringtabley.xml` workflow, which DE silently
> ignores.

## Schema

Root: `<stringtable>` containing `<String _locID="...">...</String>`
entries. Confirmed minimal example from
[forums.ageofempires.com — additive strings thread](https://forums.ageofempires.com/t/how-should-an-additive-strings-mod-look-like/213986):

```xml
<String _locID='20038'>ModContinue</String>
```

```xml
<stringtable>
  <String _locID="36883">Britain</String>
  <String _locID="490331">Elizabeth I</String>
  ...
</stringtable>
```

| Field | Type | Notes |
|---|---|---|
| Element name | `String` | Case-sensitive at the additive merge layer. |
| `_locID` | int (string-encoded) | Numeric ID referenced from civmods, homecity, personality, techtree |
| Element text | string | Localised text |

## In-place reference syntax

Other XML files reference a string by `$$<id>$$` inside text content.
For example, in homecity files:

```xml
<heroname>$$490331$$</heroname>
```

## ID range conventions

No first-party documentation. Community-observed:

- ~1-999: legacy strings, UI chrome, very early base content
- ~10000-60000: bulk of base game (civ names, unit names, tech names)
- 100000+: DLC / DE-era content

Mods should pick high IDs to avoid collisions. ANW uses the **490000+**
band (e.g. `490331`, `490382`, `490002`).

## File path conventions

- DE additive: `data/stringmods.xml` — one file per mod, regardless of
  locale. DE picks the runtime language and merges against the matching
  base stringtable.
- Legacy: `data/strings/<lang>/stringtabley.xml` — **silently ignored**
  by DE. Forum bug report:
  > "Age 3 DE no longer loads stringtables from the
  > Mod/Data/Strings/English/ folder"
  ([forums.ageofempires.com](https://forums.ageofempires.com/t/age-3-de-no-longer-loads-stringtables-from-the-mod-data-strings-english-folder/107991)).

## Cross-references

- [civmods.xml](civmods.md) — `<displaynameid>`, `<rollovernameid>`,
  `<alliedid>`, etc. resolve here.
- [personality files](personalities.md) — `<nameID>` and `<tooltipID>`
  are `_locID`s.
- [homecity XML](homecity.md) — `<heroname>$$<id>$$</heroname>`,
  `<name>$$<id>$$</name>`.
- [techtreemods](techtreemods.md) — `SetName` effects reference
  `_locID`s via `newName`/`newRollover`/`newShortRollover`.
- [Additive data mods](../additive-data-mods.md) — `_locID` matching is
  the merge key.

## Tools

| Path | Purpose |
|---|---|
| [`tools/validation/validate_string_resolution.py`](../../../tools/validation/validate_string_resolution.py) | All `_locID` refs resolve in mod or base |
| [`tools/validation/validate_no_locid_duplicates.py`](../../../tools/validation/validate_no_locid_duplicates.py) | No duplicate `_locID`s within stringmods |
| [`tools/validation/validate_stringtables.py`](../../../tools/validation/validate_stringtables.py) | Stringtable structure |
| Engine `DebugOutputGameData` | Merged stringtable dumped to `Temp\Age of Empires 3 DE\Data\data\strings\<language>` |
| Resource Manager | XML/XMB roundtrip when packaging |

## Known issues

- **Legacy `stringtabley.xml` silently ignored.** Migrate to
  `stringmods.xml`.
- **`DebugOutputGameData` does not always show stringmods.** Forum
  thread: [DebugOutputGameData not showing stringmods](https://forums.ageofempires.com/t/debugoutputgamedata-not-showing-stringmods/225246). Workarounds discussed: explicit `mergeMode` and matching element/attribute case.
- **ID collisions** with future patches. Microsoft does not publish
  reserved ranges; a low ID can be overwritten by a base patch.

## Open questions

- The complete reserved/used base-game ID list.
- Whether `mergeMode="remove"` works against `<String>` entries.
- Per-locale merge resolution: does DE merge against every locale or
  only the active one?
- Whether `_locID` values can be negative or non-decimal.

## Sources

- [forums.ageofempires.com — additive strings example](https://forums.ageofempires.com/t/how-should-an-additive-strings-mod-look-like/213986).
- [forums.ageofempires.com — silent-ignore bug for legacy paths](https://forums.ageofempires.com/t/age-3-de-no-longer-loads-stringtables-from-the-mod-data-strings-english-folder/107991).
- [forums.ageofempires.com — DebugOutputGameData stringmods thread](https://forums.ageofempires.com/t/debugoutputgamedata-not-showing-stringmods/225246).
- [Microsoft Additive Data Mods](https://support.ageofempires.com/hc/en-us/articles/360062106732-Additive-Data-Mods).
- This repo: `artifacts/extracted_base_stringtable.xml`, `data/stringmods.xml`.
