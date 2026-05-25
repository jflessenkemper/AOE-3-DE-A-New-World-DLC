# Realism Mode — Design Document
**Project:** A New World (ANW) v1.0  
**Status:** Proposal — awaiting approval before implementation  
**Date:** 2026-05-26  
**Scope:** All ~40 ANW civs, all unit classes, all building/ship classes

---

## 1. Mechanism — How to Ship It

### 1.1 How AoE3 DE applies mode-specific stats

AoE3 DE has three built-in "game mode" hooks in `civmods.xml` that auto-apply a named tech to every civ at the start of a match:

```xml
<deathmatchtech>DEDeathMatch</deathmatchtech>
<treatytech>DETreatyShadow</treatytech>
<empirewarstech>DEEmpireWars</empirewarstech>
```

When the player picks "Death Match" in the lobby, the engine auto-researches `DEDeathMatch` for every player, applying whatever `<Effect>` entries that tech defines. These techs live in `techtreemods.xml` with `<Status>UNOBTAINABLE</Status>` and `<Flag>Shadow</Flag>` so they never appear in the tech-tree UI.

The `<agetech Age0>` hook is the other mechanism: every civ's zero-cost Age 0 tech fires at game start and can chain-activate other techs via `<Effect type='TechStatus' status='active'>SomeTech</Effect>`.

**Crucially, the engine does not support custom `<realismtech>` XML tags.** Only the hardcoded tags (`deathmatchtech`, `treatytech`, `empirewarstech`) are wired to game-lobby UI toggles. This closes the "add a new game mode" route without a binary patch.

### 1.2 Three viable delivery mechanisms

| Option | Mechanism | Pros | Cons |
|--------|-----------|------|------|
| A. Shadow tech in every Age0 tech | Each civ's `ANWAge0<CivName>` already fires at game start. Add `<Effect type='TechStatus' status='active'>ANWRealismMode</Effect>` to every one of them. `ANWRealismMode` itself is the master tech that applies all stat changes. | Clean, zero new files, consistent for all civs | Realism is always on — no in-game toggle |
| B. Standalone second mod | Ship `A New World — Realism Pack` as a separate mod in the same repo. It overrides `techtreemods.xml` / `protomods.xml` with the realism values. The player subscribes to it *instead of* the base ANW mod. | True opt-in, no code sharing complexity | Two mods to maintain, diverges on every stat update |
| C. Scenario trigger | A custom scenario (`.age3Yscn`) in `Scenario/` has a game-start trigger (condition: `Timer <= 1 s`) that calls `researchTech("ANWRealismMode", player)` via XS for each player. | Works for single-player and custom game lobby | Requires the host to always pick the realism scenario; incompatible with random-map ladder play |

### 1.3 Recommendation

**Use Option B (standalone sister mod) for v1.0.** The rationale:

- Option A makes realism permanent and cannot be toggled per-session; it would prevent normal ANW play for anyone who installs it.
- Option C is too fragile (host must remember to pick the scenario, and XS `researchTech` has per-player scoping issues in MP).
- Option B is the pattern used by every major AoE3 DE balance overhaul (e.g. the Enhanced AI mod at `mods/subscribed/209052`). It is self-contained, versioned independently, and the `tools/realism_mode/generate_realism_techs.py` generator (see §4) keeps it in sync with the base mod automatically.

**Concrete file layout for the sister mod:**

```
AOE-3-DE-A-New-World/
  realism_mode/                         ← new top-level directory
    modinfo.json                        ← points at "data" subdir
    data/
      techtreemods.xml                  ← ANWRealismMode tech + all stat Effects
    docs/
      (this file lives at docs/REALISM_MODE_DESIGN.md in the parent repo)
```

The sister mod's `techtreemods.xml` defines one tech, `ANWRealismMode`, with `<Status>UNOBTAINABLE</Status>` and `<Flag>Shadow</Flag>`. Because the sister mod is loaded *in addition to* the base ANW mod, its `techtreemods.xml` is merged by the engine (mods are additive). However the tech itself still needs to be activated; the cleanest route is to add `<Effect type='TechStatus' status='active'>ANWRealismMode</Effect>` to **one** central bootstrap tech. The best candidate is `AAStandardStartingTechs` (vanilla) or the civ-neutral `DEEuropeanStandardTechs` chain — but since those are vanilla techs that should not be touched, the correct target is to add an entry to **every** civ's Age0 tech in `data/techtreemods.xml` of the sister mod.

The Python generator (§4.2) handles this: it reads `civmods.xml`, finds every `ANWAge0*` tech name, and emits a second XML block that appends `<Effect type='TechStatus' status='active'>ANWRealismMode</Effect>` to each of them in the sister mod's `techtreemods.xml`. This keeps the base mod untouched.

**Next safe DBID for `ANWRealismMode`:** `40038`  
(Current ANW max DBID in `data/techtreemods.xml` is `40037`, verified from the file.)

---

## 2. Weapon Class Taxonomy — Historical Reference Values

All figures are historical context drawn from standard military history references: Paddy Griffith's *Forward into Battle* (musketry effectiveness), B.P. Hughes's *Firepower* (18th–19th c. artillery ballistics), and the Encyclopaedia Britannica / Wikipedia tactical articles for naval gunnery. Figures are approximations suitable for scaling, not engineering specifications.

