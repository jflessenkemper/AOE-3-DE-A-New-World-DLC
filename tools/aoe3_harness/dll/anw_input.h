/*
 * anw_input.h — Public API for the ANW harness input injection layer.
 *
 * Implements §3 of artifacts/harness_design/phase2_dll_architecture.md.
 */

#ifndef ANW_INPUT_H
#define ANW_INPUT_H

#include <windows.h>

/*
 * inject_key() — Inject a keyboard event for virtual key code `vk`.
 *   down=TRUE  → KEYEVENTF_KEYDOWN (key press)
 *   down=FALSE → KEYEVENTF_KEYUP   (key release)
 *
 * Virtual key codes: https://docs.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes
 * Example: inject_key(0x57, TRUE)  = W key down
 *          inject_key(0x57, FALSE) = W key up
 */
void inject_key(WORD vk, BOOL down);

/*
 * inject_click() — Inject a left-click at client-area pixel coordinates (x, y).
 * Sends: MOUSEMOVE(abs) + LBUTTONDOWN + LBUTTONUP.
 * Coordinates are translated from client-area to screen-absolute internally.
 */
void inject_click(int x, int y);

/*
 * inject_move() — Inject a mouse-move to client-area pixel coordinates (x, y).
 * Does NOT send any button events.
 */
void inject_move(int x, int y);

#endif /* ANW_INPUT_H */
