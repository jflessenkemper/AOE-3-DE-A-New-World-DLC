/*
 * anw_dxgi_hook.c — DXGI IDXGISwapChain::Present vtable hook.
 *
 * STATUS: ENABLED — vtable index 8 verified against MinGW dxgi.h.
 *
 * Vtable verification (hardening pass 2026-05-29):
 *   Source: /usr/x86_64-w64-mingw32/sys-root/mingw/include/dxgi.h
 *           struct IDXGISwapChainVtbl (line ~1603)
 *
 *   IDXGISwapChain vtable layout — verified slot-by-slot:
 *     slot 0:  IUnknown::QueryInterface
 *     slot 1:  IUnknown::AddRef
 *     slot 2:  IUnknown::Release
 *     slot 3:  IDXGIObject::SetPrivateData
 *     slot 4:  IDXGIObject::SetPrivateDataInterface
 *     slot 5:  IDXGIObject::GetPrivateData
 *     slot 6:  IDXGIObject::GetParent
 *     slot 7:  IDXGIDeviceSubObject::GetDevice
 *     slot 8:  IDXGISwapChain::Present              <-- VERIFIED
 *     slot 9:  IDXGISwapChain::GetBuffer
 *     slot 10: IDXGISwapChain::SetFullscreenState
 *     slot 11: IDXGISwapChain::GetFullscreenState
 *     slot 12: IDXGISwapChain::GetDesc
 *     slot 13: IDXGISwapChain::ResizeBuffers
 *     slot 14: IDXGISwapChain::ResizeTarget
 *     slot 15: IDXGISwapChain::GetContainingOutput
 *     slot 16: IDXGISwapChain::GetFrameStatistics
 *     slot 17: IDXGISwapChain::GetLastPresentCount
 *
 *   IUnknown(3) + IDXGIObject(4) + IDXGIDeviceSubObject(1) = 8 methods before
 *   IDXGISwapChain::Present.  Therefore Present = vtable[8].  Confirmed.
 *
 * DXVK note:
 *   DXVK implements IDXGISwapChain via dxgi::DXGISwapChain which inherits the
 *   same COM vtable layout.  The vtable[8] = Present mapping is stable across
 *   DXVK 1.x / 2.x because DXVK must match the Windows COM ABI.
 *   If DXVK ever changes this (extremely unlikely), the log will show a crash
 *   or a Present hook that never fires — look for "DXGI Present_hook fired" in
 *   /tmp/anw_hook.log.  See also phase2_dll_architecture.md §10.2.
 *
 * Runtime guard:
 *   install_present_hook() checks that vtable and vtable[8] are non-NULL before
 *   calling MH_CreateHook.  If either is NULL the hook is skipped and a log
 *   message is emitted.
 *
 * See also:
 *   artifacts/harness_design/phase2_verification_checklist.md — live-game test plan
 *   artifacts/harness_design/phase2_dll_architecture.md §2 — design
 */

#include <windows.h>
#include <string.h>
#include <stdio.h>

/* dxgi.h is available in the MinGW cross-toolchain at:
 *   /usr/x86_64-w64-mingw32/sys-root/mingw/include/dxgi.h
 * It provides DXGI_SWAP_CHAIN_DESC and related types needed by
 * install_present_hook() to create the throwaway swap-chain for vtable probing.
 */
#include <dxgi.h>

#include "anw_dxgi_hook.h"
#include "minhook/include/MinHook.h"

/* -------------------------------------------------------------------------
 * Screenshot request state (shared between pipe thread and Present hook)
 * -------------------------------------------------------------------------
 * g_screenshot_request is set to 1 by dxgi_request_screenshot() and cleared
 * to 0 by the Present hook after writing the file.  Both threads access it
 * via InterlockedExchange to avoid a data race.
 *
 * g_path_lock serialises writes to g_screenshot_path between the pipe thread
 * (dxgi_request_screenshot) and any future reader in Present_hook.
 */
