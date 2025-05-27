import colorsys
import time
import sys
from mock_led_driver import init_strip, apply_color, apply_fade

def main():
    # Initialize the mock LED strip with default values
    strip = init_strip(num_led=144, shape="line")
    
    try:
        # Rainbow effect
        h = 0.0
        while True:
            # Convert HSV to RGB
            r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(h, 1, 1)]
            
            # Apply color to all LEDs
            apply_color(strip, (r, g, b))
            
            # Update hue
            h = (h + 0.002) % 1.0
            
            # Small delay
            time.sleep(0.01)
            
            # Check if window was closed
            if not strip.show():
                break
                
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        # Clean up
        apply_color(strip, (0, 0, 0))  # Turn off all LEDs
        strip.cleanup()

if __name__ == "__main__":
    main() 