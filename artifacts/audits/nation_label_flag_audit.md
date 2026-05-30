# Nation Label & Flag Audit — Legendary Leaders Mod

Worktree: `.claude/worktrees/hungry-banzai-e122dc/`
Date: 2026-04-28
Scope: read-only audit. No edits performed.

---

## 1. Methodology

### Files inspected (canonical sources)

| File | Role |
|---|---|
| `data/civmods.xml` (8164 lines) | Civ definitions for the 26 revolution-promoted top-level civs (`ANW*`). Source of `<DisplayNameID>`, `<HomeCityFlagTexture>`, `<HomeCityFlagIconWPF>`, `<PostgameFlagTexture>`, `<PostgameFlagIconWPF>`, `<HomeCityPreviewWPF>`, `<HomeCityFlagButtonSet>`, `<BannerTexture>`. Base civs (Aztecs..Hausa, 22 nations) are NOT modified — they keep stock definitions. |
| `data/strings/english/stringmods.xml` (2186 lines) | Localised strings. Civ display names are at locIDs `494001`–`494026`. Civ rollovers are at `400001`–`400026` and `490002`. Leader chat/taunt quotes at `493000`+. |
| `data/playercolors.xml` (54 lines) | Mod-owned civ → colour + leader-name table. |
| `LEGENDARY_LEADERS_NATION_REFERENCE.txt` (979 lines) | Generated reference doc. Treated as the canonical leader/flag/portrait spec for cross-checking. |
| `README.md` | High-level claims ("Queen Elizabeth I for British, Ivan the Terrible for Russians, Chief Gall for Lakota, Napoleon for Napoleonic France"). |
| `resources/images/icons/flags/Flag_*.png` | Flag PNG assets. |
| `resources/images/icons/singleplayer/cpai_avatar_*.png` | Lobby/score/loading-screen leader portraits. |
| `art/ui/leaders/*.{png,jpg}` | Secondary leader portrait set (used by leader pop-up / thumbnail in some surfaces). |
| `art/ui/singleplayer/cpai_avatar_*.ddt` | Stock base-civ AI avatars (binary `.ddt`). |
| `RandMaps/*.{xml,xs,set}` | Searched for civ-name labels — none found (no `ANW*`, `setCiv`, or per-civ branches). |

### Search techniques

- `Grep` for tags `<Name>`, `<DisplayNameID>`, `<RolloverNameID>`, `<HomeCityFlagTexture>`, `<HomeCityFlagButtonSet>`, `<HomeCityFlagIconWPF>`, `<PostgameFlagTexture>`, `<PostgameFlagIconWPF>`, `<HomeCityPreviewWPF>`, `<BannerTexture>`, `<Portrait>` across `data/civmods.xml`.
- `Grep` for `_locID='49[34]\\d{3}'` to enumerate civ-name and quote strings.
- File-existence shell loops (`for f in ...; do [ -f "$f" ] || echo MISSING; done`) over all 26 revolution flag PNGs and all 49 referenced portrait PNGs (26 revolution + 23 base-civ leader variants).
- `find art/` to inventory leader portrait set in `art/ui/leaders/`.

### Civs enumerated (48 total)

**22 base civs (no civmods.xml entry; stock definitions preserved):** Aztecs, British, Chinese, Dutch, Ethiopians, French, Germans, Haudenosaunee, Hausa, Inca, Indians, Italians, Japanese, Lakota, Maltese, Mexicans, Ottomans, Portuguese, Russians, Spanish, Swedes, UnitedStates.

**26 revolution civs promoted to top-level (in `data/civmods.xml`):** ANWNapoleonicFrance, ANWRevFrance, ANWAmericans, ANWMexicans, ANWCanadians, ANWFrenchCanadians, ANWBrazil, ANWArgentines, ANWChileans, ANWPeruvians, ANWColumbians, ANWHaitians, ANWIndonesians, ANWSouthAfricans, ANWFinnish, ANWHungarians, ANWRomanians, ANWBarbary, ANWEgyptians, ANWCentralAmericans, ANWBajaCalifornians, ANWYucatan, ANWRioGrande, ANWMayans, ANWCalifornians, ANWTexians.

---

## 2. Per-civ table

