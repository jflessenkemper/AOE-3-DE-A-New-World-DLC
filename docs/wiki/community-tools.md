# Community tools

> The AoE3 DE modding community has a small but active tool set.
> Resource Manager (eBaeza) is the de-facto interface for DE
> BAR/XMB/DDT work; the Kangcliff DDT Photoshop plugin handles texture
> authoring. Legacy tools (AoE3Ed, NVIDIA-DDS pipeline) work for
> legacy AoE3 only — **not** for DE.

## Tools

### Resource Manager (eBaeza)

- Repo: [eBaeza/Resource-Manager](https://github.com/eBaeza/Resource-Manager).
- README quotes:
  > "Converting XML <-> JSON <-> XMB (both Legacy and DE)."
  > "Converting DDT -> PNG. Converting DDT <-> TGA."
  > "Create BAR archive from files and folders."
  > "Comparison of BAR archives."
  > "Syntax highlighting in previewing text files (xml, xs)."
  > "replaces the AoE3Ed Viewer developed by Ykkrosh, which does not
  > work for the Definitive Edition."
- Status: **community-canonical for DE**.

### AoE3Ed / AoE3Ed Viewer (Ykkrosh)

- Status: **legacy only** — does not work for DE.
- Useful for opening legacy AoE3 BARs / XMBs.

### DDT Photoshop plugin (Kangcliff)

- [HeavenGames downloads](https://aoe3.heavengames.com/downloads/showfile.php?fileid=3775).
- Quotes:
  > "With the plug-in, you no longer need AoE3Ed to convert DDT files."
  > "generates better MIP maps than both AoE3Ed and the original game"
  > "you need to adjust the sharpness depending on the resolution or
  > type of your texture."

### Replay tools

- [`@canyougiant/aoe3de-replay-parser`](https://www.npmjs.com/package/@canyougiant/aoe3de-replay-parser) (npm) — DE-specific replay parser.
- [ESOCommunity Replay Manager v0.07](https://forums.ageofempires.com/t/v-0-07-replay-manager-tool-to-viewing-age-of-empires-iii-definitive-edition-records/197220) — viewer.
- [AoE3:DE Replay Launcher](https://eso-community.net/viewtopic.php?t=22050) — cross-patch playback.

### Engine-blessed: `DebugOutputGameData`

See [engine merge dump](validation/engine-merge-dump.md). The only
Microsoft-documented validator — dumps the merged XML so a mod author
can diff intent vs. engine state.

### AOE3 Modding Council AI guide

- [aoe3mc.github.io/ai-guide](https://aoe3mc.github.io/ai-guide/getting-started/).
- Status: **community-canonical AI documentation**.

### AOE3-Modding-Council GitHub org

- [github.com/AOE3-Modding-Council](https://github.com/AOE3-Modding-Council)
  — org exists but had **zero public repositories** at the time of
  the `aoe3_mod_full_research.md` survey. Members include
  `KevinW1998` and `VladTheJunior`.

## What does NOT exist (publicly)

Authoritative finding from `aoe3_mod_full_research.md` §4:

- No CI/CD pattern for AoE3 DE mods — `aoenw/Hundred-Days` and
  `mandosrex/AoE3ImpMod_Base` show no GitHub Actions workflows.
- No third-party XML well-formedness / stringtable referential-integrity
  validator surfaced.
- No standalone scenario `.age3Yscn` parser surfaced.
- No first-party DE mod-validation tool from Microsoft.

ANW's [static gate](validation/static-gate.md) of ~80 Python
validators is its own response to these gaps; it is not a community
standard.

## Cross-references

- [BAR archives](file-formats/bar.md) — Resource Manager opens these.
- [XMB binary XML](file-formats/xmb.md) — Resource Manager XML/XMB.
- [DDT textures](file-formats/ddt.md) — Photoshop plugin / Resource
  Manager.
- [Engine merge dump](validation/engine-merge-dump.md) —
  `DebugOutputGameData`.
- [Replays / scenarios](replays-scenarios.md) — replay parsers.
- [Static gate](validation/static-gate.md) — this repo's offline
  validators.

## Open questions

- Whether any private mod-team has internal validators that have not
  been published.
- Whether the AOE3 Modding Council intends to publish additional
  tools/guides on its GitHub org.
- Whether Microsoft will ship a first-party mod-validation tool for
  DE.

## Sources

- [Resource Manager README](https://github.com/eBaeza/Resource-Manager/blob/master/README.md).
- [Kangcliff DDT Photoshop plugin](https://aoe3.heavengames.com/downloads/showfile.php?fileid=3775).
- [AOE3 Modding Council AI guide](https://aoe3mc.github.io/ai-guide/getting-started/).
- [AOE3-Modding-Council GitHub org](https://github.com/AOE3-Modding-Council).
- [`@canyougiant/aoe3de-replay-parser`](https://www.npmjs.com/package/@canyougiant/aoe3de-replay-parser).
