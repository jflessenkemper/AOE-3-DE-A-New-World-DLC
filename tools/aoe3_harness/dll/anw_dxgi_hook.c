/*
 * anw_dxgi_hook.c — DXGI IDXGISwapChain::Present vtable hook.
 *
 * STATUS: STUBBED — responds ERR DXGI_NOT_IMPLEMENTED to SCREENSHOT commands.
 *
 * Why stubbed:
 *   Architecture §2 explicitly warns: "verify vtable index against architecture
 *   §2 commentary before hardcoding 8 — check Windows SDK dxgi.h if accessible,
 *   otherwise leave a NOTE comment explaining the assumption."
 *
 *   The DXGI COM vtable layout for IDXGISwapChain is:
 *     slot 0-2:  IUnknown (QueryInterface, AddRef, Release)
 *     slot 3-4:  IDXGIObject (SetPrivateData, SetPrivateDataInterface,
 *                             GetPrivateData, GetParent) — that's 4 methods = slots 3-6
 *     slot 7:    IDXGIDeviceSubObject::GetDevice
 *     slot 8:    IDXGISwapChain::Present          <-- assumed index
 *     slot 9:    IDXGISwapChain::GetBuffer
 *     ...
 *
 *   The index 8 is the canonical Windows SDK value documented in dxgi.h and
 *   DXVK's src/dxgi/dxgi_swapchain.h. However, DXVK may wrap the swap-chain
 *   in a proxy object with a different vtable layout. This CANNOT be verified
 *   without running the game.
 *
 *   To enable: search for STUB_DXGI_SCREENSHOT below and follow the instructions.
 *
 * See also:
 *   artifacts/harness_design/phase2_verification_checklist.md — live-game test plan
 *   artifacts/harness_design/phase2_dll_architecture.md §2 — design
 */

#include <windows.h>
#include <string.h>
#include <stdio.h>

#include "anw_dxgi_hook.h"
#include "minhook/include/MinHook.h"

/* -------------------------------------------------------------------------
 * Screenshot request state (shared between pipe thread and Present hook)
 * -------------------------------------------------------------------------
 * g_screenshot_request is set to 1 by dxgi_request_screenshot() and cleared
 * to 0 by the Present hook after writing the file.  Both threads access it
 * via InterlockedExchange to avoid a data race.
 */
static volatile LONG g_screenshot_request = 0;
/* g_screenshot_path is written in dxgi_request_screenshot() and read in
 * Present_hook.  In stub mode (DXGI_HOOK_ENABLED not defined) neither path
 * is taken, so GCC warns about unused variables.  The attribute silences
 * the warning without removing the storage that will be needed when the
 * hook is enabled. */
static char          g_screenshot_path[512] __attribute__((unused)) = {0};
static CRITICAL_SECTION g_path_lock;

/* -------------------------------------------------------------------------
 * Present hook: original function pointer
 * -------------------------------------------------------------------------
 * Filled in by MH_CreateHook; called from Present_hook to chain to real Present.
 * typedef matches IDXGISwapChain::Present(UINT SyncInterval, UINT Flags)
 */
typedef HRESULT (WINAPI *PFN_Present)(void *pSwapChain, UINT SyncInterval, UINT Flags);
/* g_Present_original is only referenced inside #ifdef DXGI_HOOK_ENABLED blocks.
 * Suppress the "unused" warning in stub builds. */
static PFN_Present g_Present_original __attribute__((unused)) = NULL;

/* -------------------------------------------------------------------------
 * STUB_DXGI_SCREENSHOT
 *
 * The hook body below is a no-op stub. To enable real screenshots:
 *
 *  1. Uncomment the screenshot capture block (search CAPTURE_BLOCK_START).
 *  2. Run the static_verify.sh "vtable index" test (checks vtable[8] vs dxgi.h).
 *  3. Ensure the game is in borderless windowed mode (DXVK direct-scanout check).
 *  4. Live-verify: set DXGI_HOOK_ENABLED=1 at build time:
 *       -DDXGI_HOOK_ENABLED
 *     then rebuild and run phase2_verification_checklist.md §5 (screenshot test).
 * -------------------------------------------------------------------------*/

#ifdef DXGI_HOOK_ENABLED
/* Real hook — only compiled when explicitly requested */

