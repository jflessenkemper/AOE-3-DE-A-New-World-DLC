# build_tour_fix_design.md
## Bug Fix Design: `tools/aoe3_automation/anw_building_tour.py`

### Prerequisites / Key Facts

- **`_rclick(x, y)`** exists in `in_game_driver.py:367–389`. The docstring
  explicitly states it cancels a pending building-placement ghost on open ground
  and is the reason it was added (the prior Escape-based cancel opened the ESC
  menu). It routes through `_HARNESS_BACKEND.rclick(x, y)` when the harness
  is registered, falling back to `xdotool click 3`. VERIFIED at
  `tools/aoe3_automation/in_game_driver.py:367–389`.
- **`HarnessClient.rclick(x, y)`** sends `RCLICK {x} {y}` over the socket.
  Docstring states: "cancels a pending building-placement ghost on open ground".
  VERIFIED at `tools/aoe3_harness/harness_client.py:514–529`.
- **`_esc_menu_open()`** exists in `in_game_driver.py:420–435`. Probes pixel
  (1750, 100) with a gamescopectl screenshot. Brown panel pixels → True.
  However `in_game_driver.py:1038–1044` contains an explicit warning: "do NOT
  use `_open_esc_menu_robust` here. Its gamescopectl-screenshot pixel probe
  reads STALE frame data." The same stale-frame risk applies to
  `_esc_menu_open()` used as a ghost-presence check.
- **`_drag`** (box-select) exists in `in_game_driver.py:392–410`. VERIFIED.
- **`anw_navigator.py`** defines `TC_COORD = (905, 475)` (verified 2026-06-03)
  and `CMD_TRAIN_SETTLER = (33, 840)` (verified 2026-06-03) with a working
  `train_settler()` method that clicks TC → CMD_TRAIN_SETTLER.
- **No idle-villager hotkey** is present anywhere in the repo. No VK constant
  for the AoE3 "select idle villager" key (typically `.` / period) is defined
  in `vk.py`. `ageup_capture.py:92` uses `xdotool key period` only as part of
  text character typing for cheat entry — NOT as a game hotkey. VERIFIED:
  nothing in the codebase uses period/`.` as a game navigation key.
- **`anw_building_tour.py` imports `_click` and `_key` from `in_game_driver`
  but does NOT import `_rclick` or `_drag`** (line 56–63). VERIFIED.

---

## BUG 1 — ESC-pause: Escape with no ghost opens the ESC menu

### Root Cause

`anw_building_tour.py:203`:
```python
# Clear any leftover placement-mode ghost (ONE Escape; a second Escape
# would open the ESC menu — verified live 2026-06-06).
_key("Escape")
time.sleep(0.3)
```

This runs unconditionally after every cell, including the normal path where the
placement was successfully committed on the previous `_click(*spot)`. When the
ghost is already gone (normal case: the user just placed a building), the
Escape has nothing to cancel and instead opens the in-game ESC menu.

### Proposed Fix (VERIFIED mechanism available)

Replace the unconditional `_key("Escape")` with a right-click on a known safe
open-ground coordinate. Right-click cancels placement-mode if a ghost is
active and is a harmless camera pan (or a no-op) if the game is in normal
selection mode. This is the verified intended use of `_rclick`:

> `harness_client.py:515–518`: "In an RTS this is the primary command verb:
> move/rally/gather, and it cancels a pending building-placement ghost on open
> ground."

**Old code** (`anw_building_tour.py:202–204`):
```python
        # Clear any leftover placement-mode ghost (ONE Escape; a second Escape
        # would open the ESC menu — verified live 2026-06-06).
        _key("Escape")
        time.sleep(0.3)
```

**New code**:
```python
        # Cancel any leftover placement-mode ghost via right-click on open
        # ground. Right-click cancels the ghost if active; if no ghost is
        # pending it is a harmless move-order on empty ground.  Never opens
        # the ESC menu (unlike Escape).  _rclick is verified in
        # in_game_driver.py:367-389 and harness_client.py:514-529.
        _rclick(*spot, delay=0.3)
```

Note: `spot` is already in scope at this point in the loop (it was the
placement coordinate). Right-clicking the just-placed building footprint is
safe — the building is selected, the rclick issues a non-destructive
move-to-same-spot command (or is ignored). Alternatively use a fixed
safe-ground coordinate outside all PLACEMENT_SPOTS, e.g. `(1400, 500)`.

