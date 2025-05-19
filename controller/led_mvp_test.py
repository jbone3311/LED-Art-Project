from apa102_pi.driver.apa102 import APA102
import colorsys
import time

NUM = 144  # Number of LEDs in your strip
strip = APA102(num_led=NUM, global_brightness=31, bus_speed_hz=12000000)
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
    # Turn off all LEDs on exit
    for i in range(NUM):
        strip.set_pixel(i, 0, 0, 0)
    strip.show()
    strip.cleanup() 