# Post-Fix Consistency Audit — Legendary Leaders Mod

Worktree: `.claude/worktrees/hungry-banzai-e122dc/`
Date: 2026-04-28
Scope: read-only verification of Batch A (home-city pathdata fix, 25 files) and Batch B (label/flag fixes in playercolors.xml / stringmods.xml / civmods.xml). No edits performed.

Source-of-truth docs cross-checked:
- `artifacts/audits/home_city_floating_audit.md`
- `artifacts/audits/nation_label_flag_audit.md`
- `LEGENDARY_LEADERS_NATION_REFERENCE.txt`

---

## TL;DR

- **Batch A (pathdata):** clean. All 26 revolution home cities now pair `<visual>` with the matching parent-civ `<pathdata>`. The only file still using `revolution\pathable_area.gr2` is `anwhomecitymexicans.xml`, which is correct (its visual is `revolution\revolution_homecity.xml`). All 22 stock home cities untouched and consistent.
- **Batch B (labels/flags):** clean. The 7 leader-name corrections in `playercolors.xml` are all in place, plus Spanish/Isabella I of Castile and the Yucatan/Carrillo Puerto entries. `stringmods.xml:2131` resolves `ANWAmericans` to "American Republic" (collision with stock UnitedStates resolved). `civmods.xml:100` wires Napoleon-specific portrait. `civmods.xml:905` uses `_mexican_rev` for Mexicans-revolution postgame flag.
- **Cosmetic / thematic carryover (P3):** all 25 reskinned revolution civs still use `<lightset>hc_revolution</lightset>`, `<watertype>London</watertype>`, and `<ambientsounds>homecity\Revolutionambientsounds.xml</ambientsounds>` regardless of which parent civ scene they reuse. Documented in audit doc as deferred Priority 3, not blocking.
- **One residual P3 issue:** civ-id `ANWColumbians` (with U) typo persists across 75 files; surfaces only to modders. Documented.

No P1 or P2 regressions found.

---

## 1. Home-city consistency — every nation

### 1a. Stock 22 civs (`data/homecity*.xml`)

All visual + pathdata pairs are within the same parent-civ namespace.

| civ | visual | pathdata | match |
|---|---|---|---|
| Americans | american\american_homecity.xml | american\american_pathable_area.gr2 | yes |
| British | british\british_homecity.xml | british\pathable_area_object.gr2 | yes |
| Chinese | china\china_homecity.xml | china\pathable_area_object.gr2 | yes |
| Inca (deinca) | inca\inca_homecity.xml | inca\pathable_area.gr2 | yes |
| Dutch | dutch\dutch_homecity.xml | dutch\dutch_homecity_pathable.gr2 | yes |
| Ethiopians | ethiopia\ethiopia_homecity.xml | ethiopia\ethiopia_pathable_area.gr2 | yes |
| French | french\french_homecity.xml | french\pathable_area_object.gr2 | yes |
| Germans | german\german_homecity.xml | german\pathable_area_object.gr2 | yes |
| Hausa | hausa\hausa_homecity.xml | hausa\hausa_pathable_area.gr2 | yes |
| Indians | india\india_homecity.xml | india\pathable_area_object.gr2 | yes |
| Italians | italy\italy_homecity.xml | italy\pathable_area_object.gr2 | yes |
| Japanese | japan\japan_homecity.xml | japan\pathable_area_object.gr2 | yes |
| Maltese | malta\malta_homecity.xml | malta\pathable_area_object.gr2 | yes |
| Mexicans | mexico\mexico_homecity.xml | mexico\pathable_area.gr2 | yes |
| Ottomans | ottoman\ottoman_homecity.xml | ottoman\pathable_area_object.gr2 | yes |
| Portuguese | portuguese\portuguese_homecity.xml | portuguese\pathable_area_object.gr2 | yes |
| Russians | russian\russian_homecity.xml | russian\pathable_area_object.gr2 | yes |
| Spanish | spanish\spanish_homecity.xml | spanish\pathable_area_object.gr2 | yes |
| Swedes | swedish\swedish_homecity.xml | swedish\pathable_area.gr2 | yes |
| Aztecs (xpaztec) | aztec\aztec_homecity.xml | aztec\pathable_area.gr2 | yes |
| Haudenosaunee (xpiroquois) | iroquois\iroquois_homecity.xml | iroquois\pathable_area.gr2 | yes |
| Lakota (xpsioux) | sioux\sioux_homecity.xml | sioux\sioux_pathable_area.gr2 | yes |

