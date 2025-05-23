# LED-Art-Project: Turrell-Style LED Art Controller

## Recent Improvements (v0.28)
- **Step numbers:** Every show step is now numbered in the JSON and displayed in the UI, making it easy to match the running effect to the source file.
- **Always-visible info panel:** The UI always shows the current step number, effect, transition, parameters, and narrative, or 'Idle' when not running.
- **Easier debugging:** You can now quickly find and edit any step in your show, thanks to clear step numbers and live info.
- **Spinorama and all creative shows updated:** All included shows now use step numbers for clarity.

## Overview
This project is a James Turrell-inspired LED art installation platform, designed to run on a Raspberry Pi and control a SK9822 (APA102-compatible) addressable LED strip. It features a web-based interface for live color/effect control, smooth transitions, and scene management, all optimized for artistic, immersive light experiences.

## Features
- **Web-based control panel** (Flask + Bootstrap)
- **Live color/effect selection** (solid, fade, scene transitions)
- **Smooth fades and transitions**
- **Scene management** (save/load custom scenes)
- **Predefined Turrell-inspired color palettes**
- **Diagnostics and safety features**

## Hardware Requirements
- Raspberry Pi (Model B or newer)
- SK9822 (APA102-compatible) 144-pixel LED strip
- 5V 60–75W power supply (with power injection every 0.5m)
- 74HCT125 level shifter (for 5V logic)
- 1000µF capacitor (across 5V/GND at strip head)
- 100Ω resistor (in DATA line)
- Wiring:
  - Red (+5V) → 5V rail
  - Yellow (CLK) → GPIO 11
  - Green (DATA) → GPIO 10
  - Black (GND) → Pi GND

