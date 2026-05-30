# XS scripts (AoE3 DE AI)

> XS ("eXtensible Scripting") is Ensemble's home-grown C-like scripting
> language used by the AoE3 DE AI. AI mods consist of a set of `.xs`
> files compiled by the engine at game-start and run in a managed
> sandbox. Entrypoint is `aiMain.xs`.

## File-level conventions

A typical AI mod ships:

| File | Role |
|---|---|
| [`game/ai/aiMain.xs`](../../../game/ai/aiMain.xs) | Top-level entrypoint, called after the personality loader sets `bt`/`cv` variables. Calls `kbAreaCalculate`, `initCivUnitTypes`, `initArrays`, `analyzeGameSettingsAndType`, `analyzeMap`, `initXSHandlers`, `initPersonality`, `enhancedInit` |
| [`game/ai/aiHeader.xs`](../../../game/ai/aiHeader.xs) | Documents `bt*` (Behavior Trait) and `cv*` (Control Variable) defaults. Comment block in this repo's copy: "This file is intended primarily as a reference for the variables that can be safely set by the loader file." |
| [`game/ai/aiLoaderStandard.xs`](../../../game/ai/aiLoaderStandard.xs) / [`aiLoaderInactive.xs`](../../../game/ai/aiLoaderInactive.xs) | Personality loader scripts referenced from `.personality` files via `<script>`. Set `bt*`/`cv*` defaults inside `preInit()` |
| [`game/ai/Age3AI.xs`](../../../game/ai/Age3AI.xs) | Engine-generic helpers |
| [`game/ai/aiHumanAssists.xs`](../../../game/ai/aiHumanAssists.xs) | Human-vs-CPU assist logic |
| `core/aiCore.xs` (included from aiMain) | Core AI services — area, kbase, attack-manager |

The XS language supports: typed locals (`int`, `float`, `bool`,
`string`, `vector`), `void` functions, `for`, `while`, `if`/`else`,
`include`, rule registration (`rule <name> active`), and a large API
of engine-exposed `aiXxx`, `kbXxx`, `xsXxx`, `cmdXxx` functions. **No
first-party DE-specific reference grammar has been located**; the
[AOE3 MC AI guide](https://aoe3mc.github.io/ai-guide/getting-started/)
and shipped base AI scripts are the de-facto reference.

## File paths

- `game/ai/*.xs` — all AI scripts.
- `game/ai/*.personality` — registers personalities.
- Engine resolves `include "core/aiCore.xs";` relative to the AI
  working directory.

## Cross-references

- [Personality files](../data-layer/personalities.md) —
  `.personality` files dispatch into XS via `<script>`.
- [AI Personality picker](../ui-layer/ai-personality-picker.md) — UI
  surface for choosing an AI.
- [Engine merge dump](../validation/engine-merge-dump.md) — debug
  tokens relevant to AI (`+ixsLog`, `+cxsLog`).
- [Mod folder structure](../mod-folder-structure.md) — `game/ai/`
  placement.

## Tools

| Path | Purpose |
|---|---|
| [`tools/validation/validate_xs_scripts.py`](../../../tools/validation/validate_xs_scripts.py) | XS script structure / referenced symbols |
| [`tools/xs_sim/`](../../../tools/xs_sim/) | This repo's XS simulator |
| **Alt+Q in-game AI debugger** | Overlay; documented in AOE3 MC guide |
| `DebugOutputGameData` / `+ixsLog` / `+cxsLog` | Debug tokens — see [engine merge dump](../validation/engine-merge-dump.md) |
| Resource Manager | XS syntax-highlight in its file previewer |

## Known issues / DE-specific behaviour

- **XS step-debugger is community-reported as broken** since vanilla
  AoE3 / TAD. No authoritative confirmation it works on DE. Source:
  [HeavenGames thread "debugging AI xs scripts"](https://aoe3.heavengames.com/cgi-bin/forums/display.cgi?action=st&fn=14&tn=34187).
- **Alt+Q AI debugger overlay** does work on DE — documented in the
  AOE3 MC AI guide.
- **`xsEffectAmount(cEffectTypeLog, ...)` / log-marker functions**:
  function exists per
  [forum reference](https://forums.ageofempires.com/t/xs-debugger-is-not-reading-the-xs-ai-script/261360);
  the specific `cEffectTypeLog` constant is not authoritatively
  documented.
- **AI scripting at scale is hard.** Wars of Liberty community
  admission:
  > "Many AI do not work due to all different ways civilizations can
  > age up, and AI scripting is incredibly time consuming and
  > difficult ... Aoe3 had poorly optimized AI code, and the script
  > in which it is written isn't flexible."
- **Per-civ AI ownership** is the dominant cost in any multi-civ mod.
  See [multi-civ architecture](../multi-civ-architecture.md).

## Open questions

- A complete first-party reference for the DE-supported subset of the
  XS API.
- Whether DE removed or added any `aiXxx`/`kbXxx`/`xsXxx` functions vs
  legacy AoE3.
- Whether `xsEffectAmount(cEffectTypeLog, ...)` log markers are
  reliably visible in DE, and the format of the resulting log file.
- Whether the engine still respects pre-DE compile errors or fails
  open.

## Sources

- [AOE3 Modding Council AI guide](https://aoe3mc.github.io/ai-guide/getting-started/) (community-canonical).
- [HeavenGames XS debugger status thread](https://aoe3.heavengames.com/cgi-bin/forums/display.cgi?action=st&fn=14&tn=34187).
- [forums.ageofempires.com — DE XS debugger thread](https://forums.ageofempires.com/t/xs-debugger-is-not-reading-the-xs-ai-script/261360).
- [thinotmandresy/wol-maori-ai](https://github.com/thinotmandresy/wol-maori-ai) — open-source AoE3 AI mod.
- This repo: `game/ai/aiMain.xs`, `aiHeader.xs`, `aiLoaderStandard.xs`.
