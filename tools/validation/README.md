# AoE3 DE Scenario Analysis Tools

## Reports

### stock_scenario_survey.md
Comprehensive binary analysis of all 79 AoE3 DE stock vanilla scenario files (`.age3Yscn`).

**Contents:**
- Full scenario table with 9 columns of metadata (file size, body version, BP records, etc.)
- Top 5 simplest scenarios ranked for use as custom multi-civ test templates
- Statistical summaries (file sizes, version distribution, BP record ranges)
- Binary structure documentation
- Recommendations for building custom test scenarios

**Best Candidate for Custom Test Scenario:**
- `Campaign/Wonders/age3yic4a.age3Yscn` (80 KB, 9 BP records, no .xs files)

**Key Finding:**
All 79 scenarios have NO associated `.xs` (script) files — all event/logic data is embedded in the binary body using the BP record system.

## Usage

To use the simplest scenario as a base for custom test maps:
1. Copy `age3yic4a.age3Yscn` to your mod working directory
2. Extract and modify binary content (requires `age3Yscn` format parser)
3. Adjust entity placement, civilizations, and victory conditions as needed
4. Re-compress with zlib and update header fields

## Analysis Methodology

**Tools:** Python 3 with struct, zlib, hashlib modules
**Analysis Scope:** 79 files, ~1.1 GB total
**Metrics Extracted:**
- Binary header and outer u32 value
- zlib decompression (all successful)
- Body version field (offset 6-10)
- BP record count (b'BP' byte sequence)
- SHA256 checksums
- File size and decompressed size
- Associated script file detection

**Results:** All 79 scenarios analyzed, 100% successful decompression