Notation: `civmods display` = string fetched via `<DisplayNameID>` → stringmods locID. `loading-screen flag` = `<HomeCityFlagIconWPF>` (the WPF asset shown on civ-pick / loading / home city). `in-game flag` = `<HomeCityFlagTexture>` / `<PostgameFlagTexture>`. For base civs no override exists, so all four columns rely on stock data; the reference file is treated as the authoritative external label.

### 2a. Base civs (22)

| canonical_name (REFERENCE) | civs.xml display | string-table | loading-screen flag | in-game flag | matches? |
|---|---|---|---|---|---|
| Aztecs / Montezuma II | stock | stock | stock (Mexica emblem) | stock | yes |
| British / Queen Elizabeth I | stock | stock | stock (UK flag) | stock | yes (label OK; portrait PNG `cpai_avatar_british_elizabeth.png` exists but is NOT wired into any XML — see §3) |
| Chinese / Kangxi Emperor | stock | stock | stock (Qing flag) | stock | yes |
| Dutch / Maurice of Nassau | stock | stock | stock (Prince's Flag) | stock | yes |
| Ethiopians / Menelik II | stock | stock | stock | stock | yes |
| French / Louis XVIII | stock | stock | stock (Bourbon Restoration) | stock | yes (label OK; portrait `cpai_avatar_french_bourbon.png` not wired in any XML) |
| Germans / Frederick the Great | stock | stock | stock (Prussian) | stock | yes |
| Haudenosaunee / Hiawatha | stock | stock | stock | stock | yes |
| Hausa / Usman dan Fodio | stock | stock | stock | stock | yes |
| Inca / Pachacuti | stock | stock | stock | stock | yes |
| Indians / Shivaji Maharaj | stock | stock | stock (Maratha) | stock | yes |
| Italians / Giuseppe Garibaldi | stock | stock | stock (Kingdom of Italy) | stock | yes |
| Japanese / Tokugawa Ieyasu | stock | stock | stock (Tokugawa crest) | stock | yes |
| Lakota / Chief Gall | stock | stock | stock | stock | yes (portrait `cpai_avatar_lakota_gall.png` exists, not wired) |
| Maltese / Jean Parisot de Valette | stock | stock | stock | stock | yes |
| Mexicans / Miguel Hidalgo y Costilla | stock | stock | stock (Mexican flag) | stock | yes — but DUPLICATE leader vs ANWMexicans (see §3) |
| Ottomans / Suleiman the Magnificent | stock | stock | stock | stock | yes |
| Portuguese / Prince Henry the Navigator | stock | stock | stock | stock | yes |
| Russians / Ivan the Terrible | stock | stock | stock | stock | yes (portrait `cpai_avatar_russians_ivan.png` exists, not wired) |
| Spanish / Isabella I of Castile | stock | stock | stock (Cross of Burgundy) | stock | yes (playercolors abbreviates to "Isabella I") |
| Swedes / Gustavus Adolphus | stock | stock | stock | stock | yes |
| UnitedStates / George Washington | stock | stock | stock (US flag) | stock | yes — but display string "United States" COLLIDES with revolution civ Americans (494003) which is also "United States" (see §3) |

Verdict for base civs: the reference file declares per-civ Legendary Leaders, but **no XML file in this mod actually re-skins the base-civ leader portrait or display name**. The new leader PNGs in `resources/images/icons/singleplayer/cpai_avatar_<civ>_<leader>.png` are dead assets w.r.t. the engine — only the stock `.ddt` avatars in `art/ui/singleplayer/cpai_avatar_<civ>.ddt` are loaded. (See §3 item B-1.)

### 2b. Revolution civs (26)

Columns: `civmods.xml line` | `<DisplayNameID>` → string | HomeCityFlagIconWPF (loading screen) | HomeCityFlagTexture (in-game) | PostgameFlagIconWPF | matches?

| canonical (REFERENCE) | civmods.xml | display | loading-screen flag | in-game flag tex | postgame WPF | matches? |
|---|---|---|---|---|---|---|
| Napoleonic France / Napoleon Bonaparte | L3,9,94,98,99,100 | "French Empire" | `Flag_French_Revolution_NE.png` | `objects\flags\french_revolution_ne` | `Flag_French_Revolution_NE.png` | partial — portrait uses generic `cpai_avatar_napoleonic_france.png` (L100) although the dedicated `cpai_avatar_napoleonic_france_napoleon.png` exists unused. |
| Revolutionary France / Robespierre | L270,276,361,365–367 | "French Republic" | `Flag_French_Revolution.png` | `objects\flags/revolutionary_france` | `Flag_French_Revolution.png` | yes |
| Americans / Thomas Jefferson | L537,543,631,635–637 | "United States" | `Flag_USA.png` | `objects\flags\USA` | `Flag_USA.png` | display NAME COLLIDES with stock UnitedStates civ; otherwise consistent. |
| Mexicans (Revolution) / Hidalgo | L807,813,902,906–908 | "Mexico" | `Flag_Mexican_Rev.png` | `objects\flags\mexican_rev` | `Flag_Mexican_Rev.png` | display label "Mexico" vs base civ "Mexicans": OK distinction, but both share leader Hidalgo (duplication). PostgameFlagTexture=`ingame_ui_postgame_flag_mexican` (without `_rev`) — possible inconsistency. |
| Canadians / Isaac Brock | L1063,1069,1157,1161–1163 | "Canada" | `Flag_Canadians.png` | `objects\flags\canadian` | `Flag_Canadians.png` | yes — but reference flag description says "British flag", which contradicts the `flag_hc_canadian.png` actually used. |
| French Canadians / Papineau | L1333,1339,1424,1425,1431 | "Lower Canada" | `Flag_SPC_Canadian.png` | `objects\flags\spc_canadians` | `Flag_SPC_Canadian.png` | yes |
| Brazil / Pedro I | L1600,1606,1696,1700–1702 | "Brazil" | `Flag_Brazilian.png` | `objects\flags\brazilian` | `Flag_Brazilian.png` | yes |
| Argentines / San Martin | L1872,1878,1967,1971–1973 | "Argentina" | `Flag_Argentinian.png` | `objects\flags\argentinian` | `Flag_Argentinian.png` | yes |
| Chileans / O'Higgins | L2128,2134,2223,2227–2229 | "Chile" | `Flag_Chilean.png` | `objects\flags\chilean` | `Flag_Chilean.png` | yes |
| Peruvians / Santa Cruz | L2384,2390,2479,2483,2485,2486 | "Peru" | `Flag_Peruvian.png` | `objects\flags\peruvian` | `Flag_Peruvian.png` | yes — but `playercolors.xml` L37 says leader = "Tupac Amaru II". |
| Columbians / Bolivar | L2646,2652,2741,2745–2747 | "Gran Colombia" | `Flag_Colombian.png` | `objects\flags\colombian` | `Flag_Colombian.png` | yes (note civ id is **Columbians** with a U, but display "Gran Colombia" with an O — minor stale spelling inside the civ id) |
| Haitians / Louverture | L2902,2908,2998,3002–3004 | "Haiti" | `Flag_Haitian.png` | `objects\flags\haitian` | `Flag_Haitian.png` | yes |
| Indonesians / Diponegoro | L3184,3190,3278,3282–3284 | "Indonesia" | `Flag_Indonesian.png` | `objects\flags\indonesian` | `Flag_Indonesian.png` | yes |
| South Africans / Paul Kruger | L3454,3460,3547,3551–3553 | "South Africa" | `Flag_South_African.png` | `objects\flags\south_african` | `Flag_South_African.png` | yes — but `playercolors.xml` L41 says leader = "Shaka Zulu". |
| Finnish / Mannerheim | L3723,3729,3816,3820–3822 | "Finland" | `Flag_Finnish.png` | `objects\flags\finnish` | `Flag_Finnish.png` | yes |
| Hungarians / Kossuth | L3982,3988,4076,4080–4082 | "Hungary" | `Flag_Hungarian.png` | `objects\flags\hungarian` | `Flag_Hungarian.png` | yes |
| Romanians / Cuza | L4242,4248,4336,4340–4342 | "Romania" | `Flag_Romanians.png` | `objects\flags\romanian` | `Flag_Romanians.png` | yes — but `playercolors.xml` L44 says leader = "Michael the Brave". |
| Barbary / Barbarossa | L4502,4508,4592,4596–4598 | "Barbary States" | `Flag_barbary.png` | `objects\flags\spc_barbary` | `Flag_barbary.png` | yes (note in-game tex `spc_barbary` differs from WPF base name `barbary`; PostgameFlagTexture is `flag_barbary`. Both files exist, no engine error.) |
| Egyptians / Muhammad Ali | L4748,4754,4839,4843–4845 | "Egypt" | `Flag_Egyptians.png` | `objects\flags\egyptian` | `Flag_Egyptians.png` | yes |
| Central Americans / Morazan | L4995,5002,5098,5102–5104 | "Central America" | `Flag_Central_American.png` | `objects\flags\mx_central_american` | `Flag_Central_American.png` | yes |
| Baja Californians / Alvarado | L5448,5455,5551,5555–5557 | "Baja California" | `Flag_baja_californian.png` | `objects\flags\mx_baja_californian` | `Flag_baja_californian.png` | yes — `playercolors.xml` L48 says leader = "Manuel Micheltorena". |
| Yucatan / Carrillo Puerto | L5901,5908,6004,6008–6010 | "Yucatán" | `Flag_yucatan.png` | `objects\flags\mx_yucatan` | `Flag_yucatan.png` | yes (display has accent á; reference uses unaccented "Yucatan") |
| Rio Grande / Canales Rosillo | L6354,6361,6457,6461–6463 | "Rio Grande" | `Flag_rio_grande.png` | `objects\flags\mx_rio_grande` | `Flag_rio_grande.png` | yes |
| Mayans / Canek | L6807,6814,6910,6914–6916 | "Maya" | `Flag_mayan.png` | `objects\flags\mx_mayan` | `Flag_mayan.png` | yes — `playercolors.xml` L51 says leader = "Tecun Uman". |
| Californians / Vallejo | L7260,7267,7363,7367–7369 | "California" | `Flag_californian.png` | `objects\flags\mx_californian` | `Flag_californian.png` | yes |
| Texians / Sam Houston | L7713,7720,7816,7820–7822 | "Texas" | `Flag_texan.png` | `objects\flags\us_texan` | `Flag_texan.png` | yes |

All 26 revolution flag PNGs referenced from `<HomeCityFlagIconWPF>` and `<PostgameFlagIconWPF>` exist on disk (verified by file-existence loop). All 26 portrait PNGs in `<HomeCityPreviewWPF>` exist on disk.

---

## 3. Inconsistencies found

### A — Display-name collisions / mismatches

- **A-1. "United States" duplicate display name.** stock `UnitedStates` civ shows "United States" (US flag); `ANWAmericans` also resolves to "United States" via `data/strings/english/stringmods.xml` L2131 `_locID='494003'` → "United States". In any lobby/civ-pick/scoreboard the player sees two civs with identical labels but different flags (the `ANWAmericans` HC flag is `Flag_USA.png`, base-civ stock is also USA flag). Recommended: rename `ANWAmericans` → e.g. "Republic of the United States", "American Republic", or "Jefferson's America" so the lobby distinguishes them. Reference file at `LEGENDARY_LEADERS_NATION_REFERENCE.txt` L466 does call it "Americans" and flag description "United States flag" — same flag, same name = unresolvable for the player.

- **A-2. Mexico duplication.** Stock `Mexicans` (display "Mexicans", leader Hidalgo per reference L320) vs `ANWMexicans` (display "Mexico" via `stringmods.xml` L2132 `494004`, leader Hidalgo per reference L803). Same leader on both rows, same flag family. The labels "Mexicans" vs "Mexico" do disambiguate, but `data/playercolors.xml` L25 says base-civ Mexicans leader = "Miguel Hidalgo" while L31 says `ANWMexicans` leader = **"Jose Maria Morelos"** — three sources disagree.

- **A-3. Civ id `Columbians` typo.** `civmods.xml` L2646 `<Name>ANWColumbians</Name>` (with U), but the displayed string `494011` is "Gran Colombia" (with O), README says "Columbians", reference doc says "Columbians" but flag PNG `Flag_Colombian.png` and texture `objects\flags\colombian` use the correct O spelling. The Mod-internal civ id is a stale typo carried over from an earlier rename. UI surfaces are mostly OK because the user only sees 494011 = "Gran Colombia"; only modders interacting with the id see the misspelling.

### B — Base-civ leader portraits/labels are documented but not wired

- **B-1. New leader portraits orphaned.** Files `cpai_avatar_british_elizabeth.png`, `cpai_avatar_lakota_gall.png`, `cpai_avatar_russians_ivan.png`, `cpai_avatar_french_bourbon.png` are present in `resources/images/icons/singleplayer/` (and referenced by `LEGENDARY_LEADERS_NATION_REFERENCE.txt` L41,281,381,121 plus by `resources/audio/standard_leader_manifest.json`), but no civ XML loads them. The README L15 claim "Queen Elizabeth I for British, Ivan the Terrible for Russians, Chief Gall for Lakota" therefore does not show up in the in-game civ picker for the 22 base civs (those still use the stock `art/ui/singleplayer/cpai_avatar_<civ>.ddt`). Reference file even acknowledges this for flags ("base-game asset (not overridden in this repo)") but for portraits it lists fresh PNG paths as if active.

- **B-2. Stale `playercolors.xml` leader names.** This file is the only mod-owned table that names base-civ + revolution-civ leaders, and several entries directly contradict `LEGENDARY_LEADERS_NATION_REFERENCE.txt`:
  - `data/playercolors.xml:31` `ANWMexicans` leader **"Jose Maria Morelos"** vs reference L803 "Miguel Hidalgo y Costilla".
  - `data/playercolors.xml:33` `ANWFrenchCanadians` leader **"Louis-Joseph de Montcalm"** vs reference L703 "Louis-Joseph Papineau".
  - `data/playercolors.xml:37` `ANWPeruvians` leader **"Tupac Amaru II"** vs reference L864 "Andres de Santa Cruz".
  - `data/playercolors.xml:41` `ANWSouthAfricans` leader **"Shaka Zulu"** vs reference L924 "Paul Kruger".
  - `data/playercolors.xml:44` `ANWRomanians` leader **"Michael the Brave"** vs reference L904 "Alexandru Ioan Cuza".
  - `data/playercolors.xml:48` `ANWBajaCalifornians` leader **"Manuel Micheltorena"** vs reference L503 "Juan Bautista Alvarado".
  - `data/playercolors.xml:51` `ANWMayans` leader **"Tecun Uman"** vs reference L783 "Jacinto Canek".
  - `data/playercolors.xml:32` `ANWCanadians` leader **"Sir Isaac Brock"** vs reference L583 "Isaac Brock" (cosmetic).
  - `data/playercolors.xml:14` Spanish leader **"Isabella I"** vs reference L400 "Isabella I of Castile" (cosmetic).
  This is the most user-visible textual discrepancy in the mod, since `playercolors.xml` is loaded at engine startup and is the closest thing to a single-source-of-truth mapping. Seven leaders are *categorically wrong*.

### C — Flag/portrait mismatches against the reference

- **C-1. Napoleonic France leader portrait.** `civmods.xml:100` sets `<HomeCityPreviewWPF>resources/images/icons/singleplayer/cpai_avatar_napoleonic_france.png</HomeCityPreviewWPF>`, but reference L825 lists `cpai_avatar_napoleonic_france_napoleon.png` (the more specific Napoleon-portrait variant exists on disk; appears in `git status` as untracked). Loading screen will show the generic banner instead of the Napoleon portrait the reference advertises.

- **C-2. Mexicans (base civ) portrait family.** Reference L321 lists `cpai_avatar_mexicans_hidalgo_base.png` for stock Mexicans, while the revolution civ uses `cpai_avatar_mexicans_hidalgo.png`. Both files exist; nothing in any mod-owned XML loads either for the base civ. Documented but not wired.

- **C-3. Canadians "British flag" claim.** Reference L587 says flag = "British flag", but `civmods.xml:1157` actually sets `<HomeCityFlagTexture>objects\flags\canadian</HomeCityFlagTexture>` and `<HomeCityFlagIconWPF>...Flag_Canadians.png</HomeCityFlagIconWPF>`. The data is internally consistent (Canadian flag everywhere), the reference doc is the stale entry.

- **C-4. Postgame flag texture for Mexicans (Revolution).** `civmods.xml:905` `<PostgameFlagTexture>ui\ingame\ingame_ui_postgame_flag_mexican</PostgameFlagTexture>` (no `_rev`), while WPF and HC textures use `mexican_rev`. The score/postgame screen will display the base-Mexican postgame flag rather than the revolutionary variant. Whether the `_rev` ddt actually exists in the stock game is unverifiable from this worktree (no `_rev` ddt is shipped here), so this may be intentional — but it does mean the loading-screen flag (revolutionary) and the postgame flag (Iturbide-era) differ.

- **C-5. Path-separator inconsistency in `ANWRevFrance`.** `civmods.xml:273` `<Portrait>objects\flags/french</Portrait>` and `:361` `<HomeCityFlagTexture>objects\flags/revolutionary_france</HomeCityFlagTexture>` mix `\` and `/` mid-path. The engine tolerates this on Windows; it's a code-smell, not a runtime bug.

### D — Stale references

- **D-1. `<HomeCityFlagButtonSet>` reuses base-civ button atlas.** Most revolution civs reuse stock atlases (`britishFlagBtn`, `swedishFlagBtn`, `ottomanFlagBtn`, `washingtonFlagBtn`, `frenchFlagBtn`, `hidalgoFlagBtn`). Six different revolution civs (`ANWSouthAfricans` L3548, `ANWIndonesians` L3279, `ANWFrenchCanadians` L1428, `ANWCanadians` L1158, `ANWHaitians` not — has its own; `ANWFinnish` L3817 etc.) bind to **other civs' button atlases**. Visual result: the lobby's small flag-button thumbnail can show the wrong national colour for those civs (e.g. Indonesian button shows British atlas slot), distinct from the loading-screen flag.

- **D-2. `<RolloverNameID>` for Napoleonic France points at 490002.** `civmods.xml:10` references `_locID='490002'` (defined `stringmods.xml:24`). Revolutionary France L277 uses `400020`. The 400020/490002 split is intentional but surfaces as **two leader-pop blurbs** (Napoleon's, Robespierre's). No bug, but the only base-civ rollover that lives at a 49xxxx id; all other 26 revolution civs live in the 400xxx block. Easy to introduce bugs when editing.

- **D-3. Avatar `.ddt` for revolution civs missing.** `art/ui/singleplayer/` ships `.ddt` AI avatars only for the 22 base civs. The 26 revolution civs rely on the WPF portrait alone. In score-screen surfaces that read the `.ddt` (rather than `HomeCityPreviewWPF`), the AI's avatar will fall back to a default. This explains why the README emphasises "lobby thumbnail to scoreboard" consistency — but the in-AI-pick avatar in singleplayer skirmish dialog will be missing for revolution civs.

### E — Files referenced but absent (none confirmed missing)

A file-existence sweep over every flag and portrait path written into `data/civmods.xml` returned **0 missing assets**. Specifically all 26 of `Flag_*.png` referenced by `<HomeCityFlagIconWPF>`/`<PostgameFlagIconWPF>` exist; all 26 of `cpai_avatar_*.png` referenced by `<HomeCityPreviewWPF>` exist. Underlying base-game `.ddt` flag/portrait textures referenced by `<HomeCityFlagTexture>`/`<PostgameFlagTexture>` could not be verified here because they live in the stock game data, not the worktree.

---

## 4. Recommended fixes (prioritised by user-visibility)

### Priority 1 — loading-screen / lobby surfaces

1. **`data/playercolors.xml`** — repair the 7 wrong leader names. (Leader name appears in the lobby tooltip & in some splash overlays.) Concrete edits:

   - `data/playercolors.xml:31` `leader="Jose Maria Morelos"` → `leader="Miguel Hidalgo y Costilla"`
   - `data/playercolors.xml:33` `leader="Louis-Joseph de Montcalm"` → `leader="Louis-Joseph Papineau"`
   - `data/playercolors.xml:37` `leader="Tupac Amaru II"` → `leader="Andres de Santa Cruz"`
   - `data/playercolors.xml:41` `leader="Shaka Zulu"` → `leader="Paul Kruger"`
   - `data/playercolors.xml:44` `leader="Michael the Brave"` → `leader="Alexandru Ioan Cuza"`
   - `data/playercolors.xml:48` `leader="Manuel Micheltorena"` → `leader="Juan Bautista Alvarado"`
   - `data/playercolors.xml:51` `leader="Tecun Uman"` → `leader="Jacinto Canek"`
   - Cosmetic: L14 `"Isabella I"` → `"Isabella I of Castile"`.

2. **Resolve the "United States" name collision (A-1).** Rename `_locID='494003'` in `data/strings/english/stringmods.xml:2131`:
   ```xml
   <String _locID='494003'>United States</String>
   ```
   to e.g.
   ```xml
   <String _locID='494003'>American Republic</String>
   ```
   so the lobby distinguishes stock `UnitedStates` (Washington) from `ANWAmericans` (Jefferson). Without this change the civ-pick screen shows two rows labelled identically.

3. **Wire the Napoleon portrait (C-1).** `data/civmods.xml:100`:
   ```xml
   <HomeCityPreviewWPF>resources/images/icons/singleplayer/cpai_avatar_napoleonic_france.png</HomeCityPreviewWPF>
   ```
   →
   ```xml
   <HomeCityPreviewWPF>resources/images/icons/singleplayer/cpai_avatar_napoleonic_france_napoleon.png</HomeCityPreviewWPF>
   ```
   so the loading screen for Napoleonic France actually shows Napoleon (the file exists; it's untracked in `git status`).

### Priority 2 — in-game label consistency

4. **Postgame flag for `ANWMexicans` (C-4).** `data/civmods.xml:905` `<PostgameFlagTexture>ui\ingame\ingame_ui_postgame_flag_mexican</PostgameFlagTexture>` → `..._mexican_rev` if the stock game ships that variant; otherwise leave a comment and continue using `_mexican` so the file is documented.

5. **Disambiguate stock Mexicans vs ANWMexicans leaders (A-2 / B-2).** Either:
   - Re-skin stock Mexicans to a non-Hidalgo leader (e.g. Benito Juárez or Iturbide) so the two civs do not double-bill the same historical figure, and update `data/playercolors.xml:25` and `LEGENDARY_LEADERS_NATION_REFERENCE.txt:320` accordingly; OR
   - Keep Hidalgo for revolution-Mexicans and pick a different leader for stock Mexicans.

6. **Resolve `ANWColumbians` typo (A-3).** Mass-rename `ANWColumbians` → `ANWColombians` across `civmods.xml`, `playercolors.xml:38`, all `ANW*homecity*.xml` filenames, AI script files in `game/ai/leaders/`, and anywhere referencing the id. Risky; only worth doing in a dedicated branch.

### Priority 3 — cosmetic / orphaned assets

7. **Wire base-civ leader portraits (B-1).** The 4+ files (`cpai_avatar_british_elizabeth.png`, `cpai_avatar_lakota_gall.png`, `cpai_avatar_russians_ivan.png`, `cpai_avatar_french_bourbon.png`, etc.) currently exist as decorative-only PNGs. To make the README claim true the mod must either (a) ship a `civs.xml` override or `civmods.xml` <Civ>` entry for each base civ that re-binds `<HomeCityPreviewWPF>` to the new portrait, or (b) generate `.ddt` versions and place them at `art/ui/singleplayer/cpai_avatar_<civ>.ddt`. (The latter is what stock loads.)

8. **Path-separator hygiene (C-5).** `data/civmods.xml:273,361` mix `\` and `/`. Normalize to `\` (matches the rest of the file) for consistency, but functionally inert.

9. **`<HomeCityFlagButtonSet>` should reference each civ's own atlas (D-1).** Several revolution civs reuse base-civ atlases; this makes the mini flag-button widget show the wrong colour. The fix requires authoring proper button-set atlases per civ — meaningful work, low priority.

10. **Update `LEGENDARY_LEADERS_NATION_REFERENCE.txt`.** This file claims to be auto-generated from `README.md` + `civmods.xml` + `aiLeaderQuotes.xs`. Since several leader assignments differ between sources (B-2), regenerate it after fixing `playercolors.xml`, or amend the generator to flag conflicts at build time.

---

### Summary of findings

- 0 missing flag/portrait assets among 52 verified file paths.
- 1 hard display-name collision ("United States" used by two civs).
- 7 wrong leader names in `data/playercolors.xml` that contradict the canonical reference.
- 1 mismatched portrait wiring for Napoleonic France (generic banner instead of Napoleon).
- 1 mismatched postgame flag texture for `ANWMexicans`.
- 1 civ-id typo (`ANWColumbians`) that surfaces only to modders.
- 4+ orphaned base-civ leader portraits documented but not loaded by any XML.
- 0 stale references to deleted/duplicated doctrines were found in `data/civmods.xml` or `data/strings/english/stringmods.xml`.

The headline issue is the **playercolors.xml leader-name drift** — that file is the only mod-owned table the engine consults at startup that names every leader, and it disagrees with the reference doc on 7 out of 48 nations.
