# LED-Art-Project: High-Level Architecture Overview

## Overview

The LED-Art-Project is a Python-based platform for creating, controlling, and
visualizing dynamic LED light art installations, inspired by the works of
James Turrell. It is designed to run on a Raspberry Pi driving an SK9822 /
APA102 addressable LED strip, and exposes a Flask web UI for live performance
and scene playback. A pygame-based mock driver is included so the full app
runs on a development machine without hardware.

---

## Main Components

### 1. Hardware Layer
- **Raspberry Pi**: Central controller.
- **Addressable LED strip** (SK9822 / APA102) connected via SPI.
- **Power supply, level shifter, capacitor, and data resistor** as documented
  in `README.md`.

### 2. Driver Layer
- **`controller/led_driver.py`**: Real hardware driver, built on `apa102-pi`.
  Exposes `init_strip`, `apply_color`, and `apply_fade(start, end, duration,
  should_cancel=None)`. The optional `should_cancel` callable lets the fade
  abort early when a scene is stopped.
- **`controller/mock_led_driver.py`**: Pygame-based simulator implementing the
  same `init_strip` / `apply_color` / `apply_fade` interface. Selected at
  startup when the `USE_MOCK_LEDS` environment variable is set.
- **`controller/config.py`**: Helper for resolving the driver from
  configuration.

### 3. Effect & Scene Engine (`effects/`)
- Effects: `solid`, `gradient`, `breathing`, `pulse`, `strobe`, `chase`.
- Transitions: `fade`, `instant`, `wave`, `middle-out`, `random_shimmer`,
  `patterned_fade`, `brightness_sweep`.
- Effects and transitions are looked up via the `EFFECTS` and `TRANSITIONS`
  registries.
- `effects.cancel_event` is a `threading.Event` that running effects/transitions
  poll between frames and during sleeps. `effects.cancel()`,
  `effects.reset_cancel()`, and `effects.is_cancelled()` are the public surface.
- `effects.apply_scene(strip, scene_data)` runs a scene synchronously; `app.py`
  runs scenes in a background thread instead so the HTTP server stays
  responsive.

### 4. Web Application (`app.py`)
- Flask app on port 5000.
- Endpoints:
  - `GET /` – serve `templates/index.html`.
  - `GET /scenes` – list scene JSON files in `scenes/`.
  - `POST /apply_scene_file` – start a scene from a file in `scenes/`.
  - `POST /apply_scene` – start a scene from a JSON body.
  - `POST /run_effect` – run a single effect (used by the Playground tab).
  - `POST /set_color` – set a solid color immediately.
  - `POST /fade` – run a one-shot crossfade.
  - `POST /stop` – cancel the running scene; turns the strip off.
  - `POST /off` – turn the strip off without affecting the running thread.
  - `POST /exit` – cancel, blank the strip, terminate the server.
  - `GET /status` – JSON snapshot of the live show state.
  - `GET /static/<path>` – static assets (e.g. `turrell_colors.json`).
- Concurrency: a single `scene_thread` global guarded by `status_lock`. Starting
  a new scene is rejected with HTTP 409 while one is running; `/stop` sets
  `effects.cancel_event` and joins the worker.

### 5. User Interface (`templates/index.html`)
- Two tabs: **Show Control** (scene picker, status panel, quick color, stop)
  and **Playground** (single-effect runner with parameter form).
- Status panel polls `GET /status` once per second; no WebSocket is used.
- The status payload contains `narrative_intro` (scene-level) and `narrative`
  (per step) which the UI renders alongside the current effect, transition,
  and parameters.

---

## Scene Format

Scenes are JSON files under `scenes/`. See `README.md` for the field reference.
A scene has `name`, optional `description` and `narrative_intro`, an array of
`steps`, and an optional `last` color. Each step names an `effect` and
`transition`, plus effect-specific parameters and a `narrative` string.

---

## Data Flow

1. The user picks a scene in the web UI and posts to `/apply_scene_file`.
2. `app.py` clears `effects.cancel_event` and starts `run_scene_thread` as a
   daemon thread.
3. The worker walks the scene's steps. For each step it updates `status`
   under `status_lock`, runs the transition, then runs the effect. Both
   honor `effects.cancel_event` so `/stop` interrupts long sleeps.
4. The browser polls `/status` and renders step number, effect, transition,
   parameters, and narrative live.

---

## Extensibility

- **Add an effect or transition**: implement a function and register it in
  `EFFECTS` / `TRANSITIONS` in `effects/__init__.py`. Use
  `effects._sleep(seconds)` instead of `time.sleep` so the effect can be
  cancelled.
- **Add a scene**: drop a JSON file in `scenes/`; it will appear in the UI
  dropdown after a refresh.
- **Swap drivers**: set `USE_MOCK_LEDS=1` to run on a dev machine; the mock
  driver implements the same surface as `led_driver.py`.

---

## Future Directions

- Audio-reactive effects.
- Scheduling / playlists.
- Multi-controller networking.
- Pause / resume in addition to stop.
- WebSocket push instead of polling for `/status`.
- Brightness, speed, and master controls in the UI (currently placeholders).
