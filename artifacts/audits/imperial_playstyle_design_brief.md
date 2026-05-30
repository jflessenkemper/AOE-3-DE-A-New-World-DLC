# Imperial Playstyle — Design Brief

Research only. No edits performed. All paths are absolute.

---

## 0. Key terminology clarification (read first)

The mod uses the word "playstyle" in **two distinct senses** that are easy to confuse:

1. **Civ-doctrine playstyle (singular)** — every civ has exactly ONE
   `psTitle` string keying its overall doctrine
   (e.g. British → "Tudor naval and mercantile", Aztecs → "Flower War
   tribute aggression"). This is the value the in-tree modal renders as
   the headline. There are **46 of them** today (one per
   `<details class="nation-node">` in the HTML), each unique.
2. **Per-age strategy entry (plural)** — inside each civ-doctrine, an
   `ages` object holds five strings keyed
   `Discovery / Colonial / Fortress / Industrial / Imperial`. Each civ
   already has an `Imperial` entry, and each leader XS file already
   contains a fifth `cAge5` rule. This is NOT "an imperial playstyle" —
   it is the imperial-age slice of the civ's only playstyle.

**The user's claim "no civ has an imperial playstyle" is true in
sense (1) and false in sense (2).** No civ-doctrine `psTitle` is the
word "Imperial". The closest near-misses are:

| psTitle | Civ | File line | Comment |
|---|---|---|---|
| `"Sublime Porte gunpowder empire"` | Ottomans / Suleiman | `a_new_world.html:3373` | "empire" not "imperial" |
| `"Sagres carrack-and-padrao empire"` | Portuguese / Henry | `:3404` | ditto |
| `"Grande Armée Grand Battery empire"` | Napoleonic France / Napoleon | `:4076` | ditto |
| `"Imperial line and Hessian reserve"` | Brazil / Pedro I | `:3654` | the only `psTitle` containing the literal word "Imperial" — refers to the unit *Imperial Musketeer* line, not an imperial doctrine |

So Brazil is technically the only `psTitle` with the literal token
`Imperial`, and it's a unit-line reference — there is **no first-class
imperial-doctrine playstyle** anywhere in the mod. The brief that
follows treats sense (1): a new headline doctrine called Imperial,
selectable per civ.

---

## 1. Playstyle taxonomy (current state)

### 1a. Civ-doctrine playstyles (46 — one per nation)

Source: `a_new_world.html` lines 2854–4327 (`window.NATION_PLAYSTYLE = {…}` literal).
Validator: `tools/validation/validate_playstyle_modal.py`.
Test: `tests/validation/test_validate_playstyle_modal.py`.

Each entry is unique. Listed here `psTitle | nation | leader | bsTitle | HTML line`:

| psTitle | Nation | Leader | bsTitle | line |
|---|---|---|---|---|
| Flower War tribute aggression | Aztecs | Montezuma II | Jungle Guerrilla Network | 2858 |
| Tudor naval and mercantile | British | Elizabeth I | Naval Mercantile Compound | 2891 |
| Eight-Banner pacification macro | Chinese | Kangxi | Compact Fortified Core | 2923 |
| Stadtholder drill-and-bank | Dutch | Maurice of Nassau | Naval Mercantile Compound | 2957 |
| Solomonic highland modernization | Ethiopians | Menelik II | Highland Citadel | 2990 |
| Bourbon Restoration court army | French | Louis XVIII | Compact Fortified Core | 3024 |
| Hohenzollern oblique-order shock | Germans | Frederick the Great | Siege Train Concentration | 3056 |
| Confederacy forest warfare | Haudenosaunee | Hiawatha | Shrine or Trade Node Spread | 3087 |
| Sokoto jihad cavalry | Hausa | Usman dan Fodio | Distributed Economic Network | 3118 |
| Tawantinsuyu mass infantry | Inca | Pachacuti | Andean Terrace Fortress | 3151 |
| Maratha Ganimi Kava raid | Indians | Shivaji | Shrine or Trade Node Spread | 3183 |
| Risorgimento volunteer columns | Italians | Garibaldi | Republican Levee | 3213 |
| Bakufu shrine-and-musket order | Japanese | Tokugawa | Shrine or Trade Node Spread | 3244 |
| Bighorn all-cavalry war | Lakota | Chief Gall | Steppe Cavalry Wedge | 3275 |
| Great Siege bastion defense | Maltese | Valette | Highland Citadel | 3310 |
| Grito de Dolores levée | Mexicans (standard) | Hidalgo | Republican Levee | 3343 |
| Sublime Porte gunpowder empire | Ottomans | Suleiman | Siege Train Concentration | 3373 |
| Sagres carrack-and-padrao empire | Portuguese | Henry | Naval Mercantile Compound | 3404 |
| Romanov column-and-cossack mass | Russians | Ivan the Terrible | Cossack Voisko | 3437 |
| Reconquista Tercio precursor | Spanish | Isabella | Forward Operational Line | 3468 |
| Lion of the North combined arms | Swedes | Gustavus Adolphus | Siege Train Concentration | 3498 |
| Continental Army Fabian-to-Yorktown | United States | Washington | Republican Levee | 3529 |
| Granadero shock-cavalry liberation | ANW Argentines | San Martin | Forward Operational Line | 3559 |
| Californio frontier horse raid | ANW BajaCalifornians | Alvarado | Mobile Frontier Scatter | 3589 |
| Corsair raider economy | ANW Barbary | Barbarossa | Naval Mercantile Compound | 3622 |
| Imperial line and Hessian reserve | ANW Brazil | Pedro I | Distributed Economic Network | 3654 |
| Ranchero defense and trade | ANW Californians | Vallejo | Distributed Economic Network | 3689 |
| Blockhouse infantry frontier | ANW Canadians | Brock | Compact Fortified Core | 3720 |
| Federal Republic native muster | ANW Central Americans | Morazán | Distributed Economic Network | 3751 |
| Balanced Republican infantry | ANW Chileans | O'Higgins | Andean Terrace Fortress | 3784 |
| Llanero liberation sweeps | ANW Columbians | Bolívar | Forward Operational Line | 3817 |
| Nizam-i Cedid modernization | ANW Egyptians | Muhammad Ali | Highland Citadel | 3847 |
| Mannerheim-line ski infantry | ANW Finnish | Mannerheim | Compact Fortified Core | 3881 |
| Honved hussar uprising | ANW Hungarians | Kossuth | Steppe Cavalry Wedge | 3915 |
| Patriote militia and Iroquois levy | ANW French Canadians | Papineau | Civic Militia Center | 3947 |
| Mass infantry insurrection | ANW Haitians | Louverture | Jungle Guerrilla Network | 3977 |
| Java War guerrilla and kraton fort | ANW Indonesians | Diponegoro | Shrine or Trade Node Spread | 4010 |
| Indigenous insurrection mass | ANW Mayans | Canek | Jungle Guerrilla Network | 4043 |
| Grande Armée Grand Battery empire | ANW Napoleonic France | Napoleon | Forward Operational Line | 4076 |
| Andean fort line and native levy | ANW Peruvians | Santa Cruz | Andean Terrace Fortress | 4107 |
| Levée-en-masse Republic | ANW Revolutionary France | Robespierre | Republican Levee | 4140 |
| Rio Grande Republic horse | ANW RioGrande | Canales | Mobile Frontier Scatter | 4170 |
| Danubian Principalities consolidation | ANW Romanians | Cuza | Civic Militia Center | 4202 |
| Boer commando trader-cavalry | ANW SouthAfricans | Kruger | Naval Mercantile Compound | 4233 |
| Republic of Texas militia | ANW Texians | Houston | Forward Operational Line | 4265 |
| Maya levy uprising | ANW Yucatan | Carrillo Puerto | Jungle Guerrilla Network | 4295 |

Note: HTML has 46 entries. ANWMexicans (Hidalgo Revolution) shares
the standard "Mexicans Hidalgo" node by design — `playercolors.xml`
lists 47 civ rows. United States Washington also serves
ANWAmericans through Jefferson under a separate node. The 48
"civ × leader" total quoted in the brief is the playercolors-derived
roster including base French/Louis XVIII; some collapse for HTML
display.

### 1b. Buildstyles (14 reusable terrain doctrines)

Source: `game/ai/leaders/leaderCommon.xs` lines 191–340; constants in
`game/ai/core/aiGlobals.xs`.

```
cLLBuildStyleCompactFortifiedCore        (4 civs)
cLLBuildStyleDistributedEconomicNetwork  (4)
cLLBuildStyleForwardOperationalLine      (5)
cLLBuildStyleMobileFrontierScatter       (2)
cLLBuildStyleShrineTradeNodeSpread       (4)
cLLBuildStyleCivicMilitiaCenter          (2)
cLLBuildStyleSteppeCavalryWedge          (2)
cLLBuildStyleNavalMercantileCompound     (5)
cLLBuildStyleSiegeTrainConcentration     (3)
cLLBuildStyleJungleGuerrillaNetwork      (4)
cLLBuildStyleHighlandCitadel             (3)
cLLBuildStyleCossackVoisko               (1)
cLLBuildStyleRepublicanLevee             (4)
cLLBuildStyleAndeanTerraceFortress       (3)
```

Buildstyles are SHARED across civs (parameterised); civ-doctrines are
NOT shared.

### 1c. Per-age strategy strings (Discovery → Imperial)

Stored inline in each `NATION_PLAYSTYLE[civ].ages` object. Validator
asserts all 5 keys present and non-empty
(`tools/validation/validate_playstyle_modal.py:54`,
`REQUIRED_AGE_KEYS = ("Discovery", "Colonial", "Fortress", "Industrial", "Imperial")`).

### 1d. Confirmation of user's claim

**User's claim CONFIRMED in the strict reading:** no civ-doctrine
`psTitle` is "Imperial" or any synonym ("imperialist", "colonial
empire", etc.). The token "Imperial" appears only inside `ages.Imperial`
strings and as part of Brazil's "Imperial line" (referring to the
Imperial Musketeer card, not a doctrine).

---

## 2. Per-civ current playstyle list

Format: `civ_id | leader | psTitle (current) | leader_xs_file | rule lines`.

### Standard nations (22)

| civ_id | leader | current psTitle | leader file | rules (init / Disc / Col / For / Ind / Imp) |
|---|---|---|---|---|
| Aztecs | Montezuma II | Flower War tribute aggression | `game/ai/leaders/leader_montezuma.xs` | 23 / 47 / 70 / 96 / 122 / 147 |
| British | Elizabeth I | Tudor naval and mercantile | `leader_wellington.xs` (chatset), Elizabeth uses `leader_wellington.xs` for now per dispatcher; *Wellington personality file kept in tree*: `leader_wellington.xs` 177 imperial | (see leader_wellington.xs) |
| Chinese | Kangxi | Eight-Banner pacification macro | `leader_kangxi.xs` | 25 / 56 / 80 / 106 / 133 / 160 |
| Dutch | Maurice of Nassau | Stadtholder drill-and-bank | `leader_maurice.xs` | 26 / 57 / 80 / 106 / 133 / 159 |
| Ethiopians | Menelik II | Solomonic highland modernization | `leader_menelik.xs` | 27 / 57 / 80 / 106 / 131 / 157 |
| French | Louis XVIII | Bourbon Restoration court army | `leader_bourbon.xs` | 31 / 64 / 87 / 114 / 141 / 169 |
| Germans | Frederick the Great | Hohenzollern oblique-order shock | `leader_frederick.xs` | 29 / 60 / 82 / 108 / 133 / 159 |
| Haudenosaunee | Hiawatha | Confederacy forest warfare | `leader_hiawatha.xs` | 24 / 53 / 76 / 103 / 128 / 154 |
| Hausa | Usman dan Fodio | Sokoto jihad cavalry | `leader_usman.xs` | (init) / … / 154 imperial |
| Inca | Pachacuti | Tawantinsuyu mass infantry | `leader_pachacuti.xs` | … / 157 imperial |
| Indians | Shivaji | Maratha Ganimi Kava raid | `leader_shivaji.xs` | … / 157 imperial |
| Italians | Garibaldi | Risorgimento volunteer columns | `leader_garibaldi.xs` | 28 / 59 / 82 / 108 / 133 / 159 |
| Japanese | Tokugawa Ieyasu | Bakufu shrine-and-musket order | `leader_tokugawa.xs` | … / 155 imperial |
| Lakota | Chief Gall | Bighorn all-cavalry war | `leader_crazy_horse.xs` | 34 / 63 / 86 / 112 / 137 / 164 |
| Maltese | Valette | Great Siege bastion defense | `leader_valette.xs` | … / 156 imperial |
| Mexicans (std) | Hidalgo | Grito de Dolores levée | `leader_hidalgo.xs` | 26 / 57 / 80 / 106 / 131 / 157 |
| Ottomans | Suleiman | Sublime Porte gunpowder empire | `leader_suleiman.xs` | … / 158 imperial |
| Portuguese | Henry the Navigator | Sagres carrack-and-padrao empire | `leader_henry.xs` | 30 / 61 / 84 / 110 / 137 / 164 |
| Russians | Ivan the Terrible | Romanov column-and-cossack mass | `leader_catherine.xs` (Catherine personality, used for Ivan in current dispatcher; see playercolors note) | 37 / 67 / 90 / 116 / 141 / 167 |
| Spanish | Isabella | Reconquista Tercio precursor | `leader_isabella.xs` | 28 / 59 / 82 / 108 / 133 / 159 |
| Swedes | Gustavus Adolphus | Lion of the North combined arms | `leader_gustavus.xs` | 28 / 59 / 82 / 108 / 133 / 159 |
| United States | Washington | Continental Army Fabian-to-Yorktown | `leader_washington.xs` | … / 157 imperial |

NOTE: `leaderCommon.xs:469-490` maps `cMyCiv == cCivBritish` →
`gLLLeaderKey = "wellington"`, and `cCivRussians` → `"catherine"`. The
HTML and `playercolors.xml` say British/Elizabeth and Russians/Ivan.
This is a known gap — there are no `leader_elizabeth.xs` or
`leader_ivan.xs` files yet; `wellington.xs` and `catherine.xs` carry
the personality stand-in. The imperial design brief below uses the
authoritative `playercolors.xml` leaders (Elizabeth, Ivan).

### Revolution nations (24+, dispatched from `leader_revolution_commanders.xs` unless noted)

All revolution civs (except ANWNapoleonicFrance, ANWAmericans,
ANWMexicans which use dedicated leader files) share rule scaffolds
`rvltAge1Discovery / rvltAge2Colonial / rvltAge3Fortress /
rvltAge4Industrial / rvltAge5Imperial` keyed by `gRvltCivId 1..23`.
Imperial rule body: `leader_revolution_commanders.xs:737-776`.

| gRvltCivId | civ | leader | current psTitle | dispatch source |
|---|---|---|---|---|
| 1 | ANWCanadians | Isaac Brock | Blockhouse infantry frontier | `leader_revolution_commanders.xs:62-81` |
| 2 | ANWRevFrance | Robespierre | Levée-en-masse Republic | `:82-101` |
| 3 | ANWFrenchCanadians | Papineau | Patriote militia and Iroquois levy | `:102-121` |
| 4 | ANWBrazil | Pedro I | Imperial line and Hessian reserve | `:602-…` |
| 5 | ANWArgentines | San Martín | Granadero shock-cavalry liberation | (in body) |
| 6 | ANWChileans | O'Higgins | Balanced Republican infantry | (in body) |
| 7 | ANWPeruvians | Santa Cruz | Andean fort line and native levy | (in body) |
| 8 | ANWColumbians | Bolívar | Llanero liberation sweeps | (in body) |
| 9 | ANWHaitians | Louverture | Mass infantry insurrection | (in body) |
| 10 | ANWIndonesians | Diponegoro | Java War guerrilla and kraton fort | (in body) |
| 11 | ANWSouthAfricans | Kruger | Boer commando trader-cavalry | (in body) |
| 12 | ANWFinnish | Mannerheim | Mannerheim-line ski infantry | (in body) |
| 13 | ANWHungarians | Kossuth | Honved hussar uprising | (in body) |
| 14 | ANWRomanians | Cuza | Danubian Principalities consolidation | (in body) |
| 15 | ANWBarbary | Barbarossa | Corsair raider economy | (in body) |
| 16 | ANWEgyptians | Muhammad Ali | Nizam-i Cedid modernization | (in body) |
| 17 | ANWCentralAmericans | Morazán | Federal Republic native muster | (in body) |
| 18 | ANWBajaCalifornians | Alvarado | Californio frontier horse raid | (in body) |
| 19 | ANWYucatan | Carrillo Puerto | Maya levy uprising | (in body) |
| 20 | ANWRioGrande | Canales | Rio Grande Republic horse | (in body) |
| 21 | ANWMayans | Canek | Indigenous insurrection mass | (in body) |
| 22 | ANWCalifornians | Vallejo | Ranchero defense and trade | (in body) |
| 23 | ANWTexians | Houston | Republic of Texas militia | (in body) |
| — | ANWNapoleonicFrance | Napoleon | Grande Armée Grand Battery empire | `leader_napoleon.xs` (dedicated) |
| — | ANWAmericans | Jefferson | (uses Continental Army Fabian-to-Yorktown via Washington) | dispatched out (`:52-56`) |
| — | ANWMexicans | Hidalgo | Grito de Dolores levée | dispatched out → standard `leader_hidalgo.xs` |

---

## 3. Engine integration points

### 3a. XS-side wiring

A "playstyle" today is implemented as **per-leader rule blocks**,
not as a separately registered switchable strategy. The pattern
(canonical example: `game/ai/leaders/leader_napoleon.xs`):

1. `void initLeader<Name>(void)` — sets personality, biases, build-style
   (`llUse<Foo>Style(...)`), tactical doctrine, a `g<Name>RulesEnabled`
   flag, and emits `llProbe("meta.leader_init", …)`.
2. Five `rule` blocks named `<leader><Phase>` with
   `inactive minInterval N`, each guarded by the same `gEnabled`
   flag and `kbGetAge() == cAgeN` (or `>= cAge5` for Imperial). Each
   sets the `bt*` biases / `cv*` ceilings, optionally calls
   `llEnableForwardBaseStyle()` etc.
3. `void enableLeader<Name>Rules(void)` — `xsEnableRule(...)` for each.

Activation entry point: `leaderCommon.xs:469-490` (for standard civs)
and `:492-528` (for revolution civs) sets `gLLLeaderKey`, then a
matching `else if (gLLLeaderKey == "<key>")` cascade calls the
init/enable pair. Revolution civs without dedicated files are handled
by the shared `leader_revolution_commanders.xs:737` `rvltAge5Imperial`
rule via a `gRvltCivId == N` switch.

### 3b. Buildstyle wiring (the only currently-shared scaffold)

`leaderCommon.xs:139` — `llConfigureBuildStyleProfile(style, wallLevel,
earlyWalls, ecoMul, hcMul, milMul, towerMul, …)` is the single
scaffold; thirteen `llUse<Style>Style()` wrappers (lines 191–340)
parameterise it. **Civs share buildstyles freely** — see §1b counts.

### 3c. HTML / reference doc generation

The HTML data is **hand-edited**, not regenerated from a script.
Searches for `gen_legendary` / `regenerate_html` / `render_tree`
return nothing in `tools/`. Two parsers consume it:

- `tools/playtest/html_reference.py` — extracts the doctrine prose
  blob from `data-search` attributes for replay-validator contracts.
- `tools/validation/validate_playstyle_modal.py` — JSON-loads the
  `window.NATION_PLAYSTYLE = {…}` literal for shape validation.

`LEGENDARY_LEADERS_NATION_REFERENCE.txt:2` claims the file is
"Generated from README.md, data/civmods.xml, and aiLeaderQuotes.xs",
but no committed generator exists — the file is regenerated by hand
or by an out-of-tree script and is read-only at validation time.

### 3d. Tools that validate the playstyle list

- `tools/validation/validate_playstyle_modal.py` — main static check.
- `tools/playtest/html_reference.py` — derives doctrine contracts.
- `tools/aoe3_automation/probe_coverage_matrix.py` — runtime
  cross-check (uses playstyle keys for matrix cells).
- `tools/cardextract/build_search_index.py` — references playstyle
  text for site-wide search.
- `tools/validation/run_staged_validation.py` — orchestrator,
  registers the modal validator in the staged suite.

---

## 4. Imperial playstyle — historical design brief, per civ

Each block is the historical/thematic angle for an "imperial-doctrine"
playstyle peer to the existing civ-doctrine, framed by the
playercolors-mapped leader. Keep ~4 bullets.

### Standard nations

**Aztecs / Montezuma II — *Triple Alliance Tribute Empire***
- Tributary network of conquered altepetl funnels maize, cotton, and
  sacrificial captives back to Tenochtitlán; encode as forced
  resource conversion and accelerated trade-post tribute.
- Xochiyaoyotl ("flower war") doctrine — staged pre-imperial battles
  to keep elite cohorts blooded and harvest captives, not extermination.
- Theocratic centralization under Huitzilopochtli; Great Temple
  shipments scale with conquered cities.
- No standing professional army in the European sense; Eagle and
  Jaguar Knight veterans expand from a tightly held core via causeway
  logistics.

**British / Elizabeth I — *Tudor Maritime Empire***
- Naval supremacy via Royal Navy + privateer (Sea Dogs: Drake, Hawkins,
  Raleigh) — heavy galleon and privateer mass.
- Joint-stock chartered companies (Muscovy 1555, Levant 1581, EIC 1600)
  — trade-route monopolies as army funding, not gold/coin extraction.
- Plantation colonization (Roanoke 1585, Virginia 1607 forerunners) —
  forward-base style "plantation" outposts on contested map edges.
- Trained-bands militia at home, professional army deferred — modest
  army pop ceiling, heavy ranged-musket plus longbow legacy.

**Chinese / Kangxi Emperor — *High Qing Imperium***
- Eight-Banner system at peak: Manchu / Han / Mongol bannermen each
  with garrison territory; mass-banner army with rotating frontier
  duty.
- Three Feudatories War (1673–81) and Galdan campaigns (1690–96) —
  long-distance pacification expedition doctrine, supply-train heavy.
- Cartographic empire (Jesuit Kangxi Atlas) — bonus to map control /
  vision and cartographer-style scout corps.
- Tributary diplomacy — not conquest of allies but ritual
  subordination; trade-post bonuses scale with controlled posts.

**Dutch / Maurice of Nassau — *Stadtholder of an Overseas Republic***
- Maurice himself is more reformer than emperor — model the imperial
  playstyle as a VOC-administered overseas empire (Spice Islands,
  Ceylon, Cape) projected from Holland.
- Engineer corps + permanent army — line of fortifications across a
  Brabant-style front with Halberdier-Ruyter combined drill.
- Bank-funded military — banks scale up army cost reductions in
  Imperial.
- Hollandic water-line defensive flooding — terrain manipulation at
  home, expansionist abroad.

**Ethiopians / Menelik II — *Solomonic Imperial Restoration***
- Menelik's actual imperium: Adwa 1896 plus the conquests of Harar,
  Kaffa, Sidamo, Welayta — the imperial expansion southward from the
  highlands.
- European-rifle modernization (Mosin, Gras, Vetterli imports), mortars
  and Hotchkiss cannons — strong Industrial→Imperial artillery jump.
- Marriage and tribute consolidation of rival rases — turn allied
  natives into garrison troops.
- Highland citadel core (Entoto / Addis Ababa) but with imperial
  road-net to Harar, modeled as outward forward-base placements.

**French / Louis XVIII — *Bourbon Restoration Imperium***
- Bourbon revanche: reclaim Louisiana echoes via plantation colonial
  policy in the Antilles; reluctant European campaigning.
- Maison du Roi cavalry as the rebuilt elite; defensive to begin,
  pivoting to expeditionary after Quasi-Spanish 1823 (Hundred Thousand
  Sons of Saint Louis).
- Algiers 1830 expedition (Charles X but built up under LXVIII) —
  late-imperial overseas colonial push, Saharan expedition unit.
- Strong artillery and engineer arm inherited from the Empire,
  filtered through legitimist court restraint.

**Germans / Frederick the Great — *Brandenburg-Prussia Imperium***
- Silesian Wars (1740–63) imperial expansion at Habsburg expense —
  oblique-order shock attack into enemy core.
- Cantonal recruitment system for sustained Doppelsoldner / Uhlan
  mass; imperial pop ceiling raised.
- Mercenary leverage (Hessian and Württemberg loans) — Saloon
  shipments scale with treasury.
- Junker officer caste — tactical doctrine bonuses to cavalry charges
  and timing pushes.

**Haudenosaunee / Hiawatha — *Confederacy Pax Iroquois***
- Beaver Wars (1640s–1701) — empire of fur, projected from the Five
  Nations homeland against Huron, Erie, Susquehannock.
- Mourning War demographic absorption — captured villager units
  convert into your population (already partially modeled with native
  treaties; deepen).
- Trade-route control of Great Lakes routes — fur post yields scale
  exponentially.
- Council-of-Sachems diplomacy — multi-fire diplomacy bonuses,
  forward-warband rather than fortress imperialism.

**Hausa / Usman dan Fodio — *Sokoto Caliphate***
- Theocratic jihad-state founded 1804 — aggressive expansion under
  caliphal authority; Lifidi knight + Fula warrior mass.
- Trans-Saharan trade reorientation — tribute and tax (jangali) on
  pastoralists fund the standing cavalry.
- Emirate confederation — daughter states (Kano, Sokoto, Bauchi)
  modelled as forward town centers under shared bias.
- Islamic scholarship as soft-power — tech-tree discount on
  conversion-style upgrades.

**Inca / Pachacuti — *Tawantinsuyu, Four Quarters***
- Pachacuti as the founder-emperor (r. 1438) — codify the Sapa Inca
  system, mit'a labor obligation, and quipu census tracking.
- Imperial road network (Qhapaq Ñan) — speed bonus to villager and
  army transit between TCs along roads.
- Storehouses (qollqa) — surplus food/textile stockpile that feeds
  imperial campaigns; ramp up granary economy.
- Forced relocation (mitmaq) — settler reassignment ability,
  villager redirect bonus.

**Indians / Shivaji Maharaj — *Maratha Confederacy Empire***
- Shivaji's coronation 1674 as Chhatrapati — imperial title claimed
  in defiance of Mughal supremacy.
- Hill-fort (Killa) network — 300+ forts, fortress placement bonus
  per controlled hill terrain.
- Ganimi Kava (guerrilla) scaled into imperial scope — coordinated
  multi-column raids deep into Mughal territory.
- Ashtapradhan ministerial structure — administrative efficiency,
  tech research speed bonus.

**Italians / Garibaldi — *Risorgimento Italian Empire (Africa Orientale ambitions)***
- Garibaldi died before Italy's African empire (Eritrea 1882, Libya
  1911) — model "his" imperial playstyle as the Mille campaign scaled
  up: continental unification first, imperial overflow second.
