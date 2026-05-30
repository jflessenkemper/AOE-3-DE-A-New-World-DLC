# Generic AI portraits / leader portraits

> When the engine cannot resolve a portrait file, it renders a generic
> placeholder ("generic AI portrait") instead of failing. The cause is
> almost always a wrong path, wrong case, missing DDT, or wrong field
> for the surface.

## Symptom

The AI dropdown, SELECT CIVILIZATION tile, or SELECT HOME CITY tile
shows a generic silhouette / placeholder portrait instead of the
expected leader image.

## Likely causes

1. **WPF PNG file is missing** at the path declared in
   `<smallportraittexturewpf>`, `<homecitypreviewwpf>`, or `.personality`
   `<icon>`.
2. **Path case mismatch.** Linux/Proton rendering can be case-sensitive
   even though Windows isn't.
3. **Slash direction.** Backslash vs forward slash empirically matters
   for some WPF fields (see [missing flags](missing-flags.md)).
4. **WPF PNG present but DDT field also required.** Per
   `aoe3_mod_full_research.md` §5:
   > "Ship a per-civ DDT at `ui\singleplayer\cpai_avatar_<civ>` matching
   > `<smallportraittexture>`. The WPF PNG path alone has not been
   > authoritatively confirmed sufficient."
5. **`<smallportraittexture>` overrides the WPF field.** When a
   civmods entry sets the legacy DDT field but no DDT exists at that
   path, the engine still falls back to generic instead of using the
   WPF PNG.

## Fixes

- Ship both the DDT (under `art\ui\singleplayer\cpai_avatar_<civ>.ddt`
  or matching base path) AND the WPF PNG (`resources/images/icons/
  singleplayer/cpai_avatar_<civ>[_<leader>].png`).
- Match base game path conventions exactly — including case.
- If unsure which field drives the surface, set both DDT + UV coords
  AND the WPF PNG.

## Cross-references

- [Portrait rendering](../ui-layer/portrait-rendering.md) — which
  fields drive which surface.
- [Personality files](../data-layer/personalities.md) — `<icon>` field.
- [civmods.xml](../data-layer/civmods.md) —
  `<matchmakingtextures>` block.
- [DDT textures](../file-formats/ddt.md).

## Tools

- [`tools/validation/validate_civ_asset_existence.py`](../../../tools/validation/validate_civ_asset_existence.py) — asset paths resolve.
- [`tools/cardextract/png_to_ddt.py`](../../../tools/cardextract/png_to_ddt.py) — PNG -> DDT conversion.

## Sources

- [HeavenGames newciv tutorial](https://aoe3.heavengames.com/modding/tutorials/expert/newciv/index.shtml).
- This repo: `aoe3_mod_full_research.md` §5.
