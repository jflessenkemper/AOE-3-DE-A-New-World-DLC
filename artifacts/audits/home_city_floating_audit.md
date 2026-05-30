# Home-City "Floating Citizens" Audit — Legendary Leaders Mod

Worktree: `.claude/worktrees/hungry-banzai-e122dc/`
Date: 2026-04-28
Scope: read-only audit. No edits performed.
User report: "British Canadian home city — people are floating in the air and walking around in the air. Make sure this is fixed for every nation."

---

## TL;DR (executive summary)

The floating-citizen bug is **not** caused by hardcoded `y` values on placed units. The mod's home-city XMLs do not place units by world position at all — they reference *named bones* inside a binary visual asset (`british\british_homecity.xml` etc.) shipped by the base game. Citizens path along *bone waypoints* inside that visual, with elevation taken from the **pathable area** referenced via `<pathdata>`.

The bug is a **pathdata/visual mismatch** introduced uniformly across **all 26 revolution-civ home cities** authored by this mod. Each anw XML reuses a parent-civ visual (e.g. `british\british_homecity.xml`) but pairs it with the generic flat `revolution\pathable_area.gr2` instead of that civ's matching pathable area (e.g. `british\pathable_area_object.gr2`). The two assets have different heightmaps; citizens snap to the revolution-pathable plane while the British scene's terrain sits below/above them, so they appear to walk on air.

Affected: **25 of 26 revolution civs** (all except ANWMexicans, which is the only one whose visual+pathdata pair is internally consistent). Stock 22 civ home-cities are untouched and correct.

---

## 1. File map — Home-city schema

### Where home-city scenes are defined

The mod authors home-city *metadata* in `data/<homecity>*.xml`. There are two flavours:

| Flavour | Files | Count | Role |
|---|---|---|---|
| Stock-civ overrides | `data/homecity*.xml` | 22 | Replace the stock home-city XML for the 22 base civs (e.g. `homecitybritish.xml`, `homecityspanish.xml`). Mostly card lists, building boxes, waypoints. |
| Revolution-civ originals | `data/anwhomecity*.xml` | 26 | New home cities for the 26 revolution civs promoted to top-level (e.g. `anwhomecitycanada.xml`, `anwhomecitynapoleon.xml`). |

These XMLs do **not** carry unit positions. They reference visual/pathable assets by relative path:

