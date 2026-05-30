# SELECT CIVILIZATION picker

> WPF-based UI players use in skirmish/lobby setup to pick a top-level
> pickable civ. Distinct from the SELECT HOME CITY picker. Enumerates
> entries from the merged `civs.xml` tree and renders each tile from a
> mix of DDT sprite-sheet textures and DE-era WPF PNG paths.

## Fields the picker reads

From `civs.xml` / `civmods.xml`:

| Field | Used for |
|---|---|
| `<name>` | Internal key, dedup key |
| `<main>` | Pickable-vs-not flag (community-suspected; only `<main>1</main>` appears) |
| `<displaynameid>` | Tile title (resolved through stringtable) |
| `<rollovernameid>` | Hover tooltip text |
| `<matchmakingtextures><bannertexture>` | DDT sprite-sheet for tile banner |
| `<matchmakingtextures><bannertexturecoords>` | UV rect into the banner DDT |
| `<matchmakingtextures><portraittexture>` + `<portraittexturecoords>` | Larger portrait variant |
| `<matchmakingtextures><smallportraittexture>` + `<smallportraittexturecoords>` | Small (legacy) portrait variant |
| `<matchmakingtextures><smallportraittexturewpf>` | DE-era PNG portrait, used by the WPF tile |
| `<homecitypreviewwpf>` | Some surfaces use this preview PNG instead |
| `<culture>` | Group/category in some sub-views |
| `<homecityflagiconwpf>` | Flag icon next to civ name |

The picker XAML lives in the base `ui*.bar` archives. No first-party
doc maps fields → controls.

## File path conventions

- DDT textures: `art\...` and `objects\flags\...` filename roots.
- WPF PNG paths: `resources\images\icons\...` (e.g.
  `resources/images/icons/flags/Flag_*.png`,
  `resources/images/icons/singleplayer/cpai_avatar_*.png`).

## Fallback chain (community-observed)

1. WPF PNG slot if specified and file exists (e.g.
   `<smallportraittexturewpf>`).
2. DDT slot + UV coords if WPF unspecified (e.g.
   `<smallportraittexture>` + `<smallportraittexturecoords>`).
3. Engine generic placeholder for missing references.

## Cross-references

- [civmods.xml](../data-layer/civmods.md) — source of every field.
- [Flag rendering](flag-rendering.md) — banner/flag asset routing.
- [Portrait rendering](portrait-rendering.md) — portrait asset routing.
- [stringmods.xml](../data-layer/stringmods.md) —
  `displaynameid`/`rollovernameid`.
- [SELECT HOME CITY picker](select-home-city.md) — the *other* picker
  that mods commonly confuse with this one.

## Tools

| Path | Purpose |
|---|---|
| [`tools/validation/validate_offline_picker.py`](../../../tools/validation/validate_offline_picker.py) | Predicts picker contents from merged civ table |
| [`tools/validation/validate_live_picker.py`](../../../tools/validation/validate_live_picker.py) | Validates against in-engine picker observation |
| [`tools/validation/validate_civmods_ui.py`](../../../tools/validation/validate_civmods_ui.py) | Field-presence + structure |
| Engine `DebugOutputGameData` | Verifies the merged civ tree the picker enumerates |

## Known issues

- **Picker doubles**: same civ appearing twice when an additive overlay
  collides with a base entry. See [picker doubles](../modding-pitfalls/picker-doubles.md).
- **Generic flags / portraits**: WPF PNG missing or wrong path → engine
  falls back to DDT or generic placeholder. See
  [generic portraits](../modding-pitfalls/generic-portraits.md).
- **ESO/multiplayer invisibility for new civs.** HeavenGames newciv
  tutorial:
  > "your civ won't ... be viewed on ESO"

## Open questions

- The exact set of fields that hide/show a civ tile (is it only
  `<main>`? does `<civsmenu>` matter?).
- Tile sort order — alphabetical, file order, declared
  `<displaynameid>` order, or `<civsmenu>` order?
- Whether changing `<main>` from 1 to 0 at runtime is honoured.
- Whether the picker reads `<homecitypreviewwpf>` directly or only via
  the home-city picker.

## Sources

- [HeavenGames newciv tutorial](https://aoe3.heavengames.com/modding/tutorials/expert/newciv/index.shtml).
- [HeavenGames Adding-A-Custom-Flag thread](https://aoe3.heavengames.com/cgi-bin/forums/display.cgi?action=ct&f=14,25197,,all).
- This repo: `artifacts/civ_picker_proof/`, `live_picker/`,
  `picker_calibration*` empirical observations.