22/22 match.

### 1b. Revolution 26 civs (`data/anwhomecity*.xml`)

| civ | visual | pathdata | match |
|---|---|---|---|
| Americans | british\british_homecity.xml | british\pathable_area_object.gr2 | yes |
| Argentina | spanish\spanish_homecity.xml | spanish\pathable_area_object.gr2 | yes |
| Baja Californians | mexico\mexico_homecity.xml | mexico\pathable_area.gr2 | yes |
| Barbary | ottoman\ottoman_homecity.xml | ottoman\pathable_area_object.gr2 | yes |
| Brazil | portuguese\portuguese_homecity.xml | portuguese\pathable_area_object.gr2 | yes |
| California | mexico\mexico_homecity.xml | mexico\pathable_area.gr2 | yes |
| Canada | british\british_homecity.xml | british\pathable_area_object.gr2 | yes |
| Central Americans | spanish\spanish_homecity.xml | spanish\pathable_area_object.gr2 | yes |
| Chile | spanish\spanish_homecity.xml | spanish\pathable_area_object.gr2 | yes |
| Columbia | spanish\spanish_homecity.xml | spanish\pathable_area_object.gr2 | yes |
| Egypt | ottoman\ottoman_homecity.xml | ottoman\pathable_area_object.gr2 | yes |
| Finland | russian\russian_homecity.xml | russian\pathable_area_object.gr2 | yes |
| French Canada | french\french_homecity.xml | french\pathable_area_object.gr2 | yes |
| Haiti | french\french_homecity.xml | french\pathable_area_object.gr2 | yes |
| Hungary | german\german_homecity.xml | german\pathable_area_object.gr2 | yes |
| Indonesians | dutch\dutch_homecity.xml | dutch\dutch_homecity_pathable.gr2 | yes |
| Maya | mexico\mexico_homecity.xml | mexico\pathable_area.gr2 | yes |
| **Mexicans (rev)** | **revolution\revolution_homecity.xml** | **revolution\pathable_area.gr2** | **yes (the only consistent revolution-namespace pair, intentional)** |
| Napoleon | french\french_homecity.xml | french\pathable_area_object.gr2 | yes |
| Peru | spanish\spanish_homecity.xml | spanish\pathable_area_object.gr2 | yes |
| Revolutionary France | french\french_homecity.xml | french\pathable_area_object.gr2 | yes |
| Rio Grande | mexico\mexico_homecity.xml | mexico\pathable_area.gr2 | yes |
| Romania | german\german_homecity.xml | german\pathable_area_object.gr2 | yes |
| South Africans | dutch\dutch_homecity.xml | dutch\dutch_homecity_pathable.gr2 | yes |
| Texas | mexico\mexico_homecity.xml | mexico\pathable_area.gr2 | yes |
| Yucatan | mexico\mexico_homecity.xml | mexico\pathable_area.gr2 | yes |

26/26 match. The single remaining `revolution\pathable_area.gr2` (Mexicans) is intentional and correct per `home_city_floating_audit.md` §3b.

**Verdict: Batch A is clean. No regressions. The float bug should be resolved for all 25 reskinned revolution civs.**

### 1c. Cosmetic-but-thematic carryover

All 25 reskinned revolution civs continue to use `<lightset>hc_revolution</lightset>`, `<watertype>London</watertype>`, and `<ambientsounds>homecity\Revolutionambientsounds.xml</ambientsounds>` regardless of their actual parent-civ visual. This is documented as Priority 3 in `home_city_floating_audit.md` §4. Examples worth flagging for future tightening:

