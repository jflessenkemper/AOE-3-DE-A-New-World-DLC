# stringmods.xml — additive stringtable

> Plain XML at `data/strings/english/stringmods.xml` (per-locale path —
> NOT a top-level `data/stringmods.xml`). Adds or overrides `_locID`-keyed
> entries in the base stringtable. Replaces the legacy
> `Mod/Data/Strings/<lang>/stringtabley.xml` workflow (the differently-named
> `stringtabley.xml`, which DE silently ignores).

## Schema

ANW's actual file is rooted at `<stringmods>` and nests
`<StringTable>` → `<Language name="English">` → `<String _locID="...">…</String>`
(verified against `data/strings/english/stringmods.xml`). The bare
`<String _locID='…'>text</String>` form documented on
[forums.ageofempires.com — additive strings thread](https://forums.ageofempires.com/t/how-should-an-additive-strings-mod-look-like/213986)
is the inner element; ANW wraps it in the `<stringmods>`/`StringTable`/`Language`
envelope:

```xml
<?xml version='1.0' encoding='utf-8'?>
<stringmods>
  <StringTable>
    <Language name="English">
      <String _locID="36883">Britain</String>
      <String _locID="490331">Elizabeth I</String>
      ...
    </Language>
  </StringTable>
</stringmods>
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

Mods should pick high IDs to avoid collisions. ANW uses two high bands
(verified in `data/strings/english/stringmods.xml`): **400000+** for
leader/civ history blurbs (e.g. `400001` José de San Martín, `400005` Sir
Isaac Brock) and **490000+** for UI display/rollover names (e.g. `490331`,
`490382`, `490002`).

## File path conventions

- DE additive (what ANW ships): `data/strings/<lang>/stringmods.xml` —
  ANW's lives at `data/strings/english/stringmods.xml`. Every repo tool
  (validators, `build_civ_columns.py`, `build_dev_reference.py`) treats
  this per-locale path as authoritative; there is **no** top-level
  `data/stringmods.xml`.
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
- This repo: `artifacts/extracted_base_stringtable.xml`, `data/strings/english/stringmods.xml`.