- Bersaglieri rapid columns, Pavisier shield infantry — fast-moving
  national infantry; Volunteer Redshirt mass on the leading edge.
- Naval hop along Mediterranean coast (Marsala 1860 echoes) —
  amphibious landing doctrine.
- Anti-clerical / anti-Bourbon political bias — penalise enemy civic
  income on flanking maneuvers.

**Japanese / Tokugawa Ieyasu — *Bakufu Pax Tokugawa***
- Sankin-kōtai daimyo rotation — imperial control via ritual and
  hostage diplomacy rather than conquest; bonus to enemy unrest /
  desertion in Imperial.
- Sakoku closed-country economy — heavy negative trade bias,
  self-sufficient shrine-economy mass.
- Osaka Campaign (1614–15) — final imperial consolidation campaign,
  late-game siege army with Naginata Rider hammer.
- Internal canal and post-road network — domestic logistics surplus
  rather than overseas projection.

**Lakota / Chief Gall — *Greater Sioux Nation (resistance imperium)***
- Gall's imperial vision = pre-Reservation Lakota sovereignty over
  the Great Plains: Powder River, Black Hills, Big Horn basin.
- Mounted warfare expansion via buffalo-hunt mobility — economy and
  army share horse production.
- Inter-tribal alliance-building (Cheyenne, Arapaho) — native treaty
  bonuses scale per allied lodge.