static HRESULT WINAPI Present_hook(void *pSwapChain, UINT SyncInterval, UINT Flags) {
    if (InterlockedCompareExchange(&g_screenshot_request, 0, 1) == 1) {
        /* CAPTURE_BLOCK_START
         * Capture the back-buffer via staging texture → Map → write BGRA file.
         *
         * Steps (abbreviated; full code deferred to live-game verification phase):
         *   1. QueryInterface(pSwapChain, IID_IDXGISwapChain, &sc)
         *   2. sc->GetBuffer(0, IID_ID3D11Texture2D, &backbuf)
         *   3. Get ID3D11Device + ID3D11DeviceContext via GetDevice
         *   4. Create staging texture (CPU-readable, same Desc)
         *   5. CopyResource(staging, backbuf)
         *   6. DeviceContext->Map(staging, ..., &mapped)
         *   7. Write BGRA raw data to g_screenshot_path
         *   8. DeviceContext->Unmap(staging, ...)
         *
         * NOTE: path conversion — g_screenshot_path is the host path
         * (e.g. /tmp/frame.bgra). Write as raw BGRA; Python client converts
         * to PNG using Pillow.  PNG encoding inside the DLL would require
         * linking libpng (complex); raw BGRA is simpler and lossless.
         * CAPTURE_BLOCK_END */

        /* Temporary stub log so we know the hook is firing */
        FILE *fp = fopen("Z:\\tmp\\anw_hook.log", "a");
        if (fp) {
            fprintf(fp, "[DXGI] Present_hook fired, screenshot stub hit\n");
            fclose(fp);
        }
    }
    return g_Present_original(pSwapChain, SyncInterval, Flags);
}

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

    /* D3D_FEATURE_LEVEL_11_0 */
    UINT feature_level = 0xb000;
    UINT selected_fl   = 0;

    /* Forward-declare the function pointer types to avoid including d3d11.h
     * (not available in MinGW cross-compile without the DirectX SDK headers).
     * We load via GetProcAddress from d3d11.dll, which is always available. */
    typedef HRESULT (WINAPI *PFN_D3D11CreateDeviceAndSwapChain)(
        void*, UINT, void*, UINT, const UINT*, UINT, UINT,
        const void*, void**, UINT*, void**, UINT*, void**);

    HMODULE d3d11 = LoadLibraryW(L"d3d11.dll");
    if (!d3d11) { DestroyWindow(hwnd); return -2; }

    PFN_D3D11CreateDeviceAndSwapChain fn =
        (PFN_D3D11CreateDeviceAndSwapChain)GetProcAddress(d3d11, "D3D11CreateDeviceAndSwapChain");
    if (!fn) { FreeLibrary(d3d11); DestroyWindow(hwnd); return -2; }

    void *pDevice      = NULL;
    void *pSwapChain   = NULL;
    void *pContext     = NULL;

    HRESULT hr = fn(NULL, 1 /*D3D_DRIVER_TYPE_HARDWARE*/, NULL, 0,
                    &feature_level, 1, 7 /*D3D11_SDK_VERSION*/,
                    &sd, (void**)&pSwapChain, (void**)&selected_fl,
                    NULL, NULL, (void**)&pContext);
    if (FAILED(hr)) {
        FreeLibrary(d3d11); DestroyWindow(hwnd); return -2;
    }

    /* vtable[8] = IDXGISwapChain::Present
     * Verify: IUnknown(3) + IDXGIObject(4) + IDXGIDeviceSubObject(1) = 8 before Present */
    void **vtable        = *(void***)pSwapChain;
    void  *present_target = vtable[8];

    MH_STATUS mh = MH_CreateHook(present_target, &Present_hook, (void**)&g_Present_original);
    if (mh != MH_OK) {
        /* Release swap-chain + device COM objects */
        ((IUnknown*)pSwapChain)->lpVtbl->Release((IUnknown*)pSwapChain);
        ((IUnknown*)pContext)->lpVtbl->Release((IUnknown*)pContext);
        FreeLibrary(d3d11); DestroyWindow(hwnd); return -1;
    }

    MH_EnableHook(present_target);

    /* Release the throwaway objects; we no longer need them */
    ((IUnknown*)pSwapChain)->lpVtbl->Release((IUnknown*)pSwapChain);
    ((IUnknown*)pContext)->lpVtbl->Release((IUnknown*)pContext);
    FreeLibrary(d3d11);
    DestroyWindow(hwnd);
    return 0;
}

#endif /* DXGI_HOOK_ENABLED */

/* -------------------------------------------------------------------------
 * Public API implementation
 * -------------------------------------------------------------------------*/

int dxgi_hook_init(void) {
    InitializeCriticalSection(&g_path_lock);

#ifdef DXGI_HOOK_ENABLED
    return install_present_hook();
#else
    /* Stub mode: log that DXGI hook is disabled */
    FILE *fp = fopen("Z:\\tmp\\anw_hook.log", "a");
    if (fp) {
        fprintf(fp, "[DXGI] Hook stubbed: DXGI_NOT_IMPLEMENTED "
                    "(rebuild with -DDXGI_HOOK_ENABLED to enable)\n");
        fclose(fp);
    }
    return 0;  /* Not an error — stub is by design */
#endif
}

void dxgi_hook_cleanup(void) {
#ifdef DXGI_HOOK_ENABLED
    if (g_Present_original) {
        MH_DisableHook(MH_ALL_HOOKS);
    }
#endif
    DeleteCriticalSection(&g_path_lock);
}

int dxgi_request_screenshot(const char *path_utf8) {
#ifdef DXGI_HOOK_ENABLED
    if (g_Present_original == NULL) {
        return -1;  /* Hook not installed */
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
#else
    (void)path_utf8;
    return -1;  /* DXGI_NOT_IMPLEMENTED */
#endif
}

int dxgi_screenshot_pending(void) {
    return (int)InterlockedCompareExchange(&g_screenshot_request, 0, 0);
}
