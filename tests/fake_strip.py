"""Recording stand-in for an APA102/SK9822 strip.

Only implements the surface effects/transitions actually use:
`set_pixel(i, r, g, b)`, `show()`, and the optional
`set_global_brightness(b)` (called by transition_brightness_sweep).

Tests can introspect:
- `pixels` — current pixel buffer as a list of [r, g, b] ints.
- `frames` — every snapshot captured at `show()` time.
- `set_pixel_calls` / `show_calls` — counters.
- `global_brightness` — last value set.
"""


class FakeStrip:
    def __init__(self, num_led=144):
        self.num_led = num_led
        self.pixels = [[0, 0, 0] for _ in range(num_led)]
        self.global_brightness = 31
        self.set_pixel_calls = 0
        self.show_calls = 0
        self.frames = []

    def set_pixel(self, i, r, g, b):
        self.set_pixel_calls += 1
        if 0 <= i < self.num_led:
            self.pixels[i] = [int(r), int(g), int(b)]

    def show(self):
        self.show_calls += 1
        self.frames.append([list(p) for p in self.pixels])

    def set_global_brightness(self, b):
        self.global_brightness = int(b)

    def cleanup(self):
        pass

    def reset(self):
        self.pixels = [[0, 0, 0] for _ in range(self.num_led)]
        self.set_pixel_calls = 0
        self.show_calls = 0
        self.frames = []