- Anti-colonial rather than expansionist — the imperial playstyle is
  "drive the bluecoats off our map" with maximum cavalry pressure
  and trail-of-burned-forts harassment.

**Maltese / Valette — *Order of St. John, Imperium of Faith***
- Valette's victory at the Great Siege 1565 — the imperial playstyle
  is held-territory empire, not territorial expansion.
- Hospitaller corsair fleet and Tripoli/Lepanto naval projection —
  amphibious raiding instead of land conquest.
- Knightly orders as administrative caste — Hospitaller production
  cap raised at Imperial; chapter shipments.
- Counter-Reformation papal alignment — diplomatic bonus from
  Catholic civs.

**Mexicans (standard) / Hidalgo — *Republican Imperial Reach (post-1821 ambition)***
- Hidalgo died in 1811 but the imperial playstyle should reflect what
  insurgent Mexico became: brief First Empire under Iturbide, then
  Republic with imperial reach to Guatemala and California.
- Campesino-led mass infantry (Insurgentes scaling into Soldado
  professional line).
- Bajío silver-mine economy — coin-heavy trickle.
- Federal-vs-centralist tension as an internal "civil
  reorganization" event during Imperial transition.

**Ottomans / Suleiman — *Sublime Porte at Apex***
- Suleiman's reign 1520–66 = Ottoman imperial summit — Mohács 1526,
  Vienna 1529, Buda, Baghdad, Aden, Algiers.