**Also required**: add `_rclick` to the import block at `anw_building_tour.py:56–63`:
```python
from tools.aoe3_automation.in_game_driver import (  # noqa: E402
    _click,
    _rclick,          # <-- add this
    _key,
    _focus_window,
    _screenshot_raw,
    _get_xdo_env,
    set_harness_backend,
)
```

**Confidence: VERIFIED**
- `_rclick` exists and the harness supports the RCLICK verb.
- `harness_client.rclick()` docstring explicitly documents it cancels a
  placement ghost.
- `in_game_driver._rclick` docstring names this exact bug as the reason the
  function was added (line 378: "pressing Escape to cancel instead opened the
  ESC menu").

**Test command** (visual inspection, no live game required for the import):
```bash
cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
python3 -c "from tools.aoe3_automation.anw_building_tour import run_building_tour; print('import OK')"
```
For a live test: run the tour with `--civ ANWBritish` and confirm that after
the first building is placed and selected, the game remains in normal in-game
state (HUD visible, no ESC menu, speed bar still present).

---

## BUG 2 — Stale villager: SETTLER_XY is a fixed coordinate

### Root Cause

`anw_building_tour.py:87` and `142–151`:
```python
SETTLER_XY = (960, 741)

def _select_settler() -> None:
    _focus_window()
    _click(*SETTLER_XY, delay=0.3)
```

The villager is at `(960, 741)` only for the very first selection. After the
first `_click(*spot)` to commit placement, the settler walks to `spot` to
build. The screen coordinate `(960, 741)` is now empty ground or another
unit, so all subsequent `_select_settler()` calls fail silently (clicking
empty ground deselects everything, building card never appears, loop captures
blank/HUD screenshots).

### Available Mechanisms

1. **TC train-settler pattern** (`anw_navigator.py:130–132, 966–974`):
   - `TC_COORD = (905, 475)` VERIFIED 2026-06-03
   - `CMD_TRAIN_SETTLER = (33, 840)` VERIFIED 2026-06-03
   - `train_settler()`: click TC → click CMD_TRAIN_SETTLER
   - Trains a new settler per build cycle. With `BUILD_SPEED_CHEAT` active and
     resources unlimited (cheats already applied), this reliably produces a
     fresh settler within seconds. Settlers are trained in ~3–5 s at speed 5
     with "speed always wins" active.

2. **`_drag` box-select** (`in_game_driver.py:392–410`, VERIFIED):
   - Could drag-select around a known area, but requires knowing where settlers
     will have wandered to — unreliable without idle-villager tracking.

3. **Idle-villager hotkey (`.` / period)**: NOT present in the codebase.
   - No VK constant for the AoE3 idle-villager key exists in `vk.py`.
   - `ageup_capture.py:92` uses `xdotool key period` only for cheat text.
   - NEEDS LIVE PROBE to confirm what key cycles idle villagers in this mod
     and whether the harness exposes a period VK (it would need `0x2E` via
     `HarnessClient.key(0x2E)` if available in the harness evdev table, but
     this is unverified).

### Proposed Fix (VERIFIED mechanism)

Use the TC train-settler pattern for each build cycle. Instead of clicking a
stale fixed coordinate, click the Town Center, then queue-train a settler, then
wait for it to appear, then select the fresh settler.

**Old `_select_settler()`** (`anw_building_tour.py:142–151`):
```python
def _select_settler() -> None:
    """Best-effort select a villager to surface the build command card. ..."""
    _focus_window()
    _click(*SETTLER_XY, delay=0.3)
```

**New `_select_settler()` using TC_COORD + CMD_TRAIN_SETTLER**:
```python
# Add at module level (import from anw_navigator or inline as constants):
# TC_COORD and CMD_TRAIN_SETTLER are verified 2026-06-03 in anw_navigator.py:130-132
_TC_COORD         = (905, 475)   # Town Center ground footprint
_CMD_TRAIN_SETTLER = (33, 840)   # top-left command card slot (Train Settler)
_SETTLER_SPAWN_WAIT = 6.0        # seconds for a new settler to appear at TC (speed=5 + speed cheat)

def _select_settler() -> None:
    """Select a settler by training a fresh one from the Town Center.

    Trains a new settler to guarantee we have a unit in a predictable
    location (TC rally point, near TC_COORD).  More reliable than clicking
    SETTLER_XY which goes stale after the first settler walks off to build.

    Requires:
      - Camera at game-start default (TC at _TC_COORD).
      - 'speed always wins' cheat active (settler trains in ~3-5s at speed 5).
      - Resources available (applied via RESOURCE_CHEATS before the loop).
    """
    _focus_window()
    _click(*_TC_COORD, delay=0.4)        # select Town Center
    time.sleep(0.3)
    _click(*_CMD_TRAIN_SETTLER, delay=0.4)  # queue train settler
    time.sleep(_SETTLER_SPAWN_WAIT)      # wait for settler to spawn at TC
    _click(*_TC_COORD, delay=0.4)        # click near TC to select the new settler
    time.sleep(0.3)
```

**Confidence: VERIFIED coordinates; NEEDS LIVE PROBE for timing**
- `TC_COORD = (905, 475)` and `CMD_TRAIN_SETTLER = (33, 840)` are both
  marked VERIFIED 2026-06-03 in `anw_navigator.py:130–132`.
- The train-settler flow is used successfully in `anw_navigator.py:966–974`.
- The `_SETTLER_SPAWN_WAIT` of 6.0 s is an estimate. Live probe needed to
  confirm that a settler spawns and walks to a selectable position near the TC
  within that window when `speed always wins` is active at speed 5.
- After spawning, the settler stands at the TC rally point (~TC_COORD area).
  Clicking TC_COORD a second time selects the newly spawned settler. However
  if the settler does not stop near TC_COORD (e.g. it auto-moves to gather),
  a drag-select `_drag(860, 430, 950, 520)` around the TC could be used as
  a fallback. NEEDS LIVE PROBE to confirm rally-point behaviour.

**Alternative if train-settler is too slow**: Increase `_SETTLER_SPAWN_WAIT`
or train 1 extra settler before the loop begins (guarantees a spare for cell 1,
then train per cell). Either approach requires only the two verified
coordinates.

**Test command** (structural, no live game):
```bash
cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
python3 -c "
from tools.aoe3_harness.anw_navigator import TC_COORD, CMD_TRAIN_SETTLER
print('TC_COORD:', TC_COORD)
print('CMD_TRAIN_SETTLER:', CMD_TRAIN_SETTLER)
"
```
For a live test: run `_select_settler()` once in isolation (no building placed)
and confirm the build command card appears.

---

## Summary Table

| Bug | Root Cause (file:line) | Fix | Confidence |
|-----|----------------------|-----|-----------|
| BUG 1: ESC-pause | `anw_building_tour.py:203` — `_key("Escape")` unconditional | Replace with `_rclick(*spot, delay=0.3)` + import `_rclick` | VERIFIED — mechanism exists, docstring explicitly names this exact bug |
| BUG 2: Stale villager | `anw_building_tour.py:87,151` — fixed `SETTLER_XY` | Train fresh settler via TC_COORD (905,475) + CMD_TRAIN_SETTLER (33,840) per cycle | Coordinates VERIFIED 2026-06-03; settler spawn timing NEEDS LIVE PROBE |

---

## What Was Verified vs Not

- VERIFIED: `_rclick` exists in `in_game_driver.py` and is exported; harness
  supports RCLICK; docstring explicitly names ESC-menu bug as reason for this function.
- VERIFIED: `TC_COORD = (905, 475)` and `CMD_TRAIN_SETTLER = (33, 840)` in
  `anw_navigator.py:130–132`, tagged verified 2026-06-03.
- NEEDS LIVE PROBE: Settler spawn timing at speed 5 + "speed always wins".
  6 s is an estimate; adjust if settler hasn't reached TC rally point.
- NEEDS LIVE PROBE: Whether the idle-villager key (`.` / period, VK 0x2E) is
  mapped in this mod's input bindings and whether the harness evdev table
  includes it — NOT present anywhere in the codebase.
- NEEDS LIVE PROBE: Whether the newly trained settler stops near TC_COORD or
  immediately auto-tasks to a resource. If it auto-tasks, drag-select may be
  needed instead of a single TC click.
