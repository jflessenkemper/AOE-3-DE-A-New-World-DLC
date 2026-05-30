# AI Personality picker

> Dropdown in skirmish setup that lets a player pick which AI personality
> opponents use. Reads `*.personality` files from `game/ai/` and the
> base game's AI directory. Shows display name, civ, and avatar icon.

## Fields the dropdown reads

From each `*.personality` file:

| Field | Used for |
|---|---|
| `<nameID>` | Display name (resolves through stringtable) |
| `<tooltipID>` | Hover tooltip |
| `<forcedciv>` | Civ name; locks AI to this civ. Resolved against `<civ><name>` in merged civs.xml |
| `<icon>` | Avatar PNG path |
| `<script>` | XS loader (e.g. `aiLoaderStandard`) |
| `<chatset>` | Chat-line bundle |
| `<rushboom>` | Strategy hint |

From `civs.xml` (resolved via `forcedciv`):

- `<displaynameid>` — civ name shown alongside the AI's display name
- `<smallportraittexturewpf>` / `<homecitypreviewwpf>` — sometimes used
  for a civ icon next to the AI portrait

## File paths

- Per-AI personality: `game/ai/<civ_or_personality>.personality`.
- Icon PNGs:
  `resources/images/icons/singleplayer/cpai_avatar_<civ>_<leader>.png`
  (e.g. `cpai_avatar_british_elizabeth.png`).
- Loader/main XS scripts: `game/ai/aiLoaderStandard.xs`, `aiMain.xs`,
  `aiHeader.xs`.

## Cross-references

- [Personality files](../data-layer/personalities.md) — full schema.
- [XS scripts](../ai-layer/xs-scripts.md) — script behaviour referenced
  by `<script>`.
- [civmods.xml](../data-layer/civmods.md) — `forcedciv` resolves through
  the merged civ table.
- [Portrait rendering](portrait-rendering.md) — `<icon>` PNG conventions.

## Known issues

- **Generic AI portraits** when `<icon>` PNG is missing or path-cased
  wrong. See [generic portraits](../modding-pitfalls/generic-portraits.md).
- **Wrong civ shown** if `<forcedciv>` does not match a `<civ><name>` in
  merged civs.xml.
- **Duplicate dropdown entries** if multiple `.personality` files share
  `<nameID>` (no engine-side dedup documented).
- HeavenGames newciv tutorial:
  > "Your new civ won't have AI unless you overwrite an existing civ"

## Open questions

- The exact dropdown sort order (file-system order, `nameID` order,
  alphabetical?).
- Whether the dropdown enumerates personalities from `<mod>/game/ai/`
  and `<base>/game/ai/` simultaneously, or whether the mod overlay
  replaces the base set.
- Whether icons must be DDT or PNG. ANW ships PNG only; base game is
  mostly PNG. **PNG appears supported but not formally documented as
  canonical.**
- Whether `<rushboom>` has documented enumerated values beyond 0/1.

## Sources

- [AOE3 Modding Council AI guide](https://aoe3mc.github.io/ai-guide/getting-started/).
- [HeavenGames newciv tutorial](https://aoe3.heavengames.com/modding/tutorials/expert/newciv/index.shtml).
- This repo: `game/ai/anwbritish.personality`, `anwfrench.personality`.
