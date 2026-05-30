# BAR archive format

> AoE3 DE bundles assets in `.bar` archives — file system in a single
> blob. ESPN magic, file table, alz4 compression for individual entries.

## Format

| Offset | Size | Field | Notes |
|---|---|---|---|
| 0 | 4 | Magic | `ESPN` (ASCII) |
| 4 | 4 | Version | uint32 LE — DE files are typically v6 |
| 8 | 4 | Unknown | uint32 |
| 12 | 264 | Reserved/path | string field |
| 276 | 4 | Number of files | uint32 LE |
| 280 | 4 | File table offset | uint32 LE |
| 284+ | … | File table entries | per-file metadata |

Each entry in the file table:
- offset (uint32) — where compressed data starts in the archive
- size_compressed (uint32)
- size_decompressed (uint32)
- size_extra (uint32) — alignment padding
- name (UTF-16-LE, length-prefixed) — `\` separators (Windows-style)
- is_compressed (bool)

## alz4 compression

Compressed entries wrap LZ4 in a custom 8-byte preamble:

| Offset | Size | Field |
|---|---|---|
| 0 | 4 | `alz4` magic |
| 4 | 4 | uncompressed size (uint32 LE) |
| 8+ | … | LZ4 block payload |

## Cross-references

- **[XMB](xmb.md)** — most XML inside `.bar` is XMB-encoded
- **[DDT](ddt.md)** — texture entries in art bars
- **[l33t](l33t.md)** — different wrapper used by replays/scenarios

## Tools

| Path | Purpose |
|---|---|
| [`tools/cardextract/bar.py`](../../../tools/cardextract/bar.py) | Pure-Python reader: `open_bar(path)` → `BarArchive`, `find()`, `read_payload()` |
| [`tools/cardextract/extract.py`](../../../tools/cardextract/extract.py) | CLI extractor |
| **eBaeza/Resource-Manager** ([github](https://github.com/eBaeza/Resource-Manager)) | Community-canonical GUI tool, supports BAR + XMB + DDT |

## Known issues

- BAR readers must handle path normalization (`\` → `/`) since file names are stored with Windows-style separators. Lookup APIs typically use `entry.normalized_name`.
- DE-era `.bar` files are version 6; legacy AoE3 could be 2/4/5.

## Open questions

> None significant — format is well-understood community-wide.

## Sources

- Reverse engineering: [eBaeza/Resource-Manager BarFile.cs](https://github.com/eBaeza/Resource-Manager) (MIT license, our `bar.py` is a Python port).
- DE compatibility verified by extracting `Game/Data/Data.bar` (this session, 2026-05-09).