- Janissary corps + Sipahi feudal cavalry + Devshirme recruitment;
  imperial pop ceiling significantly raised.
- Massive bombard park (Urban-style) — siege train doubled in
  Imperial.
- Kanun legal code + Suleymaniye public works — domestic civic bonus
  funding the campaigning.

**Portuguese / Henry the Navigator — *Estado da Índia & Atlantic Empire***
- Henry's imperial vision: feitoria (factory-fort) chain from Sagres
  → Mina → Goa, anchored by carrack and caravel routes.
- Padrão (stone marker) trade post placement — imperial-tier post
  upgrades double yields.
- Spice monopoly economy — heavy positive trade and naval bias.
- Small home army, large overseas garrison fleet — modest land pop,
  large dock pop ceiling.

**Russians / Ivan the Terrible — *Tsardom of All Russia***
- Ivan's coronation 1547 as Tsar — first "imperial" Russian title;
  imperial playstyle codifies the Kazan (1552) / Astrakhan (1556)
  conquests.
- Streltsy permanent musketeer corps — line infantry mass at
  Imperial; Oprichnik shock cavalry as terror reserve.
- Volga-Caspian trade-and-river expansion — strong upriver heading,
  river-fort placements.
- Boyar terror-reform — debuff own villager output briefly in
  Imperial transition (the Oprichnina cost), counterbalanced by
  army surge.