| file | lightset | watertype | ambient | parent visual | severity |
|---|---|---|---|---|---|
| anwhomecityamericans.xml | hc_revolution | London | Revolutionambientsounds.xml | british | P3 (London water+lightset OK on British scene; ambient is generic but tolerable) |
| anwhomecityargentina.xml:16,17,19 | hc_revolution | London | Revolutionambientsounds.xml | spanish | P3 (London watertype on Seville scene — wrong-mood) |
| anwhomecitybrazil.xml:16,17,19 | hc_revolution | London | Revolutionambientsounds.xml | portuguese | P3 (London on Lisbon scene) |
| anwhomecityegypt.xml:17,18,20 | hc_revolution | London | Revolutionambientsounds.xml | ottoman | P3 (London on Constantinople scene) |
| anwhomecityfinland.xml:16,17,19 | hc_revolution | London | Revolutionambientsounds.xml | russian | P3 (London on St Petersburg scene) |
| anwhomecityhungary.xml:16,17,19 | hc_revolution | London | Revolutionambientsounds.xml | german | P3 (London on Berlin scene) |
| anwhomecityindonesians.xml:16,17,19 | hc_revolution | London | Revolutionambientsounds.xml | dutch | P3 (London on Amsterdam scene) |
| anwhomecitytexas.xml:18,19,21 | hc_revolution | London | Revolutionambientsounds.xml | mexico | P3 (London water on Mexico scene) |

`anwhomecitymexicans.xml` keeps the revolution scene + revolution lightset/ambient — internally consistent.

These are not blocking; they are P3 polish items deferred per the original audit plan.

---

## 2. Label / flag consistency — every nation

### 2a. Stock 22 civs

`data/civmods.xml` does not override base civs, so display name + flag come from stock game data. `data/playercolors.xml` is the only mod-owned table that names them. Spot-checks against `LEGENDARY_LEADERS_NATION_REFERENCE.txt`:

| civ | leader (playercolors:line) | reference doc | match |
|---|---|---|---|
| French (L6) | Louis XVIII | Louis XVIII (L121) | yes |
| British (L7) | Queen Elizabeth I | Queen Elizabeth I (L40) | yes |
| Germans (L8) | Frederick the Great | Frederick the Great | yes |
| Russians (L9) | Ivan the Terrible | Ivan the Terrible (L381) | yes |
| **Spanish (L10)** | **Isabella I of Castile** | Isabella I of Castile (L400) | **yes (corrected from "Isabella I")** |
| Ottomans (L11) | Suleiman the Magnificent | Suleiman the Magnificent | yes |
| Portuguese (L12) | Prince Henry the Navigator | Prince Henry the Navigator | yes |
| Dutch (L13) | Maurice of Nassau | Maurice of Nassau | yes |
| Italians (L14) | Giuseppe Garibaldi | Giuseppe Garibaldi | yes |
| Maltese (L15) | Jean Parisot de Valette | Jean Parisot de Valette | yes |
| Swedes (L16) | Gustavus Adolphus | Gustavus Adolphus | yes |
| Chinese (L17) | Kangxi Emperor | Kangxi Emperor | yes |
| Japanese (L18) | Tokugawa Ieyasu | Tokugawa Ieyasu | yes |
| Indians (L19) | Shivaji Maharaj | Shivaji Maharaj | yes |
| Aztecs (L20) | Montezuma II | Montezuma II (L20) | yes |
| Haudenosaunee (L21) | Hiawatha | Hiawatha | yes |
| Inca (L22) | Pachacuti | Pachacuti | yes |
| Lakota (L23) | Chief Gall | Chief Gall (L281) | yes |
| UnitedStates (L24) | George Washington | George Washington | yes |
| Mexicans (L25) | Miguel Hidalgo | Miguel Hidalgo y Costilla (L320) | partial — short form vs full form (cosmetic, P3) |
| Ethiopians (L26) | Menelik II | Menelik II | yes |
| Hausa (L27) | Usman dan Fodio | Usman dan Fodio | yes |

22/22 acceptable. Spanish corrected. The Mexicans entry is a short form ("Miguel Hidalgo") vs the reference's full form ("Miguel Hidalgo y Costilla"); both refer to the same historical figure, no UI ambiguity.

### 2b. Revolution 26 civs

Combined `civmods.xml` (display, postgame, HC flags, portrait, line refs) + `playercolors.xml` (leader) + reference doc.

