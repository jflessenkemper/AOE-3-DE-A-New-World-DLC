# `_test_template.age3Yscn` — Body Rejection Forensics

*Generated 2026-05-13 by binary diff of decompressed bodies.*

---

## Files compared

| File | Compressed | Body (decompressed) |
|------|-----------|---------------------|
| `Bombard_Brawl.age3Yscn` (loads cleanly) | 369 942 B | 8 275 691 B |
| `_test_template.age3Yscn` (rejected: "INVALID FILE") | 160 246 B | 2 636 786 B |

---

## 1. Version field comparison (`body[6:10]`)

| File | BG version (body[6:10]) | J1 section version | BP record version |
|------|------------------------|--------------------|-------------------|
| BB (loads) | **54** (0x00000036) | 310 | 0xac (172) |
| TMPL (rejected) | **105** (0x00000069) | 338 | 0xfc (252) |
| Stock install max | **103** | 324 | 0xd5 (213) |

The template's BG version (105), J1 version (338), and BP record version (252) are ALL above the
highest values found in any of the 79 stock `.age3Yscn` files in the AoE3 DE install.

---

## 2. Body length comparison

- BB body: 8 275 691 bytes (0x7e46eb)
- TMPL body: 2 636 786 bytes (0x283bf2)

Size difference alone is expected (TMPL is a stripped template), but the version fields are not.

---

## 3. First-128-bytes diff

The first 128 bytes differ only in:

| Offset | Field | BB value | TMPL value |
|--------|-------|----------|------------|
| `[0002:0006]` | `inner_size` (u32 LE) | `0x007e46e4` | `0x00283beb` | (expected — different bodies) |
| **`[0006:000a]`** | **BG version (u32 LE)** | **54 (0x36)** | **105 (0x69)** | **KEY DIFF** |
| `[000c:000e]` | FH sub-record size | 265 | 157 | (different build string) |
| `[0010:]` | FH payload (editor build string UTF-16) | `AoE3DE_s_Test.exe 131129` | `AoE3DE_s.exe 386756` | (different editor build) |

The FH (file-header) build string reveals the origin:

- **BB**: `AoE3DE_s_Test.exe 131129 //stream/Age3/Latest-WithoutBuiltBinaries`
  → edited with an internal AoE3DE test/editor build
- **TMPL**: `AoE3DE_s.exe 386756 //stream/Age3/Age3-BuildFarm-Stable`
  → saved with build 386756, a newer retail build that writes format version 105

---

## 4. Section tag survey

Both bodies have exactly the same top-level section tags in the same order:

`FH GT SF SH CP TN PV VV CV BA CH R3 SM TR J1 CT CM PI SR AS`

**No tags present in BB but missing from TMPL, and vice versa.**
Tag presence is not the rejection cause.

### Section payload differences (notable)

| Tag | BB value/size | TMPL value/size | Notes |
|-----|--------------|----------------|-------|
| `FH` | size=265 | size=157 | Editor build string differs (see §3) |
| `GT` | size=9, player_count=7 | size=15, player_count=5 | Active player count differs |
| `TR` | size=120 338 | size=50 | BB has 9 real triggers; TMPL has 9 stub triggers |
| `J1` | size=8 025 016, ver=310 | size=2 001 759, ver=**338** | Map/world data; TMPL ver 14 above stock max |
| `CT` | size=371, has camera tracks (`Track_1`, `Track_2`) | size=25, all zeros after u32[0:2] | BB has live cinematic camera data; TMPL stub has none |
| `CV` | u32=1 | u32=2 | Camera version field differs |
| `SM` | size=52 | size=64 | Sky/map metadata size differs |

---

## 5. BP / player table comparison

Both files have exactly **9 BP records** (1 Gaia + 8 player slots). All 9 are present in both.

### BP record version

- BB: `0xac` (172) — within stock install range (max 0xd5 = 213)
- **TMPL: `0xfc` (252) — 39 above the highest BP version ever seen in any stock scenario**

### P5 `mid_flags[0:4]` (slot-active field)

The `BB_BODY_STRUCTURE.md` documents that player slots must carry `0xffffffff` (-1) here:

| Slot | BB mid[0:4] | TMPL mid[0:4] | Status |
|------|-------------|---------------|--------|
| 0 (Gaia) | `01000000` (+1) | `01000000` (+1) | match |
| 1..8 (players) | `ffffffff` (-1) | **`01000000` (+1)** | **MISMATCH** |

The TMPL carries the Gaia sentinel value (`+1`) in all 8 player slots instead of `-1`.
This means all player slots look inactive/Gaia to the engine.

### P5 tail length

- BB player slots: 26–66 bytes (contains per-slot state including additional sub-structure)
- TMPL player slots: 18 bytes (minimum — missing the extra block that BB's AI slots carry)

### BP version profile matches `QuickSavegame`

The user-data area contains `QuickSavegame.age3Yscn` (BG=105, J1=338, BP=0xfc) with an
identical version profile to `_test_template`. Quick-saves are written by the engine at runtime,
not the Scenario Editor. This strongly suggests **`_test_template` was created by launching a
game and quick-saving, not by saving from the Scenario Editor**. Scenario-editor files have BG≤103
and BP≤0xd5 in the full stock corpus.

---

## Conclusion — Most Likely Rejection Cause

The engine's Custom Scenario load-gate almost certainly enforces a **maximum supported BG version**
(the u32 at `body[6:10]`). The entire stock scenario corpus has BG ≤ 103; `_test_template` carries
BG = **105**, which is 2 above the in-install maximum.

The same over-range applies to J1 (338 vs stock max 324) and BP record version (0xfc = 252 vs
stock max 0xd5 = 213).

**Primary suspect: `body[6:10]` = 105 is above the engine's version ceiling.**

The engine almost certainly reads this field first, finds it newer than any scenario it knows
how to parse, and rejects the file immediately with "INVALID FILE" — without ever reading the BP
table or the CRC32 trailer.

### Secondary / corroborating defects (would also cause rejection even if version were fixed)

1. **P5 `mid_flags[0:4]` = `+1` on all player slots** (body offsets ~0x0027_9ef0 through
   0x0028_1930 in the P5 payloads). All 8 player slots carry the Gaia-sentinel value instead of
   the required `-1`. This makes them appear as additional Gaia slots, which is a structural
   corruption the engine may validate independently of the version check.

2. **`_test_template` is a quick-save, not a scenario file.** Its version fingerprint
   (BG=105, J1=338, BP=0xfc) is identical to `QuickSavegame.age3Yscn`. The engine's Custom
   Scenario picker may additionally gate on file type (scenario vs. save), and these version
   numbers may be the signal it uses to distinguish them.

### Fix

**Use `Bombard_Brawl.age3Yscn` as the carrier for all emitted scenarios** — it has the
correct version profile (BG=54, J1=310, BP=0xac) that falls squarely within the stock scenario
corpus. The `scenario_emitter.py` `find_default_carrier()` function already does this.

Do NOT attempt to patch `body[6:10]` in `_test_template` from 105 to 54: the J1 and BP inner
data were serialised by a different format version and downgrading just the top-level tag would
produce a mismatch that may corrupt map parsing further into the load. The safest path is to
discard `_test_template` entirely and always derive new scenarios from `Bombard_Brawl.age3Yscn`.
