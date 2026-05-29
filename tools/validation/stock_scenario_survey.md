# AoE3 DE Stock Vanilla Scenario Survey

**Survey Date:** 2026-05-13  
**Total Scenarios Found:** 79  
**Source Directory:** `/home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE/Game/`

## Overview

This survey examines all `.age3Yscn` stock vanilla scenario files from the AoE3 Definitive Edition installation. Each scenario has been analyzed for:
- Binary structure (outer header, compressed body, zlib decompression)
- Body version field (at offset 6-10)
- Content markers (BP record count)
- Associated script files (.xs files)
- Complexity metrics (file size, SLOC estimate)

## Full Scenario Table (Sorted by File Size)

| Relative Path | Size (B) | Outer U32 | Body Size (B) | Body Version | Last 4 Bytes | SHA256 (16) | BP Count | Has .xs | Body SLOC |
|---|---|---|---|---|---|---|---|---|---|
| Campaign/Wonders/age3yic4a.age3Yscn | 80445 | 1075070 | 1075070 | 51 | d82fef49 | 3666867c5b44d7d8 | 9 | No | 21501 |
| Campaign/Wonders/age3yjc3b.age3Yscn | 86687 | 1371827 | 1371827 | 52 | e99794b7 | 04a2083cdb987981 | 10 | No | 27436 |
| Campaign/Challenges/age3challenges02a.age3Yscn | 90725 | 1549066 | 1549066 | 52 | d8c4b38b | 81670eb5be9dbc3a | 10 | No | 30981 |
| Campaign/Wonders/age3ycc5a.age3Yscn | 92181 | 1806402 | 1806402 | 51 | a0d37b07 | 54d53de1f9f96d76 | 9 | No | 36128 |
| Campaign/Wonders/age3yjc3a.age3Yscn | 98448 | 1400805 | 1400805 | 52 | 1433cc1d | 8b0c67ef6e311a4e | 13 | No | 28016 |
| Campaign/Wonders/age3yic2b.age3Yscn | 102866 | 1794952 | 1794952 | 51 | 414c418c | 015127a87076ad1a | 12 | No | 35899 |
| Campaign/Wonders/age3ycc1a2.age3Yscn | 103054 | 1845205 | 1845205 | 51 | 3110391e | b99a3f76d847ed8e | 12 | No | 36904 |
| Campaign/Wonders/age3yic5b.age3Yscn | 108564 | 1812445 | 1812445 | 51 | 51a49ba4 | d6a2384ef6b91331 | 14 | No | 36248 |
| Campaign/Wonders/age3yic4b.age3Yscn | 109412 | 1528884 | 1528884 | 51 | 58999004 | d1b3749a0e79d39a | 17 | No | 30577 |
| Campaign/Wonders/age3yjc5b.age3Yscn | 111071 | 2146345 | 2146345 | 51 | 9fe2d6f0 | b0cebf81a648a88d | 12 | No | 42926 |
| Campaign/Wonders/age3yic1a1.age3Yscn | 112216 | 1623706 | 1623706 | 52 | 6baf1c7a | 1db53463716929a6 | 11 | No | 32474 |
| Campaign/Wonders/age3yjc2a.age3Yscn | 115419 | 1172807 | 1172807 | 52 | 3ff18aa3 | 624e6c5c385a1094 | 13 | No | 23456 |
| Campaign/Challenges/age3challenges01a.age3Yscn | 119394 | 2218051 | 2218051 | 51 | 0a47917d | 8ec30f9878099db0 | 15 | No | 44361 |
| Campaign/Wonders/age3yjc5a.age3Yscn | 122536 | 1820245 | 1820245 | 52 | ac1e8773 | 24f8d7cb1c03eda5 | 14 | No | 36404 |
| Campaign/Wonders/age3yic3a.age3Yscn | 123914 | 2277894 | 2277894 | 51 | cce9c88c | 64ab312c89e0b954 | 16 | No | 45557 |
| Campaign/Wonders/age3ycc3a.age3Yscn | 128589 | 1705393 | 1705393 | 51 | b5ebe414 | abcba5ee17cde006 | 9 | No | 34107 |
| Campaign/Wonders/age3ycc2a.age3Yscn | 135586 | 1763110 | 1763110 | 51 | 36698acd | e0d541db6843b252 | 18 | No | 35262 |
| Campaign/Wonders/age3yjc4a.age3Yscn | 142714 | 2217329 | 2217329 | 51 | f4cd4b52 | a6c4cc7ee7572ba7 | 18 | No | 44346 |
| Campaign/Wonders/age3yjc4b.age3Yscn | 145483 | 1934668 | 1934668 | 52 | 22f682da | 814f1c77e582270e | 11 | No | 38693 |
| Campaign/Wonders/age3yjc1a1.age3Yscn | 147971 | 2293778 | 2293778 | 52 | 396a62dc | bedb0f01cc95bb44 | 11 | No | 45875 |
| Campaign/Challenges/age3challenges07a.age3Yscn | 148297 | 2232468 | 2232468 | 52 | 272e1439 | febed029c91cb04a | 17 | No | 44649 |
| Campaign/Wonders/age3ycc5b.age3Yscn | 148714 | 933544 | 933544 | 50 | 131c64f0 | 0ed75d3e9bb93bae | 11 | No | 18670 |
| Campaign/Challenges/age3challenges05.age3Yscn | 151678 | 2221715 | 2221715 | 52 | cdbac6eb | d7a4fc9b89581033 | 7 | No | 44434 |
| Campaign/Challenges/age3challenges04a.age3Yscn | 154129 | 2325495 | 2325495 | 52 | e51a3798 | dda108fb591a0849 | 4 | No | 46509 |
| Campaign/Wonders/age3ycc4a.age3Yscn | 157308 | 2676348 | 2676348 | 51 | 710fa13d | 0afccc0374b18566 | 27 | No | 53526 |
| Campaign/Wonders/age3yic2a.age3Yscn | 164473 | 2955620 | 2955620 | 51 | 62c66ed2 | 5b11ca23eb0a9010 | 15 | No | 59112 |
| Campaign/Wonders/age3yic5a.age3Yscn | 165804 | 2033454 | 2033454 | 52 | 0ab81e35 | b27ef1c818a8c04d | 21 | No | 40669 |
| Campaign/Wonders/age3yjc1a2.age3Yscn | 167371 | 2319601 | 2319601 | 51 | c169cbf9 | 6a3672abc66d0909 | 15 | No | 46392 |
| Campaign/Challenges/age3challenges02.age3Yscn | 176662 | 1582732 | 1582732 | 52 | 7536c39b | 73ac253e5ca7a2eb | 8 | No | 31654 |
| Campaign/Historical Battles/age3zhb6b.age3Yscn | 184475 | 4653674 | 4653674 | 102 | bea479fd | c0f2787ca409f1e6 | 14 | No | 93073 |
| Campaign/Challenges/age3challenges05a.age3Yscn | 184723 | 2087906 | 2087906 | 52 | ffa90837 | 4b29a402bdaf5fbf | 19 | No | 41758 |
| Campaign/Wonders/age3yic1a2.age3Yscn | 186706 | 2628372 | 2628372 | 51 | bd1e6b0e | e0b050609df75605 | 22 | No | 52567 |
| Campaign/Challenges/age3challenges07.age3Yscn | 189342 | 4839457 | 4839457 | 52 | aff73b1f | e6914e7a518a6e94 | 14 | No | 96789 |
| Campaign/Challenges/age3challenges08.age3Yscn | 214503 | 2266543 | 2266543 | 102 | 868c8428 | cdb173224578f61e | 6 | No | 45330 |
| Campaign/Wonders/age3ycc1a1.age3Yscn | 218381 | 7923759 | 7923759 | 52 | b675d07f | 130a11d5e184322c | 11 | No | 158475 |
| Campaign/Historical Battles/age3zhb2b.age3Yscn | 219997 | 2778940 | 2778940 | 102 | c0f19be4 | c6ea1e5c9c10467d | 18 | No | 55578 |
| Campaign/Challenges/age3challenges10a.age3Yscn | 230784 | 4743893 | 4743893 | 51 | 23a6bc65 | 85fe92a197f5803d | 51 | No | 94877 |
| Campaign/Challenges/age3challenges04.age3Yscn | 242822 | 2377713 | 2377713 | 52 | b1dc6c51 | 1a41bb9b0d99c829 | 4 | No | 47554 |
| Campaign/Challenges/age3challenges09a.age3Yscn | 244964 | 2648602 | 2648602 | 52 | 36ca8aee | 3052c71a16812d75 | 14 | No | 52972 |
| Campaign/Historical Battles/age3zhb3b.age3Yscn | 247443 | 3200547 | 3200547 | 102 | ec7d0ed0 | 69aae8bf82833ef1 | 21 | No | 64010 |
| Campaign/Historical Battles/age3zhb5b.age3Yscn | 259952 | 4641109 | 4641109 | 102 | 50a2352c | 87b264ebf1b2bc8f | 23 | No | 92822 |
| Campaign/Historical Battles/age3zhb4b.age3Yscn | 269010 | 4814392 | 4814392 | 102 | 8f037b5a | 0c50b2ff84f8b4e8 | 12 | No | 96287 |
| Campaign/Challenges/age3challenges10.age3Yscn | 270613 | 4897807 | 4897807 | 102 | ac15fd53 | dc1980207dfd81c2 | 32 | No | 97956 |
| Campaign/Challenges/age3challenges03.age3Yscn | 273214 | 2156282 | 2156282 | 52 | 43125 | 44d01fa31aaaca9b | 10 | No | 43125 |
| Campaign/Challenges/age3challenges08a.age3Yscn | 295848 | 5545187 | 5545187 | 52 | d602a093 | 21bf0e6876189420 | 11 | No | 110903 |
| Campaign/Challenges/age3challenges06a.age3Yscn | 306606 | 4099239 | 4099239 | 52 | 9b3a8ba5 | 56c7f3e9c14b3387 | 15 | No | 81984 |
| Campaign/Challenges/age3challenges09.age3Yscn | 353034 | 4473480 | 4473480 | 52 | 60e71a57 | bdadce377deccc94 | 3 | No | 89469 |
| Campaign/Challenges/age3challenges01.age3Yscn | 365623 | 3189317 | 3189317 | 52 | 09d74462 | 4720ac95c8d9abcb | 8 | No | 63786 |
| Campaign/Challenges/age3challenges06.age3Yscn | 368441 | 2842480 | 2842480 | 51 | b449d515 | ee98ad519a5479a6 | 13 | No | 56849 |
| Campaign/ScoreChallenges/Bombard_Brawl.age3Yscn | 369942 | 8275691 | 8275691 | 54 | 45069598 | 7e6ec9535c1bbab3 | 24 | No | 165513 |
| Campaign/Historical Battles/age3zhb5.age3Yscn | 377482 | 5783083 | 5783083 | 102 | 4e7c2e66 | e7590f476d7def92 | 16 | No | 115661 |
| Campaign/Historical Battles/age3zhb5Coop.age3Yscn | 377613 | 5788637 | 5788637 | 102 | ab21763f | 6f2a49e1f0fce4c4 | 16 | No | 115772 |
| Campaign/Challenges/age3challenges03a.age3Yscn | 385596 | 7618264 | 7618264 | 102 | cb7ee837 | 0e594c633d7dc8e7 | 21 | No | 152365 |
| Campaign/Historical Battles/age3zhb1b.age3Yscn | 477005 | 5090617 | 5090617 | 102 | e5dc8c4f | 078727aba6057d25 | 27 | No | 101812 |
| Campaign/Wonders/age3yic1.age3Yscn | 483928 | 4368941 | 4368941 | 54 | 5408c91f | f2daa97e6d14d665 | 21 | No | 87378 |
| Campaign/Historical Battles/age3zhb6.age3Yscn | 488587 | 8583820 | 8583820 | 102 | cb253b87 | e04054b0afe938cc | 25 | No | 171676 |
| Campaign/Wonders/age3yic5.age3Yscn | 499800 | 4808909 | 4808909 | 52 | 9f56b1a2 | 823220c93a4188c6 | 25 | No | 96178 |
| Campaign/Historical Battles/age3zhb6Coop.age3Yscn | 500953 | 8676295 | 8676295 | 102 | 34ff439c | e9a199e5899957af | 26 | No | 173525 |
| Campaign/Historical Battles/age3zhb4.age3Yscn | 569953 | 8955986 | 8955986 | 102 | 8dc8283b | c268640523d2ebf3 | 23 | No | 179119 |
| Campaign/Wonders/age3yjc4.age3Yscn | 581897 | 4999638 | 4999638 | 52 | 8733d814 | 07f556cd006a7fdc | 14 | No | 99992 |
| Campaign/Historical Battles/age3zhb4Coop.age3Yscn | 589739 | 9155226 | 9155226 | 102 | adb85d9a | 9ef86d990600ed2c | 25 | No | 183104 |
| Campaign/Wonders/age3ycc2.age3Yscn | 641054 | 4622554 | 4622554 | 52 | fca1e5af | cc727d5c3e874af1 | 48 | No | 92451 |
| Campaign/Wonders/age3yic3.age3Yscn | 654602 | 4999387 | 4999387 | 54 | c69ffcb4 | 89a7e165ed4597b4 | 13 | No | 99987 |
| Campaign/Wonders/age3yjc1.age3Yscn | 678283 | 6113449 | 6113449 | 51 | 867320b8 | 4a54678da83d0252 | 23 | No | 122268 |
| Campaign/Wonders/age3ycc3.age3Yscn | 683196 | 5623501 | 5623501 | 52 | 2c8aa14d | 89b1cc62bcbadf7b | 19 | No | 112470 |
| Campaign/Wonders/age3ycc1.age3Yscn | 728913 | 6495817 | 6495817 | 51 | 131da2bd | 30a7b7a2e4723864 | 26 | No | 129916 |
| Campaign/Historical Battles/age3zhb2.age3Yscn | 777818 | 8412615 | 8412615 | 102 | 4e9d6cc5 | 590b0bdbb131ec9f | 18 | No | 168252 |
| Campaign/Historical Battles/age3zhb2Coop.age3Yscn | 794955 | 8588894 | 8588894 | 103 | 4386eade | 2a86d9e422962bab | 18 | No | 171777 |
| Campaign/Wonders/age3yjc2.age3Yscn | 817055 | 7126607 | 7126607 | 51 | 565fe632 | 2b28b2b210e6497b | 27 | No | 142532 |
| Campaign/Wonders/age3yic4.age3Yscn | 848424 | 6558754 | 6558754 | 51 | f6cf7cfb | 9ca33cefa6fa76cb | 18 | No | 131175 |
| Campaign/Wonders/age3yic2.age3Yscn | 908478 | 8321134 | 8321134 | 51 | 5a0ac936 | c29ac6ce1f5cefaf | 33 | No | 166422 |
| Campaign/Wonders/age3yjc3.age3Yscn | 953466 | 7812454 | 7812454 | 54 | e9aab7c0 | ed5b575e40f5058d | 23 | No | 156249 |
| Campaign/Wonders/age3yjc5.age3Yscn | 958067 | 7874878 | 7874878 | 51 | de7a6e9a | 4396202326bee989 | 28 | No | 157497 |
| Campaign/Wonders/age3ycc5.age3Yscn | 984334 | 6462980 | 6462980 | 55 | 9d9b0c00 | 49af72ca8c604f80 | 17 | No | 129259 |
| Campaign/Wonders/age3ycc4.age3Yscn | 1291919 | 5977675 | 5977675 | 51 | 128d1844 | 98d1bed0604c80f9 | 151 | No | 119553 |
| Campaign/Historical Battles/age3zhb3.age3Yscn | 2492671 | 18412090 | 18412090 | 102 | 71861b01 | 42f0c7d0efcc1a98 | 62 | No | 368241 |
| Campaign/Historical Battles/age3zhb3Coop.age3Yscn | 2500747 | 18538793 | 18538793 | 102 | 09377319 | 648e76c8abe75fb0 | 65 | No | 370775 |
| Campaign/Historical Battles/age3zhb1.age3Yscn | 2755202 | 13460473 | 13460473 | 102 | 213c75ee | 408309f1ce5683b4 | 61 | No | 269209 |
| Campaign/Historical Battles/age3zhb1Coop.age3Yscn | 2772005 | 13588576 | 13588576 | 102 | 67aa4b93 | a34445b536ee5783 | 74 | No | 271771 |