| civ | leader (playercolors:line) | display (locID=stringmods) | hc_flag (HomeCityFlagIconWPF) | postgame_flag | portrait | mismatches |
|---|---|---|---|---|---|---|
| ANWNapoleonicFrance | Napoleon Bonaparte (L28) | French Empire (494001) | Flag_French_Revolution_NE.png | Flag_French_Revolution_NE.png + tex …french_revolution_ne | **cpai_avatar_napoleonic_france_napoleon.png** (civmods.xml:100) | **none — Napoleon portrait wired** |
| ANWRevFrance | Maximilien Robespierre (L29) | French Republic (494002) | Flag_French_Revolution.png | matching | cpai_avatar_revolutionary_france.png | none |
| **ANWAmericans** | Thomas Jefferson (L30) | **American Republic (494003)** | Flag_USA.png | Flag_USA.png | cpai_avatar_americans.png | **none — collision with stock UnitedStates resolved** |
| **ANWMexicans** | Miguel Hidalgo y Costilla (L31) | Mexico (494004) | Flag_Mexican_Rev.png | **objects\flags\mexican_rev → ingame_ui_postgame_flag_mexican_rev (civmods.xml:902,905)** | cpai_avatar_mexicans_hidalgo.png | **none — postgame flag matches HC flag** |
| ANWCanadians | Sir Isaac Brock (L32) | Canada (494005) | Flag_Canadians.png | matching | cpai_avatar_canadians.png | cosmetic: "Sir Isaac Brock" vs reference "Isaac Brock" (P3) |
| **ANWFrenchCanadians** | Louis-Joseph Papineau (L33) | Lower Canada (494006) | Flag_SPC_Canadian.png | matching | cpai_avatar_french_canadians.png | none — leader corrected |
| ANWBrazil | Pedro I (L34) | Brazil (494007) | Flag_Brazilian.png | matching | cpai_avatar_brazil.png | none |
| ANWArgentines | Jose de San Martin (L35) | Argentina (494008) | Flag_Argentinian.png | matching | cpai_avatar_argentines.png | none |
| ANWChileans | Bernardo O'Higgins (L36) | Chile (494009) | Flag_Chilean.png | matching | cpai_avatar_chileans.png | none |
| **ANWPeruvians** | Andres de Santa Cruz (L37) | Peru (494010) | Flag_Peruvian.png | matching | cpai_avatar_peruvians.png | none — leader corrected |
| ANWColumbians | Simon Bolivar (L38) | Gran Colombia (494011) | Flag_Colombian.png | matching | cpai_avatar_columbians.png | civ-id typo `Columbians` (U) vs flag spelling `Colombian` (O) (P3, see §3) |
| ANWHaitians | Toussaint Louverture (L39) | Haiti (494012) | Flag_Haitian.png | matching | cpai_avatar_haitians.png | none |
| ANWIndonesians | Diponegoro (L40) | Indonesia (494013) | Flag_Indonesian.png | matching | cpai_avatar_indonesians.png | none |
| **ANWSouthAfricans** | Paul Kruger (L41) | South Africa (494014) | Flag_South_African.png | matching | cpai_avatar_south_africans.png | none — leader corrected |
| ANWFinnish | C. G. E. Mannerheim (L42) | Finland (494015) | Flag_Finnish.png | matching | cpai_avatar_finnish.png | none |
| ANWHungarians | Lajos Kossuth (L43) | Hungary (494016) | Flag_Hungarian.png | matching | cpai_avatar_hungarians.png | none |
| **ANWRomanians** | Alexandru Ioan Cuza (L44) | Romania (494017) | Flag_Romanians.png | matching | cpai_avatar_romanians.png | none — leader corrected |
| ANWBarbary | Hayreddin Barbarossa (L45) | Barbary States (494018) | Flag_barbary.png | matching | cpai_avatar_barbary.png | none |
| ANWEgyptians | Muhammad Ali (L46) | Egypt (494019) | Flag_Egyptians.png | matching | cpai_avatar_egyptians.png | none |
| ANWCentralAmericans | Francisco Morazan (L47) | Central America (494020) | Flag_Central_American.png | matching | cpai_avatar_central_americans.png | none |
| **ANWBajaCalifornians** | Juan Bautista Alvarado (L48) | Baja California (494021) | Flag_baja_californian.png | matching | cpai_avatar_baja_californians.png | none — leader corrected |
| ANWYucatan | Felipe Carrillo Puerto (L49) | Yucatán (494022) | Flag_yucatan.png | matching | cpai_avatar_yucatan.png | none — collision pre-empted |
| ANWRioGrande | Antonio Canales Rosillo (L50) | Rio Grande (494023) | Flag_rio_grande.png | matching | cpai_avatar_rio_grande.png | none |
| **ANWMayans** | Jacinto Canek (L51) | Maya (494024) | Flag_mayan.png | matching | cpai_avatar_mayans.png | none — leader corrected |
| ANWCalifornians | Mariano Guadalupe Vallejo (L52) | California (494025) | Flag_californian.png | matching | cpai_avatar_californians.png | none |
| ANWTexians | Sam Houston (L53) | Texas (494026) | Flag_texan.png | matching | cpai_avatar_texians.png | none |