- `<visual>` — main scene model (`*.xml` inside the game's `homecity\` art tree). Defines geometry, ambient props, **named bones** (`bone_pathnode00`, `bone_vendor01`, `bone_GuardArea01`, …). Citizens move between these bones.
- `<watervisual>` — water plane.
- `<backgroundvisual>` — backdrop.
- `<pathdata>` — `.gr2` granny file with the navmesh/heightmap that the engine uses to **snap units to ground**. **This is the y-source for every citizen.**
- `<camera>` / `<widescreencamera>` — camera frustum file.

Example (`data/anwhomecitycanada.xml:1-20`):

```xml
<?xml version='1.0' encoding='utf-8'?>
<homecity>
  <civ>ANWCanadians</civ>
  <name>$$80821$$</name>
  <heroname>$$43030$$</heroname>
  <gatherpointunit>HomeCityGatherFlag</gatherpointunit>
  <visual>british\british_homecity.xml</visual>
  <watervisual>british\british_homecity_water.xml</watervisual>
  <backgroundvisual>british\british_background.xml</backgroundvisual>
  <pathdata>revolution\pathable_area.gr2</pathdata>
  <camera>british\british_homecity_camera.cam</camera>
  <widescreencamera>british\british_homecity_widescreencamera.cam</widescreencamera>
  ...
  <lightset>hc_revolution</lightset>
  <watertype>London</watertype>
  ...
  <ambientsounds>homecity\Revolutionambientsounds.xml</ambientsounds>
```

Later in the same file (`anwhomecitycanada.xml:2108-2244`) is the `<waypoints>` block, citing bones like `bone_pathnode00` … `bone_GuardArea03`. There is no `<x>`/`<y>`/`<z>` and no `<position>` tag anywhere in any home-city XML in the repo.

```bash
$ grep -n "<x>\|<y>\|<z>\|<position\|<rotation>" data/anwhomecity*.xml | wc -l
0
```

### Where the actual scene/heightmap files live

`british\british_homecity.xml`, `british\pathable_area_object.gr2`, `revolution\pathable_area.gr2`, etc. are **not in this repo**. They are shipped by the base game (Age of Empires III: DE). The mod merely references them by relative path inside the game's home-city art tree.

```bash
$ ls art/   # in this repo
buildings  ui  units      # no homecity/, no scenes/
$ find . -maxdepth 4 \( -name '*.scn' -o -name '*.scx' \)   # zero hits
```

So the audit must reason about which stock asset is referenced and whether visual ↔ pathdata pairs are *internally coherent*.

---

## 2. British Canadian specifically

### File: `data/anwhomecitycanada.xml`

- `<civ>ANWCanadians</civ>` (L3)
- `<visual>british\british_homecity.xml</visual>` (L7) — reuses stock British scene
- `<watervisual>british\british_homecity_water.xml</watervisual>` (L8) — stock British water
- `<backgroundvisual>british\british_background.xml</backgroundvisual>` (L9) — stock British backdrop
- **`<pathdata>revolution\pathable_area.gr2</pathdata>` (L10)** — **MISMATCH: revolution navmesh, not British**
- `<camera>british\british_homecity_camera.cam</camera>` (L11) — stock British camera
- `<lightset>hc_revolution</lightset>` (L16) — revolution lighting on a British scene (cosmetic, not the float bug)
- `<watertype>London</watertype>` (L17) — stock British water type
- `<ambientsounds>homecity\Revolutionambientsounds.xml</ambientsounds>` (L19) — generic revolution sounds

### Diff vs the stock British home city (`data/homecitybritish.xml`)

| Tag | British (stock) | British Canadian (anw) | match? |
|---|---|---|---|
| `<visual>` | `british\british_homecity.xml` (L7) | `british\british_homecity.xml` (L7) | yes |
| `<watervisual>` | `british\british_homecity_water.xml` (L8) | `british\british_homecity_water.xml` (L8) | yes |
| `<backgroundvisual>` | `british\british_background.xml` (L9) | `british\british_background.xml` (L9) | yes |
| **`<pathdata>`** | **`british\pathable_area_object.gr2`** (L10) | **`revolution\pathable_area.gr2`** (L10) | **NO — root cause of float bug** |
| `<camera>` | british (L11) | british (L11) | yes |
| `<lightset>` | `London` (L17) | `hc_revolution` (L16) | no (cosmetic only) |
| `<ambientsounds>` | `britishambientsounds.xml` | `Revolutionambientsounds.xml` | no (audio only) |

### Why this causes "people float and walk in air"

`british\british_homecity.xml` is the London scene — Thames embankment, Big Ben, sloped streets, raised promenade. Its **bone path-nodes (`bone_pathnode00`…16, `bone_vendor01`…05) are positioned at the heights of the London geometry**. The matching pathable area `british\pathable_area_object.gr2` encodes the same heightmap — when the engine runs a citizen between bones, it y-snaps to that pathmesh, producing correct ground-walking.

When `<pathdata>` is swapped to `revolution\pathable_area.gr2`, the engine snaps to the *revolution scene's* (largely flat or differently-elevated) pathmesh. The visible scene (London) sits at British heights; the citizens' resolved ground is at revolution heights. Citizens render at revolution-height bone positions inside the London scene → they appear suspended above the embankment, walking on air across docks / streets that are below them.

There are no per-unit y values to fix — the fix is to align `<pathdata>` with the visual.

### Problem units to cite

Because positioning is bone-driven and the bones live in the binary visual, no individual unit is wrongly placed in the XML. Every citizen / vendor / dreg / guard pathnode in the `<waypoints>` block (`anwhomecitycanada.xml:2108-2244`) inherits the bug from the single mismatched `<pathdata>` on L10. Citing the bug is therefore a one-line cite:

- **`data/anwhomecitycanada.xml:10`** — `<pathdata>revolution\pathable_area.gr2</pathdata>` should be `british\pathable_area_object.gr2`.

---

## 3. Per-civ scan

### 3a. Stock 22 civs (`data/homecity*.xml`)

All 22 stock civ home-cities pair `<visual>` and `<pathdata>` from the same civ namespace. Internally consistent. **No floating expected.**

```
homecityamericans.xml          american\american_homecity.xml          american\american_pathable_area.gr2
homecitybritish.xml            british\british_homecity.xml            british\pathable_area_object.gr2
homecitychinese.xml            china\china_homecity.xml                china\pathable_area_object.gr2
homecitydeinca.xml             inca\inca_homecity.xml                  inca\pathable_area.gr2
homecitydutch.xml              dutch\dutch_homecity.xml                dutch\dutch_homecity_pathable.gr2
homecityethiopians.xml         ethiopia\ethiopia_homecity.xml          ethiopia\ethiopia_pathable_area.gr2
homecityfrench.xml             french\french_homecity.xml              french\pathable_area_object.gr2
homecitygerman.xml             german\german_homecity.xml              german\pathable_area_object.gr2
homecityhausa.xml              hausa\hausa_homecity.xml                hausa\hausa_pathable_area.gr2
homecityindians.xml            india\india_homecity.xml                india\pathable_area_object.gr2
homecityitalians.xml           italy\italy_homecity.xml                italy\pathable_area_object.gr2
homecityjapanese.xml           japan\japan_homecity.xml                japan\pathable_area_object.gr2
homecitymaltese.xml            malta\malta_homecity.xml                malta\pathable_area_object.gr2
homecitymexicans.xml           mexico\mexico_homecity.xml              mexico\pathable_area.gr2
homecityottomans.xml           ottoman\ottoman_homecity.xml            ottoman\pathable_area_object.gr2
homecityportuguese.xml         portuguese\portuguese_homecity.xml      portuguese\pathable_area_object.gr2
homecityrussians.xml           russian\russian_homecity.xml            russian\pathable_area_object.gr2
homecityspanish.xml            spanish\spanish_homecity.xml            spanish\pathable_area_object.gr2
homecityswedish.xml            swedish\swedish_homecity.xml            swedish\pathable_area.gr2
homecityxpaztec.xml            aztec\aztec_homecity.xml                aztec\pathable_area.gr2
homecityxpiroquois.xml         iroquois\iroquois_homecity.xml          iroquois\pathable_area.gr2
homecityxpsioux.xml            sioux\sioux_homecity.xml                sioux\sioux_pathable_area.gr2
```

All 22 are clean.

### 3b. Revolution civs (`data/anwhomecity*.xml`) — the bug zone

Scanning all 26 with `grep -m1 "<visual>\|<pathdata>"`. Every file uses `revolution\pathable_area.gr2` regardless of which parent civ visual it borrows.

| File | parent visual | pathdata | float? | fix path (recommended pathdata) |
|---|---|---|---|---|
| `anwhomecityamericans.xml:7,10` | british\british_homecity.xml | revolution\pathable_area.gr2 | YES | `british\pathable_area_object.gr2` |
| `anwhomecityargentina.xml:7,10` | spanish\spanish_homecity.xml | revolution\pathable_area.gr2 | YES | `spanish\pathable_area_object.gr2` |
| `anwhomecitybajacalifornians.xml:7,10` | mexico\mexico_homecity.xml | revolution\pathable_area.gr2 | YES | `mexico\pathable_area.gr2` |
| `anwhomecitybarbary.xml:7,10` | ottoman\ottoman_homecity.xml | revolution\pathable_area.gr2 | YES | `ottoman\pathable_area_object.gr2` |
| `anwhomecitybrazil.xml:7,10` | portuguese\portuguese_homecity.xml | revolution\pathable_area.gr2 | YES | `portuguese\pathable_area_object.gr2` |
| `anwhomecitycalifornia.xml:7,10` | mexico\mexico_homecity.xml | revolution\pathable_area.gr2 | YES | `mexico\pathable_area.gr2` |
| **`anwhomecitycanada.xml:7,10`** | **british\british_homecity.xml** | **revolution\pathable_area.gr2** | **YES (user-reported)** | **`british\pathable_area_object.gr2`** |
| `anwhomecitycentralamericans.xml:7,10` | spanish\spanish_homecity.xml | revolution\pathable_area.gr2 | YES | `spanish\pathable_area_object.gr2` |
| `anwhomecitychile.xml:7,10` | spanish\spanish_homecity.xml | revolution\pathable_area.gr2 | YES | `spanish\pathable_area_object.gr2` |
| `anwhomecitycolumbia.xml:7,10` | spanish\spanish_homecity.xml | revolution\pathable_area.gr2 | YES | `spanish\pathable_area_object.gr2` |
| `anwhomecityegypt.xml:7,10` | ottoman\ottoman_homecity.xml | revolution\pathable_area.gr2 | YES | `ottoman\pathable_area_object.gr2` |
| `anwhomecityfinland.xml:7,10` | russian\russian_homecity.xml | revolution\pathable_area.gr2 | YES | `russian\pathable_area_object.gr2` |
| `anwhomecityfrenchcanada.xml:7,10` | french\french_homecity.xml | revolution\pathable_area.gr2 | YES | `french\pathable_area_object.gr2` |
| `anwhomecityhaiti.xml:7,10` | french\french_homecity.xml | revolution\pathable_area.gr2 | YES | `french\pathable_area_object.gr2` |
| `anwhomecityhungary.xml:7,10` | german\german_homecity.xml | revolution\pathable_area.gr2 | YES | `german\pathable_area_object.gr2` |
| `anwhomecityindonesians.xml:7,10` | dutch\dutch_homecity.xml | revolution\pathable_area.gr2 | YES | `dutch\dutch_homecity_pathable.gr2` |
| `anwhomecitymaya.xml:7,10` | mexico\mexico_homecity.xml | revolution\pathable_area.gr2 | YES | `mexico\pathable_area.gr2` |
| **`anwhomecitymexicans.xml:7,10`** | **revolution\revolution_homecity.xml** | revolution\pathable_area.gr2 | **NO (consistent pair)** | (no change) |
| `anwhomecitynapoleon.xml:7,10` | french\french_homecity.xml | revolution\pathable_area.gr2 | YES | `french\pathable_area_object.gr2` |
| `anwhomecityperu.xml:7,10` | spanish\spanish_homecity.xml | revolution\pathable_area.gr2 | YES | `spanish\pathable_area_object.gr2` |
| `anwhomecityrevolutionaryfrance.xml:7,10` | french\french_homecity.xml | revolution\pathable_area.gr2 | YES | `french\pathable_area_object.gr2` |
| `anwhomecityriogrande.xml:7,10` | mexico\mexico_homecity.xml | revolution\pathable_area.gr2 | YES | `mexico\pathable_area.gr2` |
| `anwhomecityromania.xml:7,10` | german\german_homecity.xml | revolution\pathable_area.gr2 | YES | `german\pathable_area_object.gr2` |
| `anwhomecitysouthafricans.xml:7,10` | dutch\dutch_homecity.xml | revolution\pathable_area.gr2 | YES | `dutch\dutch_homecity_pathable.gr2` |
| `anwhomecitytexas.xml:7,10` | mexico\mexico_homecity.xml | revolution\pathable_area.gr2 | YES | `mexico\pathable_area.gr2` |
| `anwhomecityyucatan.xml:7,10` | mexico\mexico_homecity.xml | revolution\pathable_area.gr2 | YES | `mexico\pathable_area.gr2` |

**Diagnosis: 25 of 26 revolution-civ home cities are mis-paired.** The exception is `anwhomecitymexicans.xml`, which is the only one that uses the matching `revolution\revolution_homecity.xml` visual and is therefore internally consistent.

### Other wiring quirks (not the float bug, but related)

- All 26 anw files use `<lightset>hc_revolution</lightset>` (e.g. `anwhomecitycanada.xml:16`). For the 25 that reuse a parent civ scene, this gives wrong-mood lighting (revolution lightset over a London skybox). Cosmetic, not the bug.
- All 26 use `<ambientsounds>homecity\Revolutionambientsounds.xml</ambientsounds>` (e.g. `anwhomecitycanada.xml:19`). Same caveat: wrong audio for the visible scene.
- `anwhomecitycanada.xml:17` keeps `<watertype>London</watertype>` — that one is correct because the visual *is* London. Other anw files generally keep their parent civ's `<watertype>`; spot-checked `argentina` (`Seville`), `egypt` (`Constantinople`), all fine.
- Missing-asset risk: every referenced visual / pathable / camera / background path is a stock-game asset the mod does not ship. Spot checks confirm the *parent civ's* matching pathable file (e.g. `british\pathable_area_object.gr2`) is the same file the stock `data/homecitybritish.xml:10` already references successfully, so the proposed fix paths are guaranteed to exist on every install. No new asset shipping is required.
- `obtainableprops` lists at the file tail (e.g. `anwhomecitycanada.xml:2245-2253`) reference `PeasantVendor`, `MiddleClassPreacher`, `NiceLady`, `Thug`, `Drunk`, `RevolutionaryGuard`, `German_LightSet1`. These are stock prop archetypes — not float-relevant.

---

## 4. Recommended fixes

### Priority 1 — User's specific complaint: British Canadian

Single-line edit:

```diff
- <pathdata>revolution\pathable_area.gr2</pathdata>
+ <pathdata>british\pathable_area_object.gr2</pathdata>
```

at **`data/anwhomecitycanada.xml:10`**.

After this, citizens will y-snap to the same pathmesh that the stock British home-city uses, on the very same `british\british_homecity.xml` visual. The bug should disappear in one shot, no other edits required.

### Priority 2 — All other revolution civs (24 files)

Apply the same pattern — change `<pathdata>` on **line 10** of each anw file to the parent civ's pathable area, per the table in §3b. The matching values are exactly those used by the stock civ home-city files, so the change is mechanical.

Specifically (file:10 in each case):

| File | new pathdata value |
|---|---|
| anwhomecityamericans.xml | british\pathable_area_object.gr2 |
| anwhomecityargentina.xml | spanish\pathable_area_object.gr2 |
| anwhomecitybajacalifornians.xml | mexico\pathable_area.gr2 |
| anwhomecitybarbary.xml | ottoman\pathable_area_object.gr2 |
| anwhomecitybrazil.xml | portuguese\pathable_area_object.gr2 |
| anwhomecitycalifornia.xml | mexico\pathable_area.gr2 |
| anwhomecitycentralamericans.xml | spanish\pathable_area_object.gr2 |
| anwhomecitychile.xml | spanish\pathable_area_object.gr2 |
| anwhomecitycolumbia.xml | spanish\pathable_area_object.gr2 |
| anwhomecityegypt.xml | ottoman\pathable_area_object.gr2 |
| anwhomecityfinland.xml | russian\pathable_area_object.gr2 |
| anwhomecityfrenchcanada.xml | french\pathable_area_object.gr2 |
| anwhomecityhaiti.xml | french\pathable_area_object.gr2 |
| anwhomecityhungary.xml | german\pathable_area_object.gr2 |
| anwhomecityindonesians.xml | dutch\dutch_homecity_pathable.gr2 |
| anwhomecitymaya.xml | mexico\pathable_area.gr2 |
| anwhomecitynapoleon.xml | french\pathable_area_object.gr2 |
| anwhomecityperu.xml | spanish\pathable_area_object.gr2 |
| anwhomecityrevolutionaryfrance.xml | french\pathable_area_object.gr2 |
| anwhomecityriogrande.xml | mexico\pathable_area.gr2 |
| anwhomecityromania.xml | german\pathable_area_object.gr2 |
| anwhomecitysouthafricans.xml | dutch\dutch_homecity_pathable.gr2 |
| anwhomecitytexas.xml | mexico\pathable_area.gr2 |
| anwhomecityyucatan.xml | mexico\pathable_area.gr2 |

`anwhomecitymexicans.xml` — leave alone (already correct).

### Priority 3 — Optional cosmetic alignment (no float bug, but consistency)

For any anw where the parent civ's lightset/ambient sounds materially fit the visible scene, the modder may also want to swap:

- `<lightset>` (line 16) `hc_revolution` → parent civ's lightset (e.g. `London` for the British-Canadian/Americans, `Seville` for the Spanish-derived four, etc.). See stock `data/homecity<civ>.xml:17` for the canonical value per parent.
- `<ambientsounds>` (line 19) `homecity\Revolutionambientsounds.xml` → parent civ's ambient sounds file (e.g. `homecity\britishambientsounds.xml`). See stock `data/homecity<civ>.xml:20`.

These do not cause floating; they just give a more thematic feel. **Defer until the priority-1/2 path-fix is verified in-engine.**

### Priority 4 — Stock civs

No problem found. Do not touch.

---

## Verification plan (post-fix)

1. Apply the priority-1 fix to `anwhomecitycanada.xml:10`.
2. Boot the mod, pick **British Canadians** at the civ-select screen, enter the home city. Confirm citizens (vendors, dregs, guards, idle settlers) walk on the embankment / streets, not the air.
3. Repeat the spot-check for one civ per parent-visual family: `Argentina` (Spanish), `Brazil` (Portuguese), `Egypt` (Ottoman), `Finland` (Russian), `Indonesians` (Dutch), `Hungary` (German), `Texas` (Mexican), `Napoleonic France` (French). If those 8 look correct, the fix has covered all 25.
4. The 26th civ (`ANWMexicans`) was already correct — no regression test needed beyond a screen check that nothing changed.

---

## Sources cited

- `data/anwhomecitycanada.xml` (lines 1-19, 2108-2253)
- `data/homecitybritish.xml` (lines 1-20)
- All 26 `data/anwhomecity*.xml` files (line 7 = visual, line 10 = pathdata)
- All 22 `data/homecity*.xml` files (line 7 = visual, line 10 = pathdata) — used as the source-of-truth pairing
- `artifacts/audits/nation_label_flag_audit.md` — civ enumeration cross-check