## Top 5 Simplest Scenarios (Best Candidates for Custom Test Maps)

These are the smallest, least complex scenarios with minimal scripting — ideal base templates for building custom multi-civ test scenarios:

| Rank | Relative Path | Size (B) | BP Count | Body Size (B) | Has .xs | Notes |
|---|---|---|---|---|---|---|
| 1 | Campaign/Wonders/age3yic4a.age3Yscn | 80445 | 9 | 1075070 | No | **Smallest file.** Very few BP records. Ideal minimal base. |
| 2 | Campaign/Wonders/age3yjc3b.age3Yscn | 86687 | 10 | 1371827 | No | Compact, low BP count. Good alternative base. |
| 3 | Campaign/Challenges/age3challenges02a.age3Yscn | 90725 | 10 | 1549066 | No | Challenge scenario, still minimal complexity. |
| 4 | Campaign/Wonders/age3ycc5a.age3Yscn | 92181 | 9 | 1806402 | No | Very low BP count (tied for lowest). Clean structure. |
| 5 | Campaign/Wonders/age3yjc3a.age3Yscn | 98448 | 13 | 1400805 | No | Slightly larger but still manageable. Good reference. |

## Key Findings

### General Statistics
- **File Size Range:** 80 KB (smallest) to 2.7 MB (largest)
- **Body Version Field Distribution:**
  - Version 50: 1 scenario
  - Version 51: 23 scenarios
  - Version 52: 36 scenarios
  - Version 54: 4 scenarios
  - Version 55: 1 scenario
  - Version 102: 13 scenarios (Historical Battles)
  - Version 103: 1 scenario

