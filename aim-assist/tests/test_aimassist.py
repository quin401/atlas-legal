import json
import math

import numpy as np
import pytest

from aimassist.aimer import Aimer
from aimassist.config import Config
from aimassist.detector import Target, color_mask, find_targets
from aimassist.guard import find_anticheat
from aimassist.__main__ import main

MAGENTA = (230, 20, 230)


def frame_with(*boxes, size=200):
    f = np.zeros((size, size, 3), np.uint8)
    for x0, y0, x1, y1 in boxes:
        f[y0:y1, x0:x1] = MAGENTA
    return f


def cfg(**kw):
    return Config(fov_radius=100, **kw).validate()


# ---- config -------------------------------------------------------------
def test_config_roundtrip(tmp_path):
    p = tmp_path / "c.json"
    Config(smoothing=0.5, color_min=(1, 2, 3)).save(p)
    c = Config.load(p)
    assert c.smoothing == 0.5 and c.color_min == (1, 2, 3)


@pytest.mark.parametrize("bad", [
    {"smoothing": 0}, {"smoothing": 1.5}, {"fov_radius": 1}, {"max_step": 0},
    {"target_fps": 0}, {"sensitivity": 0}, {"color_min": (0, 0)},
    {"color_min": (255, 0, 0), "color_max": (0, 0, 0)}, {"min_blob_pixels": 0},
])
def test_config_rejects_bad_values(bad):
    with pytest.raises(ValueError):
        Config(**bad).validate()


def test_config_rejects_unknown_keys():
    with pytest.raises(ValueError, match="unknown"):
        Config.from_dict({"nope": 1})


# ---- detector -----------------------------------------------------------
def test_color_mask_bounds_inclusive():
    f = np.array([[[200, 0, 200], [199, 0, 200]]], np.uint8)
    assert color_mask(f, (200, 0, 200), (255, 90, 255)).tolist() == [[True, False]]


def test_find_single_target_centroid():
    ts = find_targets(frame_with((120, 80, 140, 120)), cfg())
    assert len(ts) == 1
    assert ts[0].x == pytest.approx(129.5, abs=0.6) and ts[0].y == pytest.approx(99.5, abs=0.6)
    assert ts[0].top == 80


def test_no_target_on_empty_frame():
    assert find_targets(frame_with(), cfg()) == []


def test_specks_and_giants_filtered():
    c = cfg(min_blob_pixels=12, max_blob_pixels=500)
    assert find_targets(frame_with((100, 100, 102, 102)), c) == []        # 4 px speck
    assert find_targets(frame_with((60, 60, 140, 140)), c) == []          # 6400 px


def test_outside_fov_ignored():
    # fov 100 in a 200px frame; corner is outside the circle
    assert find_targets(frame_with((0, 0, 20, 20)), cfg()) == []


def test_outline_gaps_are_bridged():
    f = frame_with((100, 60, 104, 120), (106, 60, 110, 120))   # 2px gap
    assert len(find_targets(f, cfg())) == 1


def test_two_targets():
    assert len(find_targets(frame_with((30, 90, 50, 110), (150, 90, 170, 110)), cfg())) == 2


# ---- aimer --------------------------------------------------------------
CENTRE = (99.5, 99.5)


def T(x, y, top=None):
    return Target(x=x, y=y, pixels=100, top=y - 10 if top is None else top)


def test_chooses_closest_to_crosshair():
    a = Aimer(cfg())
    assert a.choose([T(10, 10), T(110, 100)], CENTRE).x == 110


def test_stickiness_keeps_previous_target():
    a = Aimer(cfg(stickiness_px=60))
    first = a.choose([T(150, 100), T(30, 100)], CENTRE)
    assert first.x == 150
    # now the other is nearer the crosshair, but the original is still close to where it was
    assert a.choose([T(152, 100), T(105, 100)], CENTRE).x == 152


