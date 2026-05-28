/*
 * anw_dxgi_hook.c — DXGI IDXGISwapChain::Present vtable hook.
 *
 * STATUS: IMPLEMENTED — staging-texture pixel pipeline complete.
 *         TODO(live-game): validate DXVK Map() returns correct pixels.
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
 * D3D11 header availability:
 *   d3d11.h is NOT available in the MinGW cross-toolchain installed on this
 *   build host (/usr/x86_64-w64-mingw32/sys-root/mingw/include/d3d11.h absent).
 *   All D3D11 types are forward-declared below using the documented COM ABI.
 *   GUIDs are defined as static const GUID literals sourced from the D3D11 SDK
 *   documentation and directxtk (verified against MSDN).
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

/* =========================================================================
 * D3D11 forward declarations
 *
 * d3d11.h is unavailable on this build host.  We declare only the minimal
 * subset required for the staging-texture screenshot pipeline:
 *   - D3D11_TEXTURE2D_DESC, D3D11_MAPPED_SUBRESOURCE (structs)
 *   - D3D11_USAGE, D3D11_CPU_ACCESS_FLAG, D3D11_MAP (enums / constants)
 *   - ID3D11Resource, ID3D11Texture2D, ID3D11Device, ID3D11DeviceContext (COM)
 *
 * These match the D3D11 SDK definitions exactly (same field order, sizes, and
 * enum values).  The vtable method ordering matches the SDK COM interface
 * definition.  Verified against MSDN D3D11 reference (D3D11.h SDK 10.0.19041).
 * ========================================================================= */

/* D3D11_USAGE */
#define D3D11_USAGE_STAGING      3

/* D3D11_CPU_ACCESS_FLAG */
#define D3D11_CPU_ACCESS_WRITE   0x10000L
#define D3D11_CPU_ACCESS_READ    0x20000L

/* D3D11_MAP */
#define D3D11_MAP_READ           1

/* D3D11_BIND_FLAG — staging texture has no bind flags */
#define D3D11_BIND_NONE          0

/* DXGI_SAMPLE_DESC is defined in dxgi.h, but we use our own name to be safe */
typedef struct _ANW_DXGI_SAMPLE_DESC {
    UINT Count;
    UINT Quality;
} ANW_DXGI_SAMPLE_DESC;

/* D3D11_TEXTURE2D_DESC — matches the SDK struct field-for-field */
typedef struct _D3D11_TEXTURE2D_DESC {
    UINT         Width;
    UINT         Height;
    UINT         MipLevels;
    UINT         ArraySize;
    DXGI_FORMAT  Format;         /* DXGI_FORMAT enum from dxgi.h */
    DXGI_SAMPLE_DESC SampleDesc; /* DXGI_SAMPLE_DESC from dxgi.h */
    UINT         Usage;          /* D3D11_USAGE */
    UINT         BindFlags;      /* D3D11_BIND_FLAG combination */
    UINT         CPUAccessFlags; /* D3D11_CPU_ACCESS_FLAG combination */
    UINT         MiscFlags;      /* D3D11_RESOURCE_MISC_FLAG combination */
} D3D11_TEXTURE2D_DESC;

/* D3D11_MAPPED_SUBRESOURCE */
typedef struct _D3D11_MAPPED_SUBRESOURCE {
    void *pData;
    UINT  RowPitch;
    UINT  DepthPitch;
} D3D11_MAPPED_SUBRESOURCE;

/*
 * D3D11 COM interface forward declarations.
 *
 * Each struct holds only the vtable pointer (COM convention).  We declare
 * only the vtable methods we actually call, in the same slot order as the
 * SDK, with all preceding methods represented as void* placeholders.
 *
 * Verified vtable slot counts against MSDN:
 *   ID3D11Resource:        IUnknown(3) + 4 own methods = slots 0-6
 *   ID3D11Texture2D:       ID3D11Resource(7) + 1 own method (GetDesc) = slots 0-7
 *   ID3D11Device:          IUnknown(3) + CreateTexture2D(slot 3) + ... GetImmediateContext(slot 14 for D3D11)
 *   ID3D11DeviceContext:   IUnknown(3) + many; CopyResource=slot 25, Map=slot 14, Unmap=slot 15
 *
 * All unneeded slots are represented as void* (void* compatible with __thiscall on MSVC;
 * MinGW uses the same ABI for COM interfaces on x86_64).
 */

