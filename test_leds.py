import board
import neopixel
import time
import sys

print("Python version:", sys.version)
print("Board module available:", hasattr(board, 'D18'))

# LED strip configuration
LED_COUNT = 60
LED_PIN = board.D18
LED_BRIGHTNESS = 1.0  # Full brightness for testing
LED_ORDER = neopixel.GRB

def test_leds():
    print("\nStarting LED test...")
    print(f"LED Count: {LED_COUNT}")
    print(f"LED Pin: {LED_PIN}")
    print(f"Brightness: {LED_BRIGHTNESS}")
    print(f"Color Order: {LED_ORDER}")
    
    try:
        print("\nInitializing LED strip...")
        pixels = neopixel.NeoPixel(
            LED_PIN,
            LED_COUNT,
            brightness=LED_BRIGHTNESS,
            auto_write=True,  # Changed to True for immediate feedback
            pixel_order=LED_ORDER
        )
        
        print("\nTesting white color (all LEDs should be bright white)...")
        pixels.fill((255, 255, 255))
        time.sleep(2)
        
        print("\nTesting red color (all LEDs should be bright red)...")
        pixels.fill((255, 0, 0))
        time.sleep(2)
        
        print("\nTesting first LED only (first LED should be white, others off)...")
        pixels.fill((0, 0, 0))  # Turn all off
        pixels[0] = (255, 255, 255)  # Set first LED to white
        time.sleep(2)
        
        print("\nTurning all LEDs off...")
        pixels.fill((0, 0, 0))
        
        print("\nTest complete!")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        print("Error type:", type(e).__name__)
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    test_leds() 