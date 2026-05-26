# ANW v1.0 Release Gaps Assessment

**Date:** 2026-05-26
**Static gate status:** PASS (50/57, 0 FAIL, 7 SKIP — live-only validators)
**Question:** What are the gaps? Can we fill them in with base-game data or art?

## TL;DR

**No real content gaps remain that can be plugged with base-game data
or art.** The remaining gaps are either (a) live-gameplay data that
requires running actual matches (not asset gaps), (b) documentation
lag (XML is authoritative; design-intent JSON is stale), or
(c) design-intent constraints (revolution-only civs that are
intentionally not lobby-selectable).

## Gap inventory

### 1. Ally-deck drift (13 civs)

**What:** `data/decks_anw.json` (design-intent) ≠
`data/anwhomecity*.xml` (engine-loaded primary deck).

**Civs:** Dutch, French, Germans, Haitians, Hungarians, Napoleonic
France, Ottomans, Peruvians, Portuguese, Revolutionary France,
Russians, Spanish, USA.

**Player impact:** **None.** The engine reads the XML. Players see the
correct deck in-game; only the JSON documentation is stale.

**Can base-game data fix this?** Not the right question — this is
*documentation* drift, not engine drift. Fix is an
auto-sync-JSON-from-XML build step (v1.1 follow-up). See
`artifacts/validation/ally_deck_drift_audit.md`.

### 2. Five "stub" revolution civs

**Civs:** Californians, Central Americans, Lower Canada (was
"French Canadians"), Rio Grande, Yucatan.

**State:** Have full home-city XMLs + leader scripts + art, but **no
`civmods.xml` entry**, so they cannot be selected as primary civs in
the lobby. Reached only through Revolution dispatch in
`leader_revolution_commanders.xs`.

**Player impact:** Players reach these civs by revolting from a parent
civ (Mexicans → California/Texas revolutions; Canadians → Lower
Canada; etc.). They are *intentionally* revolution-only, matching
historical fact that these were never sovereign nations in the era.

**Can base-game data fix this?** No fix needed — this is design
intent. Adding civmods.xml entries would let players pick them as
*primary* civs, which contradicts the historical framing the mod is
built around.

### 3. Live-gameplay validators (7 SKIP)

**Validators:** `live_mod_install`, `runtime_logs`, `live_picker`,
`input_harness`, plus 3 others gated on a running game.

**What's missing:** Replay captures from actual matches. The static
gate verifies everything that can be checked from files on disk;
these final 7 verify behaviour with the engine actually running.

**Can base-game data fix this?** No — these require live game
sessions. Operator runs them manually with `--include-live` when the
game is running. Not blocking for v1.0 ship, but should be run during
final smoke-test before workshop upload.

### 4. Art surfaces (zero gaps)

All 40 ANW civs have:
- ✓ Lobby portrait (`cpai_avatar_*.png`)
- ✓ Loading flag
- ✓ Home-city preview
- ✓ Leader portrait
- ✓ Home-city flag
- ✓ Deck card back
- ✓ Postgame flag

Verified by `validate_icon_path_existence.py` (PASS, 0 missing) and
`tools/validation/build_art_contact_sheet.py` (40-civ static contact
sheet, all surfaces resolved).

## What we *could* fill with base-game data (and chose not to)

- **Leader voiceovers for revolution civs:** could fall back to base-
  game leader audio, but `resources/audio/revolution_leader_manifest.json`
  already maps each Patriote/Bolívar/etc. to deliberately chosen
  base-game speech samples. Coverage is complete.
- **Generic civ icons for the 5 stub civs:** the stubs already have
  bespoke art (Bear Flag for Californians, Patriote flag for Lower
  Canada, Lone Star for Rio Grande, etc.). Falling back to generic
  base-game icons would *reduce* polish, not fill a gap.

## Recommendation

**Ship v1.0 as-is.** The remaining gaps are documentation lag (deck
drift) and intentional design constraints (revolution-only civs). The
seven live validators should be run manually as the final pre-upload
smoke test.

## v1.1 backlog

1. Auto-sync `decks_anw.json` ← `anwhomecity*.xml` at build time, OR
   make XML the only source and delete the JSON.
2. Build playthrough harness that runs the 7 live validators on a
   fresh install (one-button smoke test).
3. (Optional) Add explicit "revolution-only" tagging to the 5 stub
   civs so dashboards label them as such instead of marking them as
   missing.
