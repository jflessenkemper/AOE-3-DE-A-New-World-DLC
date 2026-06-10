# `.personality` files — AI personality registration

> Plain-XML files at `game/ai/<name>.personality`. Each one registers an
> AI personality: which XS loader to run, which civ to lock onto,
> display name + tooltip (`_locID`), avatar icon, and chat bundle. Read
> directly by the engine — not XMB-compiled, not part of the additive
> merge.

## Schema

Reference: [`game/ai/anwbritish.personality`](../../../game/ai/anwbritish.personality).

```xml
<AI>
   <version>2</version>
   <script>aiLoaderStandard</script>
   <nameID>490200</nameID>
   <tooltipID>490201</tooltipID>
   <forcedciv>ANWBritish</forcedciv>
   <rushboom>0</rushboom>
   <icon>resources/images/icons/singleplayer/cpai_avatar_british_elizabeth.png</icon>
   <chatset>anw_british</chatset>
   <playerNames>
      <nameID>490200<civ>ANWBritish</civ></nameID>
   </playerNames>
</AI>
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `<version>` | int | Yes | `2` for DE |
| `<script>` | string | Yes | XS loader to invoke (e.g. `aiLoaderStandard`, `aiLoaderInactive`); resolves to `game/ai/<script>.xs` |
| `<nameID>` | int | Yes | `_locID` of personality display name |
| `<tooltipID>` | int | No | `_locID` of hover tooltip |
| `<forcedciv>` | string | No | Civ name (must match `<civ><name>` in merged civs.xml). For ANW personalities this is the **ANW-prefixed token** (e.g. `ANWBritish`), not the base-game token (`British`) — verified against `game/ai/anwbritish.personality`. If absent, AI uses lobby-selected civ |
| `<rushboom>` | int | No | Strategy hint flag (community-observed: 0/1) |
| `<icon>` | path | No | PNG (or DDT) avatar icon |
| `<chatset>` | string | No | Identifier for chat-line bundle |
| `<playerNames>` | block | No | List of in-game display-name candidates, optionally tagged with a `<civ>` filter |
| `<playerNames><nameID>` | int (with optional `<civ>` child) | — | Each entry is a `_locID` for a candidate name; `<civ>` narrows the pool to that civ |

## File paths

- `game/ai/<personality>.personality` — primary location.
- Icons: `resources/images/icons/singleplayer/cpai_avatar_<civ>[_<leader>].png`
  (lowercase, snake-case).
- Referenced XS loader: `game/ai/<script>.xs` (e.g.
  `aiLoaderStandard.xs`).

## Cross-references

- [XS scripts](../ai-layer/xs-scripts.md) — `<script>` resolves to an
  XS loader.
- [AI Personality picker](../ui-layer/ai-personality-picker.md) — the
  dropdown that surfaces these files.
- [stringmods.xml](stringmods.md) — `nameID`/`tooltipID` are `_locID`s.
- [Portrait rendering](../ui-layer/portrait-rendering.md) — `<icon>`
  PNG conventions.
- [Mod folder structure](../mod-folder-structure.md) — `game/ai/`
  placement.

## Tools

| Path | Purpose |
|---|---|
| [`tools/validation/validate_personality_active.py`](../../../tools/validation/validate_personality_active.py) | Personality file structure / fields |
| [`tools/validation/validate_personality_overrides.py`](../../../tools/validation/validate_personality_overrides.py) | Per-civ personality overrides resolve |
| [`tools/cardextract/generate_base_civ_personalities.py`](../../../tools/cardextract/generate_base_civ_personalities.py) | Generate `.personality` files from civ table |

## Known issues

- **Wrong leader name in saved profiles after mod uninstall.**
  Disabling/uninstalling does not retroactively repair saved profile
  leader names. No authoritative cleanup procedure documented.
- **Generic icon** if `<icon>` path is missing or wrong-cased.
- **Duplicate entries** if two `.personality` files share `<nameID>` (no
  engine-side dedup is documented).
- **`<playerNames>` syntax** — observed to allow nested `<civ>` to
  narrow the pool. Reconstructed from base personality files.

## Open questions

- Authoritative list of allowed `<script>` values (the named loaders).
- Whether `<rushboom>` has additional integer values or maps to a
  documented enum.
- Behaviour when `<forcedciv>` matches no merged civ (silent skip vs
  error).
- Whether `<chatset>` strings are looked up in a registry or are
  free-form keys.
- Whether `<icon>` accepts DDT in addition to PNG.

## Sources

- [AOE3 Modding Council AI guide](https://aoe3mc.github.io/ai-guide/getting-started/).
- This repo: `game/ai/anwbritish.personality` and siblings.