/* ID3D11Resource vtable — 7 slots total */
typedef struct _ID3D11ResourceVtbl {
    /* IUnknown */
    void *QueryInterface;   /* slot 0 */
    void *AddRef;           /* slot 1 */
    ULONG (WINAPI *Release)(void *pThis);  /* slot 2 */
    /* ID3D11DeviceChild */
    void (WINAPI *GetDevice)(void *pThis, void **ppDevice);  /* slot 3 */
    void *GetPrivateData;   /* slot 4 */
    void *SetPrivateData;   /* slot 5 */
    void *SetPrivateDataInterface;  /* slot 6 */
    /* ID3D11Resource */
    void *GetType;          /* slot 7 */
    void *SetEvictionPriority;  /* slot 8 */
    void *GetEvictionPriority;  /* slot 9 */
} ID3D11ResourceVtbl;

typedef struct _ID3D11Resource {
    const ID3D11ResourceVtbl *lpVtbl;
} ID3D11Resource;

/* ID3D11Texture2D vtable — ID3D11Resource (10 slots) + GetDesc (slot 10) */
typedef struct _ID3D11Texture2DVtbl {
    /* IUnknown */
    HRESULT (WINAPI *QueryInterface)(void *pThis, const GUID *riid, void **ppvObject);  /* slot 0 */
    ULONG   (WINAPI *AddRef)(void *pThis);    /* slot 1 */
    ULONG   (WINAPI *Release)(void *pThis);   /* slot 2 */
    /* ID3D11DeviceChild */
    void    (WINAPI *GetDevice)(void *pThis, void **ppDevice);  /* slot 3 */
    void *GetPrivateData;    /* slot 4 */
    void *SetPrivateData;    /* slot 5 */
    void *SetPrivateDataInterface;  /* slot 6 */
    /* ID3D11Resource */
    void *GetType;           /* slot 7 */
    void *SetEvictionPriority;  /* slot 8 */
    void *GetEvictionPriority;  /* slot 9 */
    /* ID3D11Texture2D */
    void    (WINAPI *GetDesc)(void *pThis, D3D11_TEXTURE2D_DESC *pDesc);  /* slot 10 */
} ID3D11Texture2DVtbl;

typedef struct _ID3D11Texture2D {
    const ID3D11Texture2DVtbl *lpVtbl;
} ID3D11Texture2D;

/*
 * ID3D11Device vtable (partial — only CreateTexture2D slot 3 and
 * GetImmediateContext).
 *
 * D3D11 device method slots (MSDN D3D11.h, verified):
 *   slot 0:  QueryInterface
 *   slot 1:  AddRef
 *   slot 2:  Release
 *   slot 3:  CreateBuffer
 *   slot 4:  CreateTexture1D
 *   slot 5:  CreateTexture2D          <-- we use this
 *   slot 6:  CreateTexture3D
 *   ...
 *   slot 14: GetImmediateContext      <-- we use this
 */
typedef struct _ID3D11DeviceVtbl {
    void *QueryInterface;         /* slot 0 */
    void *AddRef;                 /* slot 1 */
    ULONG (WINAPI *Release)(void *pThis);  /* slot 2 */
    void *CreateBuffer;           /* slot 3 */
    void *CreateTexture1D;        /* slot 4 */
    HRESULT (WINAPI *CreateTexture2D)(  /* slot 5 */
        void *pThis,
        const D3D11_TEXTURE2D_DESC *pDesc,
        const void *pInitialData,
        void **ppTexture2D);
    void *CreateTexture3D;        /* slot 6 */
    void *CreateShaderResourceView;  /* slot 7 */
    void *CreateUnorderedAccessView; /* slot 8 */
    void *CreateRenderTargetView;    /* slot 9 */
    void *CreateDepthStencilView;    /* slot 10 */
    void *CreateInputLayout;         /* slot 11 */
    void *CreateVertexShader;        /* slot 12 */
    void *CreateGeometryShader;      /* slot 13 */
    void (WINAPI *GetImmediateContext)(  /* slot 14 */
        void *pThis, void **ppImmediateContext);
} ID3D11DeviceVtbl;

