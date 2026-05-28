# FrenchCanadians vs LowerCanada — Repo Audit (Refreshed 2026-05-28)

## Summary
**No "FrenchCanadians" civ currently in playable rotation.** The mod shipped v1.0.0 (2026-05-20) with a single Canadian revolution: **"Canadians Brock Revolution"** (Isaac Brock leader). Historical references to Papineau and Lower Canada exist only in flavor text and validation logs. The user's "we're only using lower canada?" reflects seeing "Lower Canada" as the display string (locID 494006, stringmods.xml) — but Papineau/FrenchCanadians has been deprioritized in favor of the Brock variant. **Recommendation: Accept current state** — one Canadian revolution (Brock) is intentional design; if historical Papineau support is desired, that's a new feature request, not a naming cleanup.

---

## 1. Grep Counts (repo root, excluding .claude/worktrees and sound/)

| Token | Occurrences | Files |
|---|---|---|
| `ANWFrenchCanadians` (exact) | 120 | 68 |
| `ANWFrenchCanadians` + variants (case-insensitive) | 132 | 74 |
| `FrenchCanadians` (all case) | 138 | 78 |
| `LowerCanada` (exact) | 3 | 3 |
| `lowercanada` (case-insensitive) | 3 | 3 |

The 3 `LowerCanada` hits are in documentation only: `.llm/todo.md`, `MORNING_DEPLOY_BRIEF.md`, `tools/build_release_review_portal.py`.

Note: The high `FrenchCanadians` count (~138 across 78 files) is dominated by shared sound XML routing blocks (~47 sound files, 2 references each) — these are auto-generated civ-gate templates, not active game logic.

---

## Findings

### What Actually Exists
| Layer | Value | Location |
|---|---|---|
| **Playable revolution** | `Canadians Brock Revolution` | `playstyle_spec.json:363` |
| **Revolution leader** | Isaac Brock (War of 1812 general) | Same |
| **Player display name** | "Canadians" | Same |
| **Historical flavor blurb** | "Lower Canada was the French-speaking Catholic society..." | `data/strings/english/stringmods.xml:17` (locID 400012) |
| **Civ localization** | "Lower Canada" UI string (locID 494006) | `data/strings/english/stringmods.xml:1908` |
| **AI doctrine** | "Compact Fortified Core" (defensive, blockhouse infantry) | `playstyle_spec.json:366` |

### FrenchCanadians & Papineau Status
- **ANWFrenchCanadians** token: **LEGACY / DROPPED** — appears only in:
  - 48 art/sound XML files (game asset path templates, not active civs)
  - 2 reference/log files (`enriched_reference.json`, TIER2_SUMMARY.json)
  - `data/anw_civ_blurbs.json` (Papineau entry preserved for historical reference)
- **No active dispatch**: No entry in `leader_revolution_commanders.xs` for FrenchCanadians dispatch
- **No home city**: No `anwhomecityfrenchcanadians.xml` file (only `anwhomecitycanadians.xml` exists, legacy)
- **No playstyle_spec entry**: No variant with Papineau leader or "French Canadians" label

### "Lower Canada" in UI
- **locID 494006**: `<String _locID="494006">Lower Canada</String>` — a human-readable string that currently has **no active civ reference**.
- **Historical context**: Same locID family as flavor text (400012) mentioning "Lower Canada was the French-speaking Catholic society… 1837 Patriote uprising".
- **Papineau daguerreotype**: Mentioned in CHANGELOG.md as "confirmed" artwork, but associated civ is not in active rotation.

### Active 40-Civ Roster
`art_inventory.json` (built 2026-05-28) lists exactly **40 ANW civs**. `ANWFrenchCanadians` is **not in the 40-civ roster**. The active Canadian civ token is `ANWCanadians` (Brock). `ANWFrenchCanadians` is a legacy token that was never activated.

`hub_test_roster.json` (6-pass roster) confirms: Pass 1 includes "Canadians Brock Revolution", Pass 4 includes "French Louis XVIII Bourbon" — no `ANWFrenchCanadians` dispatch in any of the 6 passes.

