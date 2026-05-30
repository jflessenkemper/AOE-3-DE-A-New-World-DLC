# Portrait rendering

> Leader portraits and AI avatars surface in several places: SELECT
> CIVILIZATION tile, SELECT HOME CITY preview, AI dropdown icon, in-game
> leader portrait. Routing varies by surface. De-facto naming convention
> is `cpai_avatar_<civ>[_<leader>].png` for DE WPF surfaces and
> `<civ>_portrait.ddt` (or sprite-sheet variants) for legacy DDT
> surfaces.

## Fields involved

From `civs.xml` / `civmods.xml`:

| Field | Format | Surface |
|---|---|---|
| `<matchmakingtextures><smallportraittexture>` | DDT path | Legacy small portrait |
| `<matchmakingtextures><smallportraittexturecoords>` | UV rect | UV into small DDT |
| `<matchmakingtextures><smallportraittexturewpf>` | PNG path | DE small portrait (preferred) |
| `<matchmakingtextures><portraittexture>` + `<portraittexturecoords>` | DDT + UV | Larger portrait |
| `<homecitypreviewwpf>` | PNG path | Home-city tile preview portrait |

From `<personality>` files:

| Field | Format | Surface |
|---|---|---|
| `<icon>` | PNG (or DDT) path | AI dropdown avatar |

## Naming conventions (community-observed)

- AI/leader avatars:
  `resources/images/icons/singleplayer/cpai_avatar_<civ>[_<leader>].png`
  (lowercase, snake-case).
- Examples in this repo: `cpai_avatar_british_elizabeth.png`,
  `cpai_avatar_napoleonic_france.png`.
- Legacy DDT portraits live under `art\ui\` or sprite-sheet variants
  in `art\ui\portraits\...`.

## Resolution / fallback chain (community-observed)

1. WPF PNG slot if specified and file exists.
2. DDT slot + UV coords.
3. Engine generic placeholder ("generic AI portrait").

## Cross-references

- [civmods.xml](../data-layer/civmods.md) — fields above.
- [Personality files](../data-layer/personalities.md) — `<icon>`
  field.
- [DDT textures](../file-formats/ddt.md) — DDT rules.
- [SELECT CIVILIZATION picker](select-civilization.md) and
  [SELECT HOME CITY picker](select-home-city.md) — consumers.
- [Generic portraits pitfall](../modding-pitfalls/generic-portraits.md).

## Tools

| Path | Purpose |
|---|---|
| [`tools/cardextract/png_to_ddt.py`](../../../tools/cardextract/png_to_ddt.py) | PNG -> DDT conversion |
| [`tools/cardextract/build_leader_ddts.py`](../../../tools/cardextract/build_leader_ddts.py) | Build leader DDTs |
| [`tools/cardextract/make_blank_portraits.py`](../../../tools/cardextract/make_blank_portraits.py) | Placeholder portrait generation |
| [`tools/rebuild_portraits.py`](../../../tools/rebuild_portraits.py) | Rebuild all portrait DDTs/PNGs |
| [`tools/colorize_bw_portraits.py`](../../../tools/colorize_bw_portraits.py) | Colorize black-and-white source portraits |
| Resource Manager | DDT <-> PNG/TGA conversion |
| Kangcliff DDT Photoshop plugin | Direct DDT save |

## Known issues

- **Generic AI portrait** when WPF PNG is missing or path-cased wrong.
  Per `aoe3_mod_full_research.md` §5:
  > "Ship a per-civ DDT at `ui\singleplayer\cpai_avatar_<civ>` matching
  > `<smallportraittexture>`. The WPF PNG path alone has not been
  > authoritatively confirmed sufficient."
- **Slash direction** in WPF paths empirically matters; see
  [missing flags](../modding-pitfalls/missing-flags.md).
- **Sprite-sheet UV mismatch** when a mod ships a higher-resolution
  DDT but does not update `<smallportraittexturecoords>`.
- **DDT vs PNG precedence** is not authoritatively documented per
  surface.

## Open questions

- Authoritative per-surface DDT-vs-WPF precedence.
- Whether `<icon>` in `.personality` accepts DDT or only PNG.
- Whether the engine caches portraits across menu transitions
  (changing a portrait file mid-session).
- Whether `cpai_avatar_*` is enforced naming convention or just
  convention.

## Sources

- [HeavenGames newciv tutorial](https://aoe3.heavengames.com/modding/tutorials/expert/newciv/index.shtml).
- [Resource Manager README](https://github.com/eBaeza/Resource-Manager/blob/master/README.md).
- This repo: `game/ai/anwbritish.personality` `<icon>` paths.
