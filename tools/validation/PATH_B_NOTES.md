# Path B (lobby coverage matrix) – session notes 2026-05-08

## TL;DR

End-to-end **46-civ AI behaviour validation via the lobby picker**. 6 lobby
matches × 8 OCR-verified civs each. Built on top of the existing
`set_civ_by_token_verified()` plus new helpers for opponent slots and the
playbook A-F roster. **Infrastructure is complete and unit-tested
(23/23 passing). OCR is live-calibrated. The remaining live-fragility is
that `ANW_TO_PICKER_INDEX` is stale w.r.t. the current mod state — see
"Remaining work" below.**

## What got built (this session)

| File | Change |
|---|---|
| `tools/aoe3_automation/lobby_driver.py` | Added `set_opponent_civ_by_token_verified()`, `set_anw_8civ_lobby()`, `_find_target_row_in_picker()` (OCR-driven scroll-and-find), `_preprocess_for_ocr()` (4× LANCZOS + grayscale). Re-tuned `_ocr_picker_rows()` to read crop coords from `lobby_coords.json`. `set_civ_by_token_verified()` now falls back to OCR-driven scrolling on attempts 6+ when index-based retries exhaust. |
| `tools/aoe3_automation/lobby_coords.json` | `civ_picker.row_y_start` 296 → **301** (live re-calibration; row centres at 301, 365, 428, 494, 558, 622, 685, 751, 814, 877). New keys `civ_picker.leader_name_crop` and `civ_picker.opp_leader_name_crop` (x0=180 skips the leader flag, y0_off=±22 stays inside the highlighted-row band). `scenario_picker.file_picker_row_x` 850 → **650** (per session handoff). |
| `tools/aoe3_automation/test_picker_verified.py` | Added `TestSetOpponentCivByTokenVerified` (5 tests) and `TestSetAnw8CivLobby` (3 tests). Total 23/23 pass. |
| `tools/validation/run_full_validation.py` | New `--coverage-mode` flag. Drives `coverage_match_loop()` which iterates A–F rosters, runs `set_anw_8civ_lobby()` for each, clicks PLAY, observes for `threshold_ms+30s`, cycles game, slices `Age3Log.txt` to `<run>/scenario_logs/<LETTER>_log.txt`, then fans out via `scenario_coverage.py`. |

## OCR calibration (verified live)

1. **`row_y_start` was off by ~5 px.** Pre-existing JSON had 296; live picker
   shows row 0 highlighted band centred at y=301. Empirically derived row
   centres: 301, 365, 428, 494, 558, 622, 685, 751, 814, 877 (Δ=64).
2. **OCR was reading flag pixels as letters.** Old crop `x0=80` overlapped
   the leader flag/portrait icon; tesseract returned garbled prefixes
   (e.g. `WR cusson)` instead of `(LONDON)`).
3. **Fix**: `x0=180`, `y0_off=±22`, plus 4× LANCZOS upscale + grayscale.
   Verified live on the actual lobby screenshot: every visible row OCRs
   cleanly:

   ```
   row 0: ANDOM PERSONALITY
   row 1: DELHI)
   row 2: TENOCHTITLAN)
   row 3: WASHINGTON, D. C.)
   row 4: STOCKHOLM)
   row 5: SEVILLE)
   row 6: ST. PETERSBURG)
   row 7: LISBON)            ← highlighted (orange band detected)
   row 8: ISTANBUL)
   row 9: MEXICO CITY)
   ```

4. `_identify_civ_from_ocr` and `_ocr_text_matches_civ` correctly map these
   home-city strings to ANW tokens via `HOME_CITY_TO_TOKEN`. E.g.
   `LISBON) → ANWPortuguese`, `LONDON) → ANWBritish`.

## Two pickers, one click target

The lobby has **two distinct pickers**:

- **SELECT HOME CITY**: alphabetical-by-civ-with-home-city, opens when
  clicking the leader flag area on a row that already has a civ assigned.
  Civs labelled by home city only (e.g. `(LISBON)`).
- **SELECT CIVILIZATION**: alphabetical-by-civ-name, opens when clicking
  the leader portrait or `?` icon on a Random Personality row. Civs
  labelled by civ name (e.g. `Britain`, `Italy`).

`p1_civ_picker = [630, 170]` opens whichever picker the engine prefers for
the current state. After P1 has been set to e.g. Russia, clicking it opens
the HOME CITY picker. After P1 is reset to Random Personality, the same
coord opens the CIVILIZATION picker. **The OCR helpers handle both** — the
HOME_CITY_TO_TOKEN dict maps `(LONDON)` → `ANWBritish` so the verifier
treats both forms equivalently.

## Stale `ANW_TO_PICKER_INDEX`

Live observation: `ANW_TO_PICKER_INDEX["ANWBritish"] = 7`, but at scroll=0
the SELECT HOME CITY picker shows `(LISBON)` at row 7 (= ANWPortuguese).
The picker's actual top-scroll order is:

```
0: Random Personality
1: (DELHI)            → ANWIndians
2: (TENOCHTITLAN)     → ANWAztecs
3: (WASHINGTON, D.C.) → ANWUSA
4: (STOCKHOLM)        → ANWSwedes
5: (SEVILLE)          → ANWSpanish
6: (ST. PETERSBURG)   → ANWRussians
7: (LISBON)           → ANWPortuguese
8: (ISTANBUL)         → ANWOttomans
9: (MEXICO CITY)      → ANWMexicans
```

This is **not the alphabetical civ-name order** that
`picker_scroll_table.json` was built around. The mod (or a recent patch)
re-ordered the picker. Until the index map is rebuilt, the
index-based path of `set_civ_by_token_verified()` will land on the wrong
civ on attempt 1.

The OCR-driven fallback (`_find_target_row_in_picker()`) should
self-correct, but during the smoke it hit `(SEVILLE)` repeatedly even on
attempts 6-8. Suspected root cause: the picker auto-recentres on the
currently-selected civ when reopened, so cancel+reopen does NOT reset
scroll to the top once a non-Random civ has been chosen. The fallback
needs a "cancel → set Random → cancel → reopen → scroll-from-top" reset
preamble.

## Live smoke verdict

- Game launched OK; lobby reachable via `click_skirmish()`.
- HOME CITY picker opens correctly; 10 rows visible.
- **OCR pre-tuning**: failed (garbled text on every row).
- **OCR post-tuning**: succeeds — every row OCRs cleanly on the captured
  ANWBritish screenshot.
- **End-to-end pick**: still fails because of stale index map AND the
  not-yet-implemented "scroll-to-top" reset in the OCR fallback.
- **8-civ lobby + PLAY + auto-resign + slice + validate cycle**: NOT
  validated end-to-end this session. Infrastructure is in place; smoke
  blocks on the index/picker reset issue.

## Remaining work (priority order)

1. **Rebuild `picker_scroll_table.json` and `ANW_TO_PICKER_INDEX`.**
   `lobby_driver.py --map-picker` walks the picker and writes a new
   scroll table; ANW_TO_PICKER_INDEX needs a manual rebuild from the
   resulting `civ_names` list. With a fresh table, attempt 1 of the
   verifier should land on the right civ for every ANW token.
2. **Add a "reset to Random" pre-step** to `_find_target_row_in_picker`.
   Right now if P1 is a non-Random civ, reopening the picker auto-scrolls
   to that civ; we never see the top of the list. Fix: click Cancel,
   then click `set_civ_by_index(coords, 0)` to set Random Personality,
   then reopen. After that, scroll_down() advances from a known top.
3. **Run the smoke** (see "How to run" below) to confirm the full
   8-civ → PLAY → log-slice → validator chain works.

## How to run the full pass once tuning is locked in

```bash
# 1. Make sure the game is closed (or expect manage_game.cycle to handle it)
python3 tools/aoe3_automation/manage_game.py status

# 2. (One-time, every mod re-deploy) Rebuild the picker scroll table:
python3 tools/aoe3_automation/lobby_driver.py --map-picker
# → produces tools/aoe3_automation/artifacts/lobby_driver/picker_map/
# → manually update ANW_TO_PICKER_INDEX from the regenerated civ_names list

# 3. Run the coverage pipeline (auto-resign at 30s; 6 matches × 8 civs)
python3 tools/validation/run_full_validation.py \
    --coverage-mode \
    --threshold-ms 30000

# Output:
#   artifacts/full_validation_runs/<ts>/scenario_logs/[A-F]_log.txt
#   artifacts/full_validation_runs/<ts>/scenario_coverage_report.json
#   artifacts/full_validation_runs/<ts>/coverage_match_summary.json
```

## Known fragility

- **Game window focus**: `_ensure_window_focus()` queries by name "Age of
  Empires III"; if a stale crashed AoE3 process exists, xdotool grabs the
  wrong WID and clicks land off-screen. Mitigation: kill stray PIDs before
  each run.
- **Picker auto-scroll on reopen**: the picker centres on the currently-
  selected civ when reopened; cancel+reopen does NOT scroll back to the
  top of the list. Affects `_find_target_row_in_picker` — needs the
  "reset to Random" pre-step.
- **`p1_civ_picker` opens different pickers based on state**: when P1 has
  no civ yet → SELECT CIVILIZATION; when P1 already has one → SELECT
  HOME CITY. The OCR helpers tolerate both via `HOME_CITY_TO_TOKEN`.
- **`ANW_TO_PICKER_INDEX` drift**: index map will go stale every time the
  mod's civ list changes. Long-term: derive from picker OCR at session
  start, cache to disk for the run.
- **Tesseract row-1 drop-out**: row 1 (DELHI in the smoke screenshot)
  intermittently OCRs empty if the leader flag has unusual brightness
  bleeding into the y_center band. The retry loop tolerates one missed
  row.
