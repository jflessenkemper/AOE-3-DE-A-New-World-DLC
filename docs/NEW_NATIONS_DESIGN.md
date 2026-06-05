# New Standalone Nations — Design (decks · walling · per-age · portrait)

Mid-game revolting is now disabled (`gANWAllowRevolt=false` in aiGlobals.xs) —
the nation you pick is the nation you play. This promotes the former
revolt-targets to standalone, lobby-selectable civs. Below is the
implementation-ready design for each.

**Asset status:** the 5 American nations are base-game Mexican revolutions and
already have ANW portraits + flags (assets exist). **Belgians & Walloons have
no assets and no base-game revolution** — they need art sourced before they can
ship (flagged per nation).

Each civ, once designed, is wired in via the existing recipe (as for
ANWCanadians): `data/civmods.xml` + `data/anwhomecity<civ>.xml` +
`data/decks.json` + `anw_civ_picker_map.py` + `aiWallKnobsByCiv.xs` +
`playstyle_spec.json` per_age + a leader entry.

Wall-knob row order: `strategy, radius, gates, age2stone, trigger_age,
seg_len, towers, secondary, vils, fwd_bias, outer_ring, outposts, repair,
closure_pct, no_water`.

---

## 1. Central Americans — Francisco Morazán
- **Parent / era:** Spanish/Mexican · Federal Republic of Central America (1823–1841).
- **Portrait:** `cpai_avatar_central_americans_morazan.png` · **Flag:** `Flag_Central_American.png`.
- **Doctrine:** Liberal-federalist militia army; mountainous isthmus → defensible
  passes; machete light infantry, citizen militia, few cannon.
- **Walling — FrontierPalisades (3):** `3, 18, 3, false, 2, 20, 4, 1, 5, 0.4, 4, 3, 3, 100, true`
  (palisade frontier with chokepoint fallback at cordillera passes).