## Software Requirements
- Python 3.9+
- [apa102-pi](https://github.com/tinue/apa102-pi) (for SK9822/APA102 LED control)
- Flask (for web interface)

## Setup Instructions
1. **Connect hardware** as described above.
2. **Enable SPI** on the Pi: `sudo raspi-config` → Interface Options → SPI.
3. **Install dependencies:**
   ```sh
   pip install apa102-pi flask
   ```
4. **Run the web server:**
   ```sh
   python app.py
   ```
5. **Open your browser** to `http://<your-pi-ip>:5000` and use the color picker to control the LEDs.

## Directory Structure
- `app.py` — Flask web server
- `controller/led_driver.py` — LED control logic (apa102-pi)
- `controller/led_mvp_test.py` — Standalone MVP test script
- `effects/` — Effect and scene logic
- `templates/index.html` — Web UI
- `Docs/` — Project documentation and hardware notes

## Example: MVP Test Script
```python
from apa102_pi.driver import APA102
import colorsys, time
NUM = 144
strip = APA102(num_led=NUM, global_brightness=31, spi_speed_hz=12000000)
h = 0.0
try:
    while True:
        r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(h, 1, 1)]
        for i in range(NUM):
            strip.set_pixel(i, r, g, b)
        strip.show()
        h = (h + 0.002) % 1.0
        time.sleep(0.01)
except KeyboardInterrupt:
    for i in range(NUM):
        strip.set_pixel(i, 0, 0, 0)
    strip.show()
    strip.cleanup()
```

## Future Plans
- Expand effect and transition library (breathing, pulse, chase, etc.)
- Scene saving/loading via web UI
- Multi-segment control
- Advanced diagnostics and safety features
- Optional: Audio reactivity, scheduling, remote access, and more

## Credits
- Inspired by the works of James Turrell
- Uses [apa102-pi](https://github.com/tinue/apa102-pi) for LED control

---
For more details, see the `Docs/` folder.

## New in v0.27: Narrative, Info Panel, and Story Shows
- **Narrative feature:** Each show and step can include a `narrative_intro` and `narrative` field, letting you tell a story or describe the mood for each transition. The current step's narrative is shown live in the web interface.
- **Info panel:** The UI now displays the current effect, transition, all parameters, and the narrative for each step, updating live as the show runs.
- **Creative, story-driven shows:** Several new shows are included, each with a unique narrative and step numbers:
  - James Turrell Showcase
  - Kinetic Excite
  - Turrell Meditation
  - Storytime Dreams
  - Urban Rhythm
  - Aurora Journey
  - Colorfield Poem
  - Spinorama (spinning/fading kinetic show)

## Creating Custom Scene JSON Files

You can create your own LED art shows by writing JSON files and placing them in the `scenes/` directory. These will automatically appear in the web interface.

### JSON Structure
A scene file is a JSON object with these fields:

- `name`: (string) The display name of the show.
- `description`: (string) A short description of the show.
- `narrative_intro`: (string, optional) Text shown at the start of the show, introducing the story or mood.
- `steps`: (array) A list of steps, each describing an effect and transition.
- `last`: (array, optional) The color to start from (default: first step's color or `[0,0,0]`).

#### Example
```json
{
  "name": "My Custom Show",
  "description": "A demo with fades and pulses.",
  "narrative_intro": "This show demonstrates a simple fade and pulse.",
  "steps": [
    {
      "effect": "solid",
      "color": [255, 0, 0],
      "duration": 5,
      "transition": "fade",
      "transition_duration": 2,
      "narrative": "A bold red appears, setting the stage."
    },
    {
      "effect": "pulse",
      "color": [0, 0, 255],
      "speed": 20,
      "width_px": 10,
      "duration": 10,
      "transition": "wave",
      "transition_duration": 3,
      "narrative": "A blue pulse races by, full of energy."
    }
  ],
  "last": [0, 0, 0]
}
```

### Step Fields
Each step in `steps` can have:
- `effect`: (string, required) The effect to use. See below for options.
- `transition`: (string, optional) The transition to use before this effect. Default: `fade`.
- `transition_duration`: (number, optional) Duration of the transition in seconds. Default: 2.
- `narrative`: (string, optional) Text to display during this step, telling a story or describing the effect.
- Effect-specific parameters (see below).

### UI Improvements
- The web interface now shows:
  - The current effect and transition
  - All effect/transition parameters for the current step
  - The narrative text for the current step
  - Progress bar and step count
- All info updates live as the show runs.

### Supported Effects and Parameters
- **solid**: Show a single color.
  - `color`: `[r, g, b]` (0-255)
  - `duration`: seconds
- **gradient**: Smooth gradient from one color to another.
  - `color_start`: `[r, g, b]`
  - `color_end`: `[r, g, b]`
  - `duration`: seconds
- **breathing**: Sine-wave brightness pulsing.
  - `base_color`: `[r, g, b]`
  - `cycle_s`: seconds per pulse
  - `duration`: seconds
- **pulse**: Moving bright spot.
  - `color`: `[r, g, b]`
  - `speed`: pixels per second
  - `width_px`: width of the pulse in pixels
  - `duration`: seconds
- **strobe**: Flashing effect.
  - `color`: `[r, g, b]`
  - `duty_cycle`: 0-1 (fraction of time on)
  - `tempo`: flashes per second
  - `duration`: seconds
- **chase**: Single moving pixel.
  - `color`: `[r, g, b]`
  - `speed`: pixels per second
  - `duration`: seconds

### Supported Transitions and Parameters
- **fade**: Cross-fade between colors.
  - `duration`: seconds
- **instant**: No transition, hard cut.
- **wave**: Sinusoidal wave transition.
  - `duration`: seconds
  - `wavelength_px`: pixels per wave (default: 20)
  - `speed`: wave speed (default: 1)
- **middle-out**: Color radiates from center.
  - `duration`: seconds
- **random_shimmer**: Adds noise during fade.
  - `duration`: seconds
  - `jitter_pct`: 0-1 (default: 0.05)
- **patterned_fade**: Steps through a palette.
  - `duration`: seconds
  - `palette`: array of `[r,g,b]` colors
  - `step_s`: seconds per step
- **brightness_sweep**: Global brightness ramp.
  - `duration`: seconds
  - `min_b`: minimum brightness (default: 8)
  - `max_b`: maximum brightness (default: 20)

### Tips
- All color values are arrays: `[red, green, blue]` (0-255 each).
- You can mix and match effects and transitions in any order.
- The `duration` field is always in seconds.
- The `last` field (optional) sets the starting color for the first transition.
- You can preview and test effects in the web UI's Playground tab.

### Adding Your Scene
1. Create a new `.json` file in the `scenes/` directory.
2. Fill it out as shown above.
3. Refresh the web UI. Your show will appear in the dropdown!

For more advanced examples, see the included `turrell_showcase.json`.