### File Audit (Excluding `.git`, `artifacts`, `.claude`, `dev_subtrees`)
- **Sound files**: 48 .xml files reference `ANWFrenchCanadians` in audio event tags (unit-specific sound definitions, e.g., explorer_snds.xml)
- **Art files**: Church and explorer assets include model-selection branches for the civ token (unchanged since initial template generation)
- **Data references**: `anw_civ_blurbs.json`, `enriched_reference.json`, playtest logs
- **Total token mentions**: ~60–70 across the codebase, but none in active game-flow paths

---

## Historical Timeline (from changelog)
1. **v1.0.0 (2026-05-20)**: "40 playable ANW civilizations" listed Canadians (no "French" prefix). Papineau daguerreotype visually inspected and confirmed.
2. **Unreleased (2026-05-26)**: "Dropped Yucatan/Californians/CentralAmericans civs (no nation-card content)." No mention of Papineau/FrenchCanadians removal.
3. **Current (2026-05-28)**: Single playable Canadian variant: "Canadians Brock Revolution" (Isaac Brock, War of 1812 general).

---

## Why the Question?

The user likely observed:
1. **"Lower Canada" string in UI** (locID 494006) when inspecting localization
2. **"Papineau" references in flavor text** (stringmods.xml:17, anw_civ_blurbs.json)
3. **But no matching civ in playstyle_spec.json**
4. Concluded: "Are we using Papineau (FrenchCanadians) or Brock (Canadians)?"

**Answer**: Currently only Brock/Canadians is playable. Papineau and "Lower Canada" are historical references, not active civs.

---

## Recommendation

**Option A (Current / Status Quo)** — Accept one Canadian revolution  
- Keep "Canadians Brock Revolution" as the sole Canadian variant  
- Leave "Lower Canada" locID and Papineau flavor text as historical context (no harm)  
- Legacy `ANWFrenchCanadians` token in sound/art XMLs is harmless (art path template, not active dispatch)  
- **Cost**: None. **Risk**: Low.  

**Option B (Restore Papineau as second variant)**  
- Add "French Canadians Papineau Revolution" back to playstyle_spec.json with separate doctrine  
- Wire AI dispatch in `leader_revolution_commanders.xs` for `ANWFrenchCanadians`  
- Deduplicate "Lower Canada" string usage (currently orphaned locID 494006)  
- **Cost**: ~2–3 files edited, playstyle_spec entry, ~1–2 hours testing  
- **Risk**: Low (code path is straightforward).  

**Option C (Clean up legacy references)**  
- Delete `ANWFrenchCanadians` from all sound/art XMLs (cosmetic)  
- Remove Papineau entry from anw_civ_blurbs.json  
- Delete orphaned locID 494006  
- **Cost**: ~50 file edits (mostly XML batch regex), 30 minutes  
- **Risk**: Low (art path templates unused; locID can safely be deleted).  

**Recommendation: Choose A or B depending on whether 1 or 2 Canadian variants is desired.** C is unnecessary unless aiming for "zero dead code" standard (not critical for ship).

---

---

## 4. Map Roster Check

`RandMaps/anwHubTest.xs`: zero references to `ANWFrenchCanadians`. The overnight coverage lobby configs (`artifacts/overnight_coverage/20260512_235443/PASS0/C_lobby_cfg.json`) DO reference `ANWFrenchCanadians` as a tested AI slot — but this appears to be a stale test artifact predating the 40-civ finalization (those runs predate v1.0.0 on 2026-05-20). Current `hub_test_roster.json` does not include it.

---

## 5. Question for You

The in-game display string for the `ANWFrenchCanadians` token already reads **"Lower Canada"** (`locID 494006`, `stringmods.xml`), but this civ is not in the active 40-civ roster. `ANWFrenchCanadians` lives only in legacy sound/art routing templates and tooling scripts — it is effectively dead code. Do you want to: **(a)** leave the dead token as-is (zero effort, zero risk), **(b)** activate it as a second Canadian variant by wiring it into `playstyle_spec.json` and `leader_revolution_commanders.xs` with a Papineau leader doctrine, or **(c)** do a repo-wide token rename to `ANWLowerCanada` (78 files, ~50 of them sound XMLs)? Option (a) is the status quo; option (c) renames a legacy token that isn't loaded in-game, which is cosmetic and carries non-trivial regression risk in the sound routing tables.

---

*Audit refreshed 2026-05-28 with live grep counts (art_inventory.py run), hub_test_roster.json verification, and stringmods.xml confirmation.*