**Spanish / Isabella — *Hapsburg-Castilian Composite Empire***
- Isabella's actual successor empire (Charles V / Philip II) projected
  back — Reconquista finished 1492, Granada becomes the launch pad
  for transatlantic empire.
- Conquistador shipments: Cortés / Pizarro analogue forward-base
  drops with Rodelero + Lancer.
- New World silver trickle — economic surge tied to controlled
  trade routes.
- Inquisitorial / Catholic-monarch civic anchor — buff to cathedral /
  shrine production.

**Swedes / Gustavus Adolphus — *Stormaktstiden Baltic Empire***
- Gustavus' imperial program: Baltic Dominium Maris Baltici — Riga,
  Pomerania, Stralsund, German campaign 1630.
- Mobile field artillery (leather cannon and 3-pounder regimental
  guns) — artillery weight retained at Imperial, mobile not massed.
- Carolean-line mass with Hakkapelit cavalry shock — Caroline army
  doctrine actually formalized post-Gustavus but historically rooted.
- Torp-system soldier-cottage economy — settler/soldier hybrid
  trickle.

**United States / Washington — *Manifest-Destiny Republican Imperium***
- Washington as Cincinnatus — declines crown but the republic he
  founds projects continental empire (Louisiana 1803, Mexican Cession
  1848).
