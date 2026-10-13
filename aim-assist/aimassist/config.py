"""Configuration: a plain dataclass loaded from / saved to JSON."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path


@dataclass
class Config:
    # --- targeting region -------------------------------------------------
    fov_radius: int = 220           # px around screen centre that is scanned
    deadzone: int = 2               # px; closer than this to the target = stop

    # --- enemy colour (RGB, inclusive range per channel) ------------------
    # Default matches a saturated magenta/pink enemy outline, a common
    # "high-visibility enemy colour" option in games' accessibility menus.
    color_min: tuple[int, int, int] = (200, 0, 200)
    color_max: tuple[int, int, int] = (255, 90, 255)
    min_blob_pixels: int = 12       # ignore specks smaller than this
    max_blob_pixels: int = 40000    # ignore huge regions (UI, fullscreen tint)

    # --- aim behaviour ----------------------------------------------------
    aim_offset_y: float = 0.0       # 0 = blob centre; negative aims higher
    smoothing: float = 0.25         # 0..1 fraction of the gap closed per tick
    max_step: int = 40              # px; hard cap on movement per tick
    sensitivity: float = 1.0        # multiplier mapping screen px -> mouse counts
    stickiness_px: int = 60         # keep the previous target if still this close

    # --- loop / input -----------------------------------------------------
    target_fps: int = 120
    hold_key: str = "mouse_x1"      # hold to engage (mouse_x1/x2, shift, ctrl, alt, or a key)
    toggle_key: str = "f8"          # enable/disable the assist entirely
    panic_key: str = "f9"           # exit immediately
    monitor: int = 1                # mss monitor index (1 = primary)

    # --- safety -----------------------------------------------------------
    block_on_anticheat: bool = True
    extra_blocked_processes: list[str] = field(default_factory=list)

    def validate(self) -> "Config":
        if self.fov_radius < 10:
            raise ValueError("fov_radius must be >= 10")
        if not 0.0 < self.smoothing <= 1.0:
            raise ValueError("smoothing must be in (0, 1]")
        if self.max_step < 1:
            raise ValueError("max_step must be >= 1")
        if self.target_fps < 1 or self.target_fps > 480:
            raise ValueError("target_fps must be in 1..480")
        if self.sensitivity <= 0:
            raise ValueError("sensitivity must be > 0")
        if self.min_blob_pixels < 1 or self.max_blob_pixels < self.min_blob_pixels:
            raise ValueError("invalid blob size limits")
        for name in ("color_min", "color_max"):
            c = getattr(self, name)
            if len(c) != 3 or any(not 0 <= v <= 255 for v in c):
                raise ValueError(f"{name} must be three values in 0..255")
        if any(lo > hi for lo, hi in zip(self.color_min, self.color_max)):
            raise ValueError("color_min must be <= color_max on every channel")
        return self

    # --- persistence ------------------------------------------------------
    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"unknown config keys: {sorted(unknown)}")
        data = dict(data)
        for key in ("color_min", "color_max"):
            if key in data:
                data[key] = tuple(data[key])
        return cls(**data).validate()

    @classmethod
    def load(cls, path: str | Path | None) -> "Config":
        if path is None:
            return cls().validate()
        return cls.from_dict(json.loads(Path(path).read_text()))

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2) + "\n")