### 2.1 Smoothbore Musket (Brown Bess, Charleville M1777, etc.)

- **Caliber / projectile:** ~.75 inch / ~80 g lead ball
- **Effective range against a formation:** 50–80 m. Accuracy against individual targets essentially nil beyond 50 m. Maximum range ~250 m but virtually no aimed effect.
- **Penetration:** At 50 m, sufficient to defeat light infantry clothing and padded linen. Would NOT reliably defeat a steel cuirass (cavalry). Would defeat heavy leather/padding easily.
- **Rate of fire:** 2–4 rounds per minute (RoF) in trained hands; ~1 round per minute under heavy stress.
- **Lethality per hit at close range:** A single .75-caliber ball at effective range is almost always incapacitating (bone-shattering trauma). Casualty rate per volley at 50 m against a formed line: ~10–20% (accounting for misses, misfires, over-penetration).
- **Tactical implication:** A single well-aimed hit at close range = instant casualty. The historical "one shot, one kill" holds at 50 m.

### 2.2 Rifled Musket (Pattern 1853 Enfield, Springfield Model 1861)

- **Effective range:** 300–400 m against individual targets (with rear-sight); 200 m against formations.
- **Rate of fire:** 2–3 rounds per minute (Minie ball slower to load than round ball).
- **Lethality:** Similar per-hit lethality to smoothbore musket but at 5× the range; elongated bullet causes worse tissue damage.
- **Tactical implication:** Extends the "danger zone" dramatically; revolutionized tactics (cover, skirmish lines). In game terms: higher range, same or slightly higher damage than smoothbore.

### 2.3 Cavalry Sabre / Lance / Bayonet

- **Sabre:** At full gallop against unprotected infantry, a single cut can be fatal or severely incapacitating. Historical sources (Duffy, *The Military Experience in the Age of Reason*) indicate cavalry charges that broke through infantry killed 20–40% of defenders in the initial pass.
- **Lance:** Greater reach than sabre; more lethal on first contact, less so in melee sustained beyond initial charge.
- **Bayonet:** Most bayonet encounters were brief; actual bayonet wounds were rare (infantry typically broke before contact). A bayonet thrust at a person not wearing plate armor is near-certainly incapacitating.
- **Tactical implication:** In all cases, a single hit from a melee weapon against an unarmored target should kill or remove from action. Against plate-armored cavalry (cuirassiers), 2–3 hits may be needed.

### 2.4 Field Cannon — 3-pdr, 6-pdr, 12-pdr

| Gun | Ball weight | Effective range (solid shot) | Beaten zone (AOE at ~600m) |
|-----|------------|-------------------------------|----------------------------|
| 3-pdr (light/regimental) | 1.4 kg | 400–600 m | ~1 m wide |
| 6-pdr (standard field gun) | 2.7 kg | 600–800 m | ~2 m wide |
| 12-pdr (Napoleon / heavy) | 5.4 kg | 800–1000 m | ~3 m wide |

- **Solid shot through a formed line:** A 12-pdr ball at 400 m could disable 8–10 men in a file (ball rolls/bounces through files). At 800 m: 2–4 men.
- **Canister/case shot (close range < 200 m):** Fan of musket balls; kills/wounds 15–20 men per shot against a dense formation.
- **Explosive shell (howitzers, mortars):** Burst radius ~5–10 m; fragments wound or kill everyone within ~5 m.
- **Tactical implication:** A cannon shot should kill multiple infantry in a group (AOE), not just one. A 12-pdr ball hitting a single infantry unit in isolation should be an instant kill with high probability. Field cannon against buildings: slow attrition; a brick structure requires hundreds of hits to collapse.
- **Source:** B.P. Hughes, *Firepower: Weapons Effectiveness on the Battlefield 1630–1850* (1974).

### 2.5 Naval Artillery — Long 9, 12-pdr, 24-pdr; Carronade

| Gun | Caliber | Penetration of 2-ft oak at 100 m | Effective range |
|-----|---------|-----------------------------------|-----------------|
| Long 9-pdr | 9 lb | ~60 cm | 600 m |
| Long 12-pdr | 12 lb | ~70 cm | 800 m |
| Long 24-pdr | 24 lb | ~90 cm | 1000 m |
| 68-pdr carronade | 68 lb | ~120 cm (close range only) | 200–300 m |

- **Ship-of-the-line oak hull:** 18–24 inches (45–60 cm) of solid English oak sided. A 24-pdr ball at 200 m will penetrate but the ball is greatly slowed. At 100 m, penetration is reliable; horrific wood-splinter casualties on the gun deck.
- **Sinking a 74-gun SOL:** At Trafalgar, HMS *Victory* took 57 dead and 102 wounded from ~4 hours of engagement. The *Redoubtable* (74 guns) was taken but not sunk outright; she finally sank the next day in the storm. A SOL was essentially unsinkable from gunfire alone without prolonged engagement or a lucky magazine explosion — attrition over hours. In game terms: a 74-gun SOL vs. another 74-gun SOL should sustain 50–100 full broadside hits before sinking.
- **Frigate (36–44 guns):** Far lighter construction; sinks faster. 20–40 broadsides from a SOL would be lethal.
- **Canoe (native craft, unarmored wood):** A single cannon ball from any naval gun would be near-instantly fatal.
- **Source:** N.A.M. Rodger, *The Command of the Ocean: A Naval History of Britain 1649–1815* (2004).