- Continental Army professionalization — Regular musketeer mass with
  Sharpshooter rangers as the elite line.
- Federal-state militia split — mass cheap militia plus elite line
  available in Imperial.
- Anti-imperial founding myth — restraint penalty on declared war
  but bonus on counter-attack windows.

### Revolution nations (24 entries)

**ANW Argentines / San Martín — *Liberation-Marshal Imperium***
- San Martín's project: independent Río de la Plata, then liberate
  Chile and Peru (1817 Andes crossing, 1821 Lima).
- Granadero a Caballo regiment — elite mounted shock corps;
  cavalry-dominant imperial mass.
- Pampas cattle economy — coin-heavy ranching trickle.
- Protectoral-monarchy ambivalence — imperial playstyle reflects
  Sanmartiniano centralism rather than federal Argentina.

**ANW BajaCalifornians / Alvarado — *Californio Departmental Frontier***
- Alvarado's "free state of Alta California" 1836–42 — semi-autonomous
  imperial reach over the peninsula and missions.
- Mission-secularization estate redistribution — econ bonus from
  captured / converted mission posts.
- Vaquero ranchero cavalry — mobile horse-raiding mass.
- US-annexation backdrop — naval interception event during Imperial.

**ANW Barbary / Barbarossa — *Algiers-Ottoman Tributary Pirate State***
- Barbarossa's imperium: Algiers + Tunis as Ottoman vassal regencies;
  Mediterranean fleet under Kapudan Pasha command.
- Corsair raid economy — captured-ship resource trickle.
- Bombarding sea-power — galiot + xebec fleet, late Imperial heavy
  ship.
- Slave market and ransom diplomacy — coin trickle from raid camps.

**ANW Brazil / Pedro I — *Empire of Brazil 1822–31***
- Pedro's actual empire — Septembrist proclamation, Cisplatine War
  (1825–28), absolutist crown over slave-coffee-sugar economy.
- Plantation economy — coin-from-coffee trickle; villager-as-laborer
  bias.
- Imperial Guard German Hessian core (1824 mercenary contract) —
  Saloon shipments featuring Hessian Jäger and Doppelsoldner.
- Cisplatine campaign — naval-amphibious projection along the Plate.

**ANW Californians / Vallejo — *Sonoma Frontier Empire***
- Vallejo's military-administrative jurisdiction in Northern California
  — mission-presidio frontier dominion.
- Defensive imperial — hold the territory rather than expand;
  presidio fort line.
- Cattle and tallow trade with Russian-American Co. (Fort Ross) —
  trade-post bonus.
- Bear Flag Revolt 1846 collapse event — late-imperial debuff
  representing US annexation pressure.

**ANW Canadians / Brock — *British North American Imperium (defensive)***
- Brock's imperial playstyle = empire-defended-from-within: 1812
  defense of Upper Canada with Tecumseh's confederacy.
- Native-British alliance — Iroquois loyalist + Tecumseh-style
  Shawnee deck.
- Blockhouse fort line on the frontier — fortress placement scaled
  to map edges.
- Royal Navy lake control — Great Lakes warship priority.

**ANW Central Americans / Morazán — *Federal Republic of Central America***
- Morazán's federal imperium 1830–39 — Guatemala, El Salvador,
  Honduras, Nicaragua, Costa Rica under one flag.
- Liberal-reform civic anchor — town center radius bonus.
- Native muster — Maya / Pipil militia recruitment.
- Coffee economy plus mahogany — trade-post and lumber-yield
  scaling.

**ANW Chileans / O'Higgins — *Patria Nueva Republican Imperium***
- O'Higgins' supreme-directorship 1817–23 — Andean defensive empire
  facing Spanish reaction from Peru.
- Chacabuco / Maipú style fort-line warfare — Compact Andean
  citadel placement.
- Cochrane fleet — naval projection up the Pacific coast.
- Nitrate + copper economy (proto-) — late imperial mineral
  trickle.

**ANW Columbians / Bolívar — *Gran Colombia Bolivarian Imperium***
- Bolívar's actual imperial project: Gran Colombia 1819–31
  (Venezuela + New Granada + Quito + Panamá), aspirational Andean
  Federation.
- Llanero light-cavalry Páez-style sweeps — fastest cavalry mass at
  Imperial.
- Liberation campaigns — forward-base in enemy territory each age.
- Caudillo-fragmentation event — late-imperial dissent risk reflected
  as army-cohesion debuff if pop ceiling untapped.

**ANW Egyptians / Muhammad Ali — *Pasha of Egypt and the Sudan***
- Muhammad Ali's actual imperium: Sudan 1820, Hejaz, Levant 1831–40,
  Crete; Egyptian-Ottoman war.
- Nizam-i Cedid French-trained line infantry — heavy musketeer-mass
  + Hotchkiss-style artillery.
- Cotton-monopoly economy — single-resource imperial-tier yield.
- Mehmet Ali's industrialization — early-imperial factory analog
  buff.

**ANW Finnish / Mannerheim — *Greater Finland (Suur-Suomi) defensive imperium***
- Mannerheim's Karelia / East Karelia ambition 1918–44 — defensive
  imperial reach into ethnically Finnish Russian territory.
- Mannerheim Line entrenched defense — strong fortress placement,
  late forward-base.
- Ski-jaeger mobility in forest — light-infantry stealth movement.
- Civil War legacy split — early-imperial choice to lean
  conservative vs liberal recruitment.

**ANW French Canadians / Papineau — *Patriote Republican Imperium***
- Papineau's vision: independent Lower Canada republic with Iroquois
  and habitant militia (1837–38 rebellion).
- Civic militia center — slow imperial-tier upgrades from Manor
  parishes.
- Iroquois levy alliance — native warrior shipments.
- Anti-British counter-empire — defensive imperial flavor; not
  expansionist.

**ANW Haitians / Louverture — *Black Imperium of Saint-Domingue***
- Toussaint's 1801 constitution — governor for life with imperial
  prerogative; Dessalines later crowns himself emperor.
- Maroon and ex-slave mass infantry — large pop ceiling, cheap
  insurgent units.
- Plantation reorganization (free labor on sugar/coffee) — economic
  bonus per converted estate.
