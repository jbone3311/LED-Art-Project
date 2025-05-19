from apa102_pi.driver.apa102 import APA102
import time
import math

LED_COUNT = 144
GLOBAL_BRIGHTNESS = 31
SPI_SPEED_HZ = 12000000

strip = None

def init_strip():
    global strip
    strip = APA102(num_led=LED_COUNT, global_brightness=GLOBAL_BRIGHTNESS, bus_speed_hz=SPI_SPEED_HZ)
    return strip

def apply_color(strip, color):
    r, g, b = color
    for i in range(LED_COUNT):
        strip.set_pixel(i, r, g, b)
    strip.show()

def apply_fade(strip, start_color, end_color, duration):
    steps = 100
    delay = duration / steps
    for i in range(steps + 1):
        t = i / steps
        eased = 0.5 - 0.5 * math.cos(t * math.pi)
        intermediate = [
            int(start_color[j] + (end_color[j] - start_color[j]) * eased)
            for j in range(3)
        ]
        apply_color(strip, intermediate)
        time.sleep(delay)