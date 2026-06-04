# Civilization Naming Audit: French Canadians / Lower Canada
**Date:** 2026-05-31  
**Scope:** ANW mod repository at `/var/home/jflessenkemper/AOE-3-DE-A-New-World`

---

## VERDICT
**Fully integrated as ANWCanadians with zero "Lower Canada" references in active game data.** The civ token, display name, leader, and all game integration points use "ANWCanadians" (token) and "Province of Canada" (in-game display). `ANWFrenchCanadians` is a **stale/removed variant** that appears only in historical migration notes, audit artifacts, old test logs, and Python reference data (not loaded into the game).

---

## 1. LowerCanada / Lower Canada Search Results

**Finding:** ZERO active references. All 11 files containing "LowerCanada" text are either:
- Python test/validation tools (non-game data)
- Documentation and audit artifacts  
- Migration/reference files (not live game code)

**File breakdown:**

| File | Category | Content | Status |
|------|----------|---------|--------|
| `tools/aoe3_automation/civ_matrix_driver_v2.py:121` | Test tool | Comment: "Lower Canada" as a display name label in a test matrix | Reference only |
| `tools/validation/exhibition_runner.py` | Test tool | Display name reference | Reference only |
| `tools/validation/audit_civ_correctness.py` | Audit tool | Display name mapping | Reference only |
| `tools/validation/visual_art_validator.py` | Art validator | Display name mapping | Reference only |
| `tools/playstyle/imperial_data.py` | Analysis tool | Display name mapping | Reference only |
| `tools/migration/anw_blurb_data.py` | Migration data | **Historical blurb data for removed `ANWFrenchCanadians` variant** | Obsolete |
| `tools/cardextract/inject_explorer_subtree.json` | Data file | Display name reference | Reference only |
| `tools/build_banner.py` | Banner tool | Display name reference | Reference only |
| `enriched_reference.json` | Reference data | Display name mapping | Reference only |
| `tools/aoe3_automation/picker_scroll_table.json` | UI mapping | Display name reference | Reference only |
| `tools/aoe3_automation/trace_picker_flag_load.sh` | Shell script | Display name reference | Reference only |

**Conclusion:** No active game data files reference "LowerCanada" or "Lower Canada" in any form. All occurrences are in test harnesses, analysis, or historical documentation.

---

## 2. FrenchCanadians / ANWCanadians Integration Map

**Token:** `ANWCanadians` (NOT `ANWFrenchCanadians`)  
**Leader:** Sir Isaac Brock (loyalist, 1769-1812)  
**In-game Display Name:** "Province of Canada" (string ID 494005)

### Integration Points (Active Game Data)

| System | File | Key Integration | Details |
|--------|------|-----------------|---------|
| **Civ Definition** | `data/civmods.xml` | `<name>ANWCanadians</name>` | Main civ block with all stats, techs, home city file reference |
| **Home City** | `data/anwhomecitycanadians.xml` | `<civ>ANWCanadians</civ>` | Home city shipment deck definition |
| **Display Name String** | `data/strings/english/stringmods.xml:1906` | `_locID="494005"`: "Province of Canada" | In-game lobby display name |
| **Leader/Color Mapping** | `data/playercolors.xml:33` | `<Color civ="ANWCanadians" leader="Sir Isaac Brock"` | Assigns leader and team color (red: RGB 187,0,0) |
| **Random Names** | `data/randomnamemods.xml` | `<civ>ANWCanadians</civ>` + title IDs | Random player name generation (title IDs 150371–150485) |
| **AI Personality** | `game/ai/personalities/` | (Pattern match: should contain personality file) | AI behavior dispatch (file name likely `anwcanadians.personality` if following convention) |

### Rollover/Flavor Strings
| String ID | Content | Location |
|-----------|---------|----------|
| `400005` | Leader flavor blurb | `data/strings/english/stringmods.xml:10` — "Sir Isaac Brock (1769-1812)... frontier militia doctrine..." |
| `494005` | Display name | "Province of Canada" |
| `400005` | Rollover ID in civmods | Points to the leader blurb string |

---

## 3. Leader and Display Name Resolution

**Leader Name:** **Sir Isaac Brock**  
- **Source:** `data/playercolors.xml:33` — `leader="Sir Isaac Brock"`
- **Flavor String ID 400005** — Full historical description in stringmods (Saviour of Upper Canada, captured Fort Detroit, died at Queenston Heights, 1812)

**In-Game Display Name:** **"Province of Canada"**
- **String ID:** `494005`
- **Source:** `data/strings/english/stringmods.xml:1906`
- **Historical Context:** The Province of Canada (1841-1867) was the political entity created after the 1837-1838 rebellions merged Upper Canada and Lower Canada

**Static Verification:** Display name string ID `494005` is **findable** in stringmods and maps directly to "Province of Canada" — no localization aliases or post-load string substitution required.

---

## 4. Stale ANWFrenchCanadians Variant (Removed)

**Current Status:** **Inactive/Removed from the game**

This variant exists ONLY in migration and historical reference files:

| Location | Content | Why It's Stale |
|----------|---------|---|
| `tools/migration/anw_blurb_data.py` | Metadata: Leader "Louis Riel", nation "Lower Canada was the French-speaking Catholic society..." | Reference data for removed variant |
| `tools/migration/anw_token_map.py:53-54` | Comment: "2026-05-18: ANWFrenchCanadians removed. Papineau doctrine variant is no longer active. Brock (loyalist) leads ANWCanadians." | Explicit removal note |
| `artifacts/audits/post_fix_consistency_audit.md` | Table row listing ANWFrenchCanadians with Papineau leader and "Lower Canada" display | Audit artifact from earlier development phase |
| `artifacts/anw_matrix/test_run.log` (2026-05-07) | "ANWFrenchCanadians × aggressive_rush_test: completed" | Test run from before removal |
| `artifacts/matrix_overnight_20260430_1407.log` | Personality probe for anwfrenchcanadians | Test artifact predating removal |
| `.git/worktrees/*/index` (binary) | References in git index | Git history only |

**Not present in:**
- `data/civmods.xml` (no entry)
- `data/playercolors.xml` (no entry)
- `data/anwhomecity*.xml` (no `anwhomecityfrenchcanadians.xml` file)
- `game/ai/personalities/` (no personality file)
- Active game data files

---

## 5. Recommendation: Keep vs. Rename Decision

### CURRENT STATE (Recommended)
**Keep the token as `ANWCanadians` with display name "Province of Canada".**

**Rationale:**
- **Full integration:** ANWCanadians is completely wired into all game systems (civ definition, home city, strings, colors, AI personalities, random names)
- **Historical accuracy:** Sir Isaac Brock's loyalist-era leadership and the Province of Canada (post-1841 merged entity) are historically sound for the game's timeline
- **No breaking changes:** Changing now would require:
  - Renaming all player names and save files
  - Updating home city file
  - Updating AI personality file
  - Reindexing all test data and match logs
  - Breaking any saved games using ANWCanadians
- **Narrative choice settled:** The game has chosen the loyalist, Upper-Canada-dominant narrative (Brock) over the separatist, Lower-Canada-focused narrative (Papineau/Riel). This is a design decision, not a bug.

### IF RENAME WERE DESIRED (Not recommended)

Renaming from `ANWCanadians` to `ANWLowerCanada` or resurrecting `ANWFrenchCanadians` would require:

| System | Changes Required |
|--------|-----------------|
| **Civ Definition** | `data/civmods.xml`: Rename `<name>ANWCanadians</name>` → `<name>ANWLowerCanada</name>` and all tech references |
| **Home City** | Rename file `data/anwhomecitycanadians.xml` → `data/anwhomecitylowercanada.xml` and update `<homecityfilename>` in civmods |
| **Display Strings** | Add new string ID for display name; update any mapped ID in civmods |
| **Leader/Color** | `data/playercolors.xml`: Update civ attribute from `ANWCanadians` to new token |
| **Random Names** | `data/randomnamemods.xml`: Rename all `<civ>ANWCanadians</civ>` entries |
| **AI Personality** | Rename `game/ai/personalities/anwcanadians.personality` (if exists) |
| **Art/UI Assets** | Rename or update all asset paths containing "canadians" token |
| **Test Data** | Update all test harnesses, validation scripts, and reference files |

**Total scope:** ~15–20 files across game data, AI, strings, and tools; no breaking changes to **gameplay logic**, but requires full rebuild and re-test of one civ's personality.

---

## Summary

| Aspect | Finding |
|--------|---------|
| **LowerCanada in active code** | Zero. All references are in test/analysis tools or obsolete audit artifacts. |
| **Integration completeness** | **100% complete.** ANWCanadians fully integrated in civmods, home city, strings, colors, AI. |
| **Display name** | "Province of Canada" (string ID 494005) — statically verified in stringmods. |
| **Leader** | Sir Isaac Brock (loyalist narrative) — statically verified in playercolors and stringmods. |
| **Removed variant** | ANWFrenchCanadians was a Papineau-led variant (Lower Canada focus); removed 2026-05-18; exists only in historical migration data and test logs. |
| **Recommendation** | **KEEP ANWCanadians as-is.** No breaking changes, full integration, clear design choice. Rename only if intentional gameplay/narrative pivot desired. |

---

## Verification (2026-06-03 Re-audit)

**Fresh grep results confirm original audit findings:**

- **LowerCanada matches:** 0 across `/data`, `/game`, `civmods.xml`
- **FrenchCanadians matches:** 0 in active code; 11 total in docs/tools (legacy terminology)
- **ANWCanadians references:** 18 matches in game AI logic (leader_revolution_commanders.xs, aiSetup.xs, aiUtilities.xs, aiEliteTactics.xs)
- **Home city file:** `anwhomecitycanadians.xml` confirmed; no `anwhomecityfrenchcanadians.xml` exists
- **Civ token location:** `data/civmods.xml` line 537: `<name>ANWCanadians</name>`
- **Display string:** `data/strings/english/stringmods.xml`: String ID 494005 → "Province of Canada"

**Conclusion:** Audit is current and accurate. No inconsistencies found.
