# tools/aoe3_harness — ANW Harness Package

**Phase 3 status (2026-05-29):** DXGI pixel pipeline implemented, hot-reload
watcher added, screenshot diff module added, git-bisect wrapper added.
Live-game validation of DXGI pipeline still required (see verification checklist).

The ANW (A New World) harness automates AoE3 DE gameplay for AI data capture.
It consists of a Win32 DLL injected into the game process, a Unix socket bridge,
and Python client + CLI tools.

---

## Package Layout

```
tools/aoe3_harness/
  dll/
    anw_hook.c         — DllMain, worker thread, named pipe server (§1, §4)
    anw_dxgi_hook.c    — DXGI IDXGISwapChain::Present vtable hook (§2)
    anw_input.c        — SendInput wrappers: key/click/move (§3)
    anw_hook.h         — public header
    anw_dxgi_hook.h    — public header
    anw_input.h        — public header
    build.sh           — one-shot cross-compile script (distrobox gs-build)
    static_verify.sh   — 20-check static verification (no game needed)
    minhook/           — MinHook submodule (vtable hooking library)
  dll_client.py        — Python DllClient: Unix socket → Win32 named pipe
  cli.py               — CLI: `python3 -m tools.aoe3_harness.cli`
  tests/
    test_dll_client.py — Unit tests (41 tests, 100% line coverage)
  capture.py           — Screenshot → PNG pipeline
  launch.py            — Game launch helpers
  supervisor.py        — High-level session orchestration
  ...
```

Architecture reference: `artifacts/harness_design/phase2_dll_architecture.md`

---

## How It Works

1. `anw_hook.dll` is injected into the AoE3 DE process via `WINEDLLOVERRIDES`.
2. `DllMain` spawns a worker thread that:
   - Initialises MinHook and hooks `IDXGISwapChain::Present` (vtable slot 8,
     verified against `/usr/x86_64-w64-mingw32/sys-root/mingw/include/dxgi.h`).
   - Creates a Win32 named pipe `\\.\pipe\anwhook`.
   - Serves `\r\n`-terminated line commands: `STATE`, `KEY`, `CLICK`, `MOVE`,
     `SCREENSHOT` (IMPLEMENTED — BMP output via staging-texture pipeline;
     TODO: live-game DXVK validation needed), `QUIT`.
3. Wine exposes the named pipe as a Unix domain socket under
   `/tmp/.wine-<uid>/server-<dev>-<ino>/pipe/anwhook`.
4. `DllClient` connects to that socket and sends commands.

---

## Build

Requires: `distrobox` with a `gs-build` container (Fedora 43 + `mingw64-gcc`).

```bash
# Build both DLLs
bash tools/aoe3_harness/dll/build.sh all

# Build hook DLL only
bash tools/aoe3_harness/dll/build.sh hook

# Clean build artifacts
bash tools/aoe3_harness/dll/build.sh clean

# Build with verbose compiler output
bash tools/aoe3_harness/dll/build.sh hook --verbose
```

The build script checks that the game is NOT running before overwriting the DLL
(a running game holds the DLL locked).

---

## Static Verification (no game needed)

```bash
cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
bash tools/aoe3_harness/dll/static_verify.sh
# Expected: 20 PASS, 0 FAIL
```

In quiet mode:
```bash
bash tools/aoe3_harness/dll/static_verify.sh --quiet
```

---

## Unit Tests

```bash
cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
python3 -m pytest tools/aoe3_harness/tests/test_dll_client.py -v
# 41 tests, 100% line coverage of dll_client.py

python3 -m pytest tools/aoe3_harness/tests/test_diff.py -v
# Pixel diff tests (identical / black-vs-white / small region / heatmap / threshold)
```

---

## Hot-Reload (XS Auto-Deploy)

Watches `game/ai/**/*.xs`, `data/*.xml`, `RandMaps/*.xs` for changes and
re-deploys via `deploy_to_mod.py` on every save.  The game does not need to
be running.

```bash
# Start the watcher (foreground; Ctrl-C to stop)
python3 -m tools.aoe3_harness.cli hotreload start

# Or directly
python3 -m tools.aoe3_harness.hotreload
```

Install `inotify_simple` for event-driven (non-polling) mode:

```bash
pip install inotify_simple
```

Without it the watcher falls back to 1s stat() polling automatically.

