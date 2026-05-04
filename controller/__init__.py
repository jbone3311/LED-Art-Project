"""LED driver selector.

Set `USE_MOCK_LEDS=1` to use the pygame-based mock driver (for development on a
machine without an APA102/SK9822 strip). Otherwise the real `apa102-pi` driver
is loaded.
"""
import os

LED_COUNT = 144

if os.environ.get("USE_MOCK_LEDS", "").lower() in ("1", "true", "yes"):
    from .mock_led_driver import apply_color, apply_fade, init_strip
else:
    from .led_driver import apply_color, apply_fade, init_strip

__all__ = ["LED_COUNT", "apply_color", "apply_fade", "init_strip"]