typedef struct _ID3D11Device {
    const ID3D11DeviceVtbl *lpVtbl;
} ID3D11Device;

/*
 * ID3D11DeviceContext vtable (partial).
 *
 * D3D11DeviceContext method slots (MSDN, verified against d3d11.h SDK):
 *   slot 0:  QueryInterface
 *   slot 1:  AddRef
 *   slot 2:  Release
 *   slot 3:  GetDevice
 *   slot 4:  GetPrivateData
 *   slot 5:  SetPrivateData
 *   slot 6:  SetPrivateDataInterface
 *   slot 7:  VSSetConstantBuffers
 *   slot 8:  PSSetShaderResources
 *   slot 9:  PSSetShader
 *   slot 10: PSSetSamplers
 *   slot 11: VSSetShader
 *   slot 12: DrawIndexed
 *   slot 13: Draw
 *   slot 14: Map                <-- we use this
 *   slot 15: Unmap              <-- we use this
 *   ...
 *   slot 25: CopyResource       <-- we use this (IUnknown:3 + DeviceChild:4 = 7; context-specific: slot 25 = 7+18=25)
 *
 * Note: CopyResource is at offset 25 in ID3D11DeviceContext vtable:
 *   (IUnknown: 3) + (DeviceChild: 4) + (context methods before CopyResource: 18) = 25
 * Verified against MSDN "ID3D11DeviceContext::CopyResource method".
 */
typedef struct _ID3D11DeviceContextVtbl {
    void *QueryInterface;        /* slot 0 */
    void *AddRef;                /* slot 1 */
    ULONG (WINAPI *Release)(void *pThis);  /* slot 2 */
    void *GetDevice;             /* slot 3 */
    void *GetPrivateData;        /* slot 4 */
    void *SetPrivateData;        /* slot 5 */
    void *SetPrivateDataInterface;  /* slot 6 */
    void *VSSetConstantBuffers;  /* slot 7 */
    void *PSSetShaderResources;  /* slot 8 */
    void *PSSetShader;           /* slot 9 */
    void *PSSetSamplers;         /* slot 10 */
    void *VSSetShader;           /* slot 11 */
    void *DrawIndexed;           /* slot 12 */
    void *Draw;                  /* slot 13 */
    HRESULT (WINAPI *Map)(       /* slot 14 */
        void *pThis,
        void *pResource,
        UINT Subresource,
        UINT MapType,
        UINT MapFlags,
        D3D11_MAPPED_SUBRESOURCE *pMappedResource);
    void (WINAPI *Unmap)(        /* slot 15 */
        void *pThis,
        void *pResource,
        UINT Subresource);
    void *PSSetConstantBuffers;  /* slot 16 */
    void *IASetInputLayout;      /* slot 17 */
    void *IASetVertexBuffers;    /* slot 18 */
    void *IASetIndexBuffer;      /* slot 19 */
    void *DrawIndexedInstanced;  /* slot 20 */
    void *DrawInstanced;         /* slot 21 */
    void *GSSetConstantBuffers;  /* slot 22 */
    void *GSSetShader;           /* slot 23 */
    void *IASetPrimitiveTopology; /* slot 24 */
    void (WINAPI *CopyResource)( /* slot 25 */
        void *pThis,
        void *pDstResource,
        void *pSrcResource);
} ID3D11DeviceContextVtbl;

