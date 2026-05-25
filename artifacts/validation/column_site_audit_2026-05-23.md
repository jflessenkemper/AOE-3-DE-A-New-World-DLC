# Column Site Audit — 2026-05-23

Full systematic read of all 40 ANW civs' column text against their XS leader files.
All claims below verified by reading the actual XS file and the actual HTML — no guessing.

---

## Already Fixed This Session

| Civ | Fix Applied |
|-----|------------|
| **ANWBritish** | 7 blank thumbnails replaced with styled placeholders; Strategic Identity + Build Strategy per Age rewritten for Queen Elizabeth I (Tudor naval-mercantile doctrine, no walls, Dock-first, Longbow→Ranger Industrial transition) |
| **ANWHausa** | Leader name corrected: "Usman dan Fodio" / "Sokoto Caliphate" → "Muhammadu Kanta" / "Hausa States — Kebbi" (XS `leader_usman.xs` explicitly states rebrand and logs "Kanta initialized") |
| **ANWIndonesians** | Doctrine label corrected: "Jungle Guerrilla Network" → "Shrine Trade Node Spread" (XS uses `llUseShrineTradeNodeSpreadStyle(1)`); narr-playstyle second paragraph de-boilerplated |
| **ANWDutch** | Narr-playstyle second paragraph replaced: removed dock-first / fishing-fleet / wall-harbor language (copy-pasted from Portuguese; Dutch XS has no `cvOkToTrainNavy`); bsnote-overview corrected to Bank-first doctrine |
| **ANWNapoleonicFrance** | Removed wall claims ("Forward wall segments protect advance base", "lost ground is re-walled") — `leader_napoleon.xs` has zero wall variables; doctrine is `llUseForwardOperationalLineStyle` |
| **ANWPeruvians** | Narr-playstyle second paragraph de-boilerplated (was verbatim copy of ANWChileans); now reflects Confederation doctrine and stronger native-levy emphasis (`btBiasNative = 0.55`) |
| **ANWColumbians** | Narr-playstyle second paragraph de-boilerplated (was verbatim copy of ANWArgentines); now reflects Bolívar's wider Pan-American theatre vs. San Martín's Andes crossing |
| **ANWItalians** | Lombards description corrected: "passively generate coin" → "convert deposited resources and generate XP, funding a strong shipment cycle" (Lombards are resource-exchange buildings, not Dutch-style auto-banks) |
| **ANWMaltese** | Age IV bsnote card name corrected: "Rolling Wood" → "Shipping Supplies (2000 wood)" (Rolling Wood is not in the Maltese card list; the correct card is Shipping Supplies) |

---

## Remaining Issues — User Decisions Required

These were NOT auto-fixed because they involve historical interpretation choices or require decisions about the mod's canon. All are documentation-only — none affect gameplay, validators, or Workshop deploy.

### 🔴 High priority (clear factual errors)

