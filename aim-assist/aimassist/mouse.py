"""Relative mouse movement. Native SendInput on Windows, pynput elsewhere."""

from __future__ import annotations

import sys


class Mouse:
    def __init__(self):
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class MOUSEINPUT(ctypes.Structure):
                _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                            ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                            ("time", wintypes.DWORD),
                            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

            class INPUT(ctypes.Structure):
                class _U(ctypes.Union):
                    _fields_ = [("mi", MOUSEINPUT)]
                _anonymous_ = ("u",)
                _fields_ = [("type", wintypes.DWORD), ("u", _U)]

            self._INPUT, self._MOUSEINPUT = INPUT, MOUSEINPUT
            self._user32 = ctypes.windll.user32
            self._ctypes = ctypes
            self._move = self._move_win
        else:
            from pynput.mouse import Controller

            self._ctl = Controller()
            self._move = lambda dx, dy: self._ctl.move(dx, dy)

    def _move_win(self, dx: int, dy: int) -> None:
        MOUSEEVENTF_MOVE = 0x0001
        mi = self._MOUSEINPUT(dx, dy, 0, MOUSEEVENTF_MOVE, 0, None)
        inp = self._INPUT(type=0, mi=mi)  # INPUT_MOUSE
        self._user32.SendInput(1, self._ctypes.byref(inp), self._ctypes.sizeof(inp))

    def move_relative(self, dx: int, dy: int) -> None:
        if dx or dy:
            self._move(int(dx), int(dy))
