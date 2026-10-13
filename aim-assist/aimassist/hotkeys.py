"""Global key / mouse-button state tracking via pynput."""

from __future__ import annotations

import threading
from typing import Callable

_MOUSE_NAMES = {"mouse_left": "left", "mouse_right": "right", "mouse_middle": "middle",
                "mouse_x1": "x1", "mouse_x2": "x2"}


def normalise_key(key) -> str:
    """Map a pynput Key/KeyCode to the lower-case names used in the config."""
    name = getattr(key, "name", None)
    if name:
        # shift_l / shift_r -> shift, ctrl_l -> ctrl, etc.
        for base in ("shift", "ctrl", "alt"):
            if name.startswith(base):
                return base
        return name
    char = getattr(key, "char", None)
    return char.lower() if char else ""


class InputState:
    """Tracks held keys/buttons and fires callbacks on toggle / panic keys."""

    def __init__(self, hold: str, toggle: str, panic: str,
                 on_toggle: Callable[[], None], on_panic: Callable[[], None]):
        from pynput import keyboard, mouse

        self.hold, self.toggle, self.panic = hold.lower(), toggle.lower(), panic.lower()
        self._on_toggle, self._on_panic = on_toggle, on_panic
        self._held: set[str] = set()
        self._lock = threading.Lock()
        self._kb = keyboard.Listener(on_press=self._press, on_release=self._release)
        self._ms = mouse.Listener(on_click=self._click)

    def start(self) -> None:
        self._kb.start()
        self._ms.start()

    def stop(self) -> None:
        self._kb.stop()
        self._ms.stop()

    @property
    def engaged(self) -> bool:
        with self._lock:
            return self.hold in self._held

    def _press(self, key) -> None:
        name = normalise_key(key)
        with self._lock:
            already = name in self._held
            self._held.add(name)
        if already:
            return
        if name == self.toggle:
            self._on_toggle()
        elif name == self.panic:
            self._on_panic()

    def _release(self, key) -> None:
        with self._lock:
            self._held.discard(normalise_key(key))

    def _click(self, _x, _y, button, pressed) -> None:
        name = {"x1": "mouse_x1", "x2": "mouse_x2"}.get(button.name, f"mouse_{button.name}")
        with self._lock:
            (self._held.add if pressed else self._held.discard)(name)
