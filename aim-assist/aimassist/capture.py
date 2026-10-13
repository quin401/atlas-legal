"""Screen capture of a square region centred on the primary monitor."""

from __future__ import annotations

import numpy as np


class ScreenCapture:
    def __init__(self, fov_radius: int, monitor: int = 1):
        import mss  # imported lazily so the pure logic is testable headless

        self._sct = mss.mss()
        mons = self._sct.monitors
        if not 1 <= monitor < len(mons):
            raise ValueError(f"monitor {monitor} not found (have 1..{len(mons) - 1})")
        m = mons[monitor]
        self.size = 2 * fov_radius
        self.region = {
            "left": m["left"] + m["width"] // 2 - fov_radius,
            "top": m["top"] + m["height"] // 2 - fov_radius,
            "width": self.size,
            "height": self.size,
        }

    @property
    def centre(self) -> tuple[float, float]:
        return (self.size - 1) / 2.0, (self.size - 1) / 2.0

    def grab(self) -> np.ndarray:
        """Return an HxWx3 uint8 RGB frame."""
        shot = np.asarray(self._sct.grab(self.region))  # BGRA
        return np.ascontiguousarray(shot[..., 2::-1])   # -> RGB

    def close(self) -> None:
        self._sct.close()