- **Per-age:**
  - Disc: defensive, eco/scout.
  - Colonial: defensive · inf 0.55–0.80 cav 0.10–0.30 art 0.00–0.10 (militia).
  - Fortress: offensive (Morazán's campaigns) · inf 0.50–0.72 cav 0.15–0.35 art 0.05–0.20.
  - Industrial: offensive · inf 0.45–0.68 cav 0.15–0.35 art 0.10–0.25.
  - Imperial: offensive · inf 0.45–0.65 cav 0.15–0.35 art 0.12–0.30.
- **Deck theme:** militia/insurgente infantry shipments, machete cavalry,
  "Federation Unity" (eco/unity), fortified-pass cards, light-cannon batches.

## 2. Californians — Mariano Vallejo
- **Parent / era:** Mexican · California (Bear Flag) Republic (1846).
- **Portrait:** `cpai_avatar_californians_vallejo.png` · **Flag:** `Flag_californian.png`.
- **Doctrine:** Californio rancho cavalry — vaqueros & lancers, fast mobile
  raiding, light on perimeter (open ranch country).
- **Walling — MobileNoWalls (5), Coastal fallback:** `5, 0, 0, false, 5, 0, 0, 2, 0, 0.0, 0, 4, 0, 0, true`.
- **Per-age:**
  - Disc: offensive, scout.
  - Colonial: offensive · cav 0.40–0.65 inf 0.25–0.50 art 0.00–0.10 (lancers).
  - Fortress: offensive · cav 0.40–0.62 inf 0.25–0.50 art 0.05–0.20.
  - Industrial/Imperial: offensive, cavalry-led.
- **Deck theme:** Californio lancer/vaquero shipments, rancho economy (cattle/
  horse), Bear Flag militia, mission-supply cards.

## 3. Baja Californians — Alvarado
- **Parent / era:** Mexican · Baja California peninsula.
- **Portrait:** `cpai_avatar_baja_californians_alvarado.png` · **Flag:** `Flag_baja_californian.png`.
- **Doctrine:** Sparse desert-coast guerrillas; coastal defense + chokepoint
  ambush, palisade-tier, raiders.
- **Walling — Coastal (2), Chokepoint fallback:** `2, 16, 2, false, 2, 20, 4, 1, 4, 0.3, 4, 3, 3, 100, true`.
- **Per-age:** defensive→mixed; Colonial defensive (inf-led militia), Fortress+
  mixed inf/cav guerrilla, light artillery.
- **Deck theme:** coastal-defense cards, guerrilla skirmishers, mission/rancho
  eco, ambush/outpost cards.

## 4. Rio Grande — Antonio Canales Rosillo
- **Parent / era:** Mexican · Republic of the Rio Grande (1840).
- **Portrait:** `cpai_avatar_rio_grande_canales_rosillo.png` · **Flag:** `Flag_rio_grande.png`.
- **Doctrine:** Northern-frontier federalist ranchers; mobile cavalry on open
  plains, raid-and-retreat, light fortification.
- **Walling — FrontierPalisades (3), Mobile fallback:** `3, 18, 3, false, 2, 20, 3, 5, 5, 0.5, 4, 4, 3, 100, true`.
- **Per-age:** offensive cavalry frontier; cav-led all ages, light inf support.
- **Deck theme:** frontier ranchero cavalry, vaquero eco, outpost screen,
  federalist-militia infantry, light-cannon.

## 5. Yucatan — Felipe Carrillo Puerto
- **Parent / era:** Mexican/Maya · Republic of Yucatán (1841).
- **Portrait:** `cpai_avatar_yucatan_carrillo_puerto.png` · **Flag:** `Flag_yucatan.png`.
- **Doctrine:** Jungle Maya-militia defense; dense chokepoint segments at jungle
  pinches, ambush infantry, palisade-tier.
- **Walling — ChokepointSegments (1):** `1, 12, 2, false, 2, 16, 4, 5, 4, 0.55, 0, 3, 3, 100, true`.
- **Per-age:** defensive, infantry/militia heavy (jungle ambush), low cavalry,
  late light artillery.
- **Deck theme:** Maya militia/ambusher infantry, jungle-fortification cards,
  henequen (sisal) economy, machete cavalry, chicle/trade.

---

## 6. Belgians — (needs art) · Leopold I / Charles Rogier
- **Parent / era:** Dutch · Belgian Revolution (1830), Kingdom of Belgium.
- **Portrait:** ⚠️ none yet — source a Leopold I / 1830-revolution portrait, or
  derive a clean European-leader avatar. **Flag:** ⚠️ none — needs a Belgian
  tricolour (black-yellow-red) icon.
- **Doctrine:** Early-industrial fortress state — Belgium's ring of fortresses
  (Antwerp, Liège); drilled line infantry + artillery, strong static defense.
- **Walling — FortressRing (0), stone, strict:** `0, 16, 3, true, 2, 20, 7, 2, 8, 0.2, 6, 2, 3, 100, true`.
- **Per-age:** Colonial defensive (line inf), Fortress defensive→offensive with
  rising artillery, Industrial/Imperial offensive inf+art (Belgian industry).
- **Deck theme:** drilled line infantry, fortress/artillery cards, early-industry
  economy (coal/factory), engineer/fortification, Antwerp-defense.
- **Status:** **BLOCKED on art** (portrait + flag). Recommend basing units on
  the Dutch/European roster.

## 7. Walloons — (needs art)
- **Parent / era:** Dutch/French · industrial Wallonia (French-speaking Belgium).
- **Portrait:** ⚠️ none yet. **Flag:** ⚠️ none (Walloon cockerel / red-yellow).
- **Doctrine:** Heavy-industry artillery state — coal & steel of the Sambre-Meuse;
  cannon-heavy, urban-fortified, defensive-industrial.
- **Walling — UrbanBarricade (4), stone:** `4, 12, 3, true, 2, 20, 6, 0, 5, 0.15, 4, 1, 3, 100, true`.
- **Per-age:** defensive, artillery-heavy all mid-late ages, infantry support.
- **Deck theme:** heavy-cannon/ironworks cards, factory economy, fortified-town
  infantry, engineer.
- **Status:** **BLOCKED on art** (portrait + flag). Closely related to Belgians;
  consider whether Belgians + Walloons are two civs or one (Belgium) with a
  Walloon alt-leader.

---

## Implementation order (recommended)
1. **5 American nations first** — assets + base-game revolution rosters exist;
   each is the standard recipe (civmods + homecity + deck + picker + wall knobs
   + per_age + leader). Lowest risk, fully self-contained.
2. **Belgians (+ Walloons)** — require new portrait + flag art and a unit roster
   (no base-game revolution). Decide Belgians-only vs Belgians+Walloons. Source
   art, then implement.

Per-civ verification: `validate_xs_scripts.py`, `audit_engine_vs_spec.py`,
lobby-pick smoke (the civ appears + loads), then a farm run to grade its
per-age + walling doctrine.
