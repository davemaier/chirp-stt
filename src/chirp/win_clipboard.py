"""Windows clipboard helpers for paste-based text injection.

Uses raw Win32 APIs via ctypes to:
- Save and restore ALL clipboard formats (text, images, files, rich text, etc.)
- Write text to clipboard
- Simulate Ctrl+V via SendInput

No elevated privileges required — all APIs are standard user-level.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import time
import unicodedata

# ---------------------------------------------------------------------------
# Win32 constants
# ---------------------------------------------------------------------------
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_V = 0x56
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

# GDI handle-based formats that cannot be saved via GlobalLock/GlobalSize.
# Their memory-based equivalents (CF_DIB, CF_DIBV5) are always present and
# Windows re-synthesizes the handle formats from them automatically.
CF_BITMAP = 2
CF_ENHMETAFILE = 14
CF_PALETTE = 9
CF_METAFILEPICT = 3
CF_OWNERDISPLAY = 0x0080
_SKIP_FORMATS = frozenset(
    {CF_BITMAP, CF_ENHMETAFILE, CF_PALETTE, CF_METAFILEPICT, CF_OWNERDISPLAY}
)

# ---------------------------------------------------------------------------
# Win32 handles
# ---------------------------------------------------------------------------
user32 = ctypes.windll.user32  # type: ignore[attr-defined]
kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

# Clipboard API signatures
user32.OpenClipboard.argtypes = [ctypes.wintypes.HWND]
user32.OpenClipboard.restype = ctypes.wintypes.BOOL
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = ctypes.wintypes.BOOL
user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = ctypes.wintypes.BOOL
user32.GetClipboardData.argtypes = [ctypes.wintypes.UINT]
user32.GetClipboardData.restype = ctypes.wintypes.HANDLE
user32.SetClipboardData.argtypes = [ctypes.wintypes.UINT, ctypes.wintypes.HANDLE]
user32.SetClipboardData.restype = ctypes.wintypes.HANDLE
user32.EnumClipboardFormats.argtypes = [ctypes.wintypes.UINT]
user32.EnumClipboardFormats.restype = ctypes.wintypes.UINT

kernel32.GlobalAlloc.argtypes = [ctypes.wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = ctypes.wintypes.HANDLE
kernel32.GlobalLock.argtypes = [ctypes.wintypes.HANDLE]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [ctypes.wintypes.HANDLE]
kernel32.GlobalUnlock.restype = ctypes.wintypes.BOOL
kernel32.GlobalSize.argtypes = [ctypes.wintypes.HANDLE]
kernel32.GlobalSize.restype = ctypes.c_size_t
kernel32.GlobalFree.argtypes = [ctypes.wintypes.HANDLE]
kernel32.GlobalFree.restype = ctypes.wintypes.HANDLE


# ---------------------------------------------------------------------------
# ctypes structures for SendInput
# ---------------------------------------------------------------------------
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]

    _anonymous_ = ("_union",)
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("_union", _INPUT_UNION),
    ]


# ---------------------------------------------------------------------------
# Clipboard helpers
# ---------------------------------------------------------------------------
def _open_clipboard(max_retries: int = 5, retry_delay: float = 0.015) -> bool:
    """Open the clipboard with retries (another app may hold the lock)."""
    for attempt in range(max_retries):
        if user32.OpenClipboard(None):
            return True
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
    return False


def _save_all_formats(logger: logging.Logger) -> list[tuple[int, bytes]]:
    """Snapshot every clipboard format as (format_id, raw_bytes) pairs.

    The clipboard must NOT be open when this is called.
    Skips GDI handle formats (CF_BITMAP, CF_ENHMETAFILE, etc.) because they
    cannot be serialised via GlobalLock.  Their memory-based equivalents
    (CF_DIB / CF_DIBV5) are saved instead and Windows re-synthesizes the
    handle formats on restore.
    """
    saved: list[tuple[int, bytes]] = []
    if not _open_clipboard():
        logger.warning("Could not open clipboard for saving")
        return saved
    try:
        fmt = user32.EnumClipboardFormats(0)
        while fmt:
            if fmt not in _SKIP_FORMATS:
                handle = user32.GetClipboardData(fmt)
                if handle:
                    size = kernel32.GlobalSize(handle)
                    if size > 0:
                        ptr = kernel32.GlobalLock(handle)
                        if ptr:
                            buf = (ctypes.c_char * size)()
                            ctypes.memmove(buf, ptr, size)
                            saved.append((fmt, bytes(buf)))
                            kernel32.GlobalUnlock(handle)
            fmt = user32.EnumClipboardFormats(fmt)
    finally:
        user32.CloseClipboard()
    return saved


def _restore_all_formats(
    saved: list[tuple[int, bytes]], logger: logging.Logger
) -> None:
    """Restore a previously saved clipboard snapshot.

    The clipboard must NOT be open when this is called.
    """
    if not _open_clipboard():
        logger.warning("Could not open clipboard for restoring")
        return
    try:
        user32.EmptyClipboard()
        for fmt, data in saved:
            h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            if not h_mem:
                continue
            ptr = kernel32.GlobalLock(h_mem)
            if not ptr:
                kernel32.GlobalFree(h_mem)
                continue
            ctypes.memmove(ptr, data, len(data))
            kernel32.GlobalUnlock(h_mem)
            if not user32.SetClipboardData(fmt, h_mem):
                kernel32.GlobalFree(h_mem)
    finally:
        user32.CloseClipboard()


def _set_clipboard_text(text: str) -> bool:
    """Write text to the clipboard. Returns True on success."""
    if not _open_clipboard():
        return False
    try:
        user32.EmptyClipboard()
        encoded = text.encode("utf-16-le") + b"\x00\x00"
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
        if not h_mem:
            return False
        ptr = kernel32.GlobalLock(h_mem)
        if not ptr:
            kernel32.GlobalFree(h_mem)
            return False
        ctypes.memmove(ptr, encoded, len(encoded))
        kernel32.GlobalUnlock(h_mem)
        if not user32.SetClipboardData(CF_UNICODETEXT, h_mem):
            kernel32.GlobalFree(h_mem)
            return False
        return True
    finally:
        user32.CloseClipboard()


def _send_ctrl_v() -> None:
    """Simulate a Ctrl+V keystroke via SendInput."""
    inputs = (INPUT * 4)()
    # Ctrl down
    inputs[0].type = INPUT_KEYBOARD
    inputs[0].ki.wVk = VK_CONTROL
    inputs[0].ki.dwFlags = 0
    # V down
    inputs[1].type = INPUT_KEYBOARD
    inputs[1].ki.wVk = VK_V
    inputs[1].ki.dwFlags = 0
    # V up
    inputs[2].type = INPUT_KEYBOARD
    inputs[2].ki.wVk = VK_V
    inputs[2].ki.dwFlags = KEYEVENTF_KEYUP
    # Ctrl up
    inputs[3].type = INPUT_KEYBOARD
    inputs[3].ki.wVk = VK_CONTROL
    inputs[3].ki.dwFlags = KEYEVENTF_KEYUP

    user32.SendInput(4, inputs, ctypes.sizeof(INPUT))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def paste_with_preserve(text: str, logger: logging.Logger) -> None:
    """Paste *text* into the focused window, preserving the previous clipboard.

    Saves ALL clipboard formats (text, images, files, rich text, etc.),
    temporarily replaces the clipboard with *text*, simulates Ctrl+V,
    then restores everything.

    1. Snapshot every clipboard format (raw bytes).
    2. Replace clipboard with *text*.
    3. Simulate Ctrl+V.
    4. Wait briefly for the target app to process the paste.
    5. Restore the full clipboard snapshot.
    """
    if not text:
        return
    text = unicodedata.normalize("NFC", text)
    if not text:
        return

    saved = _save_all_formats(logger)

    if not _set_clipboard_text(text):
        logger.error("Failed to copy text to clipboard for pasting")
        return

    _send_ctrl_v()

    # Give the target application time to process the paste
    time.sleep(0.05)

    # Restore previous clipboard contents
    if saved:
        _restore_all_formats(saved, logger)
    else:
        # Clipboard was empty — clear it
        if _open_clipboard():
            user32.EmptyClipboard()
            user32.CloseClipboard()
