# A New World DLC — Mod History & Current State

> **⚠ ARCHIVED — pre-v1.0 snapshot.**
> This file was the kickoff brief for the in-progress ANW migration. The
> migration has since completed and the mod shipped as **v1.0.0** on
> **2026-05-20** with **40 playable civs** (37 lobby-pickable + 3
> revolution-trigger), not the 48 pre-cull count described below.
>
> **For current release state, read these instead:**
> - `CHANGELOG.md` — release notes (authoritative for shipped scope)
> - `a_new_world_columns.html` — 62-column review surface (40 ANW + 22 base/DLC)
> - `artifacts/validation/v1_0_release_readiness.md` — release-gate report (local, gitignored)
>
> The body below is left intact as historical context for the migration
> work that produced v1.0. The "v1.0 release checklist" section is no
> longer the source of truth — all B1–B7 gates were satisfied or
> superseded; see CHANGELOG §[1.0.0] for what actually shipped.

---

## Mod identity

- **Name:** AOE 3 DE — A New World
- **File:** `modinfo.json` → `version: 1.0.0` *(shipped 2026-05-20; the "checklist not yet complete" line below is historical)*
- **HTML reference:** `a_new_world.html` (renamed from `LEGENDARY_LEADERS_TREE.html`); the per-civ column review surface is `a_new_world_columns.html`
- **Repo root:** `/var/home/jflessenkemper/AOE-3-DE-A-New-World/`

---

## Architecture overview

The mod covers **48 civs** split into two groups (pre-migration):

| Group | Count | Prefix | Personality files | Homecity files | In civmods.xml? |
|---|---|---|---|---|---|
| Base-game civs (British, Dutch, Aztec, …) | 22 | `british`, `dutch`, … | leader-named (`wellington.personality`) | `homecity{civ}.xml` | ❌ vanilla-owned |
| Revolution civs (Barbary, Yucatan, …) | 26 | `ANW*` | `anw*.personality` | `anwhomecity*.xml` | ✅ mod-owned |

The split causes every tool and validator to carry two code paths. The **ANW migration** eliminates it.

---

## ANW migration — the big in-progress work

All 48 civs are being unified under `ANW{Civ}` (e.g. `ANWBritish`, `ANWBarbary`).

### Token convention

| Layer | Format | Example |
|---|---|---|
| `<Civ><Name>` in civmods.xml | `ANW{PascalCase}` | `ANWBritish`, `ANWBarbary` |
| Personality filename | `anw{lower}.personality` | `anwbritish.personality` |
| Homecity filename | `anwhomecity{lower}.xml` | `anwhomecitybritish.xml` |
| `<forcedciv>` | matches `<Name>` | `ANWBritish` |
| Chatset | `anw_{lower}` | `anw_british` |
| Decks JSON key | `ANW{PascalCase}` | `decks_anw.json["ANWBritish"]` |

### Phase status

| Phase | Script | Status |
|---|---|---|
| 1 — Token map | `tools/migration/anw_token_map.py` | ✅ Done |
| 2 — Build ANW civmods | `tools/migration/build_anw_civmods.py` | ✅ Done |
| 2b — Extract vanilla civs | `tools/migration/extract_vanilla_civs.py` | ✅ Done |
| 2c — Vanilla data loader | `tools/migration/vanilla_data.py` | ✅ Done |
| 3 — Migrate strings | `tools/migration/migrate_strings.py` | ✅ Done (dry-run) |
| 4 — Migrate personalities | `tools/migration/migrate_personalities.py` | ✅ Done (dry-run) |
| 5a — Migrate homecities | `tools/migration/migrate_homecities.py` | ✅ Done (dry-run) |
| 5b — Build ANW decks | `tools/migration/build_anw_decks.py` | ✅ Done (dry-run) |
| Orchestrator | `tools/migration/run_anw_migration.py` | ✅ Done |

### Apply gate — UNBLOCKED

```
data/civmods.anw.xml: 48 civs, all ANW-prefixed, 0 TODO-ANW-VANILLA markers
```

**The next destructive step — requires explicit user confirmation before running:**
```bash
python3 tools/migration/run_anw_migration.py --apply
```

This will atomically:
- Rewrite `data/civmods.xml` (48 ANW blocks)
- Rename/rewrite all 48 personality files → `game/ai/anw*.personality`
- Rename/rewrite all 48 homecity files → `data/anwhomecity*.xml`
- Rewrite `stringmods.xml`, `randomnamemods.xml`, `techtreemods.xml`, `playercolors.xml`
- Rewrite `chatsetsmods.xml`
- Write `data/decks_anw.json` (merged from decks_standard.json + decks_legendary.json)

### Remaining phases (after --apply)

