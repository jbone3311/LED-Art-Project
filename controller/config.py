import os

# Configuration for LED driver
USE_MOCK_DRIVER = True  # Set to False to use real hardware

# LED strip configuration
LED_COUNT = 144
GLOBAL_BRIGHTNESS = 31
SPI_SPEED_HZ = 12000000

def get_led_driver():
    """
    Returns the appropriate LED driver based on configuration.
    """
    if USE_MOCK_DRIVER:
        from .mock_led_driver import init_strip, apply_color, apply_fade
    else:
        from .led_driver import init_strip, apply_color, apply_fade
    
    return init_strip(), apply_color, apply_fade 