**26/26 corrected. All 7 leader fixes confirmed in `playercolors.xml`. The 8th (Yucatan/Carrillo Puerto) and 9th (Spanish/Isabella I of Castile) cosmetic fixes also confirmed.**

### 2c. Specific user requests

| ask | result |
|---|---|
| `ANWAmericans` display ≠ "United States" | confirmed — `stringmods.xml:2131` is **"American Republic"** |
| `ANWNapoleonicFrance` `HomeCityPreviewWPF` = `cpai_avatar_napoleonic_france_napoleon.png` | confirmed — `civmods.xml:100` |
| `ANWMexicans` `PostgameFlagTexture` = `..._mexican_rev` | confirmed — `civmods.xml:905` `ui\ingame\ingame_ui_postgame_flag_mexican_rev` |
| 7 leader corrections in playercolors.xml | confirmed L31, L33, L37, L41, L44, L48, L51 |
| Yucatan/Carrillo Puerto | confirmed — `playercolors.xml:49` |
| Spanish/Isabella I of Castile | confirmed — `playercolors.xml:10` |

---

## 3. Surface-broader consistency check

### 3a. Civ-name string token resolution

- `<DisplayNameID>` (494001..494026): all 26 resolve to strings in `stringmods.xml:2129..2154`. None missing.
- `<RolloverNameID>`: 25 of 26 use `400xxx` (400001..400026), defined in `stringmods.xml:5..32`. The exception is `ANWNapoleonicFrance` (`civmods.xml:10` → `490002`), defined at `stringmods.xml:24`. This is intentional per `nation_label_flag_audit.md` D-2; the loc id resolves.
- `<HistoryNameID>`: not used by `data/civmods.xml`. (Stock civs use it in their own data; the mod does not override.)

No locID dangling.

### 3b. Lobby vs scoreboard vs home-city display strings

Cross-check between three string surfaces:

- **494xxx (lobby/scoreboard label, demonym/country):** "French Empire", "French Republic", "American Republic", "Mexico", "Canada", … (`stringmods.xml:2129..2154`)
- **490200..490243 (home-city civ banner / theme blurb):** older name+blurb table (`stringmods.xml:1789..1832`). Uses demonym ("British", "Mexicans", "Americans", "Russians", …). 
- **490250..490275 (leader-name table, mod-owned):** leader names per civ (`stringmods.xml:1760..1785`).

No collisions found. The 494xxx table is the customer-facing nation/country label; the 490xxx tables are theme-blurbs that the engine surfaces alongside the leader portrait. Different surfaces, complementary not contradictory.

Spot-checks of leader-name table vs `playercolors.xml`:

| civ | playercolors leader | stringmods 49025x leader | match |
|---|---|---|---|
| ANWMexicans | Miguel Hidalgo y Costilla | Miguel Hidalgo (490253) | yes (short form) |
| ANWFrenchCanadians | Louis-Joseph Papineau | Louis-Joseph Papineau (490255) | yes |
| ANWPeruvians | Andres de Santa Cruz | Andrés de Santa Cruz (490259) | yes (accent diff, P3 cosmetic) |
| ANWSouthAfricans | Paul Kruger | Paul Kruger (490263) | yes |
| ANWRomanians | Alexandru Ioan Cuza | Alexandru Ioan Cuza (490266) | yes |
| ANWBajaCalifornians | Juan Bautista Alvarado | Juan Bautista Alvarado (490270) | yes |
| ANWYucatan | Felipe Carrillo Puerto | Felipe Carrillo Puerto (490271) | yes |
| ANWMayans | Jacinto Canek | Jacinto Canek (490273) | yes |