def test_step_moves_toward_target_and_is_capped():
    a = Aimer(cfg(smoothing=1.0, max_step=10))
    dx, dy = a.step(T(199, 99.5), CENTRE)
    assert dx == 10 and dy == 0
    dx, dy = a.step(T(99.5, 0), CENTRE)
    assert dx == 0 and dy < 0


def test_step_smoothing_fraction():
    a = Aimer(cfg(smoothing=0.5, max_step=999))
    assert a.step(T(139.5, 99.5), CENTRE) == (20, 0)


def test_deadzone_stops():
    a = Aimer(cfg(deadzone=3))
    assert a.step(T(101, 100), CENTRE) == (0, 0)


def test_no_target_no_motion():
    assert Aimer(cfg()).step(None, CENTRE) == (0, 0)


def test_subpixel_residual_accumulates():
    a = Aimer(cfg(smoothing=0.1, max_step=999, deadzone=0))
    total = sum(a.step(T(104.5, 99.5), CENTRE)[0] for _ in range(10))
    assert total == 5  # 0.5 px/tick would otherwise round away


def test_aim_offset_moves_up_for_negative_offset():
    a = Aimer(cfg(aim_offset_y=-0.25))
    x, y = a.aim_point(Target(x=50, y=100, pixels=1, top=80))  # height 40
    assert (x, y) == (50, 90)


def test_converges_on_static_target():
    a = Aimer(cfg(smoothing=0.3, max_step=50))
    pos = [0.0, 0.0]
    tgt = (80.0, 60.0)
    for _ in range(80):
        dx, dy = a.step(T(tgt[0] - pos[0] + 99.5, tgt[1] - pos[1] + 99.5), CENTRE)
        pos[0] += dx; pos[1] += dy
    assert math.hypot(tgt[0] - pos[0], tgt[1] - pos[1]) <= 3


# ---- guard --------------------------------------------------------------
def test_guard_detects_anticheat_case_insensitive():
    assert find_anticheat(["chrome.exe", "EasyAntiCheat.exe", "VGC.EXE"]) == ["easyanticheat", "vgc"]


def test_guard_clean_and_extra():
    assert find_anticheat(["game.exe"]) == []
    assert find_anticheat(["mycheck.exe"], extra=["MyCheck"]) == ["mycheck"]


# ---- cli ----------------------------------------------------------------
def test_init_config_cli(tmp_path, capsys):
    p = tmp_path / "cfg.json"
    assert main(["init-config", str(p)]) == 0
    assert json.loads(p.read_text())["smoothing"] == 0.25


# ---- app / hotkeys / capture -------------------------------------------
def test_app_refuses_when_anticheat_running(monkeypatch, capsys):
    from aimassist import app
    monkeypatch.setattr(app, "running_process_names", lambda: ["BEService.exe"])
    assert app.run(Config()) == 2
    assert "anti-cheat" in capsys.readouterr().out


def test_normalise_key():
    from types import SimpleNamespace as NS
    from aimassist.hotkeys import normalise_key
    assert normalise_key(NS(name="shift_r")) == "shift"
    assert normalise_key(NS(name="f8")) == "f8"
    assert normalise_key(NS(name=None, char="Q")) == "q"


def test_capture_converts_bgra_to_rgb(monkeypatch):
    import sys, types
    from aimassist.capture import ScreenCapture
    bgra = np.zeros((4, 4, 4), np.uint8); bgra[..., 0] = 10; bgra[..., 1] = 20; bgra[..., 2] = 30

    class FakeSct:
        monitors = [{}, {"left": 0, "top": 0, "width": 100, "height": 100}]
        def grab(self, region): return bgra
        def close(self): pass
    monkeypatch.setitem(sys.modules, "mss", types.SimpleNamespace(mss=lambda: FakeSct()))
    cap = ScreenCapture(2)
    assert cap.region == {"left": 48, "top": 48, "width": 4, "height": 4}
    assert tuple(cap.grab()[0, 0]) == (30, 20, 10)
    with pytest.raises(ValueError):
        ScreenCapture(2, monitor=5)
