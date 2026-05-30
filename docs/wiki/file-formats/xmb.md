# XMB binary XML

> Binary XML format used by AoE3 DE for compiled XML assets inside
> `.bar` archives. Not human-readable. We have a pure-Python decoder.

## Format

Outer wrapper is either `alz4`-compressed or `L33T`-zip wrapped (depending
on context). The decompressed inner stream begins with `X1` magic.

| Offset | Size | Field |
|---|---|---|
| 0 | 2 | `X1` magic |
| 2 | 4 | Inner data length (uint32 LE) |
| 6 | 2 | `XR` marker |
| 8 | 4 | Unknown (typically `4`) |
| 12 | 4 | Version (`8` for DE) |

Then a string table (length-prefixed UTF-16LE strings) and the element
tree, encoded with element-name indices into the string table.

## Element encoding

Each element references the string table by index for its tag name.
Attributes are similarly indexed. Text content can be inline UTF-16LE
or a string-table reference.

## Cross-references

- **[BAR](bar.md)** — XMB files live inside .bar archives
- **[Civmods](../data-layer/civmods.md)** — base game `civs.xml` is XMB-encoded inside `Data.bar` and our mod's `civmods.xml` (plain XML) is merged into it at engine load
- **[Stringmods](../data-layer/stringmods.md)** — base game's `stringtabley.xml` is XMB-encoded; our mod ships plain XML

## Tools

| Path | Purpose |
|---|---|
| [`tools/cardextract/xmb.py`](../../../tools/cardextract/xmb.py) | Pure-Python decoder: `parse_xmb(bytes) -> ET.Element` |
| **eBaeza/Resource-Manager** | XML ↔ XMB conversion (legacy + DE) |

## Known issues

- XMB-decoded element/attribute names use whatever case the encoder produced. For DE, base-game files use **lowercase tag names** (`<civ>`, `<name>`, `<main>`). Mod XML files using Capital tags (`<Civ>`, `<Name>`) **don't merge correctly** — see [case-sensitivity pitfall](../modding-pitfalls/case-sensitivity.md).

## Open questions

> ⚠ OPEN: Is the element-tree encoding length-prefixed at each
> element, or recursive with explicit close markers? Our decoder
> handles real-world DE XMB but the spec hasn't been verified
> exhaustively against malformed input.

## Sources

- Reverse engineering: [eBaeza/Resource-Manager XmbFile.cs](https://github.com/eBaeza/Resource-Manager) (MIT). Our `xmb.py` is a Python port.
- DE version 8 verified by parsing `civs.xml.XMB`, `techtreey.xml.XMB`, and `stringtabley.xml.XMB` from `Data.bar` (this session, 2026-05-09).
