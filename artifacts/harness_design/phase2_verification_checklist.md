# Phase 2 Live-Game Verification Checklist

**Status:** Static verification PASSED (17/17 checks). Live-game tests deferred.
**Author:** Phase 2 implementation agent (2026-05-29)
**Last updated:** Hardening pass (2026-05-29) — DXGI un-stubbed, thread audit applied.

---

## Before You Start

Run these checks before opening the game. All static-only.

```bash
# 1. Confirm the EXE is restored (rename .relaunch_blocked back)
ls ~/.local/share/Steam/steamapps/common/AoE3DE/AoE3DE_s.exe
# Expected: file exists (not a .relaunch_blocked name)

# 2. Confirm the game is NOT running
pgrep --exact AoE3DE_s.exe || echo "CLEAR — game not running"

# 3. Confirm DLL files are in place
cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
python3 -m tools.aoe3_harness.cli dll status
# Expected: All DLL files present.

# 4. Run static verification
bash tools/aoe3_harness/dll/static_verify.sh --quiet
# Expected: 17 PASS, 0 FAIL

# 5. Confirm Wine prefix path is accessible
python3 -c "
from tools.aoe3_harness.dll_client import get_pipe_socket_path
print('Socket path (pre-game):', get_pipe_socket_path())
"
# Expected: /tmp/.wine-1000/server-<hex>-<hex>/pipe/anwhook
# (socket file will not exist until the game runs and the DLL is loaded)
```

---

## Where to Find Logs

| Log                | Path                                | When it exists                    |
|--------------------|-------------------------------------|-----------------------------------|
| DLL log            | `/tmp/anw_hook.log`                 | After DLL loads (DllMain fires)   |
| Game log           | `~/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/Player/Age3Log.txt` | After game launches |
| Wine log           | Set `WINEDEBUG=+loaddll` to get DLL load/unload events on stderr |

```bash
# Stream DLL log in real time
tail -f /tmp/anw_hook.log

# Check Wine DLL load events (verbose — use only for debugging)
export WINEDEBUG=+loaddll
```

---

## Section 1: hello_anw.dll Load Test

Purpose: confirm the `WINEDLLOVERRIDES` injection mechanism works before testing
the more complex `anw_hook.dll`.

**Command:**

```bash
rm -f /tmp/anw_dll.log

WINEPREFIX="$HOME/.local/share/Steam/steamapps/compatdata/933110/pfx" \
PROTONPATH="$HOME/.local/share/Steam/steamapps/common/Proton - Experimental" \
GAMEID="933110" \
STEAM_COMPAT_CLIENT_INSTALL_PATH="$HOME/.local/share/Steam" \
WINEDLLOVERRIDES="hello_anw=n,b" \
/usr/bin/umu-run "$HOME/.local/share/Steam/steamapps/common/AoE3DE/AoE3DE_s.exe"
```

**After the game reaches the main menu:**

```bash
cat /tmp/anw_dll.log
```

**Expected output:**

```
[2026-05-29 HH:MM:SS] DLL loaded into PID XXXXXX
```

**What failure means:**

- Log absent entirely: `WINEDLLOVERRIDES` not passing through `umu-run`. Try the
  Wine registry override:
  ```bash
  WINEPREFIX="$HOME/.local/share/Steam/steamapps/compatdata/933110/pfx" \
  wine reg add "HKCU\Software\Wine\DllOverrides" /v hello_anw /t REG_SZ /d native /f
  ```
- Log present but no load message: wrong log path. Try:
  `~/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/AppData/Local/Temp/anw_dll.log`

---

## Section 2: anw_hook.dll Load + Pipe Test

Purpose: confirm the full hook DLL loads, MinHook initialises, DXGI hook installs,
and the named pipe is created.

**Command:**

