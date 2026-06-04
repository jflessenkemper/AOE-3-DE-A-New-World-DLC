# A New World AI — Release-Quality QA Plan

**Purpose:** define the full set of tests that must pass before calling this mod "release-ready" — i.e., any player can install it via the Steam Workshop / Mods folder and have it work without surprises.

Organized from cheapest/fastest to most expensive. Target: green on all Tier 1 + Tier 2 before public release; Tier 3 is "nice-to-have" continuous monitoring.

---

## Tier 0 — Baseline static validation (automatable in CI, < 2 min)

Already implemented under `tools/validation/`. These must all PASS on every commit:

| Check | Script | What it catches |
|---|---|---|
| XS syntax + symbol resolution | `validate_xs_scripts.py` | Undefined functions, undefined `cv*` globals, typos |
| HTML reference vs mod consistency | `validate_html_vs_mod.py` | Docs/reality drift |
| String table coverage | `validate_stringtables.py` | Missing `_locID`, duplicate IDs, unresolved refs |
| Live mod install matches repo | `validate_live_mod_install.py` | User-installed copy desync |
| Deck references valid | `validate_decks.py` / cards.json lookup | Raw card IDs displaying in explorer |
| Personality files resolve nameIDs | **NEW — write this** | Override display names actually land in stringmods.xml |

**Gap to close:** wire a GitHub Action (`.github/workflows/validate.yml`) running all of the above on push to main. A broken mod that passes CI is the single biggest pre-release risk.

---

## Tier 1 — Must-pass before public release (~4 hours total)

