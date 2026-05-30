# DLL Stack Removal Plan

Generated: 2026-05-30

## Summary

There is **no calibration data** in the DLL stack. Every file is legacy Wine/DLL-injection
code superseded by the AOE3DEHarness gamescope fork. The `dll/` subdirectory was already
deleted from disk (git `D` status); the remaining files are in `tools/aoe3_harness/` directly.

## Files to DELETE (all LEGACY — no calibration data)

### Already deleted from disk, need `git rm` to stage:
| File | Rationale |
|------|-----------|
| `tools/aoe3_harness/dll/anw_hook.c` | C source for the Win32 hook DLL |
| `tools/aoe3_harness/dll/anw_hook.dll` | Compiled Win32 DLL binary |
| `tools/aoe3_harness/dll/anw_hook.lib` | Import library for the hook DLL |
| `tools/aoe3_harness/dll/anw_dxgi_hook.c` | DXGI screenshot hook source (stubbed/unfinished) |
| `tools/aoe3_harness/dll/anw_dxgi_hook.h` | Header for DXGI hook |
| `tools/aoe3_harness/dll/anw_input.c` | Win32 SendInput wrapper source |
| `tools/aoe3_harness/dll/anw_input.h` | Header for input wrapper |
| `tools/aoe3_harness/dll/hello_anw.c` | DllMain loader stub source |
| `tools/aoe3_harness/dll/hello_anw.dll` | Compiled loader stub DLL |
| `tools/aoe3_harness/dll/hello_anw.lib` | Import library for loader stub |
| `tools/aoe3_harness/dll/minhook` | MinHook submodule/copy for inline hooking |
| `tools/aoe3_harness/dll/build.sh` | Build script for DLL compilation (Wine/mingw) |
| `tools/aoe3_harness/dll/static_verify.sh` | Script to verify DLL exports/symbols |
| `tools/aoe3_harness/dll/verify_dll_load.sh` | Script to verify DLL loads in Wine |

### Present on disk, need `git rm`:
| File | Rationale |
|------|-----------|
| `tools/aoe3_harness/dll_client.py` | Python Unix-socket client for the Wine named pipe; entire approach superseded by HarnessClient (gamescope control socket) |
| `tools/aoe3_harness/attach.py` | Script that waits for game process and connects via DllClient; entire approach superseded by harness_launch.py |
| `tools/aoe3_harness/tests/test_dll_client.py` | Unit tests for dll_client.py; no longer has a subject |
| `tools/aoe3_harness/preload/anw_preload.c` | LD_PRELOAD .so source that was an intermediate replacement for the DLL; superseded by gamescope control socket (confirmed removed in launch.py line 185) |
| `tools/aoe3_harness/preload/anw_preload.so` | Compiled binary of anw_preload.c |

## Files to KEEP (calibration data check — NONE FOUND)

No JSON, TOML, YAML, or other coordinate/region/click-map files exist anywhere in:
- `tools/aoe3_harness/dll/`
- `tools/aoe3_harness/preload/`
- Nor any Python file in those locations with coordinate constants

The only calibration data in the repo lives in `tools/aoe3_automation/` (e.g.
`lobby_coords.json`, `canonical_regions.json`, `picker_civ_order.json`, etc.) which
is completely unrelated to the DLL stack and is not touched by this removal.

## Import sites that need updating

`tools/aoe3_harness/attach.py` is itself being deleted, so there is no net import-site
breakage. However, `attach.py` does a deferred `from tools.aoe3_harness.dll_client import
DllClient` at line 107 — once both files are deleted this is moot.

The `tools/aoe3_harness/__init__.py` does **not** import `dll_client` or `attach` — it
only re-exports from `harness_client` and `harness_launch`. No `__init__.py` changes needed.

Grep confirmed: no file outside `tools/aoe3_harness/{dll_client,attach,tests/test_dll_client}.py`
imports `DllClient`, `dll_client`, `DLL_SYSTEM32_PATH`, `DLL_GAME_DATA_PATH`, or `DLL_NAMES`.
No import sites need updating.

## Execution steps

1. `git rm tools/aoe3_harness/dll/` files (already deleted from disk)
2. `git rm tools/aoe3_harness/dll_client.py`
3. `git rm tools/aoe3_harness/attach.py`
4. `git rm tools/aoe3_harness/tests/test_dll_client.py`
5. `git rm tools/aoe3_harness/preload/anw_preload.c`
6. `git rm tools/aoe3_harness/preload/anw_preload.so`
7. If `preload/` is now empty: `git rm -r tools/aoe3_harness/preload/` (no tracked files remain)
8. DO NOT COMMIT — bundle with broader commit work.