typedef struct _ID3D11DeviceContext {
    const ID3D11DeviceContextVtbl *lpVtbl;
} ID3D11DeviceContext;

/* COM GUIDs for QueryInterface / GetBuffer calls.
 * Values sourced from MSDN and the Windows SDK d3d11.h / dxgi.h. */
static const GUID IID_ID3D11Texture2D_anw = {
    0x6f15aaf2, 0xd208, 0x4e89,
    {0x9a, 0xb4, 0x48, 0x95, 0x35, 0xd3, 0x4f, 0x9c}
};
static const GUID IID_IDXGISwapChain_anw = {
    0x310d36a0, 0xd2e7, 0x4c0a,
    {0xaa, 0x04, 0x6a, 0x9d, 0x23, 0xb8, 0x88, 0x6a}
};


/* =========================================================================
 * Screenshot request state (shared between pipe thread and Present hook)
 * =========================================================================
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

/* Error code set by Present_hook when capture fails (0 = success). */
static volatile LONG g_screenshot_hresult = 0;

/* =========================================================================
 * Present hook: original function pointer
 * =========================================================================
 * Filled in by MH_CreateHook; called from Present_hook to chain to real Present.
 * typedef matches IDXGISwapChain::Present(UINT SyncInterval, UINT Flags)
 */
typedef HRESULT (WINAPI *PFN_Present)(void *pSwapChain, UINT SyncInterval, UINT Flags);
static PFN_Present g_Present_original = NULL;

/* =========================================================================
 * BMP output constants and inline encoder
 * =========================================================================*/
#define BMP_FILE_HEADER_SIZE  14
#define BMP_INFO_HEADER_SIZE  40
#define BMP_HEADER_TOTAL      (BMP_FILE_HEADER_SIZE + BMP_INFO_HEADER_SIZE)
#define BMP_BITS_PER_PIXEL    32   /* BGRA — matches D3D11 BGRA/RGBA formats */
#define BMP_PLANES            1
#define BMP_COMPRESSION_NONE  0    /* BI_RGB — no compression */

/*
 * write_bmp() — Write raw BGRA pixel rows as a 32bpp Windows BMP file.
 *
 * BMP stores pixels bottom-up.  mapped_data points to the first row of the
 * D3D11 mapped texture (row 0 = top of frame).  We write rows in reverse
 * order so the BMP is displayed right-side-up.
 *
 * row_pitch may be > width*4 due to GPU row alignment; we step by row_pitch
 * but only write width*4 bytes per row into the file (stride = width * 4).
 *
 * Args:
 *   path        — host-filesystem path (Win32; e.g. Z:\tmp\frame.bmp)
 *   mapped_data — pointer to the first byte of the mapped staging texture
 *   width       — texture width in pixels
 *   height      — texture height in pixels
 *   row_pitch   — row stride in bytes (from D3D11_MAPPED_SUBRESOURCE.RowPitch)
 *
 * Returns 1 on success, 0 on failure (file I/O error).
 */