### 2.6 Native Ranged Weapons — Bow, Atlatl, Sling

| Weapon | Effective range | Penetration |
|--------|----------------|-------------|
| Composite bow (Lakota, Comanche) | 60–100 m | Penetrates light padding; not steel plate |
| Longbow (English, Haudenosaunee) | 180–220 m (trained archer) | At 50 m, penetrates mail; not full plate |
| Atlatl dart (Aztec, Inca) | 30–40 m | Low-medium penetration; significant trauma |
| Sling (Inca huaraca) | 50–80 m | Stone at high velocity; equivalent to pistol ball impact |
| Throwing axe / tomahawk | 10–20 m | Significant at close range; one good hit is incapacitating |

- Native bows at close range are highly lethal (Plains warriors could shoot 10–20 arrows per minute — vastly outpacing musket RoF). A well-aimed arrow at 30 m against an unarmored person is reliably incapacitating.
- Against musketeer-era uniformed soldiers with no armor (18th-century infantry wore cloth, not metal), a composite bow is lethal at 80 m and competitive with smoothbore muskets.
- **Tactical implication:** Native ranged units should NOT be drastically weaker than muskets at close range. Their disadvantage is range (especially vs. rifled muskets) and volume of fire against massed formed infantry.
- **Source:** Pekka Hamalainen, *The Comanche Empire* (2008); John Keegan, *A History of Warfare* (1993).

### 2.7 Building Hit Points — Historical Resistance to Cannon Fire

| Structure | Construction | Time to breach with 6-pdr field guns (historical) | Game-time equivalent |
|-----------|-------------|---------------------------------------------------|----------------------|
| Wood palisade | Log + earth | Hours, possibly a day or two | 5–10 min of steady cannon fire |
| Earthwork redoubt | Packed earth + gabions | 1–3 days of systematic bombardment | 15–30 min game-time |
| Masonry fort (star fort) | Dressed stone 2–4 ft thick | 5–14 days of sustained siege artillery | 30–60 min game-time |
| Town-center (wood/brick hybrid) | Mixed | Not a military target; vulnerable to fire | 3–8 min |
| Barracks (wood framing) | Light wood | 1–2 hours sustained small-arms | 2–5 min |

- A real 18th-century siege of a proper masonry fort (Vauban-type) required heavy siege trains (24-pdr siege guns, mortars), weeks of approach trenches, and methodical breaching. The 5–10 day estimate for "breach" (not full destruction) is from documented sieges: Fort Ticonderoga 1777, Badajoz 1812.
- **Tactical implication:** Forts should be nearly impervious to field cannon — that's realistic. Only siege mortars and sustained bombardment should work.

### 2.8 Ship Hit Points Summary

| Ship | Hull type | vs. 24-pdr barrage — full broadsides to sink |
|------|----------|----------------------------------------------|
| Native canoe | Open wood | 1–2 cannon shots |
| Caravel / small caravel | Light wood, ~2 in | 8–15 broadside volleys |
| Galleon | Merchant hull, ~4 in | 15–25 volleys |
| Frigate (32–44 guns) | Naval oak, ~8 in | 25–40 volleys |
| 74-gun Ship-of-the-Line | Doubled oak, ~18 in | 50–100 volleys |

---

## 3. Scaling Table — Current AoE3 Stats to Realism Values

### 3.1 Design philosophy

The scaling must satisfy these constraints simultaneously:

1. **Musket vs. musket is 1–2 shot.** In real line warfare a single volley often decided an engagement. In game terms: a Musketeer (HP 150, taking 23 damage per shot) currently needs 7 volleys to die. That is wildly unrealistic.

2. **Cavalry saber kills non-armored target in 1 hit.** A Hussar (damage 30) hits a Musketeer (HP 150) and only does 20% of HP — total fantasy.

3. **Field cannon kills 3–6 infantry per shot** (AOE + damage boost).

4. **Fort resists 5–10 min of cannon bombardment.** Currently a Cannon (HP 475, damage 200) kills a Fort (HP 9000) in about 45 shots = 45 × 6s RoF = 270s = 4.5 min. That is already close, but the fort has no infantry or defensive fire to account for.

5. **SOL-class ship takes 50–100 broadside hits** to sink from another SOL.

6. **Relative balance between unit classes is preserved** (musket > pike > cav, cav > musket, skirmisher > cav, etc.) — the counter-system must be maintained.

The approach: define a **Realism HP** and a **Realism Damage** per class, then compute the scale factor (`realismValue / vanillaValue`) for each. The tech emits `relativity='Multiply'` effects.

### 3.2 Unit class — infantry