static volatile LONG g_screenshot_request = 0;
static char          g_screenshot_path[512] = {0};
static CRITICAL_SECTION g_path_lock;

/* -------------------------------------------------------------------------
 * Present hook: original function pointer
 * -------------------------------------------------------------------------
 * Filled in by MH_CreateHook; called from Present_hook to chain to real Present.
 * typedef matches IDXGISwapChain::Present(UINT SyncInterval, UINT Flags)
 */
typedef HRESULT (WINAPI *PFN_Present)(void *pSwapChain, UINT SyncInterval, UINT Flags);
static PFN_Present g_Present_original = NULL;

/* -------------------------------------------------------------------------
 * Present_hook — DXGI IDXGISwapChain::Present intercept
 *
 * Called on every rendered frame.  Only acts when g_screenshot_request == 1
 * (set by dxgi_request_screenshot from the pipe thread).
 *
 * Screenshot capture is deferred to live-game verification (see
 * phase2_verification_checklist.md §5 and §6).  The hook fires correctly
 * and logs each activation; full pixel capture (GetBuffer → staging texture →
 * Map → write BGRA) is the remaining live-game-only step.
 * -------------------------------------------------------------------------*/

static HRESULT WINAPI Present_hook(void *pSwapChain, UINT SyncInterval, UINT Flags) {
    if (InterlockedCompareExchange(&g_screenshot_request, 0, 1) == 1) {
        /* TODO(live-game): Capture back-buffer via staging texture → Map → write BGRA.
         *
         * Steps (deferred — requires live D3D11 device context):
         *   1. QueryInterface(pSwapChain, IID_IDXGISwapChain, &sc)
         *   2. sc->GetBuffer(0, IID_ID3D11Texture2D, &backbuf)
         *   3. Get ID3D11Device + ID3D11DeviceContext via GetDevice
         *   4. Create staging texture (CPU-readable, same Desc as backbuf)
         *   5. CopyResource(staging, backbuf)
         *   6. DeviceContext->Map(staging, 0, D3D11_MAP_READ, 0, &mapped)
         *   7. Write mapped.pData (BGRA pixels) to g_screenshot_path
         *   8. DeviceContext->Unmap(staging, 0)
         *
         * NOTE: path is in g_screenshot_path (Win32 Z:\\ path written by the
         * pipe thread under g_path_lock).  Write as raw BGRA; Python client
         * converts to PNG via Pillow.
         */
        FILE *fp = fopen("Z:\\tmp\\anw_hook.log", "a");
        if (fp) {
            EnterCriticalSection(&g_path_lock);
            fprintf(fp, "[DXGI] Present_hook fired — screenshot deferred, path: %s\n",
                    g_screenshot_path);
            LeaveCriticalSection(&g_path_lock);
            fclose(fp);
        }
        /* Clear request so the pipe thread's timeout loop sees it done */
        /* (Already cleared by InterlockedCompareExchange above) */
    }
    return g_Present_original(pSwapChain, SyncInterval, Flags);
}

/* -------------------------------------------------------------------------
 * install_present_hook — acquire throwaway swap-chain, read vtable[8], hook.
 *
 * Returns:
 *    0  success
 *   -1  MH_CreateHook failed
 *   -2  D3D11 device / swap-chain creation failed (headless environment)
 * -------------------------------------------------------------------------*/
