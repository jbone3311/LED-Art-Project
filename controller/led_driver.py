import RPi.GPIO as GPIO
import time
import math

# LED strip configuration
LED_COUNT = 150        # Number of LED pixels (5m * 30 LEDs/m)
DATA_PIN = 18         # GPIO pin for data
CLOCK_PIN = 19        # GPIO pin for clock
LED_BRIGHTNESS = 0.5  # Set to 0.5 for half brightness (recommended for testing)

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(DATA_PIN, GPIO.OUT)
GPIO.setup(CLOCK_PIN, GPIO.OUT)

def send_byte(byte):
    """Send a single byte to the LED strip."""
    for _ in range(8):
        GPIO.output(CLOCK_PIN, GPIO.LOW)
        GPIO.output(DATA_PIN, GPIO.HIGH if byte & 0x80 else GPIO.LOW)
        GPIO.output(CLOCK_PIN, GPIO.HIGH)
        byte <<= 1

def init_strip():
    """Initialize the LED strip with proper configuration."""
    try:
        # Send start frame
        for _ in range(4):
            send_byte(0x00)
        
        # Clear all LEDs
        for _ in range(LED_COUNT):
            send_byte(0xFF)  # Brightness
            send_byte(0x00)  # Blue
            send_byte(0x00)  # Green
            send_byte(0x00)  # Red
        
        # Send end frame
        for _ in range(4):
            send_byte(0xFF)
        
        return True
    except Exception as e:
        print(f"Error initializing LED strip: {e}")
        raise

def apply_color(color):
    """Apply a single color to all pixels.
    
    Args:
        color: RGB color as a tuple (r, g, b)
    """
    try:
        # Send start frame
        for _ in range(4):
            send_byte(0x00)
        
        # Set all LEDs to the specified color
        brightness = int(31 * LED_BRIGHTNESS)  # Scale brightness to 0-31
        for _ in range(LED_COUNT):
            send_byte(0xE0 | brightness)  # Brightness (5 bits) + 3 bits of 1s
            send_byte(color[2])  # Blue
            send_byte(color[1])  # Green
            send_byte(color[0])  # Red
        
        # Send end frame
        for _ in range(4):
            send_byte(0xFF)
    except Exception as e:
        print(f"Error applying color: {e}")
        raise

def apply_fade(start_color, end_color, duration):
    """Fade smoothly between two colors.
    
    Args:
        start_color: Starting RGB color as tuple (r, g, b)
        end_color: Ending RGB color as tuple (r, g, b)
        duration: Duration of fade in seconds
    """
    try:
        steps = 100
        delay = duration / steps
        
        for i in range(steps + 1):
            t = i / steps
            # Use cosine easing for smooth transitions
            eased = 0.5 - 0.5 * math.cos(t * math.pi)
            intermediate = [
                int(start_color[j] + (end_color[j] - start_color[j]) * eased)
                for j in range(3)
            ]
            apply_color(intermediate)
            time.sleep(delay)
    except Exception as e:
        print(f"Error during fade: {e}")
        raise

def cleanup():
    """Clean up the LED strip (turn off all LEDs)."""
    try:
        apply_color((0, 0, 0))
        GPIO.cleanup()
    except Exception as e:
        print(f"Error during cleanup: {e}")
        raise