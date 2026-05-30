# Engine merge dump (`DebugOutputGameData`)

> The engine-blessed way to verify what the additive merge actually
> produced. A `user.cfg` token that dumps the post-merge XML tree
> (civs, techtree, proto, stringtable) to a Temp directory.

## How to enable

Add `DebugOutputGameData` to your `user.cfg`:

```
<install>/Games/Age of Empires 3 DE/<id>/Startup/user.cfg
```

Authoritative description ([Microsoft Additive Data Mods](https://support.ageofempires.com/hc/en-us/articles/360062106732-Additive-Data-Mods)):

> The engine dumps the post-merge data tree to
> `Temp\Age of Empires 3 DE\Data\...` (merged `civs.xml`, `techtree.xml`,
> `proto.xml`, per-language `stringtable.xml`, etc.).

Output is human-readable XML, diff-friendly.

## Other useful debug tokens

| Token | Purpose | Status |
|---|---|---|
| `DebugOutputGameData` | Dump merged data tree | Microsoft-documented; works on DE |
| `developer` | In-game developer overlay / extended debug menus | Community-observed; DE support unclear |
| `+ixsLog` | Verbose XS interpreter logging | Community-observed; output destination not authoritatively documented |
| `+cxsLog` | Compiled-XS / XS-compiler logging | Community-observed; same caveats as `+ixsLog` |
| Alt+Q (in-game) | AI debugger overlay (plan state, attack-manager queues) | AOE3 MC guide; works on DE |

The `xsEffectAmount(cEffectTypeLog, ...)` XS function prints a marker
into the XS log from inside an AI script. Forum reference:
[XS debugger is not reading the XS AI script](https://forums.ageofempires.com/t/xs-debugger-is-not-reading-the-xs-ai-script/261360).
The specific `cEffectTypeLog` constant value is not authoritatively
documented in searched sources.

## File paths

- Config file: `<install>\Startup\user.cfg`.
- Dump root: `<user-temp>\Age of Empires 3 DE\Data\...` (where
  `<user-temp>` is `%TEMP%` on Windows or the Proton-equivalent on
  Linux).

## Cross-references

- [Additive data mods](../additive-data-mods.md) — what
  `DebugOutputGameData` validates.
- [XS scripts](../ai-layer/xs-scripts.md) — `+ixsLog`, `+cxsLog`,
  log-marker calls.
- [stringmods.xml](../data-layer/stringmods.md) — known issue with
  stringmods not appearing in dump.
- [Static gate](static-gate.md) — offline validators that complement
  the engine dump.

## Tools that use the dump

| Path | Purpose |
|---|---|
| [`tools/validation/validate_engine_merged_xml.py`](../../../tools/validation/validate_engine_merged_xml.py) | Validates merged XML against expectations |
| Manual diff vs mod-source XML | The canonical post-merge validation pattern |

## Known issues

- **`DebugOutputGameData` does not always show stringmods.** Forum
  thread: [DebugOutputGameData not showing stringmods](https://forums.ageofempires.com/t/debugoutputgamedata-not-showing-stringmods/225246). Workarounds discussed include explicit `mergeMode` and matching element/attribute case.
- **XS step-debugger broken since vanilla AoE3 / TAD.** No DE
  confirmation.
- **`developer` token effect on DE binary is unclear** — community
  references exist but no DE-specific confirmation.

## Open questions

- Complete inventory of every legal token in DE's `user.cfg` parser.
- Exact log-file path/name written by `+ixsLog` / `+cxsLog`.
- Whether `developer` enables additional in-game cheats / overlays on
  DE.
- Authoritative format of the XS log file written by
  `xsEffectAmount(cEffectTypeLog, ...)`.
- Whether tokens are case-sensitive in `user.cfg`.

## Sources

- [Microsoft Additive Data Mods](https://support.ageofempires.com/hc/en-us/articles/360062106732-Additive-Data-Mods).
- [forums.ageofempires.com — DebugOutputGameData stringmods thread](https://forums.ageofempires.com/t/debugoutputgamedata-not-showing-stringmods/225246).
- [forums.ageofempires.com — DE XS debugger thread](https://forums.ageofempires.com/t/xs-debugger-is-not-reading-the-xs-ai-script/261360).
- [HeavenGames XS debugger status thread](https://aoe3.heavengames.com/cgi-bin/forums/display.cgi?action=st&fn=14&tn=34187).
- [AOE3 Modding Council AI guide](https://aoe3mc.github.io/ai-guide/getting-started/).