All 7 corrected leaders agree across `playercolors.xml`, `stringmods.xml` 490xxx leader-name table, and `LEGENDARY_LEADERS_NATION_REFERENCE.txt`.

### 3c. Civ id vs filename consistency

| civ id (`civmods.xml <Name>`) | corresponding home-city file |
|---|---|
| ANWNapoleonicFrance | anwhomecitynapoleon.xml |
| ANWRevFrance | anwhomecityrevolutionaryfrance.xml |
| ANWAmericans | anwhomecityamericans.xml |
| ANWMexicans | anwhomecitymexicans.xml |
| ANWCanadians | anwhomecitycanada.xml |
| ANWFrenchCanadians | anwhomecityfrenchcanada.xml |
| ANWBrazil | anwhomecitybrazil.xml |
| ANWArgentines | anwhomecityargentina.xml |
| ANWChileans | anwhomecitychile.xml |
| ANWPeruvians | anwhomecityperu.xml |
| **ANWColumbians** | **anwhomecitycolumbia.xml** (filename uses "columbia" with O; civ id uses "Columbians" with U — typo, P3) |
| ANWHaitians | anwhomecityhaiti.xml |
| ANWIndonesians | anwhomecityindonesians.xml |
| ANWSouthAfricans | anwhomecitysouthafricans.xml |
| ANWFinnish | anwhomecityfinland.xml |
| ANWHungarians | anwhomecityhungary.xml |
| ANWRomanians | anwhomecityromania.xml |
| ANWBarbary | anwhomecitybarbary.xml |
| ANWEgyptians | anwhomecityegypt.xml |
| ANWCentralAmericans | anwhomecitycentralamericans.xml |
| ANWBajaCalifornians | anwhomecitybajacalifornians.xml |
| ANWYucatan | anwhomecityyucatan.xml |
| ANWRioGrande | anwhomecityriogrande.xml |
| ANWMayans | anwhomecitymaya.xml |
| ANWCalifornians | anwhomecitycalifornia.xml |
| ANWTexians | anwhomecitytexas.xml |

All 26 home-city filenames link via the `<HomeCityFilename>` tag in `civmods.xml`; they do not need to match the civ id verbatim, so the country/state-style naming (e.g. `canada` vs `Canadians`) is fine.

The single id-level oddity is the `Columbians` (U) typo, which now exists in 75+ files (per Grep on 246 occurrences in 75 files). User-visible labels use the correct "Colombian"/"Colombia" spelling everywhere; only modders editing the codebase see "Columbians". Documented in `nation_label_flag_audit.md` A-3 as Priority 3 (mass rename, deferred).

### 3d. Leader names in stringmods.xml taunt / unit name strings

Searched for any reference to the *previous wrong* leader names (Tupac Amaru, Shaka Zulu, Michael the Brave, Manuel Micheltorena, Tecun Uman, Jose Maria Morelos, Louis-Joseph de Montcalm). Findings:

- `stringmods.xml:1251` `<string _locid="151133" comment="proto-Explorer civ-ANWMexicans type-title">José María Morelos</string>` — this is the **Explorer unit name** for the Mexican-revolution civ, not the leader. José María Morelos is a separate historical figure used for the in-game hero/explorer unit. Coexisting with leader Hidalgo is by design (leader != explorer). **No conflict.** P3 cosmetic note only.
- `stringmods.xml:478` `Juan Bautista Alvarado` — appears as the deGeneral unit name for `ANWCalifornians`. The leader for California is Vallejo (`playercolors.xml:52`), and the leader for Baja California is now Alvarado. Two civs reference Alvarado in different roles; fine.
- `stringmods.xml:602` `Pedro de Alvarado` — Conquistador-era explorer name for Central Americans (Morazan is leader). Different historical Alvarado, fine.
- `stringmods.xml:694` `Alonso de Alvarado` — Chilean explorer. O'Higgins is leader. Fine.
- `stringmods.xml:1568` `Alexandru Ioan Cuza` — Romanian explorer = leader (same person). Fine.
- `stringmods.xml:1607` `Kruger` — South African Ironclad name. Leader Kruger. Fine.

No taunt or history string references the *old wrong* leader names anywhere. The corrections are not contradicted by any text surface.

### 3e. Reference doc cross-check

