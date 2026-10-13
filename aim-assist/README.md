# aim-assist

A lightweight PC aim-assist for **offline / single-player / bot-match** shooters.
It watches a small square of the screen around your crosshair, finds enemies by
colour, and nudges your mouse toward the closest one while you hold a key.

It only reads screen pixels and moves the mouse. It never touches the game's
memory or files.

## Offline use only

- Use it against NPCs / bots in single-player or private bot matches.
- On startup it **refuses to run** if common anti-cheat services are running
  (EasyAntiCheat, BattlEye, Vanguard, FACEIT, PunkBuster, XIGNCODE...). Don't
  work around that: in online games it ruins matches for real players and gets
  accounts banned.

## Setup (Windows 10/11, Python 3.10+)

```
cd aim-assist
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python -m aimassist init-config config.json
```

## Make enemies easy to detect

Colour detection needs enemies in a colour nothing else on screen uses. In the
game settings turn on **enemy outline / highlight colour** (or a colourblind
mode) and pick saturated magenta, or whatever suits your game. Then set
`color_min` / `color_max` in `config.json` to cover that colour.

## Calibrate

Put an enemy near the crosshair and run:

```
python -m aimassist calibrate -c config.json
```

It writes `calibration_frame.png` and `calibration_mask.png`. In the mask,
white = pixels the tool treats as enemy. Adjust the colour range until only
enemies are white (no HUD, no scenery), and note the printed target count.

## Run

```
python -m aimassist run -c config.json
```

| Key (default)   | Action                          |
|-----------------|---------------------------------|
| hold mouse_x1   | aim assist active while held    |
| F8              | toggle assist on/off            |
| F9              | panic: exit immediately         |
| Ctrl+C          | exit from the terminal          |

Run the game in **borderless windowed** mode on the primary monitor (the capture
reads the screen; exclusive fullscreen can capture black).

## Tuning (`config.json`)

| Setting | Effect |
|---|---|
| `fov_radius` | Scan radius around the crosshair. Smaller = only pulls toward things already near. |
| `smoothing` | Fraction of the gap closed each tick. Lower = softer, more human pull. |
| `max_step` | Max pixels moved per tick. |
| `sensitivity` | Scale from screen pixels to mouse counts; raise if it undershoots, lower if it overshoots/oscillates. |
| `aim_offset_y` | Fraction of target height; `-0.3` aims higher (toward the head). |
| `stickiness_px` | Stays on the current target instead of flicking between two. |
| `hold_key` | `mouse_x1`, `mouse_x2`, `mouse_left`, `mouse_right`, `shift`, `ctrl`, `alt`, or any key name. |
| `extra_blocked_processes` | Add your own process names to the safety guard. |

If it oscillates around the target, lower `smoothing` or `sensitivity`. If it
feels too snappy, lower `smoothing` and `max_step`.

## Layout

```
aimassist/detector.py  colour mask + connected-component target finding
aimassist/aimer.py     target choice, stickiness, smoothing, sub-pixel carry
aimassist/capture.py   mss screen grab (BGRA -> RGB)
aimassist/mouse.py     SendInput (Windows) / pynput fallback
aimassist/hotkeys.py   global hold / toggle / panic keys
aimassist/guard.py     anti-cheat process refusal
aimassist/app.py       main loop
tests/                 pytest suite (detector, aimer, config, guard, capture)
```

## Tests

```
pip install -r requirements-dev.txt
python -m pytest
```