**Phase 6 — Tooling + validators rewrite**
Every tool that has a base-vs-rev branch collapses to one path over 48 ANW civs:
- `tools/validation/validate_html_vs_mod.py` — collapse `CIV_TO_HOMECITY` dict
- `tools/validation/validate_civmods_ui.py` — single iterator, no base/rev branch
- `tools/validation/validate_civ_crossrefs.py` — same
- `tools/validation/validate_civ_homecities.py` — same
- `tools/validation/validate_personality_overrides.py` — same
- `tools/validation/validate_dev_subtrees.py` — drop deferred-slug list
- `tools/cardextract/refresh_dev_subtrees.py` — drop `is_revolution` branch
- `tools/cardextract/refresh_mod_civ_decks_html.py` — read `decks_anw.json` only
- `tools/playtest/expectations.py` — one row per ANW civ

**Phase 7 — In-engine smoke test**
- Lobby picker shows exactly 48 ANW civs (no vanilla "British"/"Dutch" alongside)
- ANWBritish (Elizabeth): lobby name, portrait, flag, scoreboard, F4, end-game all correct
- ANWBarbary: same
- Doctrine matrix run → 0 FAIL rows in `playtest_report.txt`

**Phase 8 — Documentation + tag**
- CHANGELOG entry (BREAKING: save/replay compat broken, base civs replaced by ANW versions)
- Bump `modinfo.json` → `1.0.0` (already set but gate not met)
- Tag `v1.0.0`

---

## v1.0 release checklist

- [ ] **B1 ⛔ BLOCKER** ANW migration `--apply` + Phase 6 validators pass
- [ ] **B2 ⛔ BLOCKER** Doctrine matrix run → 0 FAIL rows in `playtest_report.txt` (~60 min on rig)
- [ ] B3 Install sanity (no error dialogs, mod in Mods list)
- [ ] B4 Lobby personality matrix — 48 ANW civs show correct name/portrait/tooltip
- [ ] B5 Four archetype matches — AI build order matches HTML reference prose
- [ ] B6 Save/Load smoke test
- [ ] B7 Uninstall clean-up
- [ ] After all above: finalize CHANGELOG, tag `v1.0.0`

---

## Current static test status

```
❌ Some validators fail — expected pre-migration
```

Failing checks reference `anwhomecity*.xml` and `anw*.personality` files that don't exist yet (they're created by `--apply`). Everything else passes. After `--apply` + Phase 6 the suite should be fully green.

---

## Key files (don't re-grep these)

| What | Path |
|---|---|
| Mod info | `modinfo.json` |
| HTML reference | `a_new_world.html` |
| Civ definitions (current) | `data/civmods.xml` (26 ANW blocks) |
| Civ definitions (post-migration) | `data/civmods.anw.xml` (48 ANW blocks, apply-ready) |
| ANW token map | `tools/migration/anw_token_map.py` |
| Migration orchestrator | `tools/migration/run_anw_migration.py` |
| Civ blurbs (48 nations) | `data/anw_civ_blurbs.json` |
| Merged decks (post-migration) | `data/decks_anw.json` |
| AI leader files | `game/ai/leaders/leader_*.xs` (23 files) |
| Personality files | `game/ai/*.personality` (48 files, pre-rename) |
| String overrides | `data/strings/english/stringmods.xml` |
| Playstyle spec | `playstyle_spec.json` (46 civs × 15 doctrines) |
| Card decks (current) | `data/decks_standard.json`, `data/decks_legendary.json` |
| Static test suite | `bash tools/test.sh --no-packaged` |
| Full validation suite | `python3 tools/validation/run_staged_validation.py` |

---

## Key constants (don't re-grep)

**Wall strategy** — `game/ai/aiHeader.xs:202-207`
```
0=FortressRing  1=ChokepointSegments  2=CoastalBatteries
3=FrontierPalisades  4=UrbanBarricade  5=MobileNoWalls
```

**Leader key bridge** (engine slug → spec slug):
```
wellington→elizabeth  catherine→ivan  crazyhorse→gall  jean→valette  usman→muhammadu
```
Defined at `game/ai/leaders/leaderCommon.xs:480-485`.

**15 canonical doctrines** — `tools/playtest/extract_playstyle_spec.py:94`

**Probe format:**
```
[LLP v=2 t=<ms> p=<id> civ=<name> ldr=<key> tag=<x.y>] k=v ...
```

---

## Recent git history (last 10 commits)

```
c0aa1f2 Dev subtrees: short consistent flag-hover blurb across all 48 civs
68dde06 Dev subtrees: drop the #locID badges from resolved strings
5c0cf20 Dev subtrees: pull actual text + art for base civs from vanilla data
1059e49 ANW migration: vanilla civ extraction + HTML reference ANW Provenance
e279ae7 ANW migration phases 3-5 (dry-run) + orchestrator
5ba5c87 ANW migration phase 2 (dry-run): build_anw_civmods.py + proposed civmods.anw.xml
e5bd044 ANW migration phase 1: token map foundation
4b84fb1 Dev subtrees: visual spot-check layout — images, game context, prominent strings
9c89fda Fix Yucatan Development subtree leaking outside nation-node
0464f90 Fix broken flag filenames + darken wood background
```
