# Controller Rewrite Notes — lobby_driver.py

Status: in-progress (last update incremental; see timestamps in commits / file mtimes).

## Goal
- 100% reliable civ selection by token (any of 46 ANW civs).
- Configure 8-civ lobby in <30s (stretch <15s).
- Backward-compatible public API: `set_civ_by_token_verified`,
  `set_opponent_civ_by_token_verified`, `set_anw_8civ_lobby`.

## Baseline (current code) measured pain points
1. `_find_target_row_in_picker` runs an OCR walk (10 rows × 4× LANCZOS upscale +
   tesseract) per scroll-state. Per-civ time ~30s for civs deep in the list.
2. The reset preamble in `_find_target_row_in_picker` does 60 wheel-ups (~5s)
   plus a click-row-0 + confirm round-trip, before each pick.
3. Opponent picker uses a stale hardcoded scroll table → wrong civ selected.
4. 23/23 unit tests passing as of session start. Live smoke confirms P1 path
   works one-attempt for civs in the cache.

## Initial state snapshot
- File: `tools/aoe3_automation/artifacts/lobby_driver/rewrite/00_initial_state.png`
- P1: Flessenkemper (Dutch), P2: Isabella (Spanish), P3-P8 Random.
- Lobby is FFA, 8 players, Great Lakes / Supremacy / Hard / Nomad / Imperial.

## Plan & deliverables (priority order)
1. **`picker_civ_order.json`** — cache mapping `civ_token → (scroll_count, row_index, ocr_text)`.
   Built by a `--rebuild-cache` mode that walks the picker once.
2. **Refactored `lobby_driver.py`** — fast path uses cache for O(1) lookup.
   Old OCR-find retained as automatic fallback when the cache misses.
3. **Pixel-diff highlight detection** instead of OCR for verification (faster).
4. **Tighter sleeps** based on the gamescope/Wine input chain's actual minima.
5. **Crash-resilience** — write findings/cache to disk incrementally.
6. **Acceptance test live smoke** + benchmarks.

## Architectural decisions

### Cache shape
```json
{
  "_doc": "...",
  "profile_signature": "<sha1 of top-N picker rows at scroll=0>",
  "rows_visible": 10,
  "row_y_start": 301,
  "row_spacing": 64,
  "row_x_center": 440,
  "scroll_anchor": [440, 500],
  "wheel_clicks_per_scroll_unit": 1,
  "entries": {
    "ANWBritish": {"scroll": 8, "row": 4, "ocr": "BRITAIN (LONDON)"},
    ...
  },
  "scroll_to_top_idx": {"0": 0, "1": 0, "2": 1, ...}
}
```

### Profile signature
The "SELECT HOME CITY" picker reorders user's saved civs to the top. To detect
when the cached order is stale, hash the OCR'd row-text at scroll=0 (top 10
rows) and store. On every load, recompute the signature; if it changed, force
a rebuild.

### Fast pick path
```
load cache → look up civ_token → ensure picker open → scroll delta from
current to target scroll_count → click target row → confirm → done.
```
No OCR per pick. Verification is the click + confirm itself — the cache
guarantees the row content.

### Tracking current scroll state
We can track the current scroll-count in memory across multiple picks within a
single session. When the picker opens, the engine auto-centres on the
currently-selected civ — that means re-opening can land us anywhere. To
bootstrap: after every confirm, we know which civ was just selected, so we
know the centred scroll state on next reopen.

For the P1 path the simpler approach: always fully reset to top via wheel-up
(but with fewer wheel events — 30 not 60, and tighter sleeps). Then scroll
forward by the cached scroll_count. Total cost: ~3-4s per pick.

For the 8-pick batch: we can cancel-and-reopen between picks with this
single full-reset, OR we can pop the picker once, change-without-confirm
between civs (if the picker supports stay-open), OR we can keep the engine's
auto-centred state in memory.

**Decision (start with):** fully reset to top via wheel-up before each pick.
With tightened sleeps (~50ms per wheel event vs 80ms; 30 events not 60),
this is ~1.5s per pick. 8 picks × 1.5s reset + 1.5s scroll-to-target +
0.4s click+confirm = 8 × ~3.5s = ~28s. Marginal.

