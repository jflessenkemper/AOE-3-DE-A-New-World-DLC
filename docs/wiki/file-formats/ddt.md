# DDT texture format

> Ensemble's runtime texture format. `RTS3` magic, formats 1/4/8 (BGRA32
> / DXT1 / DXT3), per-mipmap data with power-of-two dimensions.

## Format

Authoritative quote (HeavenGames AoE3Ed forum):

> "The four numbers in brackets are '(usage, alpha, format, levels)',
> where 'format' is: 1 = uncompressed 32-bit-per-pixel BGRA, 4 = DXT1
> compressed with 1-bit alpha channel, or 8 = DXT3 compressed."

> "dimensions must be multiples of 4 ... the game requires power-of-two
> sizes."

Header (community-reconstructed, consistent across AoE3Ed, the Kangcliff
Photoshop plugin, and Resource Manager):

| Field | Type | Description |
|---|---|---|
| magic | char[4] | `RTS3` |
| usage | uint8 | engine-side usage flag (UI / terrain / model / etc.) |
| alpha | uint8 | alpha presence/encoding |
| format | uint8 | `1` = BGRA32 uncompressed, `4` = DXT1+1-bit alpha, `8` = DXT3 |
| levels | uint8 | mipmap level count (>= 1) |
| width | uint32 | top-level mip width (power-of-two) |
| height | uint32 | top-level mip height |
| per-level offset+size table | (uint32, uint32) x levels | byte offset and size of each mipmap |
| pixel data | bytes | concatenated mipmap blocks |

Format-by-format payload:

- **format 1 (BGRA32)**: width x height x 4 bytes per mip.
- **format 4 (DXT1+1-bit alpha)**: standard DXT1 4x4 block compression,
  8 bytes per block.
- **format 8 (DXT3)**: standard DXT3 4x4 block compression, 16 bytes per
  block (explicit alpha).

## File path conventions

- Inside base `.bar`s: `art\...`, `ui\...`, `objects\flags\...`.
- Mod overrides at the same path under `art/` shadow base files
  (filename-override technique). HeavenGames "Adding A Custom Flag":
  > "Basically we're just telling the engine to use a different texture
  > for a predetermined file name that's already in the game."
- DE-era WPF PNG fields bypass DDT entirely and reference
  `resources/images/...png` paths instead.

## Cross-references

- [Flag rendering](../ui-layer/flag-rendering.md) — sprite-sheet + UV
  coords usage.
- [Portrait rendering](../ui-layer/portrait-rendering.md) —
  `cpai_avatar_*` portrait paths.
- [BAR archives](bar.md) — DDTs ship inside BARs.
- [SELECT CIVILIZATION picker](../ui-layer/select-civilization.md) and
  [SELECT HOME CITY picker](../ui-layer/select-home-city.md) — DDT refs
  via `<bannertexture>`, `<smallportraittexture>`, etc.

## Tools

| Path | Purpose |
|---|---|
| [`tools/cardextract/png_to_ddt.py`](../../../tools/cardextract/png_to_ddt.py) | This repo's PNG -> DDT converter |
| **Resource Manager** ([github](https://github.com/eBaeza/Resource-Manager)) | DDT <-> PNG, DDT <-> TGA. Recommended for DE |
| **Kangcliff DDT Photoshop plugin** ([HG download](https://aoe3.heavengames.com/downloads/showfile.php?fileid=3775)) | Direct save-as-DDT in Photoshop, MIP generation |
| **AoE3Ed** (Ykkrosh, legacy) | DDT viewer/editor for legacy AoE3 only |

## Known issues

- **Non-power-of-two textures fail to load** or render corrupted.
- **MIP quality varies by tool.** Kangcliff plugin generates better MIPs
  than AoE3Ed and the original game per its release notes; sharpness
  must be adjusted per resolution.
- **Format choice affects alpha fidelity.** DXT1+1-bit alpha produces
  hard edges; DXT3 (format 8) is safer for UI sprites with smooth alpha.
- **Sprite-sheet UV coords** must match the actual top-mip resolution.
  Replacing a banner DDT at higher resolution without updating
  `<bannertexturecoords>` crops wrong.

## Open questions

- The full set of valid `usage` byte values and engine semantics. Tools
  generally pass it through unchanged.
- Whether DE introduced any DDT format codes beyond 1/4/8.
- Exact alpha-flag semantics for combinations like (alpha=1, format=4).
- Whether the engine validates the per-level offset/size table.

## Sources

- HeavenGames forum: [thread 30356](http://aoe3.heavengames.com/cgi-bin/forums/display.cgi?action=ct&f=14,30356,,10) (format quote).
- HeavenGames forum: [thread 39229](https://aoe3.heavengames.com/cgi-bin/forums/display.cgi?action=ct&f=14,39229,,10) (extended discussion).
- [Kangcliff DDT Photoshop plugin](https://aoe3.heavengames.com/downloads/showfile.php?fileid=3775).
- [Resource Manager README](https://github.com/eBaeza/Resource-Manager/blob/master/README.md).
