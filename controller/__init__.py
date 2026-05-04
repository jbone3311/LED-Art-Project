"""LED driver selector + pixel tap.

Set `USE_MOCK_LEDS=1` to use the pygame-based mock driver (for development on
a machine without an APA102/SK9822 strip). Otherwise the real `apa102-pi`
driver is loaded.

`init_strip()` wraps the underlying strip's `set_pixel` so every pixel write
is mirrored into a process-wide buffer accessible via `get_pixels()`. The web
UI streams that buffer to the browser for a live preview canvas.
"""
import os
import threading

LED_COUNT = 144

if os.environ.get("USE_MOCK_LEDS", "").lower() in ("1", "true", "yes"):
    from .mock_led_driver import apply_color, apply_fade, init_strip as _init_strip
else:
    from .led_driver import apply_color, apply_fade, init_strip as _init_strip


_pixel_buffer = [(0, 0, 0)] * LED_COUNT
_pixel_lock = threading.Lock()


def get_pixels():
    """Return a snapshot of the current pixel buffer as a list of (r, g, b) tuples."""
    with _pixel_lock:
        return list(_pixel_buffer)


def init_strip(*args, **kwargs):
    strip = _init_strip(*args, **kwargs)
    orig_set_pixel = strip.set_pixel

    def set_pixel(i, r, g, b, *a, **kw):
        if 0 <= i < LED_COUNT:
            with _pixel_lock:
                _pixel_buffer[i] = (int(r), int(g), int(b))
        return orig_set_pixel(i, r, g, b, *a, **kw)

    strip.set_pixel = set_pixel
    return strip


__all__ = ["LED_COUNT", "apply_color", "apply_fade", "init_strip", "get_pixels"]
