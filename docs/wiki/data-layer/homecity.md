# Home City XML

> Plain XML at `data/<modprefix>homecity<civ>.xml`. Defines a single
> Home City: civ binding, hero/leader name, default cards, ambient
> sound, scene files, camera, starting coffers. Each civ in
> `civmods.xml` references its homecity via `<homecityfilename>`.

## Schema

Top-level container: `<homecity>`. Reference example in this repo:
[`data/anwhomecitybritish.xml`](../../../data/anwhomecitybritish.xml).

| Field | Type | Notes |
|---|---|---|
| `<civ>` | string | Civ key, must match `<civ><name>` in civs.xml |
| `<name>` | string | Display name; commonly `$$<id>$$` referencing a `_locID` |
| `<heroname>` | string | Leader/hero display name; `$$<id>$$` |
| `<gatherpointunit>` | proto | Unit used as the home-city gather flag |
| `<visual>` | path | XML scene file (e.g. `british\british_homecity.xml`) |
| `<watervisual>` | path | Water-scene XML |
| `<backgroundvisual>` | path | Background-scene XML |
| `<pathdata>` | path | `.gr2` granny pathing file |
| `<camera>` / `<widescreencamera>` | path | `.cam` camera files |
| `<transportroundtriptime>` / `<transportactivationtime>` | int/float | Transport ship timings |
| `<level>` | int | Initial home-city level |
| `<skillpoints>` | int | Initial skill points |
| `<lightset>` | string | Lighting bundle (e.g. `London`) |
| `<watertype>` | string | Water-rendering bundle |
| `<numpropunlocksearned>` | int | Unlocked decorations count |
| `<ambientsounds>` | path | XML bundle of ambient sounds |
| `<xsai>` | string | Home-city XS AI hook (e.g. `generic_city`) |
| `<heroprotounits>` | block of `<protounit>` | Hero proto units available |
| `<coffers>` | block (`<current>`/`<maximum>`) | Per-resource coffer values: food, wood, gold, fame, ships, skillpoints, xp |
| `<cards>` | block of `<card>` | Available home-city cards |

### `<card>` block

| Field | Notes |
|---|---|
| `<name>` | Card identifier (resolves to a tech in techtree) |
| `<maxcount>` | Times the card can be sent (-1 = infinite) |
| `<level>` | Required home-city level to unlock |
| `<prereqtech>` | Required prerequisite (card name or tech) |
| `<age>` | Earliest age usable (0..4) |
| `<displayunitcount>` | UI hint: units delivered |
| `<infiniteinlastage>` | 0/1 toggle |

## File paths

- `data/<modprefix>homecity<civ>.xml` (e.g. `anwhomecitybritish.xml`).
- Visual / water / background / pathing / camera files: `data/<civ>/...`
  mirroring base layout. Some scene assets ship inside base BARs and
  are referenced by name only.

## Cross-references

- [civmods.xml](civmods.md) — `<homecityfilename>` references this
  file.
- [stringmods.xml](stringmods.md) — `<name>$$<id>$$</name>` and
  `<heroname>$$<id>$$</heroname>` reference `_locID`s.
- [techtreemods.xml](techtreemods.md) — `<card><prereqtech>` references
  techs/cards.
- [SELECT HOME CITY picker](../ui-layer/select-home-city.md) — picker
  enumerates and renders homecity entries.
- [Additive data mods](../additive-data-mods.md) — additive merge
  applies if a mod replaces an existing homecity.

## Tools

| Path | Purpose |
|---|---|
| [`tools/validation/validate_civ_homecities.py`](../../../tools/validation/validate_civ_homecities.py) | Per-civ homecity presence and structure |
| [`tools/validation/validate_homecity_assets_exist.py`](../../../tools/validation/validate_homecity_assets_exist.py) | Visual/scene asset paths resolve |
| [`tools/validation/validate_homecity_cards.py`](../../../tools/validation/validate_homecity_cards.py) | Card refs resolve into techtree |
| [`tools/validation/validate_homecity_leader_match.py`](../../../tools/validation/validate_homecity_leader_match.py) | Hero name matches expected leader |
| [`tools/validation/validate_homecity_visuals.py`](../../../tools/validation/validate_homecity_visuals.py) | Visual references valid |
| [`tools/validation/validate_no_homecity_doubles.py`](../../../tools/validation/validate_no_homecity_doubles.py) | Suppression entries override `<homecityfilename>` to empty for hidden civs |
| Engine `DebugOutputGameData` | Merged homecity dumped if mod overrides one |

## Known issues

- **Visual/scene assets** (`<visual>`, `<watervisual>`,
  `<backgroundvisual>`) typically reuse base-game scenes. Custom city
  scenes are out of scope of additive XML; they require BAR-shipped
  scene files.
- **Card-ID drift across patches.** Cards are referenced by string
  name; if a base patch renames a card, mods break.
- **Heroprotounits** must exist in the merged proto tree; new custom
  heroes need a corresponding protomods entry.
- **Saved profile reuse**: homecity changes do not retroactively
  migrate saved profiles. Players may need to reset their profile.

## Open questions

- Whether `<xsai>` accepts arbitrary custom keys or only a fixed set.
- Whether `<numpropunlocksearned>` interacts with player profile data
  or only seeds initial state.
- Whether `<level>` higher than 1 is honoured for new civs.
- Authoritative list of `<lightset>` and `<watertype>` keys.

## Sources

- [HeavenGames newciv tutorial](https://aoe3.heavengames.com/modding/tutorials/expert/newciv/index.shtml).
- This repo: `data/anwhomecitybritish.xml` and siblings.
