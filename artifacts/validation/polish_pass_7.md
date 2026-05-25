# Polish Pass 7 — Deep Static Audit
Generated 2026-05-26.

---

## Executive Summary

**6 new issues found** — none of these were flagged in passes 3, 4, 5, or 6.

| # | Severity | File | Civ | Category |
|---|----------|------|-----|----------|
| 1 | Medium | `data/anw_civ_blurbs.json` | ANWSwedes | Unique unit wrong name — "Horse Artillery" should be "Leather Cannon" |
| 2 | Medium | `data/anw_civ_blurbs.json` | ANWJapanese | Phantom building — "Buddhist Temple" does not exist in AoE3 DE |
| 3 | Low | `data/anw_civ_blurbs.json` | ANWJapanese | Phantom/duplicate building — "Shinto Shrine" is not a distinct engine building (engine name is "Shrine", already listed) |
| 4 | Medium | `data/anw_civ_blurbs.json` | ANWChinese | Phantom building — "Old Summer Palace" does not exist in AoE3 DE |
| 5 | Medium | `data/anw_civ_blurbs.json` | ANWMaltese | Wrong building name — "Sacre Infermeria" is not the engine name; real building is "Hospital" |
| 6 | High | `playstyle_spec.json` | Indians Akbar | Spec claim `expects_artillery: true` directly contradicts XS (`btBiasArt = -0.3` at Colonial; `btBiasCav = 0.75 → 1.0` = cavalry-dominant) |

---

## Per-Civ Findings

### Issue 1 — ANWSwedes: `unique_units` lists "Horse Artillery" instead of "Leather Cannon"

**File:** `data/anw_civ_blurbs.json` line 491 (the `ANWSwedes` `unique_units` array)

**Evidence:**
```json
"unique_units": ["Carolean", "Hakkapelit", "Horse Artillery"]
```

**The problem:** "Horse Artillery" (`xpHorseArtillery`) is the War Chiefs expansion unit, available to multiple civilizations via the `HCXPShipHorseArtillery2` card. It is not Swedish-unique. The Swedish-unique artillery is the **Leather Cannon** (`deLeatherCannon`), confirmed in:
- `game/ai/leaders/leader_gustavus.xs`: `btBiasArt = 0.75; // Leather Cannon as line element.`
- `data/anwhomecityswedes.xml`: five `DEHCShipLeatherCannons*` cards (Leather Cannon shipments)
- `data/cards.json`: `DEHCShipLeatherCannons2` → `"name": "5 Leather Cannons"`
- Base game string table: "Leather Cannon" confirmed as a Swedish unique unit

The `playstyle` tooltip (correctly updated in pass 6) already says "Leather Cannon artillery." The `unique_units` array contradicts it.

**Fix:** `data/anw_civ_blurbs.json`, `ANWSwedes.unique_units`: replace `"Horse Artillery"` with `"Leather Cannon"`.

---

### Issue 2 — ANWJapanese: "Buddhist Temple" is a phantom building

**File:** `data/anw_civ_blurbs.json`, `ANWJapanese.unique_buildings`

**Evidence:**
```json
"unique_buildings": ["Shrine", "Castle", "Buddhist Temple", "Shinto Shrine"]
```

**The problem:** "Buddhist Temple" does not exist in AoE3 DE. A full text search of:
- `artifacts/extracted_base_stringtable.xml` — "Buddhist" and "BuddhistTemple" have **zero hits**
- `data/techtreemods.xml` — zero hits
- `data/strings/english/stringmods.xml` — zero hits
- All home city XMLs — zero hits

The AoE3 DE base game lists Japanese unique buildings as: **Cherry Orchard, Dojo, Shrine** (per the in-game civ overview string). Japanese wonders are: Golden Pavilion, Great Buddha, The Shogunate, Torii Gates, Toshogu Shrine — none called "Buddhist Temple."

**Fix:** Remove `"Buddhist Temple"` from `ANWJapanese.unique_buildings`.

---

### Issue 3 — ANWJapanese: "Shinto Shrine" is a phantom / duplicate entry

**File:** `data/anw_civ_blurbs.json`, `ANWJapanese.unique_buildings`

**Evidence:**
```json
"unique_buildings": ["Shrine", "Castle", "Buddhist Temple", "Shinto Shrine"]
```

**The problem:** "Shinto Shrine" is not a distinct engine building. The engine proto name is simply `ypShrine`. It appears in the base game as "Shrine" — the same building already listed as the first entry in the array. "Shinto Shrine" never appears in `extracted_base_stringtable.xml` as a building name. This is either a duplicate listing of "Shrine" under a wrong display name, or a fabricated entry.