```bash
rm -f /tmp/anw_hook.log

WINEPREFIX="$HOME/.local/share/Steam/steamapps/compatdata/933110/pfx" \
PROTONPATH="$HOME/.local/share/Steam/steamapps/common/Proton - Experimental" \
GAMEID="933110" \
STEAM_COMPAT_CLIENT_INSTALL_PATH="$HOME/.local/share/Steam" \
WINEDLLOVERRIDES="anw_hook=n,b" \
/usr/bin/umu-run "$HOME/.local/share/Steam/steamapps/common/AoE3DE/AoE3DE_s.exe"
```

**After the game reaches the main menu (~15-30 seconds):**

```bash
cat /tmp/anw_hook.log
```

**Expected output:**

```
[2026-05-29 HH:MM:SS] anw_hook.dll loaded into PID XXXXXX — worker thread started
[2026-05-29 HH:MM:SS] [worker] MinHook initialized
[2026-05-29 HH:MM:SS] [DXGI] vtable[8] (Present) = 0x... — hooking
[2026-05-29 HH:MM:SS] [DXGI] Present hook installed at vtable[8]
[2026-05-29 HH:MM:SS] [worker] Creating named pipe: \\.\pipe\anwhook
[2026-05-29 HH:MM:SS] [worker] Pipe created, waiting for client...
```

**What failure means:**

- No log: DLL not loaded (check `WINEDLLOVERRIDES`; see Section 1).
- "MinHook initialized" missing but hook OK: MinHook init failed; game version
  may have moved function addresses. Check error code in log.
- "DXGI vtable[8]... FATAL: vtable pointer is NULL": D3D11 device creation failed.
  Likely the game is running in a headless/software-render mode. Ensure a real
  GPU is available and DXVK is active.
- "Pipe created" missing: worker thread crashed before reaching the pipe loop.
  Check log for earlier errors.

---

## Section 3: STATE Command (Pipe Heartbeat)

With the game running and `anw_hook.dll` loaded (Section 2 confirmed):

**Command:**

```bash
cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
python3 -m tools.aoe3_harness.cli input state
```

**Expected output:**

```
ALIVE pid=XXXXXX tick=0
```

**What failure means:**

- `ConnectionError: Could not connect ... after 5 attempts`:
  The Unix socket does not exist. Debug:
  ```bash
  python3 -c "
  from tools.aoe3_harness.dll_client import get_pipe_socket_path
  import os, glob
  p = get_pipe_socket_path()
  print('Expected socket:', p)
  # If not found, list all pipe dirs
  for d in glob.glob('/tmp/.wine-1000/server-*/pipe/'):
      print('Found pipe dir:', d)
      print('  Contents:', os.listdir(d))
  "
  ```
  If the derived path is wrong, the wineserver may be using a different server
  directory. The `get_pipe_socket_path()` function derives the path from the
  WINEPREFIX inode — if the prefix was deleted and recreated, the inode changes.

---

## Section 4: KEY Injection Test

With STATE working, start a **skirmish vs AI** (not multiplayer):

**Command:**

```bash
# H key = select Town Centre in AoE3 (0x48)
python3 -m tools.aoe3_harness.cli input key 0x48
# Expected: camera jumps to town centre
```

**Expected output:**

```
OK
```

And the game camera should jump to the town centre.

**What failure means:**

- `OK` returned but no visible effect: Game window not in focus.
  `SendInput` targets the foreground window. Bring AoE3 to the foreground first.
- `ERR invalid vk`: Virtual key code out of range (must be 0x01–0xFF).
- Note in `/tmp/anw_hook.log`: `[pipe] cmd: KEY 0x48` should appear, confirming
  the pipe command was received.

---

## Section 5: CLICK Injection Test

**Command:**

```bash
# Left-click at screen centre (1920x1080 → 960, 540)
python3 -m tools.aoe3_harness.cli input click 960 540
```

**Expected output:**

```
OK
```

And a left-click should register at the centre of the game window.

**What failure means:**

- `OK` but click has no effect: Coordinates are in the game window's **client area**
  (pixels from top-left of the window). For fullscreen/borderless at 1920x1080,
  (960, 540) is the screen centre. If the game is windowed, subtract the window
  chrome offset.
