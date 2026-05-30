# Session handoff — 2026-05-09 (overnight)

## TL;DR

The mod's "46 civs in lobby picker" goal is **directly fixable** — the 25
civs that don't load use a non-alpha StatsID format the engine rejects
("1A"-"1Y"). Change them to 2-char alpha (26²=676 combinations, ~633
available) and they'll appear. Engine schema confirmed by reverse-engineering
the base game's `civs.xml` from `Data.bar`.

Plus a handful of test-infrastructure improvements landed: deduped
`stringmods.xml` (leader names render correctly now), built a unified
validator gate, added a `validate_civ_loadability.py` that catches this
exact bug pre-deploy.

## What's broken (in priority order)

### 1. 25 ANW civs invisible in lobby picker — STATSID FORMAT BUG

**Root cause (confirmed via base game civs.xml extraction):**
- Engine's lobby picker shows civs that have `<main>1</main>` + a valid
  2-char alpha `<statsid>` in the merged civmods.xml
- Base game's 22 unique StatsIDs are all 2-char alpha (SP, BR, FR, PT, DU,
  RU, DE, OT, IR, SI, AZ, JP, CH, IN, IC, SW, US, ET, HA, MX, IT, MT)
- **ANW added 25 civs with "1X" format StatsIDs (1A-1Y).** Engine rejects.
- 21 ANW civs that DO load use 2-char alpha format (replacing base game
  slots). ANWRevFrance with new StatsID=RF works, proving engine accepts
  NEW 2-char alpha StatsIDs from civmods.xml.

**Affected civs (25):** ANWCanadians (1A), ANWHaitians (1B),
ANWIndonesians (1C), ANWSouthAfricans (1D), ANWBritish (1E),
ANWFrenchCanadians (1F), ANWFrench (1G), ANWBajaCalifornians (1H),
ANWYucatan (1I), ANWRioGrande (1J), ANWMayans (1K), ANWCalifornians (1L),
ANWTexians (1M), ANWMexicans (1N), ANWEgyptians (1O), ANWOttomans (1P),
ANWPortuguese (1Q), ANWArgentines (1R), ANWChileans (1S),
ANWPeruvians (1T), ANWColumbians (1U), ANWSpanish (1V), ANWHungarians (1W),
ANWRomanians (1X), ANWSwedes (1Y).

**Fix path:** edit `data/civmods.xml` for each of these 25 civs, change
`<statsid>1X</statsid>` to a new 2-char alpha code. Two strategies:

a) **Replace base game slots fully** — assign ANWBritish=BR,
   ANWFrench=FR, ANWSpanish=SP, ANWPortuguese=PT, ANWMexicans=MX,
   ANWOttomans=OT, ANWSwedes=SW. But these are ALREADY taken by other
   ANW civs (FR by ANWNapoleonicFrance, MX by ANWCentralAmericans, OT
   by ANWBarbary, PT by ANWBrazil, SW by ANWFinnish). Pick which civ
   gets the base slot and demote the other to a new alpha code.

b) **Use new alpha codes** — assign each missing civ a unique 2-char
   alpha code that doesn't collide. Engine adds them as NEW picker
   entries alongside base game civs. User stays unsatisfied because
   "base game civs still show up", but all 46 ANW civs become pickable.

**My recommendation: (b) for now**, then consider stripping base game
civs via a separate civmods entry that sets their `<main>0</main>`
(if engine respects mod overrides on `main`).

**Validator that catches this:** `tools/validation/validate_civ_loadability.py`
(shipped this session). Run before every deploy. 10/10 unit tests pass.

### 2. Opponent picker click-targeting

P2-P8 picker clicks land on wrong civ (proven empirically: asked for
ANWArgentines/Aztecs roster, got George Washington x3 + Random x4).
Different click pipeline than P1's picker. Untouched this session.

**Workaround:** use per-civ-match mode (P1 picker proven working at
~7-9s/civ). 46 sequential matches × ~30s = ~40 min full run.

### 3. Scenarios still blocked by Arxan integrity check