### 1.1 Install-sanity test (30 min)
Steps a fresh user would take:
- Clone the mod repo to a clean machine
- Copy `game/`, `data/` contents to `%USERPROFILE%\Games\Age of Empires 3 DE\<steamID>\mods\` (Windows) or the Proton equivalent
- Verify Steam/Epic launcher shows the mod available
- Enable in-game, restart
- Confirm main menu loads without errors (no "XS script error" dialog)

**Pass criteria:** zero error dialogs. Mod shows in "Mods" list with correct version.

### 1.2 Lobby personality matrix (~2 hours) — **HIGHEST-VALUE DYNAMIC TEST**
For each of 22 overridden personalities (elizabeth→Wellington, amina→Usman, Ivan→Catherine, etc.):

1. Enter Single Player Skirmish setup
2. In any AI slot, open the personality dropdown
3. Select the personality by its **overridden name** (e.g. look for "Duke of Wellington", not "Queen Elizabeth")
4. Verify the slot now shows:
   - ✅ Overridden display name (e.g. "Duke of Wellington")
   - ✅ Overridden portrait icon (e.g. Wellington image, not Elizabeth)
   - ✅ Overridden tooltip text (e.g. "British · line-and-logistics...")
   - ✅ Correct civ auto-selected (`forcedciv` applied)
5. Screenshot for record

**Pass criteria:** all 4 checks pass for all 22. Driver: `tools/aoe3_automation/personality_matrix.py` (to be written).

### 1.3 In-game quote + scoreboard verification (one match per archetype, ~4 hours)
Four archetype matches, each 15 min:
- **Aggressive:** Napoleon / Suleiman / Washington
- **Defensive:** Wellington / Valette / Pachacuti
- **Economic:** Henry / Kangxi / Maurice
- **Naval:** Valette / Kangxi on water map

For each:
- Scoreboard shows overridden leader name (not base-game queen/king default)
- In-match taunt/chat triggers show correct leader name + portrait
- AI actually plays the doctrine stated in HTML (build order + unit mix matches)

### 1.4 Revolution-civ spot-check (30 min)
Pick 3 of the 26 `anw*` civs (e.g. Napoleonic France, Haitians, Finnish) and confirm each:
- Appears in civ picker as a top-level civ
- Loads into a match with correct starting units, tech tree, home city
- AI plays (not stuck idle)

### 1.5 Save/Load smoke test (30 min)
- Start any Skirmish match
- Play 5 min
- Save → quit to main menu → reload save
- Confirm: AI resumes, no XS errors, units + resources preserved, scoreboard intact

### 1.6 Uninstall clean-up (15 min)
- Disable the mod in the Mods menu
- Restart game
- Confirm: base game plays normally, no leftover string IDs, no crash on Skirmish setup

---

## Tier 2 — Should-pass before wide release (~6 hours)

### 2.1 Difficulty sweep (2 hours)
Run a 15-min match at each difficulty (Sandbox / Easy / Moderate / Hard / Extreme / Expert) with the same civ (e.g. British/Wellington). Confirm:
- AI does not crash at any difficulty
- Higher difficulty = more aggressive/efficient play (sanity check)
- AI does not stall (zero units after 10 min = fail)

### 2.2 Game-mode sweep (2 hours)
For Wellington + Napoleon:
- Supremacy (default)
- Deathmatch
- Empire Wars
- Treaty (20-min timer)

Confirm AI enters correct age/posture for each mode. Treaty in particular tests that AIs don't attack during the timer.

### 2.3 Map coverage (1 hour, spot-check)
Pick 5 maps covering different terrains:
- Great Plains (open land)
- Caribbean (island/naval)
- Yukon (cold/closed)
- Bayou (swamp/tight)
- Saguenay (winter/forested)

Run a 10-min match on each with one defensive + one aggressive AI. Confirm no pathing errors, AI doesn't get stuck.

### 2.4 Multi-AI stress test (1 hour)
8-player FFA with 8 different overridden leaders. Confirm:
- All 8 start correctly
- No XS performance degradation (frame rate > 30 fps at 10 min)
- Scoreboard shows all 8 leader names correctly

---

## Tier 3 — Release+ continuous monitoring

### 3.1 Multiplayer / LAN (not fully automatable)
- Manual: host a 2-player LAN game with a friend, both have mod installed. Confirm sync.
- Manual: host with mod, joiner WITHOUT mod. Document expected behavior (desync? refused?). **Likely finding:** host-only mod. Add to README.

### 3.2 Campaign-mode compatibility
Vanilla campaigns (Act I/II/III, Shadow, Asian Dynasties, historical battles). Does mod break any scripted scenario? Test one mission per act.

### 3.3 Workshop-style submission
If publishing to Steam Workshop:
- `.age3mod` packaging
- Mod.xml metadata (author, version, description, thumbnail)
- Workshop upload via in-game mod browser
- Fresh VM download + install test

---

## Tier 4 — Polish / localization (pre-1.0 final)

- **Language coverage:** stringmods.xml currently English-only. Confirm non-English users see base-game strings (not raw IDs) for unmodded areas. Ideally provide French/German/Spanish stringmods translations for the 26 mod civs.
- **Accessibility:** colorblind mode, subtitles for leader quotes
- **Load time:** mod-enabled load time should be within 10% of base game
- **Memory:** no leak after 1-hour match

---

## Bug-class regression checks (keep these in CI forever)

Each is a "bug we found, don't let it come back" test:

| Regression | Test |
|---|---|
| `llIsEliteUnit` undefined | validate_xs_scripts must flag undefined helpers |
| `cvMinNumVills` undeclared | validate_xs_scripts must flag undefined cv-vars |
| Raw card IDs displaying | check cards.json resolves every deck entry to name+desc |
| Personality nameID → missing string | new validator: for each .personality in game/ai/, confirm nameID + tooltipID exist in stringmods.xml with non-empty value |
| Duplicate `_locID` in stringmods.xml | validate_stringtables |
| Mod install drift | validate_live_mod_install |

---

## Release checklist (one-page summary)

- [ ] Tier 0 all green in CI
- [ ] Tier 1.1 install-sanity ✅
- [ ] Tier 1.2 all 22 personalities verified in lobby ✅
- [ ] Tier 1.3 four archetype matches observed ✅
- [ ] Tier 1.4 three revolution civs confirmed playable ✅
- [ ] Tier 1.5 save/load works ✅
- [ ] Tier 1.6 uninstall clean ✅
- [ ] Tier 2 sweeps done
- [ ] README updated with install instructions, compatibility matrix, known issues
- [ ] Version bump in `data/version.xml` (or equivalent)
- [ ] Git tag + GitHub release with changelog
- [ ] (Optional) Steam Workshop upload

---

## What's actually tested *right now* (as of 2026-04-22)

- ✅ Tier 0: all static validators pass
- ✅ Tier 0: CI **NOT yet wired** — high-priority gap
- ⚠️ Tier 1.2: **0 of 22** personalities deterministically verified in lobby (matrix driver not yet written)
- ⚠️ Tier 1.3: one informal multi-civ Deathmatch run; doctrine comparison inconclusive (random personalities selected, not the overrides under test)
- ✅ Tier 1.4: revolution civs selectable in picker (confirmed via earlier 45-civ matrix)
- ❌ Tier 1.5: save/load never tested
- ❌ Tier 1.6: uninstall never tested
- ❌ Tier 2: nothing
- ❌ Tier 3: nothing
- ❌ Tier 4: nothing

**Honest release-readiness verdict: ~30%.** The mod *probably* works for most users, but it has not been end-to-end validated in the way an official release would demand. Tier 1.2 + 1.3 + CI are the critical gaps to close before a confident public release.