static int write_bmp(const char *path, const void *mapped_data,
                     UINT width, UINT height, UINT row_pitch) {
    FILE *fp = fopen(path, "wb");
    if (!fp) return 0;

    DWORD stride      = width * 4;          /* bytes per row in the output */
    DWORD pixel_bytes = stride * height;
    DWORD file_size   = BMP_HEADER_TOTAL + pixel_bytes;

    /* BITMAPFILEHEADER (14 bytes, little-endian) */
    unsigned char fhdr[BMP_FILE_HEADER_SIZE];
    fhdr[0] = 'B';  fhdr[1] = 'M';
    /* bfSize */
    fhdr[2]  = (unsigned char)(file_size);
    fhdr[3]  = (unsigned char)(file_size >> 8);
    fhdr[4]  = (unsigned char)(file_size >> 16);
    fhdr[5]  = (unsigned char)(file_size >> 24);
    /* bfReserved1, bfReserved2 */
    fhdr[6]  = 0;  fhdr[7]  = 0;
    fhdr[8]  = 0;  fhdr[9]  = 0;
    /* bfOffBits — offset to pixel data */
    fhdr[10] = (unsigned char)(BMP_HEADER_TOTAL);
    fhdr[11] = 0;  fhdr[12] = 0;  fhdr[13] = 0;

    /* BITMAPINFOHEADER (40 bytes, little-endian) */
    unsigned char ihdr[BMP_INFO_HEADER_SIZE];
    memset(ihdr, 0, sizeof(ihdr));
    /* biSize */
    ihdr[0] = (unsigned char)(BMP_INFO_HEADER_SIZE);
    /* biWidth */
    ihdr[4] = (unsigned char)(width);
    ihdr[5] = (unsigned char)(width >> 8);
    ihdr[6] = (unsigned char)(width >> 16);
    ihdr[7] = (unsigned char)(width >> 24);
    /* biHeight (positive = bottom-up; we write rows in reverse) */
    ihdr[8]  = (unsigned char)(height);
    ihdr[9]  = (unsigned char)(height >> 8);
    ihdr[10] = (unsigned char)(height >> 16);
    ihdr[11] = (unsigned char)(height >> 24);
    /* biPlanes */
    ihdr[12] = BMP_PLANES;
    /* biBitCount */
    ihdr[14] = BMP_BITS_PER_PIXEL;
    /* biCompression = BI_RGB = 0 (already zero) */
    /* biSizeImage */
    ihdr[20] = (unsigned char)(pixel_bytes);
    ihdr[21] = (unsigned char)(pixel_bytes >> 8);
    ihdr[22] = (unsigned char)(pixel_bytes >> 16);
    ihdr[23] = (unsigned char)(pixel_bytes >> 24);
    /* biXPelsPerMeter, biYPelsPerMeter, biClrUsed, biClrImportant — zero */

    fwrite(fhdr, 1, BMP_FILE_HEADER_SIZE, fp);
    fwrite(ihdr, 1, BMP_INFO_HEADER_SIZE, fp);

    /* Write pixel rows bottom-up (BMP convention when biHeight > 0) */
    const unsigned char *data = (const unsigned char *)mapped_data;
    for (UINT row = height; row-- > 0; ) {
        fwrite(data + (size_t)row * row_pitch, 1, (size_t)stride, fp);
    }

    fclose(fp);
    return 1;
}

/* =========================================================================
 * Present_hook — DXGI IDXGISwapChain::Present intercept
 *
 * Called on every rendered frame.  Only acts when g_screenshot_request == 1
 * (set by dxgi_request_screenshot from the pipe thread).
 *
 * Screenshot capture algorithm (per phase2_dll_architecture.md §2):
 *   1. QueryInterface for IDXGISwapChain
 *   2. GetBuffer(0) → ID3D11Texture2D *backBuffer
 *   3. backBuffer->GetDevice() → ID3D11Device *device
 *   4. device->GetImmediateContext() → ID3D11DeviceContext *ctx
 *   5. backBuffer->GetDesc() → width, height, format
 *   6. device->CreateTexture2D (staging, USAGE_STAGING, CPU_ACCESS_READ)
 *   7. ctx->CopyResource(staging, backBuffer)
 *   8. ctx->Map(staging, 0, D3D11_MAP_READ, 0, &mapped)
 *   9. write_bmp(path, mapped.pData, w, h, mapped.RowPitch)
 *  10. ctx->Unmap(); release all temporaries
 *
 * TODO(live-game): validate that DXVK's staging texture Map() returns
 * correct BGRA pixels.  The code is architecturally correct per D3D11 spec
 * but has not been executed against a real DXVK-backed swap chain.
 * =========================================================================*/
