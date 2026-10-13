"""Pure aiming maths: pick a target, produce a smoothed mouse delta."""

from __future__ import annotations

import math

from .config import Config
from .detector import Target


class Aimer:
    """Stateful target chooser with smoothing and target stickiness."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._last: tuple[float, float] | None = None
        self._residual = (0.0, 0.0)   # sub-pixel remainder carried between ticks

    def reset(self) -> None:
        self._last = None
        self._residual = (0.0, 0.0)

    def aim_point(self, t: Target) -> tuple[float, float]:
        # Offset is a fraction of blob height measured from the centre.
        height = max(1.0, 2.0 * (t.y - t.top))
        return t.x, t.y + self.cfg.aim_offset_y * height

    def choose(self, targets: list[Target], centre: tuple[float, float]) -> Target | None:
        """Closest target to the crosshair, but prefer the previous one if it
        is still nearby, which stops jitter between two similar candidates."""
        if not targets:
            self._last = None
            return None
        cx, cy = centre

        def dist(t: Target, ref: tuple[float, float]) -> float:
            px, py = self.aim_point(t)
            return math.hypot(px - ref[0], py - ref[1])

        if self._last is not None:
            near = [t for t in targets if dist(t, self._last) <= self.cfg.stickiness_px]
            if near:
                best = min(near, key=lambda t: dist(t, self._last))
                self._last = self.aim_point(best)
                return best
        best = min(targets, key=lambda t: dist(t, (cx, cy)))
        self._last = self.aim_point(best)
        return best

    def step(self, target: Target | None, centre: tuple[float, float]) -> tuple[int, int]:
        """Integer mouse delta for this tick (0, 0 when nothing to do)."""
        if target is None:
            self._residual = (0.0, 0.0)
            return 0, 0
        px, py = self.aim_point(target)
        dx, dy = px - centre[0], py - centre[1]
        if math.hypot(dx, dy) <= self.cfg.deadzone:
            self._residual = (0.0, 0.0)
            return 0, 0

        dx *= self.cfg.smoothing * self.cfg.sensitivity
        dy *= self.cfg.smoothing * self.cfg.sensitivity

        # Cap the step length, preserving direction.
        length = math.hypot(dx, dy)
        if length > self.cfg.max_step:
            scale = self.cfg.max_step / length
            dx, dy = dx * scale, dy * scale

        dx += self._residual[0]
        dy += self._residual[1]
        ix, iy = int(round(dx)), int(round(dy))
        self._residual = (dx - ix, dy - iy)
        return ix, iy