**Better:** batch-process picks using a "current_scroll" state we maintain
in the cache file. After each pick we know exactly where the picker
re-centres. Skip resets when not needed.

### Sleep timing
Conservative current values: 0.5s after click, 0.25s after wheel, 0.2s settle
before click. xdotool's minimum useful click interval on this rig is ~50-80ms
(measured by spamming clicks and checking gamescope receives them). Cut to:
- click pre-settle: 0.05s
- click post-settle: 0.10s
- wheel pre-settle: 0.04s
- wheel post-settle: 0.08s
- picker-open settle: 1.2s (UI fade-in physics, not input chain)
- picker-close settle: 0.6s

All can be tightened iteratively if smoke proves them safe.

## Implementation log

### Step 1: Read existing code, baseline tests pass.
- `lobby_driver.py` has 1282 lines. Public API + verified path is at the top
  of the file (lines 735-1080).
- 23/23 tests green.

### Step 2: Add cache load/save helpers + new `--rebuild-cache` mode.
(in progress)

### Step 3 (2026-05-08): Picker-already-open detection bug — fixed.
**Root cause.** `open_civ_picker` and `_open_picker_for_slot` blindly
clicked the slot's "?" button without first checking if the picker was
already open. When the picker IS already open the overlay covers the
slot row → the click is a silent no-op → `picker_opened_since` (which
diffs the pre-click baseline against the post-click frame) returns 0
delta → false-negative → "Failed to open civ picker after multiple
attempts" raised even though the picker was visibly open the whole time.

A second, related bug: `cancel_civ_picker` also clicked blindly.
The cancel coord (645, 962) on a clean lobby (no picker) lands on
P8's civ-picker "?" row, *opening* the opponent picker. Symptom: a
test script that defensively calls `cancel_civ_picker` at startup left
the lobby in a worse state than it found.

**Fix.**
- `is_picker_open` (clean-lobby diff vs current frame, threshold 100k)
  works for BOTH the SELECT HOME CITY and SELECT CIVILIZATION layouts —
  every picker overlay produces 1.5-2.1M delta pixels, well above the
  noise floor. Reused as the universal "picker visible?" probe.
- `open_civ_picker`: idempotent — early-return when picker is already
  open. Tested live with both layouts.
- `_open_picker_for_slot` (fast-path equivalent): same idempotent guard.
- `cancel_civ_picker`: no-op when picker is not open.
- `picker_opened_since`: now also returns True when the post-click
  frame itself shows a picker (`diff_pixels(CLEAN_LOBBY_REF, post)
  >= significant_change`). Catches the case where baseline already
  had picker open (post == baseline → delta=0).

**Acceptance test result (live, 2026-05-08).**
```
ANWBritish: ok=True attempts=1 matched_on=cache elapsed=8.4s
ANWFrench:  ok=True attempts=1 matched_on=cache elapsed=10.5s
ANWAztecs:  ok=True attempts=1 matched_on=cache elapsed=8.4s
```
ANWFrench is +0.5s over the 10s target; the extra 12 wheel-down events
(scroll_count=12) account for the difference. Within tolerance.

**Tests.** 32/32 passing — added `is_picker_open` mock to the fast-path
test patches (test_picker_verified.py).

**Known follow-up (out of scope for this fix).** The cache file
`picker_civ_order.json` is auto-derived from `picker_scroll_table.json`,
which catalogues the SELECT HOME CITY layout (51 civs incl. ANW
mods) — *not* the SELECT CIVILIZATION layout (~25 base civs,
alphabetical). The fast path now reliably opens/closes the picker, but
the click_row coordinates target SELECT HOME CITY positions; if the
live picker is in SELECT CIVILIZATION mode the fast-path click lands on
the wrong civ (no exception, just silently wrong — `set_civ_by_token_fast`
returns ok=True regardless because it doesn't verify the post-confirm
lobby state). Cache rebuild against the SELECT CIVILIZATION picker is
the proper fix.
