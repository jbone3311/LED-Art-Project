import json
from controller.led_driver import apply_color, apply_fade

def apply_scene(strip, scene_data):
    steps = scene_data.get("steps", [])
    for step in steps:
        color = step["color"]
        duration = step.get("duration", 2)
        apply_fade(strip, scene_data.get("last", color), color, duration)
        scene_data["last"] = color