Additionally, "Castle" is not a Japanese-unique building. Castles are available to multiple Asian civs (Chinese, Indians also use them). The AoE3 DE Japanese civ overview explicitly lists unique buildings as "Cherry Orchard, Dojo, Shrine" — not Castle.

**Fix:** Remove `"Shinto Shrine"` from `ANWJapanese.unique_buildings`. Optionally also remove `"Castle"` (it is shared, not Japanese-unique) and add `"Dojo"` (confirmed Japanese-unique building).

---

### Issue 4 — ANWChinese: "Old Summer Palace" is a phantom building

**File:** `data/anw_civ_blurbs.json`, `ANWChinese.unique_buildings`

**Evidence:**
```json
"unique_buildings": ["Summer Palace", "Porcelain Tower", "Old Summer Palace"]
```

**The problem:** "Old Summer Palace" (Yuan Ming Yuan) does not exist as an AoE3 DE building. Full search results:
- `artifacts/extracted_base_stringtable.xml`: zero hits for "Old Summer Palace" or "OldSummerPalace" as a building name
- `data/techtreemods.xml`: zero hits
- `data/strings/english/stringmods.xml`: zero hits
- All home city XMLs: zero hits
- Only appearances in project: `anw_civ_blurbs.json` itself + derived visual audit HTML

The real Chinese age-up wonders (confirmed in base strings) are: Summer Palace, Porcelain Tower, Temple of Heaven, Confucian Academy. "Old Summer Palace" is not among them.

Note: "Summer Palace" and "Porcelain Tower" are valid Chinese wonders that DO exist. Only the third entry is phantom.

**Fix:** Remove `"Old Summer Palace"` from `ANWChinese.unique_buildings`.

---

### Issue 5 — ANWMaltese: "Sacre Infermeria" is the wrong building name

**File:** `data/anw_civ_blurbs.json`, `ANWMaltese.unique_buildings`

**Evidence:**
```json
"unique_buildings": ["Bastion", "Sacre Infermeria"]
```

**The problem:** The Maltese unique healing building is called **"Hospital"** in the AoE3 DE engine — not "Sacre Infermeria." This is confirmed by the in-game Maltese civ overview string (base string table):

> `Unique Buildings: Hospital, Fixed Gun, Depot, Commandery`

"Sacre Infermeria" has zero hits in `extracted_base_stringtable.xml`, `techtreemods.xml`, `strings/english/stringmods.xml`, and all home city XMLs. The string "Hospital" occurs extensively in the Maltese context (29+ string entries referencing it).

Additionally, "Bastion" is a **wall upgrade technology** in AoE3 DE — not a building that can be listed as a unique structure. The base string reads: "Enables the Bastion upgrade to be researched at your Walls." It is a tech researched at the wall, not a separate building.

**Fix:**
- `ANWMaltese.unique_buildings`: replace `"Sacre Infermeria"` with `"Hospital"`
- Consider removing `"Bastion"` (it is a wall upgrade tech, not a building) or replacing with `"Commandery"` (which IS a Maltese-unique building per the base game civ overview)

---

### Issue 6 — Indians spec claim `expects_artillery: true` contradicts XS

**File:** `playstyle_spec.json`, `"Indians Akbar"` entry (lines 459–478)

**Evidence from spec:**
```json
"claims": {
  "wall_strategy": 0,
  "first_military_building": "barracks_or_stable",
  "expects_artillery": true,
  "first_wall_before_ms": 720000,
  "military_distance_band": [0.7, 1.0]
}
```

**Evidence from XS (`game/ai/leaders/leader_shivaji.xs`):**
```
llSetMilitaryFocus(0.55, 0.6, 0.2);  // Cavalry-leaning composition.
// Colonial
btBiasInf = 0.55;
btBiasCav = 0.75;  // Sowar / Mahout raid pressure.
btBiasArt = -0.3;  // <-- actively suppressed
llEnableForwardBaseStyle();

// Fortress
btBiasInf = 0.7;
btBiasCav = 0.85;  // Howdah Elephant + Sowar mass.
btBiasArt = 0.3;

// Imperial
btBiasInf = 0.9;
btBiasCav = 1.0;
btBiasArt = 0.65;
```

**The problem:** `expects_artillery: true` is directly contradicted by the XS. Artillery bias is **negative** (`-0.3`) at Colonial and only reaches 0.65 at Imperial — never dominant. The dominant arm is cavalry (`0.75 → 1.0`). The `ai_behaviour_map.md` confirms: `Indians Akbar` init ratios are `0.55/0.6/0.2 (inf/cav/art)`.