| Unit | Vanilla HP | Vanilla Main Dmg | Realism HP | Realism Dmg | HP Scale | Dmg Scale | Kills in N hits |
|------|-----------|-----------------|------------|------------|----------|-----------|-----------------|
| Musketeer | 150 | 23 (Ranged) | **30** | **30** | 0.20× | 1.30× | 1 hit to kill |
| Skirmisher | 120 | 15 (Ranged) | **25** | **22** | 0.21× | 1.47× | 1–2 hits |
| Pikeman | 120 | 8 (Hand) | **25** | **30** | 0.21× | 3.75× | 1 hit vs. light inf |
| Dragoon (mounted) | 200 | 22 (Ranged) | **45** | **28** | 0.23× | 1.27× | 1–2 hits |
| Hussar (melee cav) | 320 | 30 (Hand) | **60** | **65** | 0.19× | 2.17× | 1 hit kills infantry |
| Cuirassier (heavy) | 425 | 25 (Hand) | **80** | **70** | 0.19× | 2.80× | 1 hit kills infantry |
| Grenadier | 200 | 24 (Hand) | **35** | **35** | 0.18× | 1.46× | 1 hit vs. infantry |
| Longbowman | 95 | 16 (Ranged) | **20** | **25** | 0.21× | 1.56× | 1–2 hits |
| Crossbowman | 100 | 16 (Ranged) | **22** | **20** | 0.22× | 1.25× | 1–2 hits |
| NatTomahawk | 170 | 16 (Ranged) | **30** | **28** | 0.18× | 1.75× | 1–2 hits |

**Summary infantry scale:** HP multiplier ~0.20, damage multiplier ~1.5–3.0 depending on class.

Expressed as multipliers for the tech effects:
- Infantry HP: `×0.20` (Override Hitpoints to `initialhitpoints * 0.20`)
- Light ranged damage: `×1.5`
- Cavalry hand damage: `×2.2`
- Heavy cavalry hand damage: `×2.8`

### 3.3 Unit class — artillery

| Unit | Vanilla HP | Vanilla Main Dmg | Realism HP | Realism Dmg | Notes |
|------|-----------|-----------------|------------|------------|-------|
| Falconet (3-pdr equiv.) | 200 | 100 (Cannon) | **80** | **120** | Kills 1–2 infantry/shot |
| Cannon (6-pdr/12-pdr) | 475 | 200 (Cannon) | **150** | **300** | Kills 3–5 infantry/shot |
| Mortar | 300 | 500 (Cannon) | **100** | **600** | Kills 5–8 infantry in AOE |
| GreatBombard | 475 | 200 | **160** | **350** | Siege specialist |

Artillery HP: `×0.33`  
Artillery damage (cannon): `×1.5–1.6`  
Key rationale: artillery crew are 6–8 men; a single musket hit on an exposed crew is catastrophic — hence the HP reduction is severe. But the artillery's destructive power against infantry should be overwhelming.

### 3.4 Unit class — naval

The naval scaling is the most delicate because the gap between a canoe and a ship-of-the-line needs to widen dramatically.

| Ship | Vanilla HP | Vanilla Main Dmg | Realism HP | Realism Dmg | SOL hits-to-sink |
|------|-----------|-----------------|------------|------------|-----------------|
| Canoe | 220 | 16 | **50** | **20** | 2–3 cannon hits |
| Caravel | 800 | 75 | **400** | **80** | ~8–10 Frigate hits |
| Galleon | 1500 | 50 | **600** | **60** | ~15 Frigate hits |
| Frigate | 2000 | 90 | **2000** | **100** | ~40 Frigate hits |
| Monitor/Ironclad | 2000 | 200 | **3500** | **250** | Very hard to sink |

For the vanilla Frigate, RoF is 2 seconds (0.50 shots/sec) and 75% armor reduces incoming damage to 25%. Effective incoming per shot = 90 × 0.25 = 22.5 per hit. With Realism HP = 2000, that is 88 hits to kill a Frigate — close to the 50–100 target. The Frigate HP is kept at vanilla to avoid needing a huge multiplier, while **canoe and galleon HP is reduced** to reflect their much lighter construction.

Naval HP scale: canoe `×0.23`, galleon `×0.40`, frigate `×1.0` (keep vanilla), Monitor `×1.75`.  
Naval damage scale: `×1.1–1.25` (modest increase — the armor system already handles most of the survivability).

### 3.5 Buildings

| Building | Vanilla HP | Realism HP | Multiplier | Rationale |
|----------|-----------|------------|-----------|-----------|
| TownCenter | 6500 | **8000** | 1.23× | Brick/log; defensible but not a fort |
| Barracks | 2500 | **1000** | 0.40× | Wooden frame; burns easily |
| Fort (FortFrontier) | 9000 | **80000** | 8.9× | Star fort; resists weeks of bombardment |
| Outpost | 2000 | **4000** | 2.0× | Earthwork/log blockhouse |
| House | 1200 | **500** | 0.42× | Civilian construction |
| Wall (palisade) | 1000 | **500** | 0.50× | Log palisade; burns readily |

Key: the Fort HP is the most dramatic change. With a Cannon dealing 300 Realism damage (after multiplier) and 6s RoF:
- Fort HP 80000 ÷ 300 = ~267 cannon hits × 6s = 1600 s ≈ 26 minutes of sustained cannon fire.
- A battery of 4 cannons: ~6.5 minutes — realistic for a field attack on a properly garrisoned fort.
- A single cannon: 26 minutes, which is near the game's match length — correct behavior (you shouldn't be able to solo-cannon a fort in 30 seconds).

### 3.6 Consolidated scale-factor table

These are the `relativity='Multiply'` amounts the generated tech will apply:

| Category | Stat | Scale factor |
|----------|------|-------------|
| All infantry | Hitpoints | 0.20 |
| Light ranged inf | Ranged Damage | 1.50 |
| Heavy inf | Ranged Damage | 1.30 |
| Melee inf (pike/halberd) | Hand Damage | 3.50 |
| Light cavalry | Hand Damage | 2.20 |
| Heavy cavalry (cuirassier) | Hand Damage | 2.80 |
| Artillery units | Hitpoints | 0.33 |
| Field artillery (Falconet) | Cannon Damage | 1.20 |
| Heavy artillery (Cannon) | Cannon Damage | 1.50 |
| Mortar/Howitzer | Cannon Damage | 1.20 |
| Canoe/light boat | Hitpoints | 0.23 |
| Galleon/trade ship | Hitpoints | 0.40 |
| Frigate | Hitpoints | 1.00 (unchanged) |
| Monitor/Ironclad | Hitpoints | 1.75 |
| Naval damage | Ranged Damage | 1.15 |
| Barracks/Stable/ArtDepot | Hitpoints | 0.40 |
| Fort (FortFrontier) | Hitpoints | 8.90 |
| Outpost | Hitpoints | 2.00 |
| TownCenter | Hitpoints | 1.23 |
| House | Hitpoints | 0.42 |
| Wall | Hitpoints | 0.50 |

---

## 4. Engineering Plan

### 4.1 Protounit IDs that need touching

Based on the parsed `protoy.xml` (the merged runtime copy at  
`Steam/steamapps/compatdata/933110/pfx/.../AppData/Local/Temp/Age of Empires 3 DE/Data/data/protoy.xml`),  
the approximate scope:

- **Infantry (HP 50–200, has ranged/hand attack):** ~180 distinct protounits. Includes all civ variants: Musketeer, Skirmisher, Dragoon, Pikeman, plus their civ-specific analogs (Janissary, Strelet, Ashigaru, Mitmaq, etc.) and all the `Nat*` (native warrior) and `Merc*` (mercenary) variants.
- **Cavalry (HP 150–500, hand attack):** ~90 protounits. Hussar variants, Cuirassier, CavalryArcher, UhlaN, Spahi, Cossack, etc.
- **Artillery (HP 150–600, cannon/barrage attack):** ~40 protounits. Falconet, Cannon, Mortar, GreatBombard, RussianCannon, various SPC siege guns.
- **Naval (HP 200–2500, ranged attack, NavalMilitary unit type):** ~25 protounits. All ship types from Canoe to Monitor.
- **Buildings (HP 500–9000):** ~30 building types. Fort, TownCenter, Barracks, Stable, ArtilleryDepot, Church, Bank, Blockhouse, Outpost, walls.
- **Heroes/Explorers:** ~15 units (see §5 for treatment).

**Total estimate: ~380 protounit entries that need at least one stat-scaled Effect.**

The generator (§4.2) enumerates them by querying unit types (`AbstractInfantry`, `AbstractCavalry`, `NavalMilitary`, etc.) rather than hard-coding names, so new ANW-added units are picked up automatically.

### 4.2 Python generator — `tools/realism_mode/generate_realism_techs.py`

**Inputs:**
- `protoy.xml` (runtime merged copy, path configurable)
- A YAML config file `tools/realism_mode/scale_factors.yml` encoding the table in §3.6
- `data/civmods.xml` (to enumerate all `ANWAge0*` tech names for the bootstrap-activation block)

**Outputs (written to `realism_mode/data/techtreemods.xml`):**
- One master `ANWRealismMode` tech containing all `<Effect>` entries
- One activation-bootstrap block for each civ's Age0 tech

**Algorithm sketch:**
```python
for unit in proto_root.findall('.//unit'):
    unit_types = {ut.text for ut in unit.findall('unittype')}
    category = classify_unit(unit_types)        # returns 'infantry', 'cavalry', etc.
    if category is None:
        continue
    factors = SCALE_FACTORS[category]           # from scale_factors.yml
    for stat, mult in factors.items():
        emit_effect(unit.get('name'), stat, mult, relativity='Multiply')
```

`classify_unit` checks unit types in priority order:
1. If has `NavalMilitary` → naval
2. If has `AbstractArtillery` → artillery
3. If has `AbstractHeavyCavalry` or `AbstractCavalry` → cavalry
4. If has `AbstractInfantry` → infantry
5. If has `Building` and not `Unit` → building
6. Otherwise skip (pets, props, projectiles, etc.)

### 4.3 Tech mod XML format — before/after example for Musketeer

**Current vanilla/ANW values (from `protoy.xml` verified above):**
```
Musketeer:  HP=150, VolleyRangedAttack Dmg=23, MeleeHandAttack Dmg=13
```

