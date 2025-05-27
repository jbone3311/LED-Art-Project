# LED-Art-Project: High-Level Architecture Overview

## Overview

The LED-Art-Project is a Python-based platform for creating, controlling, and visualizing dynamic LED light art installations, inspired by the works of James Turrell. It is designed to run on a Raspberry Pi (or similar hardware) and provides both a web-based and a mock (simulated) interface for development, testing, and live performance. The system supports scene creation, effect/transition libraries, and a responsive UI for both real and simulated LEDs.

---

## Main Components

### 1. **Hardware Layer**
- **Raspberry Pi**: Central controller for the system.
- **Addressable LED Strip**: (e.g., SK9822, APA102) connected via SPI.
- **Power Supply & Level Shifter**: Ensures safe and reliable operation.

### 2. **Driver Layer**
- **controller/led_driver.py**: Controls real LED hardware using SPI and libraries like `apa102-pi`.
- **controller/mock_led_driver.py**: Simulates an LED strip using Pygame for development and demo purposes.

### 3. **Effect & Scene Engine**
- **effects/**: Contains effect and transition logic (e.g., solid, gradient, breathing, pulse, strobe, chase, and transitions like fade, wave, shimmer).
- **scenes/**: JSON files describing shows, each with a name, description, and a sequence of steps (effects, transitions, durations, and narratives).

### 4. **Web Application Layer**
- **app.py**: Flask server providing REST endpoints, WebSocket updates, and serving the web UI.
- **templates/led_display.html**: Main web interface for controlling and visualizing the LED strip, including show selection, creation, and playback.

### 5. **User Interface**
- **Web UI**: Responsive controls for shape, size, brightness, effect selection, show creation, and live preview.
- **Mock LED Window**: (Optional) Pygame window for local simulation.

---

## Data Flow

1. **User Interaction**
   - Users interact with the web UI to select or create shows, adjust parameters, and start/stop playback.
2. **Show Management**
   - Shows are stored as JSON files in `scenes/` and loaded via the web UI or API.
3. **Effect/Transition Execution**
   - The Flask app launches a thread to run the selected show, step by step, applying effects and transitions to the LED strip (real or mock).
4. **LED Output**
   - For real hardware: SPI commands are sent to the LED strip.
   - For mock: Pygame or browser-based visualization is updated in real time.
5. **Live Updates**
   - WebSocket messages broadcast current state, color, title, and narrative to all connected clients for real-time feedback.

---

## Extensibility

- **Effect/Transition Registry**: New effects and transitions can be added by implementing Python functions and registering them in the `effects/` module.
- **Scene Format**: Shows are defined in JSON, making it easy to create, edit, and share new scenes.
- **Driver Abstraction**: The system can switch between real and mock drivers via an environment variable (`USE_MOCK_LEDS`).
- **UI Customization**: The web interface is modular and can be extended with new controls, visualizations, or editor features.

---

## Future Directions

- **Audio-Reactive Modes**: Sync light patterns with music.
- **Scheduling & Automation**: Timed scene changes and routines.
- **Multi-Controller Networking**: Synchronize multiple installations.
- **Advanced Diagnostics**: Power monitoring, error reporting, and safety features.
- **Mobile & Remote Access**: Secure control from anywhere.
- **Live Coding/Plugin System**: Hot-reloadable effect plugins for rapid prototyping.

---

## Summary

The LED-Art-Project is a flexible, extensible platform for creative light art, supporting both real and simulated environments. Its modular architecture allows for easy expansion, rapid prototyping, and a rich user experience for both artists and developers. 