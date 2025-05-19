import json
from controller.led_driver import apply_color, apply_fade

def apply_scene(strip, scene_data):
    steps = scene_data.get("steps", [])
    last = scene_data.get("last", steps[0]["color"] if steps else [0,0,0])
    for step in steps:
        color = step["color"]
        duration = step.get("duration", 2)
        apply_fade(strip, last, color, duration)
        last = color