**Sister-mod `techtreemods.xml` entry (generated, not hand-written):**
```xml
<Tech name="ANWRealismMode" type="Normal">
    <DBID>40038</DBID>
    <Status>UNOBTAINABLE</Status>
    <Flag>Shadow</Flag>
    <Effects>

        <!-- ===== MUSKETEER ===== -->
        <!-- HP: 150 * 0.20 = 30 -->
        <Effect type="Data" amount="0.2000" subtype="Hitpoints" relativity="Multiply">
            <Target type="ProtoUnit">Musketeer</Target>
        </Effect>
        <!-- MaxHP must match InitialHP -->
        <Effect type="Data" amount="0.2000" subtype="MaxHitpoints" relativity="Multiply">
            <Target type="ProtoUnit">Musketeer</Target>
        </Effect>
        <!-- Ranged damage: 23 * 1.30 = ~30 -->
        <Effect type="Data" action="VolleyRangedAttack" amount="1.3000"
                subtype="Damage" relativity="Multiply">
            <Target type="ProtoUnit">Musketeer</Target>
        </Effect>
        <Effect type="Data" action="StaggerRangedAttack" amount="1.3000"
                subtype="Damage" relativity="Multiply">
            <Target type="ProtoUnit">Musketeer</Target>
        </Effect>
        <Effect type="Data" action="DefendRangedAttack" amount="1.3000"
                subtype="Damage" relativity="Multiply">
            <Target type="ProtoUnit">Musketeer</Target>
        </Effect>

        <!-- ... (Hussar, Cannon, Frigate, Fort, etc. follow the same pattern) ... -->

    </Effects>
</Tech>
```

**Result in-game:**
- Musketeer HP: 30 (was 150)
- Musketeer ranged damage: ~30 (was 23)
- A Musketeer receives 30 damage from a single volley → dead in 1 shot.
- A Hussar delivers 65 damage hand-attack → Musketeer dead in 1 hit (65 > 30 HP).
- A Falconet AOE shot (120 Realism damage with new HP=30 infantry) kills 4+ infantry per shot.

**Action names to cover for infantry ranged damage:**  
`VolleyRangedAttack`, `StaggerRangedAttack`, `DefendRangedAttack` — all three must be updated or a unit can be exploited by forcing one of the non-updated action states. The generator does this systematically by iterating all `<protoaction>` entries with matching `<damagetype>`.

### 4.4 Activation bootstrap block

For each of the 40 civs, the sister mod adds to the techtreemods merge:
```xml
<!-- Activation: fires ANWRealismMode at game start for every ANW civ -->
<Tech name="ANWAge0NapoleonicFrench" type="Normal">
    <Effects>
        <Effect type="TechStatus" status="active">ANWRealismMode</Effect>
    </Effects>
</Tech>
<Tech name="ANWAge0RevolutionaryFrench" type="Normal">
    <Effects>
        <Effect type="TechStatus" status="active">ANWRealismMode</Effect>
    </Effects>
</Tech>
<!-- ... one block per ANWAge0* tech in civmods.xml ... -->
```

The generator reads civmods.xml, extracts all `<tech>` children of `<agetech><age>Age0</age>`, and emits one such block per unique tech name. At last count there are ~40 ANW civs → ~40 Age0 tech names (some may share, e.g. multiple civs re-use `ANWAge0British`).

---

## 5. Edge Cases

### 5.1 Aztec Eagle Runner Knights and Non-Historical Fantasy Units

`xpEagleKnight` (HP 180, Dmg 15 ranged) is the in-game representation of Aztec Eagle Warriors — elite Jaguar/Eagle knight soldiers who were historically real but carried obsidian-edged wooden swords (macuahuitl), not firearms. They belong to the infantry class but their weapon damage profile is hand-combat / short-range projectile.

**Recommended treatment:**
- Apply the same HP scale (×0.20 → HP ~36) as other infantry. Historically an Eagle Warrior was no more bullet-resistant than any other person.
- Apply a **higher** hand-damage multiplier (×3.0 instead of ×2.0) to reflect the devastating chopping power of the macuahuitl at close range. Historical sources (Bernal Diaz, *The Conquest of New Spain*) describe the macuahuitl capable of severing a horse's head in one blow.
- Do NOT give them enhanced resistance to ranged damage. A musket ball cuts down an Eagle Warrior just as easily as a Spanish soldier.
- Net effect: Eagle Knights become glass-cannon melee specialists — fragile if shot, terrifying if they close range. This is historically plausible.

The same logic applies to `xpJaguarKnight` (HP 215, Dmg 16 hand), `deMaceman`, `NatHolcanSpearman` and similar pre-firearm melee units.

### 5.2 Hero Units — Explorer, Leader Heroes, Warchiefs

The Explorer (HP 400) and leader heroes (Warchiefs at HP 500, SPCGreatPlainsChief at HP 900) are gameplay abstractions, not literally single soldiers.

**Two options:**

**Option A (Gameplay abstraction — recommended):** Hero units are excluded from the HP scaling entirely. Rationale: the Explorer represents the player's command presence on the battlefield, not a literal man. Reducing the Explorer to 80 HP (400 × 0.20) would make him one-shotted by a sniper at range 16 — he would be functionally unplayable and unrevivable. Heroes already have limited respawn and are precious resources. Keep hero HP at vanilla (or apply a mild 0.50× reduction). Apply the damage scaling to their attacks if those attacks target normal units (their damage would otherwise become disproportionately high against the now-fragile infantry).

**Option B (Full realism):** Scale heroes identically. This makes the mod very punishing and would require rethinking resurrection mechanics. Not recommended for v1.0.

**Recommended: Option A.** In `generate_realism_techs.py`, skip any unit whose name contains `Explorer`, `Warchief`, or is tagged `Hero` in unit types.

### 5.3 Native Civilizations vs. Gunpowder — Lakota, Maya, Inca

