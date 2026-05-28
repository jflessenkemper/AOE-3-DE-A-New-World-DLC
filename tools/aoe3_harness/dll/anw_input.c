/*
 * anw_input.c — Win32 SendInput wrappers for keyboard and mouse injection.
 *
 * Implements §3 of artifacts/harness_design/phase2_dll_architecture.md:
 *   inject_key()   — KEY_DOWN or KEY_UP for a virtual key code
 *   inject_click() — MOUSEMOVE + LBUTTONDOWN + LBUTTONUP at client-area coords
 *   inject_move()  — MOUSEMOVE only
 *
 * All functions operate via Win32 SendInput(), which is safe to call from any
 * thread inside the target process.  No SetWindowsHookEx required.
 *
 * Coordinate system for click/move:
 *   The pipe client sends pixel coordinates in the game window's client area.
 *   inject_click/inject_move convert from client-area pixels to the absolute
 *   coordinates expected by MOUSEEVENTF_ABSOLUTE using ClientToScreen() on
 *   the foreground window, then scale to [0, 65535].
 *
 * Anti-cheat guard (§10.1):
 *   The functions are no-ops if EasyAntiCheat.dll is loaded, preventing
 *   accidental injection in multiplayer sessions.
 */

#include <windows.h>
#include "anw_input.h"

/* --------------------------------------------------------------------------
 * Internal helpers
 * -------------------------------------------------------------------------- */

/* Returns TRUE if EasyAntiCheat is loaded — injection must be skipped. */
static BOOL eac_active(void) {
    return GetModuleHandleW(L"EasyAntiCheat.dll") != NULL;
}

/* --------------------------------------------------------------------------
 * Public API
 * -------------------------------------------------------------------------- */

void inject_key(WORD vk, BOOL down) {
    if (eac_active()) return;

    INPUT inp = {0};
    inp.type           = INPUT_KEYBOARD;
    inp.ki.wVk         = vk;
    inp.ki.dwFlags     = down ? 0 : KEYEVENTF_KEYUP;
    inp.ki.time        = 0;
    inp.ki.dwExtraInfo = 0;
    SendInput(1, &inp, sizeof(INPUT));
}

void inject_click(int x, int y) {
    if (eac_active()) return;

    /* Translate client-area (x, y) to screen coordinates. */
    HWND hwnd = GetForegroundWindow();
    POINT pt = { x, y };
    if (hwnd) {
        ClientToScreen(hwnd, &pt);
    }

    int screen_w = GetSystemMetrics(SM_CXSCREEN);
    int screen_h = GetSystemMetrics(SM_CYSCREEN);

    /* Clamp to screen bounds to avoid out-of-range MOUSEEVENTF_ABSOLUTE coords. */
    if (pt.x < 0) pt.x = 0;
    if (pt.y < 0) pt.y = 0;
    if (pt.x >= screen_w) pt.x = screen_w - 1;
    if (pt.y >= screen_h) pt.y = screen_h - 1;

    LONG abs_x = (LONG)((pt.x * 65535L) / screen_w);
    LONG abs_y = (LONG)((pt.y * 65535L) / screen_h);

    INPUT inp[3] = {0};

    /* Event 0: move to absolute position */
    inp[0].type            = INPUT_MOUSE;
    inp[0].mi.dwFlags      = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE;
    inp[0].mi.dx           = abs_x;
    inp[0].mi.dy           = abs_y;

    /* Event 1: left button down */
    inp[1].type            = INPUT_MOUSE;
    inp[1].mi.dwFlags      = MOUSEEVENTF_LEFTDOWN;

    /* Event 2: left button up */
    inp[2].type            = INPUT_MOUSE;
    inp[2].mi.dwFlags      = MOUSEEVENTF_LEFTUP;

    SendInput(3, inp, sizeof(INPUT));
}

void inject_move(int x, int y) {
    if (eac_active()) return;

    HWND hwnd = GetForegroundWindow();
    POINT pt = { x, y };
    if (hwnd) {
        ClientToScreen(hwnd, &pt);
    }

    int screen_w = GetSystemMetrics(SM_CXSCREEN);
    int screen_h = GetSystemMetrics(SM_CYSCREEN);

    if (pt.x < 0) pt.x = 0;
    if (pt.y < 0) pt.y = 0;
    if (pt.x >= screen_w) pt.x = screen_w - 1;
    if (pt.y >= screen_h) pt.y = screen_h - 1;

    LONG abs_x = (LONG)((pt.x * 65535L) / screen_w);
    LONG abs_y = (LONG)((pt.y * 65535L) / screen_h);

    INPUT inp = {0};
    inp.type       = INPUT_MOUSE;
    inp.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE;
    inp.mi.dx      = abs_x;
    inp.mi.dy      = abs_y;

    SendInput(1, &inp, sizeof(INPUT));
}