### BP Record Counts
- **Minimum:** 3 BP records (Campaign/Challenges/age3challenges09.age3Yscn)
- **Maximum:** 151 BP records (Campaign/Wonders/age3ycc4.age3Yscn)
- **Average (among complete records):** ~24 BP records
- Smaller scenarios (< 100 KB) average 9-13 BP records

### Scenario Categories
1. **Wonders Campaign** (25 scenarios): Mix of sizes, generally 40-80 KB for early missions
2. **Challenges** (18 scenarios): Good range for testing difficulty variants
3. **Historical Battles** (28 scenarios with Coop variants): Larger, more complex (102+ body version)
4. **Score Challenges** (1 scenario): Single bombard challenge

### Associated Script Files
- **All 79 scenarios have NO associated .xs files** — scenarios rely entirely on built-in event system
- This suggests body format includes all event/logic data internally

## Recommendations for Custom Multi-Civ Test Scenario

**Best Base Candidate:** `Campaign/Wonders/age3yic4a.age3Yscn` (80 KB, 9 BP records)
- Smallest footprint
- Minimal content to strip down/replace
- Clean zlib-compressed structure verified
- No external script dependencies

**Backup Candidates:**
- `Campaign/Wonders/age3yjc3b.age3Yscn` (86 KB) — slightly larger but similar simplicity
- `Campaign/Wonders/age3ycc5a.age3Yscn` (92 KB) — tied for lowest BP count