The three major pre-firearm native civs in AoE3 DE (Haudenosaunee, Lakota, Aztecs, Inca) field archery, melee, and some hybrid units. In Realism Mode, their matchup against gunpowder civs needs careful handling.

**Historical reality:**
- Plains warriors (Lakota, Comanche) armed with bows could loose 10–20 arrows per minute — far faster than a musketeer's 2–4 shots per minute. At close range (< 80 m) a mounted archer was *more* lethal per unit time than a musketeer. Their disadvantage: effective range ceiling ~100 m vs. 250–300 m for a smoothbore musket, and essentially zero range vs. a rifled musket.
- Inca warriors with slings could match smoothbore range and do comparable damage per hit. Inca huaraca slingers at Cajamarca terrified Spanish horses.
- Melee native warriors (Eagle Knights, Jaguar Knights) were formidable against arquebusiers in forest/close terrain, irrelevant against disciplined musket volleys in open field.

**In-game translation:**
- Native ranged units: HP ×0.20 (same as infantry), damage ×1.75 (slightly higher than musketeer at ×1.5) to represent higher RoF — but **no range increase** (their max range stays lower than a rifled musket).
- Native melee units: HP ×0.20, hand damage ×3.0–3.5 to reflect true close-combat lethality.
- Native cavalry (Lakota light cavalry): HP ×0.25 (faster, harder to hit than European heavy cavalry), damage ×2.0.

**Net result:** Native civs are competitive in forest/close-quarters maps but are outranged and outgunned in open-field battles — historically accurate. They remain viable at lower unit counts, which is appropriate since they were numerically disadvantaged.

### 5.4 Multiplayer Balance vs. Single-Player Asymmetry

**Core tension:** Realism Mode makes every civ lethally fragile. In multiplayer, the first player to mass a volley and fire wins. The 1–2 shot kill dynamics make micro-management skill the dominant factor, not strategic depth. This could break competitive play.

**Recommendations:**

1. **Realism Mode is a single-player / co-op mode first.** The design document and the mod's description should be explicit that it is not balanced for competitive 1v1 or team matchmaking. Label it "Historical Immersion Mode" with a clear "Not for ranked play" disclaimer in the mod description.

2. **For multiplayer co-op (players vs. AI):** The AI in ANW is already tuned (via `game/ai/`) with custom doctrine profiles. The realism damage values do not change AI decision-making scripts (XS), only the outcomes of combat resolution. The AI will still build armies, advance ages, and issue orders — it will just lose units faster when attacked. This is broadly fine for co-op: the human players enjoy the historical fragility, and the AI opponent is also fragile, keeping challenge roughly balanced.