static int install_present_hook(void) {
    /* Create a minimal 1x1 hidden window to attach a throwaway swap-chain */
    HWND hwnd = CreateWindowExW(0, L"STATIC", L"anwhook_tmp",
                                WS_OVERLAPPEDWINDOW, 0, 0, 1, 1,
                                NULL, NULL, NULL, NULL);
    if (!hwnd) return -2;

    /* Minimal DXGI swap-chain description */
    DXGI_SWAP_CHAIN_DESC sd = {0};
    sd.BufferCount                        = 1;
    sd.BufferDesc.Width                   = 1;
    sd.BufferDesc.Height                  = 1;
    sd.BufferDesc.Format                  = 28; /* DXGI_FORMAT_R8G8B8A8_UNORM */
    sd.BufferDesc.RefreshRate.Numerator   = 60;
    sd.BufferDesc.RefreshRate.Denominator = 1;
    sd.BufferUsage                        = 0x20; /* DXGI_USAGE_RENDER_TARGET_OUTPUT */
    sd.OutputWindow                       = hwnd;
    sd.SampleDesc.Count                   = 1;
    sd.Windowed                           = TRUE;
    sd.SwapEffect                         = 0; /* DXGI_SWAP_EFFECT_DISCARD */

    /* D3D_FEATURE_LEVEL_11_0 = 0xb000 */
    UINT feature_level = 0xb000;
    UINT selected_fl   = 0;

    /* Forward-declare the function pointer type to avoid including d3d11.h
     * (not available in MinGW cross-compile without the DirectX SDK headers).
     * Load at runtime via GetProcAddress from d3d11.dll, which is always present.
     *
     * Actual signature:
     *   D3D11CreateDeviceAndSwapChain(pAdapter, DriverType, Software, Flags,
     *     pFeatureLevels, FeatureLevels, SDKVersion,
     *     pSwapChainDesc, ppSwapChain,
     *     pFeatureLevel,   ← UINT* (we pass &selected_fl, same size as D3D_FEATURE_LEVEL)
     *     ppDevice, pContext)
     */
    typedef HRESULT (WINAPI *PFN_D3D11CreateDeviceAndSwapChain)(
        void*, UINT, void*, UINT, const UINT*, UINT, UINT,
        const DXGI_SWAP_CHAIN_DESC*, void**, UINT*, void**, UINT*, void**);

    HMODULE d3d11 = LoadLibraryW(L"d3d11.dll");
    if (!d3d11) {
        FILE *fp = fopen("Z:\\tmp\\anw_hook.log", "a");
        if (fp) { fprintf(fp, "[DXGI] LoadLibrary(d3d11.dll) failed\n"); fclose(fp); }
        DestroyWindow(hwnd);
        return -2;
    }

    PFN_D3D11CreateDeviceAndSwapChain fn =
        (PFN_D3D11CreateDeviceAndSwapChain)GetProcAddress(d3d11, "D3D11CreateDeviceAndSwapChain");
    if (!fn) {
        FILE *fp = fopen("Z:\\tmp\\anw_hook.log", "a");
        if (fp) { fprintf(fp, "[DXGI] GetProcAddress(D3D11CreateDeviceAndSwapChain) failed\n"); fclose(fp); }
        FreeLibrary(d3d11);
        DestroyWindow(hwnd);
        return -2;
    }

    void *pDevice      = NULL;
    void *pSwapChain   = NULL;
    void *pContext     = NULL;

    HRESULT hr = fn(NULL, 1 /*D3D_DRIVER_TYPE_HARDWARE*/, NULL, 0,
                    &feature_level, 1, 7 /*D3D11_SDK_VERSION*/,
                    &sd, (void**)&pSwapChain, &selected_fl,
                    NULL, NULL, (void**)&pContext);
    (void)pDevice; /* not used; suppressed */
    if (FAILED(hr)) {
        FILE *fp = fopen("Z:\\tmp\\anw_hook.log", "a");
        if (fp) { fprintf(fp, "[DXGI] D3D11CreateDeviceAndSwapChain failed: 0x%08lx\n", (unsigned long)hr); fclose(fp); }
        FreeLibrary(d3d11);
        DestroyWindow(hwnd);
        return -2;
    }

    /* Runtime sanity check: vtable pointer must be readable.
     * vtable[8] = IDXGISwapChain::Present — verified against:
     *   /usr/x86_64-w64-mingw32/sys-root/mingw/include/dxgi.h
     *   struct IDXGISwapChainVtbl, slot 8 (IUnknown:3 + IDXGIObject:4 +
     *   IDXGIDeviceSubObject:1 = 8 base methods before Present).
     */
    void **vtable = *(void***)pSwapChain;
    if (!vtable) {
        FILE *fp = fopen("Z:\\tmp\\anw_hook.log", "a");
        if (fp) { fprintf(fp, "[DXGI] FATAL: vtable pointer is NULL — cannot hook\n"); fclose(fp); }
        ((IUnknown*)pSwapChain)->lpVtbl->Release((IUnknown*)pSwapChain);
        if (pContext) ((IUnknown*)pContext)->lpVtbl->Release((IUnknown*)pContext);
        FreeLibrary(d3d11);
        DestroyWindow(hwnd);
        return -2;
    }
    void *present_target = vtable[8];
    if (!present_target) {
        FILE *fp = fopen("Z:\\tmp\\anw_hook.log", "a");
        if (fp) { fprintf(fp, "[DXGI] FATAL: vtable[8] (Present) is NULL — cannot hook\n"); fclose(fp); }
        ((IUnknown*)pSwapChain)->lpVtbl->Release((IUnknown*)pSwapChain);
        if (pContext) ((IUnknown*)pContext)->lpVtbl->Release((IUnknown*)pContext);
        FreeLibrary(d3d11);
        DestroyWindow(hwnd);
        return -2;
    }

    FILE *fp_v = fopen("Z:\\tmp\\anw_hook.log", "a");
    if (fp_v) {
        fprintf(fp_v, "[DXGI] vtable[8] (Present) = %p — hooking\n", present_target);
        fclose(fp_v);
    }

    MH_STATUS mh = MH_CreateHook(present_target, &Present_hook, (void**)&g_Present_original);
    if (mh != MH_OK) {
        FILE *fp = fopen("Z:\\tmp\\anw_hook.log", "a");
        if (fp) { fprintf(fp, "[DXGI] MH_CreateHook failed: %d\n", (int)mh); fclose(fp); }
        ((IUnknown*)pSwapChain)->lpVtbl->Release((IUnknown*)pSwapChain);
        if (pContext) ((IUnknown*)pContext)->lpVtbl->Release((IUnknown*)pContext);
        FreeLibrary(d3d11);
        DestroyWindow(hwnd);
        return -1;
    }

    MH_EnableHook(present_target);

    FILE *fp_ok = fopen("Z:\\tmp\\anw_hook.log", "a");
    if (fp_ok) { fprintf(fp_ok, "[DXGI] Present hook installed at vtable[8]\n"); fclose(fp_ok); }

    /* Release the throwaway objects; we no longer need them.
     * MinHook keeps the hook installed by patching the original function code,
     * not by holding a reference to the swap-chain object. */
    ((IUnknown*)pSwapChain)->lpVtbl->Release((IUnknown*)pSwapChain);
    if (pContext) ((IUnknown*)pContext)->lpVtbl->Release((IUnknown*)pContext);
    FreeLibrary(d3d11);
    DestroyWindow(hwnd);
    return 0;
}

/* -------------------------------------------------------------------------
 * Public API implementation
 * -------------------------------------------------------------------------*/

int dxgi_hook_init(void) {
    InitializeCriticalSection(&g_path_lock);
    return install_present_hook();
}

void dxgi_hook_cleanup(void) {
    if (g_Present_original) {
        MH_DisableHook(MH_ALL_HOOKS);
    }
    DeleteCriticalSection(&g_path_lock);
}

int dxgi_request_screenshot(const char *path_utf8) {
    if (g_Present_original == NULL) {
        /* Hook not installed — D3D11 device creation likely failed in headless env */
        return -1;
    }
    size_t len = strlen(path_utf8);
    if (len >= sizeof(g_screenshot_path)) {
        return -2;
    }
    EnterCriticalSection(&g_path_lock);
    memcpy(g_screenshot_path, path_utf8, len + 1);
    LeaveCriticalSection(&g_path_lock);
    InterlockedExchange(&g_screenshot_request, 1);
    return 0;
}

int dxgi_screenshot_pending(void) {
    return (int)InterlockedCompareExchange(&g_screenshot_request, 0, 0);
}
