# SELECT HOME CITY picker

> WPF screen used to pick / manage Home Cities (saved-profile-style
> entities tied to a civ). Distinct from the SELECT CIVILIZATION
> picker; consumes overlapping but distinct field sets and surfaces
> different bugs.

## Fields the picker reads

From `civs.xml` / `civmods.xml`:

| Field | Used for |
|---|---|
| `<name>` / `<displaynameid>` | Tile title |
| `<homecityfilename>` | Resolves to a homecity XML, providing hero name and city name |
| `<homecityflagiconwpf>` | Flag icon |
| `<homecityflagbuttonwpf>` | Flag button (clickable variant) |
| `<homecitypreviewwpf>` | The portrait/preview PNG shown on the tile |
| `<homecityflagtexture>` (DDT) + `<homecityflagbuttonset>` (legacy buttonset) | Legacy fallback |
| `<postgameflagiconwpf>` | Used in post-game scoreboard, often shown alongside |

From the referenced `homecity*.xml`:

- `<heroname>$$<id>$$</heroname>` — hero/leader name (`_locID`)
- `<name>$$<id>$$</name>` — home city display name (`_locID`)
- `<level>` — initial player home city level
- `<skillpoints>` — initial skill points

The XAML lives in the base `ui*.bar`; partial extracts in this repo:

- [`artifacts/extracted_uihomecitypicker.xaml`](../../../artifacts/extracted_uihomecitypicker.xaml)
- [`artifacts/extracted_uihomecitypicker.xml`](../../../artifacts/extracted_uihomecitypicker.xml)

## File path conventions

- WPF PNGs: `resources\images\icons\flags\flag_hc_*.png`,
  `resources/images/icons/singleplayer/cpai_avatar_*.png`.
- DDT fallbacks: `art\...`, `objects\flags\...`.
- Homecity XMLs: `data\anwhomecity<civ>.xml` (this mod) or
  `data\homecity<civ>.xml` (base game).

## Fallback chain (community-observed)

1. WPF PNG slot (`<homecityflagbuttonwpf>`, `<homecitypreviewwpf>`,
   `<homecityflagiconwpf>`).
2. DDT + buttonset slot (`<homecityflagtexture>` +
   `<homecityflagbuttonset>`).
3. Engine placeholder.

## Cross-references

- [civmods.xml](../data-layer/civmods.md) — source of fields.
- [Home City XML](../data-layer/homecity.md) — file referenced by
  `<homecityfilename>`.
- [Flag rendering](flag-rendering.md) — flag asset routing.
- [Portrait rendering](portrait-rendering.md) — portrait asset routing.
- [SELECT CIVILIZATION picker](select-civilization.md) — the other
  picker.

## Tools

| Path | Purpose |
|---|---|
| [`tools/validation/validate_no_homecity_doubles.py`](../../../tools/validation/validate_no_homecity_doubles.py) | Suppression entries override `<homecityfilename>` to empty for hidden civs |
| [`tools/validation/validate_civ_homecities.py`](../../../tools/validation/validate_civ_homecities.py) | Per-civ homecity presence |
| Engine `DebugOutputGameData` | Verifies merged tree the picker reads |

## Known issues

- **Picker doubles** specific to home-city saved profiles: when an
  additive mod adds a new civ but also touches the base civ entry, the
  home-city picker may show two saved profiles per civ — one from base
  saved data, one from the mod default. Fix in this repo: also
  override `<homecityfilename></homecityfilename>` to empty on
  suppression entries. See
  [picker doubles](../modding-pitfalls/picker-doubles.md).
- **Saved profiles persist across mod uninstall.** No authoritative
  documentation of how DE prunes saved profiles. Treat profile
  cleanup as a manual operation.
- **WPF path slashes.** Backslash vs forward slash in WPF paths
  matters in some fields; rule not documented. See
  [missing flags](../modding-pitfalls/missing-flags.md).

## Open questions

- Whether the picker enumerates from the same merged `civs.xml` view
  as the SELECT CIVILIZATION picker, or from a different filtered
  view.
- Whether `<homecityflagiconwpf>` and `<homecityflagbuttonwpf>` are
  interchangeable or one is required.
- The exact rule for "saved profile" creation and cleanup.
- Whether the picker honours `<main>0</main>`.

## Sources

- [HeavenGames newciv tutorial](https://aoe3.heavengames.com/modding/tutorials/expert/newciv/index.shtml).
- This repo: extracted XAML/XML, `civ_binding_verifications/`,
  `picker_calibration*` empirical probes.