| Civ | Issue | Recommended fix |
|-----|-------|-----------------|
| **ANWRussians** | `btRushBoom`, narr-playstyle claim "rushes to a third Town Center to fuel the cavalry stream" — `leader_catherine.xs` has no TC-count variable, no `cvMinNumTCs`, no third-TC trigger anywhere in the file. This is a fabricated mechanical claim. | Remove/replace the third-TC claim with accurate description: "builds 1–2 TCs and relies on Strelet batches and Cossack raids, not TC sprawl" |
| **ANWRussians** | Age III bsnote lists card names that don't exist in the Russian deck: "Musket 2", "Strelets 2", "Snaplocks". Real card names: "13 Rekruts", "19 Streltsy", "Strelet Combat". | Correct Age III card names to match the Russian card list shown in the same column |
| **ANWRussians** | Age I note mentions "Soldier Torps" card — no such card exists for Russians (it's a Swedish-themed card). Real Discovery cards: "Landed Gentry", "Allotment System". | Correct Age I card name |
| **ANWOttomans** | "stone-and-forward walls" claimed in bsnote and narr-playstyle — `leader_suleiman.xs` sets no `gLLWallStrategy` and no `gLLEarlyWallingEnabled`. No wall code exists for Ottomans. | Remove wall claims; replace with Janissary + siege-train forward pressure (no walls, just heavy artillery) |
| **ANWOttomans** | Age II–III bsnote uses generic card names ("Fencing School", "Settlers 2", "Spies 1", "Artillery Combat", "Janissary Combat") instead of Ottoman-specific names. Real names: "Matrakci School", "5 Yörüks", "6 Muhbirs", "Topçular", "Enderun School". | Align card names with what's shown in the same column's card list |
| **ANWTexians** | Column describes an infantry/Sharpshooter doctrine. XS (`leader_revolution_commanders.xs`) sets `btBiasCav = 0.8` at Colonial rising to `0.9` at Industrial/Imperial — the highest cavalry weighting in the entire mod. The column never mentions cavalry as the primary force. | Rewrite Strategic Identity: "Texas Lancer cavalry-first doctrine from Colonial; Sharpshooters screen the flanks" |
| **ANWGermans** | Age III note names "German Chevaulegers" as primary cavalry; XS `frederickObliqueOrder` comment says "Uhlan hammer wing" and `btBiasCav = 0.7`. Chevaulegers is a card that replaces War Wagons (an alternative path), not the primary cavalry axis. | Replace "Chevaulegers" with "Uhlans" in Age III note |
| **ANWGermans** | Age IV note references "Uhlan Combat" card — no such card exists in the German Industrial deck. Real card: "Lipizzaner Cavalry" (buffs Uhlans). | Correct card name |

### 🟡 Medium priority (historical accuracy / design decisions)

| Civ | Issue | Options |
|-----|-------|---------|
| **ANWHaitians** | Column labels civ "First Empire of Haiti" with Toussaint Louverture as leader. Toussaint died in French imprisonment (1803) before independence was declared; he never created an empire. The First Empire was founded by Jean-Jacques Dessalines in 1804. | Option A: Rename to "Republic of Saint-Domingue" (Toussaint's actual governance title). Option B: Change leader to Dessalines and keep "First Empire." Option C: Keep as-is (artistic licence). |
| **ANWMayans** | Column names "Jacinto Canek" as leader. Jacinto Canek was executed in 1761 — he predates the Cruzob movement (Caste War 1847) by ~86 years. The Cruzob's founding leaders were Cecilio Chi and Jacinto Pat. | Option A: Change to Cecilio Chi. Option B: Keep Canek (symbolic of Maya resistance broadly). |
| **ANWMexicans** | Column calls the polity "First Mexican Empire" and assigns Hidalgo as leader. Hidalgo was executed in 1811; the First Mexican Empire was declared under Iturbide in 1821. The correct pairing would be "Insurgent Mexico / Mexican War of Independence." | Option A: Rename to "Mexico — Grito de Dolores / Hidalgo" or "Insurgent Mexico." Option B: Keep as-is. |
| **ANWRevFrance** | Robespierre named as the civ's strategic commander in the sub-header. Robespierre was a politician / Committee member, executed in 1794, never a military commander. | Option A: Replace with Lazare Carnot ("organizer of victory," actual military head of the Revolution). Option B: Descriptive sub-header like "The Terror · Revolutionary France" without a single named commander. |
| **ANWBrazil** | XS logs "Pedro II" (`"activating ANW Brazil Pedro II personality"`); HTML header says "Pedro I of Brazil." These are different emperors. | Option A: Align to Pedro II (1841–1889, the long reign, more historically significant for the AoE3 era). Option B: Change XS log to Pedro I and keep HTML. Note: gameplay is identical either way. |
| **ANWLakota** | Column correctly names Chief Gall in the sub-header but the AI portrait is `cpai_avatar_lakota_crazy_horse.png`. Gall and Crazy Horse are different historical figures. | Option A: Rename the portrait DDT file to reference Gall. Option B: Change sub-header back to Crazy Horse. Option C: Keep as-is (portrait art is reused). |
| **ANWCanadians** | Strategic identity text references "Lower-Canada Patriote doctrine" — this is Papineau's 1837 rebellion, while the AI personality is Isaac Brock (War of 1812, died 1812). They are different conflicts 25 years apart. | Remove "Patriote doctrine" phrase; replace with "War of 1812 defensive posture." |

### 🟢 Low priority (minor, cosmetic)

**Eighth loop pass (2026-05-25): six low-priority items were auto-fixed in
`a_new_world_columns.html` after re-verifying each card name against the
Cards section rendered in the same column. All edits are documentation-only
and the validator gate stays at 41/48 PASS, 0 FAIL.**

| Civ | Issue | Status |
|-----|-------|--------|
| **ANWJapanese** | Header "Shrine or Trade Node Spread" → "Shrine Trade Node Spread". | ✅ Fixed 2026-05-25 |
| **ANWHaudenosaunee** | Same header wording fix applied. | ✅ Fixed 2026-05-25 |
| **ANWSwedes** | Age I "Torp Team / Explorer / Leather Cannons Foundry / Leather Cannons 1" → real names "Duelist / TEAM New Sweden / Julita Styckebruk / 2 Leather Cannons". Age II "Royal Decree / Irish Brigaders / Landsnechts / Leather Cannons 3 / Leather Cannon repeat" → real names "Treaty of Roskilde / Contract Irish Brigadiers / Contract Landsknechts / 3 Leather Cannons / 2-Leather-Cannons repeat". | ✅ Fixed 2026-05-25 |
| **ANWFinnish** | Age I "Tree Spawn / Torp Team" → "Finnish Taiga / TEAM New Sweden". Age II "Strelet spawn / mercenary contracts" → "Strelet Horde / Contract Irish Brigadiers / Contract Landsknechts". | ✅ Fixed 2026-05-25 |
| **ANWHaudenosaunee** | "Aenna Shotgun Rider" (non-existent unit — Aenna is foot infantry) → "Aenna foot infantry" in bsnote-overview / Age IV bsnote / unit pill / strategic identity. | ✅ Fixed 2026-05-25 |
| **ANWGermans** | Age IV "Uhlans 3 / Uhlan Combat / Giant Grenadiers / Habsburg Allies 2" → real names "11 Uhlans / Lipizzaner Cavalry / Potsdam Giants / 17 Habsburg Allies". | ✅ Fixed 2026-05-25 |
| **ANWEthiopians** | Sub-header "Menelik" → "Menelik II" (distinguishes from the legendary 10th-century BCE Menelik I). | ✅ Fixed 2026-05-25 |
| **ANWGermans** | Trade bias (`btBiasTrade = -0.25`) never mentioned in the column — Prussia is explicitly "an army with a country" in the XS comment. Minor omission. | ⚪ Skipped (intentional flavour) |
| **ANWChileans** | Uses "Kallankas and Tambos" (Inca architectural terms) for a 19th-century Chilean republic context. Minor flavour oddity. | ⚪ Skipped (intentional flavour) |
| **ANWAztecs** | Doctrine label "Jungle Guerrilla Network" but XS overrides wall strategy to `ChokepointSegments`. Label names the helper function, not the effective wall strategy. | ⚪ Skipped (label is helper-function name) |
| **ANWInca** | Same pattern: label "Andean Terrace Fortress" but XS overrides to `FortressRing`. | ⚪ Skipped (label is helper-function name) |
| **ANWFrench (Bourbon)** | Avatar image `cpai_avatar_french_napoleon.png` — Napoleon's portrait is being used for the Bourbon Restoration civ (Louis XVIII). | ⚠️ Aesthetic — requires DDT rename, deferred to user |
| **ANWNapoleonicFrance** | Age III note mentions "Voltigeur" as a core column unit; XS explicit bias is Cuirassier (cavalry). Minor overstatement. | ⚪ Skipped (Voltigeur is in unit pool) |

---

## What Was NOT Changed (intentional design choices)

- **ANWSouthAfricans** — Naval Mercantile Compound doctrine for Paul Kruger's landlocked Transvaal is historically incongruous but matches the XS exactly. Left as-is.
- **ANWHaudenosaunee** — Hiawatha anachronism (game spans 1492–1876; Hiawatha was ~12th–15th century). This matches base-game canon. Left as-is.
- **ANWSwedes / ANWFinnish** — Mannerheim reference in Finnish text is 20th century (Winter War) but functions as a recognisable shorthand. Design choice.
- **Wokou Junks for ANWIndonesians** — Wokou were 16th-century pirates; Diponegoro's Java War was 1825–30. Anachronistic but a game-design choice.

---

## Thumbnail Status

- **ANWBritish**: 7 blank thumbnails — replaced with styled "not captured" placeholders (opacity 0.45, dark red background). Real captures require an in-game session.
- **All other 39 civs**: 0 blank thumbnails. All have 10 synthesised static-art surfaces.

---

## Validator State

**41/48 PASS, 0 FAIL, 7 SKIP** (unchanged — column site changes do not affect game validators)

The 7 SKIPs all require a running game instance. None block Workshop deploy.

---

*Generated 2026-05-23 by systematic XS-vs-HTML audit across all 40 ANW civs.*
