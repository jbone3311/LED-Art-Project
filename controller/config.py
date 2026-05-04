"""Backwards-compatible shim. New code should import directly from `controller`.

The driver is selected via the `USE_MOCK_LEDS` environment variable in
`controller/__init__.py`.
"""
from . import LED_COUNT, apply_color, apply_fade, init_strip

GLOBAL_BRIGHTNESS = 31
SPI_SPEED_HZ = 12000000


def get_led_driver():
    return init_strip(), apply_color, apply_fade
