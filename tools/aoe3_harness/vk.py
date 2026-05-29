"""vk.py — Win32 virtual key code constants for the AOE3DEHarness.

Values match the Win32 Virtual-Key codes accepted by the AOE3DEHarness
keymap (``ASAP-Australia/AOE-3-DE-Harness``).  All constants are plain
integers so they can be passed directly to :class:`HarnessClient` verb
methods (``key``, ``key_down``, ``key_up``).

Reference: https://learn.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes
"""

from __future__ import annotations

__all__ = [
    # Modifiers
    "VK_SHIFT",
    "VK_LSHIFT",
    "VK_RSHIFT",
    "VK_CONTROL",
    "VK_LCONTROL",
    "VK_RCONTROL",
    "VK_MENU",
    "VK_LMENU",
    "VK_RMENU",
    "VK_LWIN",
    "VK_RWIN",
    # Navigation / editing
    "VK_RETURN",
    "VK_ESCAPE",
    "VK_BACK",
    "VK_TAB",
    "VK_SPACE",
    "VK_DELETE",
    "VK_INSERT",
    "VK_HOME",
    "VK_END",
    "VK_PRIOR",
    "VK_NEXT",
    # Arrows
    "VK_LEFT",
    "VK_UP",
    "VK_RIGHT",
    "VK_DOWN",
    # Function keys
    "VK_F1",
    "VK_F2",
    "VK_F3",
    "VK_F4",
    "VK_F5",
    "VK_F6",
    "VK_F7",
    "VK_F8",
    "VK_F9",
    "VK_F10",
    "VK_F11",
    "VK_F12",
    # Digits 0-9
    "VK_0",
    "VK_1",
    "VK_2",
    "VK_3",
    "VK_4",
    "VK_5",
    "VK_6",
    "VK_7",
    "VK_8",
    "VK_9",
    # Letters A-Z
    "VK_A",
    "VK_B",
    "VK_C",
    "VK_D",
    "VK_E",
    "VK_F",
    "VK_G",
    "VK_H",
    "VK_I",
    "VK_J",
    "VK_K",
    "VK_L",
    "VK_M",
    "VK_N",
    "VK_O",
    "VK_P",
    "VK_Q",
    "VK_R",
    "VK_S",
    "VK_T",
    "VK_U",
    "VK_V",
    "VK_W",
    "VK_X",
    "VK_Y",
    "VK_Z",
]

# ---------------------------------------------------------------------------
# Modifier keys
# ---------------------------------------------------------------------------

VK_SHIFT: int = 0x10
VK_LSHIFT: int = 0xA0
VK_RSHIFT: int = 0xA1
VK_CONTROL: int = 0x11
VK_LCONTROL: int = 0xA2
VK_RCONTROL: int = 0xA3
VK_MENU: int = 0x12      # Alt
VK_LMENU: int = 0xA4     # Left Alt
VK_RMENU: int = 0xA5     # Right Alt
VK_LWIN: int = 0x5B
VK_RWIN: int = 0x5C

# ---------------------------------------------------------------------------
# Navigation / editing keys
# ---------------------------------------------------------------------------

VK_RETURN: int = 0x0D    # Enter
VK_ESCAPE: int = 0x1B
VK_BACK: int = 0x08      # Backspace
VK_TAB: int = 0x09
VK_SPACE: int = 0x20
VK_DELETE: int = 0x2E
VK_INSERT: int = 0x2D
VK_HOME: int = 0x24
VK_END: int = 0x23
VK_PRIOR: int = 0x21     # Page Up
VK_NEXT: int = 0x22      # Page Down

# ---------------------------------------------------------------------------
# Arrow keys
# ---------------------------------------------------------------------------

VK_LEFT: int = 0x25
VK_UP: int = 0x26
VK_RIGHT: int = 0x27
VK_DOWN: int = 0x28

# ---------------------------------------------------------------------------
# Function keys F1–F12
# ---------------------------------------------------------------------------

VK_F1: int = 0x70
VK_F2: int = 0x71
VK_F3: int = 0x72
VK_F4: int = 0x73
VK_F5: int = 0x74
VK_F6: int = 0x75
VK_F7: int = 0x76
VK_F8: int = 0x77
VK_F9: int = 0x78
VK_F10: int = 0x79
VK_F11: int = 0x7A
VK_F12: int = 0x7B

# ---------------------------------------------------------------------------
# Digit keys 0–9  (top-row, not numpad)
# ---------------------------------------------------------------------------

VK_0: int = 0x30
VK_1: int = 0x31
VK_2: int = 0x32
VK_3: int = 0x33
VK_4: int = 0x34
VK_5: int = 0x35
VK_6: int = 0x36
VK_7: int = 0x37
VK_8: int = 0x38
VK_9: int = 0x39

# ---------------------------------------------------------------------------
# Letter keys A–Z
# ---------------------------------------------------------------------------

VK_A: int = 0x41
VK_B: int = 0x42
VK_C: int = 0x43
VK_D: int = 0x44
VK_E: int = 0x45
VK_F: int = 0x46
VK_G: int = 0x47
VK_H: int = 0x48
VK_I: int = 0x49
VK_J: int = 0x4A
VK_K: int = 0x4B
VK_L: int = 0x4C
VK_M: int = 0x4D
VK_N: int = 0x4E
VK_O: int = 0x4F
VK_P: int = 0x50
VK_Q: int = 0x51
VK_R: int = 0x52
VK_S: int = 0x53
VK_T: int = 0x54
VK_U: int = 0x55
VK_V: int = 0x56
VK_W: int = 0x57
VK_X: int = 0x58
VK_Y: int = 0x59
VK_Z: int = 0x5A