`LEGENDARY_LEADERS_NATION_REFERENCE.txt` agrees with corrected leaders:
- L320 Mexicans: Miguel Hidalgo y Costilla
- L400 Spanish: Isabella I of Castile
- L503 Baja Californians: Juan Bautista Alvarado
- L703 French Canadians: Louis-Joseph Papineau
- L783 Mayans: Jacinto Canek
- L803 ANWMexicans: Miguel Hidalgo y Costilla
- L864 Peruvians: Andres de Santa Cruz
- L904 Romanians: Alexandru Ioan Cuza
- L924 South Africans: Paul Kruger
- L964 Yucatan: Felipe Carrillo Puerto

All 10 entries align with `playercolors.xml`. The reference doc was already correct at audit time; the fix work brought `playercolors.xml` into agreement with it.

---

## 4. Issues table (severity-graded)

### P1 (visible regressions)

None found.

### P2 (in-game label / wrong-flag visible)

None found.

### P3 (thematic / cosmetic / modder-facing)

| # | file | line | current | expected | severity | notes |
|---|---|---|---|---|---|---|
| 1 | data/playercolors.xml | 25 | "Miguel Hidalgo" | "Miguel Hidalgo y Costilla" | P3 | Stock Mexicans civ; reference doc uses full form. Cosmetic, unambiguous. |
| 2 | data/playercolors.xml | 32 | "Sir Isaac Brock" | "Isaac Brock" | P3 | Cosmetic prefix. Reference doc omits "Sir". |
| 3 | data/civmods.xml | 2646 | `<Name>ANWColumbians</Name>` (and 75 more files) | `ANWColombians` | P3 | Modder-facing typo. UI shows "Gran Colombia" / "Colombian" correctly. Mass rename deferred. |
| 4 | data/strings/english/stringmods.xml | 1769 | "Andrés de Santa Cruz" | "Andres de Santa Cruz" (or vice-versa in playercolors) | P3 | Accent diacritic difference between mod-owned tables. No engine impact. |
| 5 | data/anwhomecity*.xml × 25 | 16-19 | `<lightset>hc_revolution</lightset>` + `<watertype>London</watertype>` + `<ambientsounds>Revolutionambientsounds.xml</ambientsounds>` | parent-civ values per stock `homecity*.xml` | P3 | Wrong-mood lighting/audio for reskinned scenes (e.g. London watertype on Constantinople scene). Documented as deferred Priority 3 in home_city_floating_audit.md §4. |
| 6 | data/civmods.xml | 273, 361 | mixed `\` and `/` separators in path | normalize to `\` | P3 | Code-smell, engine-tolerant. |
| 7 | data/civmods.xml various | several | `<HomeCityFlagButtonSet>` reuses other civs' atlases (e.g. ANWSouthAfricans uses `swedishFlagBtn`, ANWIndonesians uses `britishFlagBtn`) | per-civ atlas | P3 | Mini button widget shows wrong colour. Authoring work deferred. |
| 8 | resources/images/icons/singleplayer/cpai_avatar_british_elizabeth.png + 3 others | n/a | base-civ portraits exist on disk but no XML loads them (the mod doesn't override base-civ portrait). README claim re: Queen Elizabeth I etc. is therefore not reflected in the in-game civ-pick screen for the 22 base civs. | wire base-civ portraits via civmods Civ entries OR ship `.ddt` versions at `art/ui/singleplayer/cpai_avatar_<civ>.ddt` | P3 | Documented in nation_label_flag_audit.md B-1. |

---

## 5. Verdict per section

- **§1 home-city consistency:** clean. 48/48 visual+pathdata pairs internally consistent; the 1 remaining `revolution\pathable_area.gr2` reference (Mexicans-revolution) is correct.
- **§2 label/flag consistency:** clean. All 26 revolution civs display the correct country label, hero, flag, and portrait. All 7 named leader corrections + Yucatan + Spanish/Isabella confirmed in `playercolors.xml`. The 3 specifically-named asks (American Republic / Napoleon portrait / mexican_rev postgame) verified in source.
- **§3 broader cross-check:** clean on locID resolution and on string-surface agreement. The pre-existing `ANWColumbians` typo and the 25× wrong-mood lightset/watertype/ambient remain as documented P3 deferrals; neither is a regression introduced by the fix batches.

No edits were made by this audit. Read-only verification only.