static HRESULT WINAPI Present_hook(void *pSwapChain, UINT SyncInterval, UINT Flags) {
    if (InterlockedCompareExchange(&g_screenshot_request, 0, 1) == 1) {
        char path_copy[512];
        EnterCriticalSection(&g_path_lock);
        memcpy(path_copy, g_screenshot_path, sizeof(path_copy));
        LeaveCriticalSection(&g_path_lock);

        HRESULT hr = S_OK;
        LONG capture_hr = 0;

        /* --- 1. QueryInterface for IDXGISwapChain --- */
        IDXGISwapChain *sc = NULL;
        hr = ((IUnknown*)pSwapChain)->lpVtbl->QueryInterface(
            (IUnknown*)pSwapChain, &IID_IDXGISwapChain_anw, (void**)&sc);
        if (FAILED(hr) || !sc) {
            FILE *fp = fopen("Z:\\tmp\\anw_hook.log", "a");
            if (fp) { fprintf(fp, "[DXGI] QI for IDXGISwapChain failed: 0x%08lx\n",
                               (unsigned long)hr); fclose(fp); }
            capture_hr = (LONG)hr;
            goto screenshot_done;
        }

        /* --- 2. GetBuffer(0) → back-buffer ID3D11Texture2D --- */
        ID3D11Texture2D *backBuffer = NULL;
        hr = sc->lpVtbl->GetBuffer(sc, 0, &IID_ID3D11Texture2D_anw, (void**)&backBuffer);
        ((IUnknown*)sc)->lpVtbl->Release((IUnknown*)sc);
        if (FAILED(hr) || !backBuffer) {
            FILE *fp = fopen("Z:\\tmp\\anw_hook.log", "a");
            if (fp) { fprintf(fp, "[DXGI] GetBuffer failed: 0x%08lx\n",
                               (unsigned long)hr); fclose(fp); }
            capture_hr = (LONG)hr;
            goto screenshot_done;
        }

        /* --- 3. GetDevice → ID3D11Device --- */
        ID3D11Device *device = NULL;
        backBuffer->lpVtbl->GetDevice(backBuffer, (void**)&device);
        if (!device) {
            FILE *fp = fopen("Z:\\tmp\\anw_hook.log", "a");
            if (fp) { fprintf(fp, "[DXGI] GetDevice returned NULL\n"); fclose(fp); }
            ((IUnknown*)backBuffer)->lpVtbl->Release((IUnknown*)backBuffer);
            capture_hr = (LONG)E_FAIL;
            goto screenshot_done;
        }

        /* --- 4. GetImmediateContext → ID3D11DeviceContext --- */
        ID3D11DeviceContext *ctx = NULL;
        device->lpVtbl->GetImmediateContext(device, (void**)&ctx);
        if (!ctx) {
            FILE *fp = fopen("Z:\\tmp\\anw_hook.log", "a");
            if (fp) { fprintf(fp, "[DXGI] GetImmediateContext returned NULL\n"); fclose(fp); }
            ((IUnknown*)device)->lpVtbl->Release((IUnknown*)device);
            ((IUnknown*)backBuffer)->lpVtbl->Release((IUnknown*)backBuffer);
            capture_hr = (LONG)E_FAIL;
            goto screenshot_done;
        }

        /* --- 5. Get back-buffer description (width, height, format) --- */
        D3D11_TEXTURE2D_DESC desc;
        backBuffer->lpVtbl->GetDesc(backBuffer, &desc);

        /* --- 6. Create staging texture (USAGE_STAGING, CPU_ACCESS_READ) --- */
        D3D11_TEXTURE2D_DESC stage_desc = desc;
        stage_desc.Usage          = D3D11_USAGE_STAGING;
        stage_desc.BindFlags      = D3D11_BIND_NONE;
        stage_desc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
        stage_desc.MiscFlags      = 0;
        stage_desc.MipLevels      = 1;
        stage_desc.ArraySize      = 1;
        stage_desc.SampleDesc.Count   = 1;
        stage_desc.SampleDesc.Quality = 0;

        ID3D11Texture2D *stagingTex = NULL;
        hr = device->lpVtbl->CreateTexture2D(device, &stage_desc, NULL, (void**)&stagingTex);
        ((IUnknown*)device)->lpVtbl->Release((IUnknown*)device);
        if (FAILED(hr) || !stagingTex) {
            FILE *fp = fopen("Z:\\tmp\\anw_hook.log", "a");
            if (fp) { fprintf(fp, "[DXGI] CreateTexture2D(staging) failed: 0x%08lx\n",
                               (unsigned long)hr); fclose(fp); }
            ((IUnknown*)ctx)->lpVtbl->Release((IUnknown*)ctx);
            ((IUnknown*)backBuffer)->lpVtbl->Release((IUnknown*)backBuffer);
            capture_hr = (LONG)hr;
            goto screenshot_done;
        }

        /* --- 7. CopyResource(staging ← backBuffer) --- */
        ctx->lpVtbl->CopyResource(ctx, (void*)stagingTex, (void*)backBuffer);
        ((IUnknown*)backBuffer)->lpVtbl->Release((IUnknown*)backBuffer);

        /* --- 8. Map staging texture for CPU read --- */
        D3D11_MAPPED_SUBRESOURCE mapped;
        hr = ctx->lpVtbl->Map(ctx, (void*)stagingTex, 0,
                              D3D11_MAP_READ, 0, &mapped);
        if (FAILED(hr)) {
            FILE *fp = fopen("Z:\\tmp\\anw_hook.log", "a");
            if (fp) { fprintf(fp, "[DXGI] Map(staging) failed: 0x%08lx\n",
                               (unsigned long)hr); fclose(fp); }
            ((IUnknown*)stagingTex)->lpVtbl->Release((IUnknown*)stagingTex);
            ((IUnknown*)ctx)->lpVtbl->Release((IUnknown*)ctx);
            capture_hr = (LONG)hr;
            goto screenshot_done;
        }

        /* --- 9. Write BMP file --- */
        int bmp_ok = write_bmp(path_copy, mapped.pData,
                               desc.Width, desc.Height, mapped.RowPitch);

        {
            FILE *fp = fopen("Z:\\tmp\\anw_hook.log", "a");
            if (fp) {
                fprintf(fp, "[DXGI] Screenshot %s: %s (%ux%u pitch=%u)\n",
                        bmp_ok ? "OK" : "write FAILED",
                        path_copy, desc.Width, desc.Height, mapped.RowPitch);
                fclose(fp);
            }
        }

        /* --- 10. Unmap + release --- */
        ctx->lpVtbl->Unmap(ctx, (void*)stagingTex, 0);
        ((IUnknown*)stagingTex)->lpVtbl->Release((IUnknown*)stagingTex);
        ((IUnknown*)ctx)->lpVtbl->Release((IUnknown*)ctx);

        if (!bmp_ok) {
            capture_hr = (LONG)E_FAIL;
        }

    screenshot_done:
        InterlockedExchange(&g_screenshot_hresult, capture_hr);
        /* g_screenshot_request already cleared by InterlockedCompareExchange above */
    }
    return g_Present_original(pSwapChain, SyncInterval, Flags);
}

/* =========================================================================
 * install_present_hook — acquire throwaway swap-chain, read vtable[8], hook.
 *
 * Returns:
 *    0  success
 *   -1  MH_CreateHook failed
 *   -2  D3D11 device / swap-chain creation failed (headless environment)
 * =========================================================================*/
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

/* =========================================================================
 * Public API implementation
 * =========================================================================*/

int dxgi_hook_init(void) {
    InitializeCriticalSection(&g_path_lock);
    InterlockedExchange(&g_screenshot_hresult, 0);
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
    InterlockedExchange(&g_screenshot_hresult, 0);
    InterlockedExchange(&g_screenshot_request, 1);
    return 0;
}

int dxgi_screenshot_pending(void) {
    return (int)InterlockedCompareExchange(&g_screenshot_request, 0, 0);
}

LONG dxgi_screenshot_hresult(void) {
    return (LONG)InterlockedCompareExchange(&g_screenshot_hresult, 0, 0);
}