- Anti-French / anti-Spanish posture — buff vs European civs in
  defensive battles.

**ANW Hungarians / Kossuth — *Honvéd Republican Imperium 1848–49***
- Kossuth's revolutionary government — independent Hungary projecting
  Magyar suzerainty over Croatia / Transylvania / Slovakia.
- Honvéd hussar and uhlan mass — strongest cavalry weight among
  Revolution civs.
- National Guard levée — cheap militia spam scaling with town centers.
- Russian-intervention collapse event — late imperial pressure, AI
  must spike before turn 5.

**ANW Indonesians / Diponegoro — *Mataram-Yogyakarta Defensive Imperium***
- Diponegoro's Java War 1825–30 — sultanate-led religious imperium
  resisting Dutch.
- Kraton-fort defense + jungle guerrilla — combined buildstyle
  signature; raise fortress level in Imperial.
- Native Javanese levée plus Bugis mercenary — auxiliary mass.
- Spice and rice economy — heavy food trickle, low coin.

**ANW Mayans / Canek — *Caste-War Indigenous Imperium***
- Canek's 1761 Cisteil rebellion (anachronized — but the playstyle
  represents the long Caste War aspiration).
- Indigenous mass infantry levy — cheap pop ceiling.
- Cenote-and-jungle terrain control — chokepoint walling style with
  Maya fort.
- Anti-Spanish creole resistance — buff vs Spanish/Mexicans.

**ANW Napoleonic France / Napoleon — *Premier Empire Français***
- Already partly modeled. Imperial playstyle = canonical Grande
  Armée at full corps strength: Imperial Guard, Grand Battery,
  Cuirassier wing, Continental System trade-refusal.
- Marshalate command tree — five-marshal-style shipment options.
- Conscription via Class Levy — pop ceiling 180.
- Continental Blockade hard trade penalty + native penalty.

**ANW Peruvians / Santa Cruz — *Peru-Bolivian Confederation 1836–39***
- Santa Cruz's actual imperium: federation of North/South Peru +
  Bolivia under his Protectorate.
- Andean fort-line + native Aymara levy — terrace-fortress placement.
- Silver from Potosí — coin trickle.
- Chilean War of Confederation collapse — late-imperial threat.

**ANW Revolutionary France / Robespierre — *Republican Anti-Imperium***
- Robespierre opposed imperial titles — the "imperial" playstyle for
  this civ is the Terror-state at its export-revolution apex (1794
  Sister Republics: Batavian, Helvetic, Cisalpine).
- Levée en masse mass conscription — largest infantry pop ceiling.
- Committee of Public Safety civic anchor — coup-of-thermidor
  collapse risk modelled as a brief late-imperial debuff.
- Sans-culotte free-corps native-style auxiliaries.

**ANW RioGrande / Canales — *Republic of the Rio Grande 1840***
- Canales' separatist republic on the Texas-Tamaulipas-Coahuila
  borderlands — short-lived imperial reach over Northern Mexico.
- Vaquero / Chinaco horse mass — fastest cavalry at Imperial.
- Border-raid frontier scatter buildstyle scaled up.
- Centralist-Mexican collapse event — political defeat rather than
  battlefield.

**ANW Romanians / Cuza — *United Principalities Imperium***
- Cuza's 1859–66 union of Wallachia and Moldavia — proto-Romanian
  imperial reach toward Transylvania and Dobruja.
- Land-reform peasant levy — cheap militia mass.
- Phanariot legacy + Western-trained Dorobanti — mixed line infantry
  + Russian-trained line + French-style Rosior dragoon.
- Ottoman-suzerain to full-independent transition — late imperial
  political pivot event.

**ANW SouthAfricans / Kruger — *Boer Republican Imperium***
- Kruger's Transvaal — gold-mine state, defensive empire against
  British encroachment (Jameson Raid, Second Boer War).
- Commando-cavalry mounted infantry — fast horse-rifle hybrid.
- Witwatersrand gold economy — coin spike at Industrial→Imperial.
- Volksraad civic anchor + laager defensive doctrine — strongpoint
  laagers as semi-mobile fort.

**ANW Texians / Houston — *Republic of Texas 1836–46***
- Houston's actual republic — independent Texas claiming up the Rio
  Grande and into Santa Fe.
- Volunteer militia + Texas Rangers — frontier counter-punch
  doctrine.
- Cotton-and-cattle economy + land-grant settlement — villager pop
  ceiling raised.
- US-annexation 1845 — late-imperial federation event (resource
  influx).

**ANW Yucatan / Carrillo Puerto — *Yucatecan Socialist Imperium***
- Carrillo Puerto's 1922–24 governorship — "Apostle of the Maya
  Race", agrarian-socialist regional autonomy.
- Henequén plantation economy — coin trickle with villager
  reorganization buff.
- Mayan auxiliary levy — native warrior shipments.
- Anti-Mexican-federal stance + 1924 collapse — late-imperial
  political event.

---

## 5. Recommendation: shared scaffold vs per-civ unique

**Recommend a hybrid: a single shared scaffold that delegates to a
per-civ tuning block — exactly mirroring the existing
`leader_revolution_commanders.xs:737-776` `rvltAge5Imperial` pattern.**

Justification from §3:

- Buildstyles are already shared (14 styles → 46 civs) via parameterised
  `llConfigureBuildStyleProfile`. Pattern proven scalable.
- Per-age rules in dedicated leader files (Napoleon, Catherine,
  Frederick, etc.) all share the same shape: 5 rules guarded by
  `kbGetAge() == cAgeN`, body sets `bt*` biases. This is mechanical
  duplication ripe for a scaffold.
- The revolution dispatcher already proves a single rule body can
  carry 23 civ-specific tunings via a `gRvltCivId` switch. Extending
  that switch to all 48 civs (with new `gLLImperialCivId` index)
  would let one new XS file, e.g. `game/ai/playstyles/imperial.xs`,
  hold all imperial-doctrine tuning vectors.
- The HTML `NATION_PLAYSTYLE` modal already has an `ages.Imperial`
  string slot per civ — adding a peer "imperialPsTitle" / "imperialAges"
  field is a localized JSON edit, not a structural change.
- 48 hand-authored files would duplicate ~120 lines × 48 = ~5760 lines
  of near-identical scaffolding. A single scaffold + 48 tuning rows
  (~6 lines each) is ~400 lines total.

**Concrete proposal:**

1. New file `game/ai/playstyles/imperial.xs` — defines
   `initImperialPlaystyle()`, five rules
   `imperialAge1..imperialAge5`, each with a `gLLImperialCivId`
   switch. Re-uses existing `bt*` and `cv*` knobs.
