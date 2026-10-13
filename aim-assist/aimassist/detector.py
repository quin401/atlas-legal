"""Colour-based target detection on an RGB frame."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage

from .config import Config


@dataclass(frozen=True)
class Target:
    x: float        # centroid, in frame coordinates
    y: float
    pixels: int     # blob area
    top: float      # topmost row of the blob (handy for head-height aiming)


def color_mask(frame: np.ndarray, lo, hi) -> np.ndarray:
    """Boolean mask of pixels whose RGB lies in [lo, hi] on every channel."""
    lo = np.asarray(lo, dtype=np.uint8)
    hi = np.asarray(hi, dtype=np.uint8)
    return np.all((frame[..., :3] >= lo) & (frame[..., :3] <= hi), axis=-1)


def find_targets(frame: np.ndarray, cfg: Config) -> list[Target]:
    """Return blobs matching the enemy colour, within the circular FOV.

    ``frame`` is an HxWx3(+) uint8 RGB array that is already cropped to the
    scan region centred on the crosshair.
    """
    h, w = frame.shape[:2]
    mask = color_mask(frame, cfg.color_min, cfg.color_max)

    # Circular FOV around the frame centre.
    yy, xx = np.ogrid[:h, :w]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    mask &= (yy - cy) ** 2 + (xx - cx) ** 2 <= cfg.fov_radius ** 2
    if not mask.any():
        return []

    # Close small gaps so a thin outline becomes one connected blob.
    mask = ndimage.binary_closing(mask, structure=np.ones((3, 3), bool), iterations=2)

    labels, n = ndimage.label(mask)
    if n == 0:
        return []
    idx = np.arange(1, n + 1)
    sizes = ndimage.sum(mask, labels, idx)
    centers = ndimage.center_of_mass(mask, labels, idx)
    slices = ndimage.find_objects(labels)

    out: list[Target] = []
    for size, (my, mx), sl in zip(sizes, centers, slices):
        if cfg.min_blob_pixels <= size <= cfg.max_blob_pixels:
            out.append(Target(x=float(mx), y=float(my), pixels=int(size), top=float(sl[0].start)))
    return out