- The DLL calls `ClientToScreen(GetForegroundWindow(), &pt)` to translate.
  Confirm the game window is in the foreground.

---

## Section 6: SCREENSHOT Command Test

The SCREENSHOT command is now **enabled** (DXGI Present hook installed).
The pixel capture step (staging texture → Map → write BGRA) is still deferred
pending live-game confirmation that the hook fires correctly.

**Expected current behaviour (with hook enabled but capture deferred):**

```bash
python3 -c "
from tools.aoe3_harness.dll_client import DllClient, DllClientError
with DllClient() as c:
    try:
        c.screenshot('/tmp/test.bgra')
    except DllClientError as e:
        print('Error:', e)
"
```

**Expected output:**

```
Error: SCREENSHOT failed: ERR DXGI_NOT_IMPLEMENTED
```

(This is expected: `g_Present_original` is NULL if D3D11 device creation failed
in the headless environment during init. If the hook installed successfully,
the response will be `ERR SCREENSHOT timeout` instead — meaning the hook fired
but no pixels were captured, because the capture block is still deferred.)

**Check the log:**

```bash
grep DXGI /tmp/anw_hook.log
```

Expected if hook fired:
```
[DXGI] Present_hook fired — screenshot deferred, path: Z:\tmp\test.bgra
```

**To enable full pixel capture (future work):**

1. Uncomment the `TODO(live-game)` block in `anw_dxgi_hook.c` `Present_hook()`.
2. Implement the staging texture → Map → fwrite pipeline.
3. Rebuild: `bash tools/aoe3_harness/dll/build.sh hook`.
4. Convert raw BGRA to PNG (Python):
   ```python
   from PIL import Image
   w, h = 1920, 1080
   raw = Path('/tmp/frame.bgra').read_bytes()
   img = Image.frombytes('RGBA', (w, h), raw, 'raw', 'BGRA')
   img.save('/tmp/frame.png')
   ```

---

## Section 7: EAC Guard Test

Purpose: confirm the DLL refuses to attach in multiplayer where EAC is active.

**Steps:**

1. Launch via Steam (not `umu-run` with `WINEDLLOVERRIDES`).
2. Navigate to ranked/multiplayer lobby — this loads EasyAntiCheat.
3. In a separate terminal, try to manually load the DLL via registry override.
4. Check `/tmp/anw_hook.log`.

**Expected:** Log is absent or does NOT contain "worker thread started".

**What failure means (DLL loads in MP):**

EAC may use a different DLL name. Update the guard in `anw_hook.c` DllMain:

```c
if (GetModuleHandleW(L"EasyAntiCheat_EOS.dll") != NULL) return FALSE;
if (GetModuleHandleW(L"easyanticheat_x64.dll") != NULL) return FALSE;
```

Rebuild and redeploy.

---

## Rollback Instructions

If anything goes wrong, fully remove the hook DLL:

```bash
# 1. Unset WINEDLLOVERRIDES in current shell
unset WINEDLLOVERRIDES

# 2. Remove DLL from Wine system32
rm -f "$HOME/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/windows/system32/anw_hook.dll"
rm -f "$HOME/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/windows/system32/hello_anw.dll"

# 3. Remove DLL from game data dir
rm -f "$HOME/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/anw_hook.dll"
rm -f "$HOME/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/hello_anw.dll"

# 4. Remove Wine registry override (if added manually)
WINEPREFIX="$HOME/.local/share/Steam/steamapps/compatdata/933110/pfx" \
wine reg delete "HKCU\Software\Wine\DllOverrides" /v anw_hook /f

# 5. Verify game launches normally via Steam (no WINEDLLOVERRIDES)
```

---

## Static Verification Reference

Run at any time without the game:

```bash
cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
bash tools/aoe3_harness/dll/static_verify.sh
# Expected: 17 PASS, 0 FAIL
```