---

## Screenshot Diffing

Compare two PNG screenshots pixel-by-pixel:

```bash
# Report changed-pixel percentage + changed region bbox
python3 -m tools.aoe3_harness.cli diff before.png after.png

# With heatmap output (red = changed, black = unchanged)
python3 -m tools.aoe3_harness.cli diff before.png after.png --output heatmap.png
```

Run diff unit tests:

```bash
python3 -m pytest tools/aoe3_harness/tests/test_diff.py -v
```

---

## Doctrine Bisect

Find which commit broke a doctrine probe:

```bash
python3 -m tools.aoe3_harness.cli bisect \
    --probe wall.closure \
    --civ ANWFrench \
    --target 0.6 \
    --good abc1234 \
    --bad def5678
```

This runs `git bisect start` and writes `.git/bisect_test_anw.sh`.  The inner
loop requires launching the game manually at each step until `exhibition_runner`
supports autonomous mode.

---

## Live Verification (game required)

See `artifacts/harness_design/phase2_verification_checklist.md` for the full
step-by-step checklist. Summary:

1. Restore `AoE3DE_s.exe.relaunch_blocked` → `AoE3DE_s.exe`
2. Launch with `WINEDLLOVERRIDES="anw_hook=n,b"` via `umu-run`
3. Check `/tmp/anw_hook.log` for "Pipe created, waiting for client..."
4. Run `python3 -m tools.aoe3_harness.cli input state` → `ALIVE pid=... tick=0`
5. Test KEY, CLICK, SCREENSHOT commands

---

## CLI

```bash
# Query DLL status (game must be running)
python3 -m tools.aoe3_harness.cli input state

# Inject key press (W = 0x57)
python3 -m tools.aoe3_harness.cli input key 0x57

# Left-click at screen centre
python3 -m tools.aoe3_harness.cli input click 960 540

# Check DLL files are in place
python3 -m tools.aoe3_harness.cli dll status

# Request a screenshot (game must be running with DXGI hook active)
# Output is a BMP file; convert to PNG with: python3 -c "from PIL import Image; Image.open('frame.bmp').save('frame.png')"
python3 -m tools.aoe3_harness.cli input state  # then use DllClient.screenshot() directly

# Watch XS files and auto-deploy (game need not be running)
python3 -m tools.aoe3_harness.cli hotreload start

# Diff two screenshots
python3 -m tools.aoe3_harness.cli diff before.png after.png --output heatmap.png
```

---

## Named Pipe Protocol

All commands and responses are `\r\n`-terminated ASCII lines.

| Command             | Response                         |
|---------------------|----------------------------------|
| `STATE`             | `ALIVE pid=<PID> tick=0`         |
| `KEY <vk_hex>`      | `OK`                             |
| `KEY_DOWN <vk_hex>` | `OK`                             |
| `KEY_UP <vk_hex>`   | `OK`                             |
| `CLICK <x> <y>`     | `OK`                             |
| `MOVE <x> <y>`      | `OK`                             |
| `SCREENSHOT <path>` | `OK <path>` or `ERR <reason>`    |
| `QUIT`              | `OK`                             |

`<vk_hex>` is a Windows virtual key code in hex, e.g. `0x57` for W.
`<path>` is a Win32 path (Z:\\ prefix for host filesystem).

---

## DLL Log

The DLL writes to `/tmp/anw_hook.log` (Wine maps `Z:\tmp\` → `/tmp/`).

```bash
tail -f /tmp/anw_hook.log
```

---

## Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| `/tmp/anw_hook.log` absent | DLL not loaded | Check `WINEDLLOVERRIDES` env var |
| `ConnectionError` from DllClient | Wineserver socket not found | Check `/tmp/.wine-1000/` for server dirs |
| Build: "AoE3DE_s.exe appears to be running" | Wine zombie processes | Restart wineserver: `wineserver -k` |
| KEY has no effect | Game not in focus | Bring game window to foreground |
| SCREENSHOT returns ERR | Present hook not firing (headless D3D11 device failed) | Verify game is running with a real GPU |

---

## Anti-Cheat Guard

`DllMain` returns `FALSE` (aborts load) if `EasyAntiCheat.dll` is loaded.
This prevents accidental injection in ranked multiplayer. The harness is
intended for **single-player / skirmish vs AI only**.