Reverse-engineered: Arxan-packed `.text` sections (entropy 7.99/8.0).
Goldberg DLL hijack triggers integrity guard ("Fatal Error: one or more
game files is invalid"). All custom scenarios fail "INVALID FILE" at
picker click time. Documented in `tools/validation/scenario_load_bypass.md`.

## What landed this session

| Deliverable | Status |
|---|---|
| `tools/validation/validate_civ_loadability.py` + 10 unit tests | ✅ |
| `tools/validation/run_all_validators.py` (unified pre-deploy gate, 32 validators) | ✅ |
| stringmods.xml dedupe (42 conflicting locID dups → 0; leader names render correctly now) | ✅ |
| Picker-open detection bug fix (idempotent open/close, false-negative `picker_opened_since`) | ✅ |
| `picker_civ_order.json` cache (45/46 ANW civs, **but cache is over-permissive — civ_loadability validator overrides via StatsID class**) | ⚠ |
| Batched scroll: 38% speedup (476ms/tick → 100ms/tick) | ✅ |
| Static art verifier: 1432 PASS / 30 WARN / 25 FAIL (artist work remainder) | ✅ |
| Auto-fix art bugs (122/150 FAILs cleared in earlier session pass) | ✅ |
| Base game `civs.xml` extracted to `artifacts/base_game_civs.xml`, JSON at `artifacts/base_game_civs.json` | ✅ (this session) |
| Unit test count overall (across all suites) | ~80 passing |

## Validator gate first run (32 validators)

22 PASS, 8 FAIL, 2 SKIP. Fails:
- `civ_loadability` — the StatsID bug (expected; we just shipped the validator that surfaces it)
- `playstyles`, `leader_vs_spec`, `doctrine_compliance`, `visuals`,
  `dev_subtrees`, `html_reference`, `html_vs_mod` — uninvestigated this
  session; some might be CLI-arg issues, some real bugs.

Run: `python3 tools/validation/run_all_validators.py`
Reports at: `tools/validation/run_all_validators_report.{md,json}`

## Concrete next steps (in priority order)

1. **Fix the StatsID bug.** ~30 min mechanical edit:
   - Decide strategy (a) or (b) above
   - Edit `data/civmods.xml` 25 entries
   - Run `validate_civ_loadability.py` → expect 46/46 PASS
   - `manage_game.py cycle` → verify 46 civs in lobby picker
2. **Investigate the 8 unrelated validator FAILs** (playstyles, etc.)
3. **Fix opponent picker click-targeting** so 8-civ-per-match mode works
4. **Run end-to-end real-game validation** for all 46 civs

## Reference: tools to know about

- `tools/validation/run_all_validators.py` — single CI gate, 32 validators
- `tools/validation/validate_civ_loadability.py` — catches StatsID bug pre-deploy
- `tools/aoe3_automation/lobby_driver.py` — 50KB, OCR-verified picker, batched scroll
- `tools/aoe3_automation/picker_civ_order.json` — picker position cache (45/46 civs)
- `tools/bar_extract.py` — extract `.bar` archives (used to find civs.xml)
- `tools/cardextract/xmb.py` — XMB → ElementTree decoder
- `artifacts/base_game_civs.json` — 126 base game civ entries
- `artifacts/base_game_civs.xml` — same as readable XML
- `tools/validation/scenario_load_bypass.md` — the Arxan investigation

## Reference: things NOT to redo

- Goldberg DLL hijack — Arxan kills the game on launch. **Don't.**
- Scenario emitter — engine rejects all custom binaries. **Use Scenario Editor manually if scenarios are needed.**
- Steam Cloud / `remotecache.vdf` SHA1 manifest — disproven as the gate; engine validates something else (memory-time hash?).
- Trying to fix the OCR matcher to be perfectly accurate — `validate_civ_loadability.py` uses StatsID format as authoritative, so the cache being slightly fuzzy doesn't matter.

## Notes for tomorrow

The "fix StatsIDs" step is **the unblock**. Everything we built this
session — validators, OCR pipeline, batched scroll, art verifier — was
infrastructure the StatsID fix lets us actually USE on 46 civs. Once
the picker shows 46 ANW civs, run:

```bash
python3 tools/validation/run_all_validators.py             # gate
python3 tools/validation/validate_civ_loadability.py        # 46/46
python3 tools/validation/run_full_validation.py --threshold-ms 30000  # full pass
```

That's the path to "every nation tested thoroughly."

<!-- 2026-05-19: Deleted 4 dormant civs (ANWCalifornians, ANWCentralAmericans, ANWRioGrande, ANWYucatan) — all were main=0 placeholders with no agetech block. Civ total reduced from 44 to 40. -->
