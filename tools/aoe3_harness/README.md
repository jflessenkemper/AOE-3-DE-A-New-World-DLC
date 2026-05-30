# tools/aoe3_harness — ANW Harness Package

**Current status:** AOE3DEHarness compositor-based pipeline, Phase 6 verified (smoke test PASS,
all Tier 1 + Tier 2 features confirmed). The legacy DLL-injection stack has been removed.

The ANW (A New World) harness automates AoE3 DE gameplay for AI data capture.
It uses the AOE3DEHarness gamescope-fork binary which exposes a Wayland-level
control socket — no DLL injection or WINEDLLOVERRIDES required.

---

## Package Layout

```
tools/aoe3_harness/
  harness_client.py    — HarnessClient: Python client for the AOE3DEHarness socket
  harness_launch.py    — Launch AOE3DEHarness + umu-run; returns HarnessClient
  launch.py            — Lower-level game launch helpers (kill_stale, build_env, launch_game)
  supervisor.py        — High-level session orchestration (run_pass, per-pass civs)
  validator.py         — Doctrine compliance validation
  capture.py           — Screenshot → PNG pipeline via HarnessClient
  cli.py               — CLI: `python3 -m tools.aoe3_harness.cli`
  smoke_socket.py      — Socket smoke test (Phase 6 verification)
  tests/
    test_harness_client.py  — Unit tests for HarnessClient
    test_diff.py            — Pixel diff tests
  ...
```

---

## How It Works

1. `harness_launch.py` spawns the `AOE3DEHarness` binary (a gamescope fork), which
   in turn launches AoE3 DE via umu-run inside its compositor.
2. AOE3DEHarness exposes a Unix-domain socket (default: `/run/user/1000/AOE3DEHarness.sock`)
   with a line-protocol API: `STATE`, `KEY`, `CLICK`, `MOVE`, `SCREENSHOT`, `QUIT`.
3. `HarnessClient` connects to that socket and sends commands.
4. No Wine DLL injection or `LD_PRELOAD` is needed.

Wire protocol (same as AOE3DEHarness compositor):
- All commands are `\n`-terminated plain text lines.
- Success responses begin with `OK`; errors begin with `ERR <CODE>`.
- `STATE` response: `STATE pid=<N> uptime=<N>ms w=<N> h=<N>`
- `SCREENSHOT` success: `OK path=<path> bytes=<N>`

---

## Unit Tests

```bash
cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
python3 -m pytest tools/aoe3_harness/tests/ -v
```

---

## Hot-Reload (XS Auto-Deploy)

Watches `game/ai/**/*.xs`, `data/*.xml`, `RandMaps/*.xs` for changes and
re-deploys via `deploy_to_mod.py` on every save. The game does not need to
be running.

```bash
# Start the watcher (foreground; Ctrl-C to stop)
python3 -m tools.aoe3_harness.cli hotreload start
```

Install `inotify_simple` for event-driven (non-polling) mode:

```bash
pip install inotify_simple
```

Without it the watcher falls back to 1s stat() polling automatically.

---

## Screenshot Diffing

```bash
# Report changed-pixel percentage + changed region bbox
python3 -m tools.aoe3_harness.cli diff before.png after.png

# With heatmap output (red = changed, black = unchanged)
python3 -m tools.aoe3_harness.cli diff before.png after.png --output heatmap.png
```

---

## Doctrine Bisect

```bash
python3 -m tools.aoe3_harness.cli bisect \
    --probe wall.closure \
    --civ ANWFrench \
    --target 0.6 \
    --good abc1234 \
    --bad def5678
```

---

## Live Verification (game required)

```bash
# Launch with the AOE3DEHarness compositor
python3 -m tools.aoe3_harness.harness_launch

# Socket smoke test (no game required — tests socket connectivity layer)
python3 tools/aoe3_harness/smoke_socket.py
```

---

## CLI

```bash
# Deploy mod
python3 -m tools.aoe3_harness.cli deploy

# Run one pass
python3 -m tools.aoe3_harness.cli run --pass 1

# Run all passes
python3 -m tools.aoe3_harness.cli run --all-passes

# Watch XS files and auto-deploy
python3 -m tools.aoe3_harness.cli hotreload start

# Diff two screenshots
python3 -m tools.aoe3_harness.cli diff before.png after.png --output heatmap.png
```

---

## Anti-Cheat Guard

AOE3DEHarness is intended for **single-player / skirmish vs AI only**.
The compositor wrapper approach does not inject code into the game process.