2. Dispatcher in `leaderCommon.xs` — extend `gLLLeaderKey` cascade to
   set `gLLImperialCivId` and call `initImperialPlaystyle()` after
   the existing `initLeader<Name>()`.
3. HTML — extend `window.NATION_PLAYSTYLE[civ]` schema with optional
   `imperialPsTitle`, `imperialAges`, etc., and the modal's renderer
   gains a "Switch playstyle" tab. Keep current civ-doctrine intact
   for backwards compat.
4. The user asked for an imperial playstyle for **every** nation, so
   pre-populate all 48 entries from §4 above.

---

## 6. Test surfaces (extend for 100% coverage)

All paths absolute. These are everywhere a new "imperial" playstyle
must be wired:

### Static validators
- `/var/home/jflessenkemper/AOE-3-DE-Legendary-Leaders-AI/.claude/worktrees/hungry-banzai-e122dc/tools/validation/validate_playstyle_modal.py`
  — extend `REQUIRED_STRING_FIELDS` and/or add a new
  `REQUIRED_IMPERIAL_FIELDS` block; add `Imperial` peer-doctrine
  presence assertion.
- `/var/home/jflessenkemper/AOE-3-DE-Legendary-Leaders-AI/.claude/worktrees/hungry-banzai-e122dc/tests/validation/test_validate_playstyle_modal.py`
  — extend fixture (lines 23, 95–99) with imperial test cases:
  must cover both presence and absence of the new field.
- `/var/home/jflessenkemper/AOE-3-DE-Legendary-Leaders-AI/.claude/worktrees/hungry-banzai-e122dc/tools/validation/run_staged_validation.py`
  — orchestrator (line 2 imports validator); ensure new check is in
  the staged list.
- `/var/home/jflessenkemper/AOE-3-DE-Legendary-Leaders-AI/.claude/worktrees/hungry-banzai-e122dc/tools/validation/validate_xs_scripts.py`
  — XS syntax validator (referenced from
  `tests/validation/test_validate_xs_scripts.py`); will catch new
  `imperial.xs` file.
- `/var/home/jflessenkemper/AOE-3-DE-Legendary-Leaders-AI/.claude/worktrees/hungry-banzai-e122dc/tools/validation/validate_html_vs_mod.py`
  — HTML cross-check; needs to know the new imperial playstyle is a
  legitimate doctrine.
- `/var/home/jflessenkemper/AOE-3-DE-Legendary-Leaders-AI/.claude/worktrees/hungry-banzai-e122dc/tools/validation/validate_civ_crossrefs.py`
  + matching test
  `tests/validation/test_validate_civ_crossrefs.py`
  — civ-list cross-reference; ensure all 48 civs have imperial entry.
- `/var/home/jflessenkemper/AOE-3-DE-Legendary-Leaders-AI/.claude/worktrees/hungry-banzai-e122dc/tools/validation/validate_personality_overrides.py`
  — personality file integrity; new playstyle may need new
  personality keys.

### Replay / runtime checks
- `/var/home/jflessenkemper/AOE-3-DE-Legendary-Leaders-AI/.claude/worktrees/hungry-banzai-e122dc/tools/playtest/html_reference.py`
  — doctrine-contract parser (lines 53–82 wall/naval/forward keyword
  maps); add imperial-keyword recognizers.
- `/var/home/jflessenkemper/AOE-3-DE-Legendary-Leaders-AI/.claude/worktrees/hungry-banzai-e122dc/tools/playtest/expectations.py`
  — runtime expectation surface; add imperial-mode expectations.
- `/var/home/jflessenkemper/AOE-3-DE-Legendary-Leaders-AI/.claude/worktrees/hungry-banzai-e122dc/tools/playtest/replay_probes.py`
  — probe extractors; ensure `meta.leader_init` / new
  `meta.playstyle_active` probe is captured.
- `/var/home/jflessenkemper/AOE-3-DE-Legendary-Leaders-AI/.claude/worktrees/hungry-banzai-e122dc/tests/playtest/test_replay_probes.py`
  — extend.
- `/var/home/jflessenkemper/AOE-3-DE-Legendary-Leaders-AI/.claude/worktrees/hungry-banzai-e122dc/tests/playtest/test_expectations.py`
  — extend.

### Search / coverage tools
- `/var/home/jflessenkemper/AOE-3-DE-Legendary-Leaders-AI/.claude/worktrees/hungry-banzai-e122dc/tools/aoe3_automation/probe_coverage_matrix.py`
  — playstyle-axis matrix; add imperial column.
- `/var/home/jflessenkemper/AOE-3-DE-Legendary-Leaders-AI/.claude/worktrees/hungry-banzai-e122dc/tools/cardextract/build_search_index.py`
  — site search; index new psTitles.

### Reference docs
- `LEGENDARY_LEADERS_NATION_REFERENCE.txt` — add per-nation imperial
  block (current `Expected playstyle:` line is the obvious target).
- `a_new_world.html` — extend `window.NATION_PLAYSTYLE`
  entries; modal renderer (`renderPlaystyle` line 4339).
- `README.md` — playstyle section.
- `docs/testing-harness.md` — note new validator hooks.

### CI workflows
- `/var/home/jflessenkemper/AOE-3-DE-Legendary-Leaders-AI/.claude/worktrees/hungry-banzai-e122dc/.github/workflows/playstyle-modal-validation.yml`
  — runs `validate_playstyle_modal.py` on every push; will start
  failing immediately if HTML is updated before XS, so coordinate.
- `/var/home/jflessenkemper/AOE-3-DE-Legendary-Leaders-AI/.claude/worktrees/hungry-banzai-e122dc/.github/workflows/validation-suite.yml`
  — full suite gate.

---

## Appendix: counts
- Standard nations: 22 (`leaderCommon.xs:469-490` cascade).
- Revolution nations dispatched bespoke: 23
  (`leader_revolution_commanders.xs:14-35` legend) + 3 dedicated
  (Napoleonic France, Americans/Jefferson, Mexicans/Hidalgo) = 26
  revolution civs total.
- HTML nation-nodes: 46 (Mexicans rev shares standard node;
  Americans rev has its own Jefferson node).
- `playercolors.xml`: 47 explicit civ rows
  (`data/playercolors.xml:6-53`).
- Imperial-doctrine briefs in §4: 22 standard + 22 revolution = 44
  written; gaps (USA-Jefferson Revolution, Standard-Mexicans
  duplicate) noted inline.