Pass 5 correctly rewrote the `doctrine_prose` field to Ganimi Kava framing ("Sowar cavalry raids"), but **did not update the `claims` block**. The claims block was inherited from the Highland Citadel template (same as Egyptians, Ethiopians, Maltese) and was never corrected.

The `military_distance_band: [0.7, 1.0]` is also suspect — a "forward base" doctrine civ (XS enables `llEnableForwardBaseStyle()` at Colonial) should project militarily at [1.0, 1.3] range, not [0.7, 1.0] (which is citadel-turtle range). However, the ai_behaviour_map checks the `wall_strategy` not the distance band directly for this case.

**Fix (`playstyle_spec.json`, `"Indians Akbar"` claims block):**
```json
"claims": {
  "wall_strategy": 0,
  "first_military_building": "barracks_or_stable",
  "expects_cavalry": true,
  "first_wall_before_ms": 720000,
  "military_distance_band": [1.0, 1.3]
}
```
(Change `expects_artillery: true` → `expects_cavalry: true`; update `military_distance_band` to match forward-base civ pattern.)

---

## Verified Clean

Items researched in this pass that showed NO new issues:

| Category | Result |
|----------|--------|
| Deck card sanity (all 859 unique DEHC/ANW cards vs techtreemods + home cities + cards.json) | 0 missing — all deck-referenced DEHC and ANW cards resolve to known tech entries |
| Unique units: Barbary "Corsair Marksman" | Valid — confirmed in base strings: "Corsair Marksman", "REV Corsair Marksman" |
| Unique units: Canadians "Metis Pathfinder", "Metis Voyageur" | Valid — both confirmed in base strings (locID 80860 = "Métis Pathfinders", "Métis Voyageur") |
| Unique units: Romanian "Rosior Dragoon", "Dorabant" | Valid — both found in ANW stringmods (DE expansion units) |
| Unique units: Peruvians "Chasqui" | Valid — confirmed in base strings ("Ages up very fast and allows Chasquis…") |
| Unique units: Hausa "Lifidi Knight" | Valid — confirmed in base strings |
| Unique units: Lakota "Wakina Rifle", "Axe Rider", "Dog Soldier", "Tokala Soldier" | Valid — all in base strings or XS |
| Unique units: Mexicans "Salteador", Italians "Papal Guard", "Papal Lancer", "Bersagliere" | Valid — all confirmed in base strings |
| Unique units: NapoleonicFrance "Voltigeur", "Old Guard" | Valid — in techtreemods.xml (6 and 2 hits respectively) |
| Haitians "Maroon" unit legitimacy | Valid — ANWAge0Haitians tech applies SetName xpColonialMilitia → locID 80693 = "Maroon" |
| Indians spec `doctrine_prose` | Already fixed in pass 5 — current prose is Ganimi Kava / forward-base framing |
| NapoleonicFrance `doctrine_summary` | Already fixed in pass 6 — "Grande Armée combined-arms empire" (not "Grand Battery") |
| Peruvians "Kallankas" | Already fixed in pass 6 — blurbs.json updated |
| Haudenosaunee "Aenna Shotgun Rider" | Already fixed in pass 5 — blurbs.json now says "Aenna" |
| Cross-source (blurbs vs spec vs age_build_notes) for Swedes | Pass 6 fixed `playstyle` tooltip; spec doctrine_prose is generic Forward Operational Line template — acceptable; age_build_notes correctly mentions Leather Cannon throughout |
| ANWJapanese "Shrine" (first entry) | Valid — "Shrine" is confirmed Japanese unique building |
| ANWChinese "Summer Palace", "Porcelain Tower" | Valid — confirmed Chinese wonders in base strings |
| ANWMaltese "Bastion" as wall upgrade | Flagged in Issue 5 above but not a NEW phantom unit; exists as a real tech just wrongly categorized as building |

---

## Scope / Skipped

- **Base game validation**: units/buildings not in the ANW mod files but confirmed in `artifacts/extracted_base_stringtable.xml` were treated as valid (base game handles them). This is intentional — the mod does not need to re-declare stock AoE3 DE proto entries.
- **Anachronism/theme drift** (task 6): No new anachronisms found beyond the already-known design decision to include Mannerheim (20th century Finnish leader) as a revolution civ — this is intentional mod design, not a bug.
- **Decimal-precision drift in spec claims** (task 4): The `expects_artillery` error for Indians (Issue 6) was found. Other spec claims (wall_strategy, military_distance_band, expects_forward) were cross-checked against ai_behaviour_map.md output and found consistent for all other civs reviewed.
- **"Castle" for ANWJapanese**: Flagged in Issue 3 as non-unique shared building, but noted as a minor secondary concern — the primary bugs are the phantom "Buddhist Temple" and "Shinto Shrine" entries.
