import pygame
import math
from typing import Tuple, Optional, List, Dict
import sys
import time

class MockLEDStrip:
    def __init__(self, num_led: int = 144, global_brightness: int = 31, bus_speed_hz: int = 12000000, shape: str = "line"):
        # Validate parameters
        if num_led <= 0:
            raise ValueError("Number of LEDs must be positive")
        if not 0 <= global_brightness <= 31:
            raise ValueError("Global brightness must be between 0 and 31")
        if bus_speed_hz <= 0:
            raise ValueError("Bus speed must be positive")
        if shape not in ["line", "square", "rectangle", "circle", "triangle"]:
            raise ValueError("Shape must be one of: line, square, rectangle, circle, triangle")
            
        self.num_led = num_led
        self.global_brightness = global_brightness
        self.bus_speed_hz = bus_speed_hz
        self.shape = shape
        self.pixels = [(0, 0, 0) for _ in range(num_led)]
        
        # Set default display parameters
        self.pixel_size = 20  # Default pixel size
        self.pixel_spacing = 2  # Default spacing
        self.shape_size = 70  # Default shape size percentage
        self.show_numbers = False  # Default to not showing numbers
        
        # Animation control
        self.animation_speed = 1.0  # Speed multiplier for animations
        self.last_update = 0  # For timing animations
        
        # Add title and narrative attributes
        self.title = ""
        self.narrative = ""
        
        # Add window state tracking
        self.window_open = False
        self.pygame_initialized = False
        
        # Set default screen dimensions
        self.screen_width = 1200
        self.screen_height = 800
        
        # Shape-specific LED counts
        self.shape_counts = {
            "line": {"length": num_led},
            "square": {"side": int(math.sqrt(num_led))},
            "rectangle": {"width": int(math.sqrt(num_led * 1.618)), "height": int(num_led / math.sqrt(num_led * 1.618))},
            "circle": {"total": num_led},
            "triangle": {"side": num_led // 3}
        }
        
        # Create sliders before calculating positions
        self.sliders = self._create_sliders()
        # Calculate positions
        self.positions = self._calculate_positions()

    def _init_pygame(self):
        """Initialize Pygame if not already initialized"""
        if not self.pygame_initialized:
            try:
                pygame.init()
                self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
                pygame.display.set_caption("LED Strip Simulation")
                
                # Font for displaying information
                self.font = pygame.font.Font(None, 36)  # Larger font for title
                self.narrative_font = pygame.font.Font(None, 24)  # Font for narrative
                self.small_font = pygame.font.Font(None, 20)
                
                # Create UI elements
                self.buttons = self._create_buttons()
                self.checkboxes = self._create_checkboxes()
                
                self.pygame_initialized = True
                self.window_open = True
                
            except pygame.error as e:
                print(f"Error initializing Pygame: {e}")
                return False
        return True

    def _create_buttons(self) -> Dict:
        buttons = {}
        button_width = 120
        button_height = 35
        spacing = 15
        start_x = 20  # Start from left side
        start_y = self.screen_height - button_height - 20  # Bottom of screen
        
        # Shape selection buttons
        shapes = ["line", "square", "rectangle", "circle", "triangle"]
        for i, shape in enumerate(shapes):
            x = start_x + (button_width + spacing) * i
            buttons[shape] = {
                "rect": pygame.Rect(x, start_y, button_width, button_height),
                "active": False,  # Track if button is being clicked
                "last_click": 0   # Track when button was last clicked
            }
            
        return buttons

    def _create_sliders(self) -> Dict:
        sliders = {}
        slider_width = 150
        slider_height = 20
        spacing = 30
        start_x = 20  # Start from left side
        start_y = self.screen_height - 100  # Above buttons
        
        # Display adjustment sliders
        sliders["pixel_size"] = {
            "rect": pygame.Rect(start_x, start_y, slider_width, slider_height),
            "value": self.pixel_size,
            "min": 1,
            "max": 40,
            "label": "Pixel Size"
        }
        sliders["pixel_spacing"] = {
            "rect": pygame.Rect(start_x + slider_width + spacing, start_y, slider_width, slider_height),
            "value": self.pixel_spacing,
            "min": 0,
            "max": 10,
            "label": "Spacing"
        }
        sliders["brightness"] = {
            "rect": pygame.Rect(start_x + (slider_width + spacing) * 2, start_y, slider_width, slider_height),
            "value": self.global_brightness,
            "min": 0,
            "max": 31,
            "label": "Brightness"
        }
        sliders["shape_size"] = {
            "rect": pygame.Rect(start_x + (slider_width + spacing) * 3, start_y, slider_width, slider_height),
            "value": self.shape_size,
            "min": 20,
            "max": 80,
            "label": "Size"
        }
        sliders["led_count"] = {
            "rect": pygame.Rect(start_x + (slider_width + spacing) * 4, start_y, slider_width, slider_height),
            "value": self.num_led,
            "min": 1,
            "max": 300,
            "label": "LED Count"
        }
        
        return sliders

    def _create_checkboxes(self) -> Dict:
        checkboxes = {}
        checkbox_size = 20
        spacing = 10
        start_x = 20  # Start from left side
        start_y = self.screen_height - 150  # Above sliders
        
        # Show numbers checkbox
        checkboxes["show_numbers"] = {
            "rect": pygame.Rect(start_x, start_y, checkbox_size, checkbox_size),
            "checked": self.show_numbers,
            "label": "Show LED Numbers"
        }
        
        return checkboxes

    def _calculate_positions(self) -> List[Tuple[int, int]]:
        positions = []
        center_x = self.screen_width // 2
        center_y = self.screen_height // 2
        
        # Get shape size percentage from slider
        shape_size_percent = self.sliders["shape_size"]["value"] / 100.0
        
        # Calculate total size including spacing
        total_size = self.pixel_size + self.pixel_spacing
        
        if self.shape == "line":
            # Calculate total width based on shape size percentage
            total_width = min(self.screen_width, self.screen_height) * shape_size_percent
            start_x = (self.screen_width - total_width) // 2
            
            # Calculate spacing to fit all LEDs
            spacing = total_width / (self.num_led - 1) if self.num_led > 1 else 0
            
            # Ensure minimum spacing
            min_spacing = total_size
            if spacing < min_spacing:
                # Adjust total width to accommodate minimum spacing
                total_width = min_spacing * (self.num_led - 1)
                start_x = (self.screen_width - total_width) // 2
                spacing = min_spacing
            
            for i in range(self.num_led):
                x = start_x + i * spacing
                positions.append((int(x), center_y))
                
        elif self.shape == "square":
            # Calculate the size of the square
            square_size = min(self.screen_width, self.screen_height) * shape_size_percent
            
            # Calculate how many LEDs we can fit on each side
            leds_per_side = self.num_led // 4
            remaining_leds = self.num_led % 4
            
            # Calculate the spacing between LEDs
            if leds_per_side > 1:
                spacing = square_size / (leds_per_side - 1)
            else:
                spacing = square_size
            
            # Calculate the starting position (top-left corner)
            start_x = center_x - square_size // 2
            start_y = center_y - square_size // 2
            
            # Place LEDs around the square
            # Top edge (left to right)
            for i in range(leds_per_side):
                x = start_x + (i * spacing)
                positions.append((int(x), int(start_y)))
            
            # Right edge (top to bottom)
            for i in range(leds_per_side):
                y = start_y + (i * spacing)
                positions.append((int(start_x + square_size), int(y)))
            
            # Bottom edge (right to left)
            for i in range(leds_per_side):
                x = start_x + square_size - (i * spacing)
                positions.append((int(x), int(start_y + square_size)))
            
            # Left edge (bottom to top)
            for i in range(leds_per_side):
                y = start_y + square_size - (i * spacing)
                positions.append((int(start_x), int(y)))
            
            # Add any remaining LEDs to the top edge
            for i in range(remaining_leds):
                x = start_x + ((leds_per_side + i) * spacing)
                positions.append((int(x), int(start_y)))
            
            # Ensure we have exactly the requested number of LEDs
            if len(positions) > self.num_led:
                positions = positions[:self.num_led]
            elif len(positions) < self.num_led:
                # Add any missing LEDs to the top edge
                while len(positions) < self.num_led:
                    x = start_x + (len(positions) * spacing)
                    positions.append((int(x), int(start_y)))
            
            # Debug output
            print(f"Square debug:")
            print(f"Square size: {square_size}")
            print(f"LEDs per side: {leds_per_side}")
            print(f"Spacing: {spacing}")
            print(f"Start position: ({start_x}, {start_y})")
            print(f"Total positions: {len(positions)}")
            
        elif self.shape == "rectangle":
            # Calculate total size based on shape size percentage
            total_width = min(self.screen_width, self.screen_height) * shape_size_percent
            total_height = total_width * 0.6  # Make rectangle 60% as tall as wide
            
            # Calculate LEDs per side based on perimeter length
            perimeter = 2 * (total_width + total_height)
            leds_per_side = {
                "top": int(self.num_led * total_width / perimeter),
                "right": int(self.num_led * total_height / perimeter),
                "bottom": int(self.num_led * total_width / perimeter),
                "left": int(self.num_led * total_height / perimeter)
            }
            
            # Adjust to use all LEDs
            remaining_leds = self.num_led - sum(leds_per_side.values())
            leds_per_side["top"] += remaining_leds
            
            # Calculate spacing for each side
            spacing_x = total_width / (leds_per_side["top"] - 1) if leds_per_side["top"] > 1 else 0
            spacing_y = total_height / (leds_per_side["right"] - 1) if leds_per_side["right"] > 1 else 0
            
            # Ensure minimum spacing
            min_spacing = total_size
            if spacing_x < min_spacing or spacing_y < min_spacing:
                # Adjust dimensions to accommodate minimum spacing
                if spacing_x < min_spacing:
                    total_width = min_spacing * (leds_per_side["top"] - 1)
                    spacing_x = min_spacing
                if spacing_y < min_spacing:
                    total_height = min_spacing * (leds_per_side["right"] - 1)
                    spacing_y = min_spacing
            
            start_x = center_x - total_width // 2
            start_y = center_y - total_height // 2
            
            # Distribute LEDs around the rectangle
            # Top edge
            for i in range(leds_per_side["top"]):
                x = start_x + i * spacing_x
                positions.append((int(x), start_y))
            
            # Right edge
            for i in range(leds_per_side["right"]):
                y = start_y + i * spacing_y
                positions.append((start_x + total_width, int(y)))
            
            # Bottom edge
            for i in range(leds_per_side["bottom"]):
                x = start_x + total_width - i * spacing_x
                positions.append((int(x), start_y + total_height))
            
            # Left edge
            for i in range(leds_per_side["left"]):
                y = start_y + total_height - i * spacing_y
                positions.append((start_x, int(y)))
                    
        elif self.shape == "circle":
            # Calculate radius based on shape size percentage
            radius = min(self.screen_width, self.screen_height) * shape_size_percent / 2
            
            # Calculate minimum angle between LEDs to prevent overlap
            circumference = 2 * math.pi * radius
            min_spacing = total_size
            min_angle = 2 * math.pi * min_spacing / circumference
            angle_step = max(min_angle, 2 * math.pi / self.num_led)
            
            # Adjust radius if needed to fit all LEDs
            if angle_step > 2 * math.pi / self.num_led:
                radius = (min_spacing * self.num_led) / (2 * math.pi)
            
            for i in range(self.num_led):
                angle = i * angle_step
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                positions.append((int(x), int(y)))
                
        elif self.shape == "triangle":
            # Calculate total size based on shape size percentage
            height = min(self.screen_width, self.screen_height) * shape_size_percent / 2
            side_length = height * 2 / math.sqrt(3)
            
            # Calculate vertices
            top = (center_x, center_y - height // 2)
            left = (center_x - side_length // 2, center_y + height // 2)
            right = (center_x + side_length // 2, center_y + height // 2)
            
            # Calculate LEDs per side
            leds_per_side = self.num_led // 3
            remaining_leds = self.num_led % 3
            
            # Calculate minimum spacing
            min_spacing = total_size
            
            # Calculate side lengths
            side_lengths = {
                "top_left": math.sqrt((left[0] - top[0])**2 + (left[1] - top[1])**2),
                "left_right": math.sqrt((right[0] - left[0])**2 + (right[1] - left[1])**2),
                "right_top": math.sqrt((top[0] - right[0])**2 + (top[1] - right[1])**2)
            }
            
            # Adjust side lengths if needed to accommodate minimum spacing
            total_perimeter = sum(side_lengths.values())
            if total_perimeter < min_spacing * self.num_led:
                scale_factor = (min_spacing * self.num_led) / total_perimeter
                height *= scale_factor
                side_length *= scale_factor
                # Recalculate vertices
                top = (center_x, center_y - height // 2)
                left = (center_x - side_length // 2, center_y + height // 2)
                right = (center_x + side_length // 2, center_y + height // 2)
            
            # Distribute LEDs along the sides
            current_led = 0
            for side in ["top_left", "left_right", "right_top"]:
                leds_this_side = leds_per_side + (1 if remaining_leds > 0 else 0)
                remaining_leds -= 1
                
                for i in range(leds_this_side):
                    pos = i / (leds_this_side - 1) if leds_this_side > 1 else 0
                    
                    if side == "top_left":
                        x = top[0] + (left[0] - top[0]) * pos
                        y = top[1] + (left[1] - top[1]) * pos
                    elif side == "left_right":
                        x = left[0] + (right[0] - left[0]) * pos
                        y = left[1] + (right[1] - left[1]) * pos
                    else:  # right_top
                        x = right[0] + (top[0] - right[0]) * pos
                        y = right[1] + (top[1] - right[1]) * pos
                    
                    positions.append((int(x), int(y)))
                    current_led += 1
        
        return positions

    def _update_led_count(self):
        if self.shape == "line":
            self.num_led = self.shape_counts["line"]["length"]
        elif self.shape == "square":
            side = self.shape_counts["square"]["side"]
            self.num_led = side * side
        elif self.shape == "rectangle":
            width = self.shape_counts["rectangle"]["width"]
            height = self.shape_counts["rectangle"]["height"]
            self.num_led = width * height
        elif self.shape == "circle":
            self.num_led = self.shape_counts["circle"]["total"]
        elif self.shape == "triangle":
            self.num_led = self.shape_counts["triangle"]["side"] * 3
            
        self.pixels = [(0, 0, 0) for _ in range(self.num_led)]
        self.positions = self._calculate_positions()

    def _handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()
        current_time = time.time()
        
        # Handle shape selection buttons
        for shape, button_data in self.buttons.items():
            rect = button_data["rect"]
            if rect.collidepoint(mouse_pos):
                if mouse_pressed[0] and not button_data["active"]:
                    # Button is being clicked
                    button_data["active"] = True
                    button_data["last_click"] = current_time
                    self.shape = shape
                    self.sliders = self._create_sliders()
                    self.positions = self._calculate_positions()
                    return True
                elif not mouse_pressed[0] and button_data["active"]:
                    # Button was released
                    button_data["active"] = False
            elif not mouse_pressed[0] and button_data["active"]:
                # Mouse moved away while clicking
                button_data["active"] = False
        
        # Handle checkboxes
        for name, checkbox in self.checkboxes.items():
            if checkbox["rect"].collidepoint(mouse_pos) and mouse_pressed[0]:
                # Toggle the checkbox state
                self.show_numbers = not self.show_numbers
                checkbox["checked"] = self.show_numbers
                # Update the checkbox in the dictionary
                self.checkboxes[name] = checkbox
                return True
        
        # Handle sliders
        for name, slider in self.sliders.items():
            if slider["rect"].collidepoint(mouse_pos) and mouse_pressed[0]:
                # Calculate new value based on mouse position
                rel_x = mouse_pos[0] - slider["rect"].x
                value_range = slider["max"] - slider["min"]
                new_value = int(slider["min"] + (rel_x / slider["rect"].width) * value_range)
                new_value = max(slider["min"], min(slider["max"], new_value))
                
                if new_value != slider["value"]:
                    slider["value"] = new_value
                    if name == "pixel_size":
                        self.pixel_size = new_value
                    elif name == "pixel_spacing":
                        self.pixel_spacing = new_value
                    elif name == "brightness":
                        self.global_brightness = new_value
                    elif name == "shape_size":
                        self.shape_size = new_value
                    elif name == "led_count":
                        self.num_led = new_value
                        self.pixels = [(0, 0, 0) for _ in range(new_value)]
                    
                    # Recalculate positions whenever any slider changes
                    self.positions = self._calculate_positions()
                    return True
        
        return False

    def set_pixel(self, index: int, r: int, g: int, b: int):
        """Set a single pixel's color"""
        if 0 <= index < self.num_led:
            # Validate color values
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            
            # Apply global brightness
            brightness_factor = self.global_brightness / 31
            self.pixels[index] = (
                int(r * brightness_factor),
                int(g * brightness_factor),
                int(b * brightness_factor)
            )
            # Force display update
            self.show()

    def show(self):
        """Update the display and handle events"""
        if not self.window_open:
            return True
            
        try:
            if not self.pygame_initialized:
                if not self._init_pygame():
                    return False
            
            # Handle Pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.window_open = False
                    pygame.quit()
                    self.pygame_initialized = False
                    return False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.window_open = False
                        pygame.quit()
                        self.pygame_initialized = False
                        return False
            
            # Handle UI interactions
            self._handle_events()
            
            # Clear screen
            self.screen.fill((0, 0, 0))
            
            # Draw each LED with consistent spacing
            for i, (color, (x, y)) in enumerate(zip(self.pixels, self.positions)):
                # Calculate the total size including spacing
                total_size = self.pixel_size + self.pixel_spacing
                
                # Draw the LED as a square
                size = max(1, self.pixel_size)
                pygame.draw.rect(self.screen, color, 
                               (x - size//2, y - size//2, 
                                size, size))
                # Draw spacing rectangle
                pygame.draw.rect(self.screen, (30, 30, 30),
                               (x - total_size//2, y - total_size//2,
                                total_size, total_size), 1)
                
                # Draw LED number if enabled
                if self.show_numbers:
                    text = self.small_font.render(str(i), True, (255, 255, 255))
                    self.screen.blit(text, (x + size//2, y + size//2))
            
            # Draw UI elements
            self._draw_ui()
            
            # Update display
            pygame.display.flip()
            
            # Small delay to prevent high CPU usage
            pygame.time.delay(10)
            
            return self.window_open
            
        except pygame.error as e:
            print(f"Error in show(): {e}")
            self.window_open = False
            self.pygame_initialized = False
            return False

    def _draw_ui(self):
        # Draw a semi-transparent background for controls
        control_bg = pygame.Surface((self.screen_width, 120))
        control_bg.set_alpha(200)
        control_bg.fill((0, 0, 0))
        self.screen.blit(control_bg, (0, self.screen_height - 120))
        
        # Draw title at the top
        if self.title:
            title_surface = self.font.render(self.title, True, (255, 255, 255))
            title_rect = title_surface.get_rect(center=(self.screen_width // 2, 30))
            self.screen.blit(title_surface, title_rect)
        
        # Draw narrative at the bottom
        if self.narrative:
            narrative_surface = self.narrative_font.render(self.narrative, True, (255, 255, 255))
            narrative_rect = narrative_surface.get_rect(center=(self.screen_width // 2, self.screen_height - 60))
            self.screen.blit(narrative_surface, narrative_rect)
        
        # Draw shape selection buttons with visual feedback
        for shape, button_data in self.buttons.items():
            rect = button_data["rect"]
            # Calculate button color based on state
            if shape == self.shape:
                color = (150, 150, 150)  # Selected
            elif button_data["active"]:
                color = (200, 200, 200)  # Being clicked
            else:
                color = (100, 100, 100)  # Normal
            
            pygame.draw.rect(self.screen, color, rect)
            text = self.font.render(shape.capitalize(), True, (255, 255, 255))
            text_rect = text.get_rect(center=rect.center)
            self.screen.blit(text, text_rect)
        
        # Draw checkboxes
        for name, checkbox in self.checkboxes.items():
            # Draw checkbox background
            pygame.draw.rect(self.screen, (50, 50, 50), checkbox["rect"])
            if checkbox["checked"]:
                # Draw a checkmark or filled box when checked
                pygame.draw.rect(self.screen, (100, 100, 100), checkbox["rect"].inflate(-4, -4))
            
            # Draw checkbox label
            text = self.small_font.render(checkbox["label"], True, (255, 255, 255))
            self.screen.blit(text, (checkbox["rect"].right + 10, checkbox["rect"].y))
        
        # Draw sliders
        for name, slider in self.sliders.items():
            # Draw slider background
            pygame.draw.rect(self.screen, (50, 50, 50), slider["rect"])
            
            # Draw slider value
            value_rect = pygame.Rect(
                slider["rect"].x,
                slider["rect"].y,
                (slider["value"] - slider["min"]) / (slider["max"] - slider["min"]) * slider["rect"].width,
                slider["rect"].height
            )
            pygame.draw.rect(self.screen, (100, 100, 100), value_rect)
            
            # Draw slider label and value
            label = f"{slider['label']}: {slider['value']}"
            text = self.small_font.render(label, True, (255, 255, 255))
            self.screen.blit(text, (slider["rect"].x, slider["rect"].y - 20))
        
        # Draw information at the top of the screen
        info_text = f"Total LEDs: {self.num_led} | Shape: {self.shape.capitalize()} | Brightness: {self.global_brightness}"
        text_surface = self.font.render(info_text, True, (255, 255, 255))
        self.screen.blit(text_surface, (20, 20))
    
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.window_open:
                pygame.quit()
                self.window_open = False
        except:
            pass  # Ignore cleanup errors

    def set_animation_speed(self, speed: float):
        """Set the animation speed multiplier (1.0 is normal speed)"""
        self.animation_speed = max(0.1, min(10.0, speed))

    def get_led_positions(self) -> List[Tuple[int, int]]:
        """Get the current positions of all LEDs"""
        return self.positions.copy()

    def get_led_count(self) -> int:
        """Get the total number of LEDs"""
        return self.num_led

    def get_shape(self) -> str:
        """Get the current shape"""
        return self.shape

    def set_shape(self, shape: str):
        """Set the shape and recalculate positions"""
        if shape in ["line", "square", "rectangle", "circle", "triangle"]:
            self.shape = shape
            self.positions = self._calculate_positions()

    def set_brightness(self, brightness: int):
        """Set the global brightness (0-31)"""
        if 0 <= brightness <= 31:
            self.global_brightness = brightness
            self.sliders["brightness"]["value"] = brightness

    def set_pixel_size(self, size: int):
        """Set the pixel size (10-40)"""
        if 10 <= size <= 40:
            self.pixel_size = size
            self.sliders["pixel_size"]["value"] = size
            self.positions = self._calculate_positions()

    def set_pixel_spacing(self, spacing: int):
        """Set the pixel spacing (0-10)"""
        if 0 <= spacing <= 10:
            self.pixel_spacing = spacing
            self.sliders["pixel_spacing"]["value"] = spacing
            self.positions = self._calculate_positions()

    def set_shape_size(self, size: int):
        """Set the shape size percentage (20-80)"""
        if 20 <= size <= 80:
            self.shape_size = size
            self.sliders["shape_size"]["value"] = size
            self.positions = self._calculate_positions()

    def set_title(self, title):
        """Set the title to display at the top of the window"""
        self.title = title
        pygame.display.set_caption(f"LED Strip Simulation - {title}")

    def set_narrative(self, narrative):
        """Set the narrative text to display at the bottom"""
        self.narrative = narrative

    def open_window(self):
        """Open the Pygame window"""
        if not self.window_open:
            self.window_open = True
            return self.show()
        return True

def init_strip(num_led: int = 144, shape: str = "line"):
    """Initialize a new LED strip"""
    return MockLEDStrip(num_led=num_led, shape=shape)

def apply_color(strip, color):
    """Apply a color to all LEDs"""
    r, g, b = color
    for i in range(strip.num_led):
        strip.set_pixel(i, r, g, b)
    strip.show()

def apply_fade(strip, start_color, end_color, duration, should_cancel=None):
    """Fade from start color to end color. Aborts early if should_cancel() is True."""
    steps = 100
    delay = duration / steps if steps else 0
    for i in range(steps + 1):
        if should_cancel is not None and should_cancel():
            return
        t = i / steps
        eased = 0.5 - 0.5 * math.cos(t * math.pi)
        intermediate = [
            int(start_color[j] + (end_color[j] - start_color[j]) * eased)
            for j in range(3)
        ]
        apply_color(strip, intermediate)
        pygame.time.delay(int(delay * 1000))  # Convert to milliseconds
