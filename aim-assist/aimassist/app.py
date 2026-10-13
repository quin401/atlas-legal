"""Main loop."""

from __future__ import annotations

import threading
import time

from .aimer import Aimer
from .config import Config
from .detector import find_targets
from .guard import find_anticheat, running_process_names


def run(cfg: Config, debug: bool = False) -> int:
    if cfg.block_on_anticheat:
        hits = find_anticheat(running_process_names(), cfg.extra_blocked_processes)
        if hits:
            print(f"Refusing to start: anti-cheat detected ({', '.join(hits)}).\n"
                  "This tool is for offline / single-player / bot-match games only.")
            return 2

    from .capture import ScreenCapture
    from .hotkeys import InputState
    from .mouse import Mouse

    stop = threading.Event()
    enabled = threading.Event()
    enabled.set()

    def toggle():
        enabled.clear() if enabled.is_set() else enabled.set()
        print("assist", "ON" if enabled.is_set() else "OFF")

    def panic():
        print("panic key pressed, exiting")
        stop.set()

    cap = ScreenCapture(cfg.fov_radius, cfg.monitor)
    mouse, aimer = Mouse(), Aimer(cfg)
    inputs = InputState(cfg.hold_key, cfg.toggle_key, cfg.panic_key, toggle, panic)
    inputs.start()
    print(f"Running. Hold [{cfg.hold_key}] to aim, [{cfg.toggle_key}] toggles, "
          f"[{cfg.panic_key}] quits. Ctrl+C also quits.")

    period = 1.0 / cfg.target_fps
    next_tick = time.perf_counter()
    try:
        while not stop.is_set():
            if enabled.is_set() and inputs.engaged:
                frame = cap.grab()
                targets = find_targets(frame, cfg)
                target = aimer.choose(targets, cap.centre)
                dx, dy = aimer.step(target, cap.centre)
                mouse.move_relative(dx, dy)
                if debug and target:
                    print(f"targets={len(targets)} dx={dx} dy={dy}")
            else:
                aimer.reset()
            next_tick += period
            delay = next_tick - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            else:
                next_tick = time.perf_counter()
    except KeyboardInterrupt:
        pass
    finally:
        inputs.stop()
        cap.close()
    return 0