3. **For PvP:** If the user wants a PvP-viable Realism Mode, consider a "Mild Realism" variant using ×0.50 HP scale (instead of ×0.20) and ×1.10 damage. This gives 3–5 shot kills (still far more lethal than vanilla's 7 shots) without making musketeer duels feel like a coin flip. This is a secondary target for v1.1.

4. **Host enforcement:** Because the sister mod is subscribed per-player, and AoE3 DE validates that all players in a session have the same mod set, if the host has Realism Pack installed and the other player doesn't, the session will either fail to start or drop to base-game stats. This is the existing engine behavior for mismatched mods. No special coding is needed — the engine handles it. Document this in the mod's README.

---

## 6. Toggle UX

### 6.1 How a player turns it on

**Primary method: Mod subscription (recommended v1.0)**
1. Player subscribes to "ANW — Realism Pack" mod on the AoE3 DE Workshop (or installs locally under `mods/local/`).
2. In the game lobby, both players must have the same mod set active. The Realism Pack is toggled via the Mods panel in the main menu, not per-session.
3. No in-game UI changes needed — Realism activates automatically via the Age0 shadow tech chain.

**Secondary method: Custom scenario (optional v1.1)**
A dedicated scenario file `Scenario/ANEWWORLD_REALISM.age3Yscn` could be added. Using the XS trigger system (already reverse-engineered in `tools/validation/scenario_trigger_parser.py` and `scenario_trigger_writer.py`), a game-start trigger fires `researchTech("ANWRealismMode", playerID)` for all players. This allows:
- Single-player skirmish with Realism from a "custom game" scenario without needing a separate mod install.
- Per-session opt-in without mod switching.
- Build this with `tools/validation/scenario_trigger_builder_v2.py` which already supports writing `.age3Yscn` triggers.

**Checkpoint:** The scenario approach requires `ANWRealismMode` to NOT auto-activate via the Age0 chain — otherwise it activates twice. If shipping both UX paths, the sister mod should expose `ANWRealismMode` as `<Status>OBTAINABLE</Status>` (researchable), and the Age0 chain auto-research is only present in the scenario variant. This bifurcation adds maintenance cost; leave it for v1.1.

### 6.2 Multiplayer compatibility

As noted in §5.4, AoE3 DE enforces mod parity: all players in a session must have the same mods active. The engine raises an "incompatible mod set" lobby error if there is a mismatch. This is host-enforced at the engine level with no additional work required from the mod. The only action needed: document clearly in the Realism Pack's `modinfo.json` description that it must be enabled by all players.

### 6.3 UI label (for future in-game checkbox)

If AoE3 DE's WPF UI layer (custom game settings screen) ever exposes a hook for mod-added game mode toggles, the desired label is:

- **Display name:** "Historical Realism"
- **Tooltip:** "Units deal and receive historically accurate damage. Infantry die in 1–2 shots. Forts require sustained siege. Not recommended for ranked play."

Until that hook exists, the subscription model is the only path.

---

## 7. Implementation Checklist (Engineering — Do Not Start Until Design Approved)

- [ ] Create `realism_mode/` directory and `modinfo.json`
- [ ] Create `tools/realism_mode/scale_factors.yml` with the values from §3.6
- [ ] Write `tools/realism_mode/generate_realism_techs.py` (see §4.2 sketch)
- [ ] Run generator against runtime `protoy.xml` to produce `realism_mode/data/techtreemods.xml`
- [ ] Manual review: spot-check Musketeer, Hussar, Cannon, Frigate, Fort entries
- [ ] In-game test: 1v1 Musketeer duel → confirm 1-shot kill
- [ ] In-game test: Cannon bombardment of FortFrontier → confirm 5–10 min resistance
- [ ] In-game test: Frigate vs. Frigate → confirm ~40 broadside hit duration
- [ ] In-game test: Native bow vs. Musketeer at 80 m → confirm competitive
- [ ] Update `docs/REALISM_MODE_DESIGN.md` with final scale factors after playtest

---

## Appendix A — Unit Stats Reference (Verified from protoy.xml)

Figures from the merged runtime `protoy.xml` at:  
`Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/AppData/Local/Temp/Age of Empires 3 DE/Data/data/protoy.xml`

| Unit | HP | Main Attack | Dmg | Range | RoF | Armor |
|------|----|------------|-----|-------|-----|-------|
| Musketeer | 150 | VolleyRangedAttack | 23 | 12 | 3.0s | Hand 0.20 |
| Skirmisher | 120 | VolleyRangedAttack | 15 | 20 | 3.0s | Ranged 0.30 |
| Pikeman | 120 | MeleeHandAttack | 8 | — | 1.5s | Hand 0.10 |
| Dragoon | 200 | DefendRangedAttack | 22 | 12 | 3.0s | Ranged 0.20 |
| Hussar | 320 | MeleeHandAttack | 30 | — | 1.5s | Ranged 0.20 |
| Cuirassier | 425 | MeleeHandAttack | 25 | — | 1.5s | Ranged 0.20 |
| Grenadier | 200 | VolleyRangedAttack | 16 | 12 | 3.0s | Ranged 0.50 |
| Longbowman | 95 | VolleyRangedAttack | 16 | 22 | 1.5s | Ranged 0.30 |
| Falconet | 200 | CannonAttack | 100 | 26 | 4.0s | Ranged 0.75 |
| Cannon | 475 | CannonAttack | 200 | 28 | 6.0s | Ranged 0.75 |
| Mortar | 300 | CannonAttack | 500 | 40 | 6.0s | Ranged 0.75 |
| Caravel | 800 | RangedAttack | 75 | 20 | 2.0s | Ranged 0.50 |
| Frigate | 2000 | RangedAttack | 90 | 30 | 2.0s | Ranged 0.75 |
| Galleon | 1500 | RangedAttack | 50 | 20 | 2.0s | Ranged 0.75 |
| Canoe | 220 | RangedAttack | 16 | 18 | 2.0s | Ranged 0.50 |
| Monitor | 1200 | LongRangeAttack | 200 | 70 | 20s | Ranged 0.50 |
| FortFrontier | 9000 | CannonAttack | 150 | 26 | 3.0s | — |
| Outpost | 2000 | CannonAttack | 60 | 24 | 3.0s | — |
| TownCenter | 6500 | RangedAttack | 9 | 32 | 3.0s | — |
| Barracks | 2500 | — | — | — | — | — |
| xpEagleKnight | 180 | VolleyRangedAttack | 15 | 12 | 1.5s | — |
| xpJaguarKnight | 215 | MeleeHandAttack | 16 | — | 1.5s | — |

---

## Appendix B — Source Citations

1. **Paddy Griffith**, *Forward into Battle: Fighting Tactics from Waterloo to the Near Future*, rev. ed. (Marlborough: Crowood Press, 1990) — musket effective range and volley lethality.
2. **B.P. Hughes**, *Firepower: Weapons Effectiveness on the Battlefield 1630–1850* (London: Arms and Armour Press, 1974) — artillery calibers, ranges, and casualty data.
3. **N.A.M. Rodger**, *The Command of the Ocean: A Naval History of Britain 1649–1815* (London: Penguin, 2004) — ship-of-the-line construction, Trafalgar casualty data, naval gun penetration.
4. **John Keegan**, *A History of Warfare* (London: Hutchinson, 1993) — general lethality comparisons across weapon classes and eras.
5. **Pekka Hamalainen**, *The Comanche Empire* (New Haven: Yale University Press, 2008) — Plains warrior archery effectiveness and tactical comparison with firearms.
6. **Wikipedia** — "Brown Bess", "Charleville musket", "Carronade", "Battle of Trafalgar", "Siege of Badajoz (1812)" — used for range/caliber spot-checks.
7. **Bernal Díaz del Castillo**, *The Conquest of New Spain* (trans. J.M. Cohen, Penguin Classics, 1963) — macuahuitl descriptions and Aztec warrior effectiveness.
