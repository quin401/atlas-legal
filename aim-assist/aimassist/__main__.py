"""CLI: python -m aimassist {run,calibrate,init-config}"""

from __future__ import annotations

import argparse
import sys

from .config import Config


def calibrate(cfg: Config, out: str) -> int:
    """Grab the scan region and report how many pixels match the enemy colour,
    saving the frame and the mask as PPM/PGM-free .npy-less PNGs via stdlib."""
    import zlib, struct
    import numpy as np
    from .capture import ScreenCapture
    from .detector import color_mask, find_targets

    cap = ScreenCapture(cfg.fov_radius, cfg.monitor)
    frame = cap.grab()
    cap.close()
    mask = color_mask(frame, cfg.color_min, cfg.color_max)
    print(f"matching pixels: {int(mask.sum())}, targets: {len(find_targets(frame, cfg))}")

    def png(path: str, arr: np.ndarray) -> None:
        h, w, _ = arr.shape
        raw = b"".join(b"\x00" + arr[y].tobytes() for y in range(h))
        def chunk(t: bytes, d: bytes) -> bytes:
            c = struct.pack(">I", len(d)) + t + d
            return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
        data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
        open(path, "wb").write(data)

    png(f"{out}_frame.png", frame)
    png(f"{out}_mask.png", np.repeat((mask * 255).astype(np.uint8)[..., None], 3, axis=2))
    print(f"wrote {out}_frame.png and {out}_mask.png (white = matched enemy colour)")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="aimassist", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="start the aim assist")
    r.add_argument("-c", "--config"); r.add_argument("--debug", action="store_true")
    c = sub.add_parser("calibrate", help="screenshot the scan region and show what matches")
    c.add_argument("-c", "--config"); c.add_argument("-o", "--out", default="calibration")
    i = sub.add_parser("init-config", help="write a default config.json")
    i.add_argument("path", nargs="?", default="config.json")
    args = p.parse_args(argv)

    if args.cmd == "init-config":
        Config().save(args.path); print(f"wrote {args.path}"); return 0
    cfg = Config.load(args.config)
    if args.cmd == "calibrate":
        return calibrate(cfg, args.out)
    from .app import run
    return run(cfg, debug=args.debug)


if __name__ == "__main__":
    sys.exit(main())
