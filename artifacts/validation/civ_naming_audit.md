# AOE3 ANW Civ Naming Audit

**Date:** 2026-05-30  
**Status:** Audit only — no changes made

---

## 1. Quantitative Summary

| Pattern | Count |
|---------|-------|
| `FrenchCanadians` | 0 |
| `ANWFrenchCanadians` | 0 |
| `LowerCanada` (all variants) | 0 |
| `ANWCanadians` | 1,813+ references |

**Conclusion:** The codebase uses **ANWCanadians** exclusively. There are zero references to LowerCanada or FrenchCanadians anywhere in source XML, XS, or JSON files.

---

## 2. File Inventory

Core files referencing ANWCanadians / Canadians (5 files):
- `/data/civmods.xml` — Main civ registration; `displaynameid=494005` ("Province of Canada")
- `/data/anwhomecitycanadians.xml` — Home city definitions
- `/data/playercolors.xml` — Player color assignments
- `/data/randomnamemods.xml` — Name generator mods
- `/data/techtreemods.xml` — Tech tree overrides

String definitions:
- `/data/strings/english/stringmods.xml` — Contains display strings + flavor text

---

## 3. In-Game Display Name

**Code identifier:** `ANWCanadians`  
**Display name ID:** `494005`  
**Actual label:** "Province of Canada"  
**Hero leader:** Isaac Brock (string ID 490254)  
**Flavor text:** "The Canadians field a doctrine of frontier militia, Indigenous alliances, early aggressive action..." (string ID 400005)

**Also defined but unused:**
- String ID 494006 = "Lower Canada" (exists in stringmods.xml but not wired to any civ)

---

## 4. Why "Province of Canada"?

The civ is historically anchored on Isaac Brock (1769–1812) and the War of 1812, making it **Upper Canada** / British North America, not Lower Canada (which was French-majority Quebec). The current "Province of Canada" label is accurate to the 1841–1867 union after Brock's era. "Lower Canada" string 494006 appears to be legacy text (perhaps from an earlier French-Canadian civ concept that was never implemented).

---

## 5. Recommendation Matrix

| Option | Effort | Compatibility | Notes |
|--------|--------|---------------|-------|
| **(A) Keep as-is** | Zero | Perfect | Current state is consistent: ANWCanadians, display "Province of Canada", Brock hero, accurate to War of 1812 lore. |
| **(B) Rename to ANWLowerCanada** | ~500 lines touched | Breaks saves | Would require changes to: civmods.xml, homecity, techtree, randomnames, AI references. Determinism unaffected. Saves from before rename will fail to load ANWCanadians (mod breakage). |
| **(C) Display-only rename** | ~2 lines | Perfect | Change string 494005 from "Province of Canada" to "Lower Canada" only. Keeps code identifier ANWCanadians. Minimal risk. |

---

## 6. Risk Assessment

**Option A (status quo):**
- Risk: None. No changes = no breakage.
- User confusion: "We only use Lower Canada?" is a misunderstanding; the civ is Canadians (Brock's Upper Canada / British North America).

**Option B (full rename to ANWLowerCanada):**
- Risk: **High.** Breaks all saved games from before the rename. Would require a save-file migration tool or major version bump.
- Impact: ~5 XML files + ~40+ line changes across civ setup.
- Determinism: Unaffected (rename is cosmetic at runtime; internal civ token changes are deterministic).
- User communication: Would need to explain why Lower Canada (French-majority, Patriote Rebellion) is tied to Isaac Brock (Upper Canada, War of 1812 hero). Historical mismatch.

**Option C (display-name-only rename to "Lower Canada"):**
- Risk: **Minimal.** Cosmetic string change; no save-game impact.
- Impact: 1 line in stringmods.xml (change 494005 value).
- Determinism: Unaffected.
- Trade-off: User sees "Lower Canada" on diplomacy panel, but hero remains Brock. Potential confusion (Brock was Upper Canada hero, not Lower Canada).

---

## 7. Recommendation

**Keep Option A (status quo).** The civ is correctly wired as ANWCanadians with display name "Province of Canada" and hero Isaac Brock. There is no "LowerCanada" variant in the repo—the user's impression is incorrect. The unused string 494006 ("Lower Canada") is legacy dead code that can be safely ignored or removed in a cleanup pass.

If the user intended to ask about **whether** to create a separate Lower Canada civ (French-majority Quebec), that would be a new feature, not a rename. The current civ covers 1812 British North America adequately.