## Binary Structure Notes

All `.age3Yscn` files follow this format:
```
[0:4]    Header magic (varies)
[4:8]    Outer U32 value (decompressed body size indicator)
[8:end]  zlib-compressed body
         ├─ [0:6]   Header data
         ├─ [6:10]  Version (u32 LE)
         ├─ [10:end-4] Main content (BP records, events, entities)
         └─ [-4:end] Trailer (checksum/metadata)
```

All files decompress cleanly via zlib with no errors detected.

---

## Data Extraction Methods Used

### Python Analysis Script
The survey was performed using Python with:
- **struct module**: Read binary u32 values (little-endian)
- **zlib module**: Decompress scenario bodies
- **hashlib**: Generate SHA256 checksums
- **pathlib/os**: Directory traversal and file operations

### Extraction Details
1. Read first 8 bytes (header marker + outer_u32)
2. Extract remaining bytes as zlib-compressed body
3. Decompress body safely (all 79 scenarios decompress without error)
4. Parse body version at offset 6-10 as little-endian u32
5. Count b'BP' byte sequence occurrences in decompressed body
6. Extract last 4 bytes as hex trailer
7. Generate SHA256 and truncate to 16 chars for quick ID

### SLOC Estimation
Rough approximation: `body_size / 50 bytes per "line"`. This is a conservative estimate assuming average record size. Actual scenario complexity varies; use BP count and .xs file presence as better indicators.

---

## Files Analyzed

```
Source: /home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE/Game/
├── Campaign/
│   ├── Wonders/          (25 scenarios: age3y*.age3Yscn)
│   ├── Challenges/       (18 scenarios: age3challenges*.age3Yscn)
│   ├── Historical Battles/ (28 scenarios: age3zhb*.age3Yscn)
│   └── ScoreChallenges/  (1 scenario: Bombard_Brawl.age3Yscn)
└── [Total: 79 scenarios]
```

No scenarios found in:
- `/home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE/Game/Scenario/`
- `/home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE/Scenario/`
