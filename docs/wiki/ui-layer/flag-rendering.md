# Flag rendering

> Civ flags surface in many UI places: SELECT CIVILIZATION tile banner,
> SELECT HOME CITY flag button, post-game scoreboard, in-game minimap
> pin, ESO matchmaking banner. The engine pulls flag art from a layered
> set of fields in `civs.xml` / `civmods.xml`. Legacy paths use DDT
> sprite-sheets; DE adds WPF PNG paths that bypass DDT for some
> surfaces.

## Fields involved

From `civs.xml` / `civmods.xml`:

| Field | Format | Surface |
|---|---|---|
| `<homecityflagtexture>` | DDT path (no extension) | Legacy home-city flag |
| `<homecityflagbuttonset>` | buttonset id (legacy `buttonsets.xml`) | Legacy home-city flag button |
| `<homecityflagbuttonsetlarge>` | buttonset id | Legacy large variant |
| `<postgameflagtexture>` | DDT path | Post-game scoreboard |
| `<postgameflagiconwpf>` | PNG path | DE post-game scoreboard (preferred) |
| `<homecityflagiconwpf>` | PNG path | DE home-city flag icon |
| `<homecityflagbuttonwpf>` | PNG path | DE home-city flag button |
| `<matchmakingtextures><bannertexture>` | DDT path | Tile banner DDT (sprite-sheet) |
| `<matchmakingtextures><bannertexturecoords>` | UV rect into the banner DDT | UV |

From `buttonsets.xml`: `homecityflagbuttonset` and `...Large` resolve
to a buttonset id; the buttonset XML maps to DDT sprite-sheet plus
state UV coords.

## Resolution / fallback chain (community-observed)

1. **WPF PNG path** if specified and file exists at
   `resources\images\icons\flags\...`.
2. **DDT path + buttonset/UV coords** if WPF unspecified.
3. **Engine generic placeholder.**

Authoritative quote on filename-override technique (HeavenGames
"Adding A Custom Flag" tutorial):

> "Basically we're just telling the engine to use a different texture
> for a predetermined file name that's already in the game."

## File path conventions

- DDTs: `art\<flag>\<name>.ddt`, `objects\flags\<name>.ddt`.
- DDT sprite sheets: `art\ui\flags\<sheet>.ddt`.
- Sprite-sheet UV format: `<bannertexturecoords>x y w h</bannertexturecoords>`
  (community-observed; exact unit — pixels vs. normalised — not
  authoritatively documented).
- WPF PNG flags: `resources\images\icons\flags\Flag_<Civ>_NE.png`,
  `resources\images\icons\flags\flag_hc_<civ>.png`.

## Cross-references

- [civmods.xml](../data-layer/civmods.md) — fields above.
- [DDT textures](../file-formats/ddt.md) — DDT sprite-sheet rules.
- [SELECT CIVILIZATION picker](select-civilization.md) and
  [SELECT HOME CITY picker](select-home-city.md) — main consumers.
- [Missing flags / forward slashes](../modding-pitfalls/missing-flags.md).

## Tools

| Path | Purpose |
|---|---|
| [`tools/validation/validate_civ_asset_existence.py`](../../../tools/validation/validate_civ_asset_existence.py) | Asset paths in civmods resolve to files |
| [`tools/build_banner.py`](../../../tools/build_banner.py) | This repo's banner builder |
| Resource Manager | DDT <-> PNG, BAR creation |
| [HG AoE3DE Flag-Maker Pack](https://forums.ageofempires.com/t/aoe3de-flag-maker-pack/103377) | Premade flag assets |

## Known issues

- **Sprite-sheet UVs vs replacement DDT**: replacing a banner DDT with
  a different-resolution texture without updating
  `<bannertexturecoords>` crops wrong.
- **Slash direction in WPF paths**: backslash vs forward slash
  empirically matters in some fields. **No authoritative rule
  documented.**
- **DE-vs-DDT precedence**: not authoritatively documented.
  Empirically DE prefers WPF PNG when present, but it is unclear
  whether that holds for every flag field or only some.
- **Filename-override only works if the path matches the base path
  exactly.**

## Open questions

- Authoritative DDT-vs-WPF precedence rule per surface.
- Slash convention rule (`\` vs `/`) in WPF PNG fields.
- Coordinate units in `<bannertexturecoords>` (pixels vs normalised).
- Whether `<homecityflagbuttonset>` is required when
  `<homecityflagbuttonwpf>` is present, or fully replaced.

## Sources

- [HeavenGames Adding-A-Custom-Flag](https://aoe3.heavengames.com/cgi-bin/forums/display.cgi?action=ct&f=14,25197,,all).
- [forums.ageofempires.com — AoE3DE Flag-Maker Pack](https://forums.ageofempires.com/t/aoe3de-flag-maker-pack/103377).
- [Resource Manager README](https://github.com/eBaeza/Resource-Manager/blob/master/README.md).
- This repo: `data/civmods.xml`.
