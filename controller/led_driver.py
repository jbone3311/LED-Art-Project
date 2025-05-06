from rpi_ws281x import PixelStrip, Color
import time
import math

LED_COUNT = 60
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 255
LED_INVERT = False

strip = None

def init_strip():
    global strip
    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS)
    strip.begin()
    return strip

def apply_color(strip, color):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(*color))
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