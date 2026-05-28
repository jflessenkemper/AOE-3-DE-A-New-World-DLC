/*
 * anw_dxgi_hook.h — Public API for the DXGI vtable hook (IDXGISwapChain::Present).
 *
 * Implements §2 of artifacts/harness_design/phase2_dll_architecture.md.
 *
 * NOTE (2026-05-29): DXGI screenshot hook is STUBBED in this build.
 * The Present vtable hook requires runtime verification of the vtable index
 * (architecture doc §2 warns: "verify index via dxgi.h before hardcoding").
 * Without live-game testing the index cannot be confirmed correct, and shipping
 * a wrong index silently corrupts the swap-chain call, crashing the game.
 *
 * The stub responds with ERR DXGI_NOT_IMPLEMENTED to SCREENSHOT pipe commands.
 * All other hook machinery (MinHook init/cleanup) is fully wired so the only
 * change needed to enable screenshots is: uncomment the MH_CreateHook call in
 * anw_dxgi_hook.c once vtable[8] is verified against dxgi.h.
 */

#ifndef ANW_DXGI_HOOK_H
#define ANW_DXGI_HOOK_H

/*
 * dxgi_hook_init() — Install the IDXGISwapChain::Present vtable hook via MinHook.
 *
 * Must be called from the worker thread AFTER MH_Initialize().
 * Creates a throwaway 1x1 swap-chain to obtain the Present function pointer,
 * then hooks it with MinHook.
 *
 * Returns:
 *   0  — hook installed successfully (or stubbed with no-op)
 *  -1  — MinHook error installing hook
 *  -2  — D3D11CreateDeviceAndSwapChain failed
 */
int dxgi_hook_init(void);

/*
 * dxgi_hook_cleanup() — Remove the Present hook and release MinHook resources.
 *
 * Must be called from DLL_PROCESS_DETACH before MH_Uninitialize().
 */
void dxgi_hook_cleanup(void);

/*
 * dxgi_request_screenshot() — Signal the Present hook to capture the next frame.
 *
 * path_utf8: Output file path as a UTF-8 string (host path, e.g. "/tmp/frame.png").
 *            The DLL converts to Wine Z: path internally.
 *            Maximum 512 bytes including null terminator.
 *
 * Returns:
 *   0  — request queued (Present hook will fulfil on next frame)
 *  -1  — DXGI hook not installed (stub mode — returns ERR DXGI_NOT_IMPLEMENTED)
 *  -2  — path too long
 */
int dxgi_request_screenshot(const char *path_utf8);

/*
 * dxgi_screenshot_pending() — Returns non-zero if a screenshot request is outstanding.
 */
int dxgi_screenshot_pending(void);

#endif /* ANW_DXGI_HOOK_H */
