import json
import math
import random
import time
from controller.led_driver import apply_color, apply_fade, LED_COUNT

def effect_solid(strip, color, duration, **kwargs):
    apply_color(strip, color)
    time.sleep(duration)

def effect_gradient(strip, color_start, color_end, duration, **kwargs):
    steps = LED_COUNT
    for i in range(steps):
        t = i / (steps - 1)
        r = int(color_start[0] + (color_end[0] - color_start[0]) * t)
        g = int(color_start[1] + (color_end[1] - color_start[1]) * t)
        b = int(color_start[2] + (color_end[2] - color_start[2]) * t)
        strip.set_pixel(i, r, g, b)
    strip.show()
    time.sleep(duration)

def effect_breathing(strip, base_color, cycle_s, duration, **kwargs):
    steps = int(duration * 30)
    for i in range(steps):
        t = (i % int(cycle_s * 30)) / (cycle_s * 30)
        brightness = 0.5 + 0.5 * math.sin(2 * math.pi * t)
        color = [int(c * brightness) for c in base_color]
        apply_color(strip, color)
        time.sleep(1/30)

def effect_pulse(strip, color, speed, width_px, duration, **kwargs):
    steps = int(duration * 30)
    for i in range(steps):
        pos = int((i * speed / 30) % LED_COUNT)
        for j in range(LED_COUNT):
            if abs(j - pos) < width_px // 2:
                strip.set_pixel(j, *color)
            else:
                strip.set_pixel(j, 0, 0, 0)
        strip.show()
        time.sleep(1/30)

def effect_strobe(strip, color, duty_cycle, tempo, duration, **kwargs):
    period = 1 / max(tempo, 0.01)
    on_time = period * duty_cycle
    off_time = period - on_time
    t_end = time.time() + duration
    while time.time() < t_end:
        apply_color(strip, color)
        time.sleep(on_time)
        apply_color(strip, [0, 0, 0])
        time.sleep(off_time)

def effect_chase(strip, color, speed, duration, **kwargs):
    steps = int(duration * 30)
    for i in range(steps):
        pos = int((i * speed / 30) % LED_COUNT)
        for j in range(LED_COUNT):
            if j == pos:
                strip.set_pixel(j, *color)
            else:
                strip.set_pixel(j, 0, 0, 0)
        strip.show()
        time.sleep(1/30)

# --- Transitions ---
def transition_fade(strip, from_color, to_color, duration, **kwargs):
    apply_fade(strip, from_color, to_color, duration)

def transition_instant(strip, from_color, to_color, **kwargs):
    apply_color(strip, to_color)

def transition_wave(strip, from_color, to_color, duration, wavelength_px=20, speed=1, **kwargs):
    steps = int(duration * 30)
    for t in range(steps):
        for i in range(LED_COUNT):
            phase = 2 * math.pi * (i / wavelength_px - speed * t / steps)
            mix = 0.5 + 0.5 * math.sin(phase)
            color = [int(from_color[j] + (to_color[j] - from_color[j]) * mix) for j in range(3)]
            strip.set_pixel(i, *color)
        strip.show()
        time.sleep(1/30)

def transition_middle_out(strip, from_color, to_color, duration, **kwargs):
    steps = int(duration * 30)
    mid = LED_COUNT // 2
    for t in range(steps):
        spread = int((t / steps) * mid)
        for i in range(LED_COUNT):
            if abs(i - mid) <= spread:
                strip.set_pixel(i, *to_color)
            else:
                strip.set_pixel(i, *from_color)
        strip.show()
        time.sleep(1/30)

def transition_random_shimmer(strip, from_color, to_color, duration, jitter_pct=0.05, **kwargs):
    steps = int(duration * 30)
    for t in range(steps):
        for i in range(LED_COUNT):
            mix = t / steps
            base = [int(from_color[j] + (to_color[j] - from_color[j]) * mix) for j in range(3)]
            jitter = [min(255, max(0, int(c + random.uniform(-jitter_pct, jitter_pct) * 255))) for c in base]
            strip.set_pixel(i, *jitter)
        strip.show()
        time.sleep(1/30)

def transition_patterned_fade(strip, from_color, to_color, duration, palette=None, step_s=1, **kwargs):
    if not palette:
        palette = [from_color, to_color]
    steps = int(duration / step_s)
    for i in range(steps):
        color = palette[i % len(palette)]
        apply_color(strip, color)
        time.sleep(step_s)
    apply_color(strip, to_color)

def transition_brightness_sweep(strip, from_color, to_color, duration, min_b=8, max_b=20, **kwargs):
    steps = int(duration * 30)
    for t in range(steps):
        brightness = int(min_b + (max_b - min_b) * 0.5 * (1 - math.cos(math.pi * t / steps)))
        color = [int(from_color[j] + (to_color[j] - from_color[j]) * (t / steps)) for j in range(3)]
        # This assumes the strip object has a set_global_brightness method
        if hasattr(strip, 'set_global_brightness'):
            strip.set_global_brightness(brightness)
        apply_color(strip, color)
        time.sleep(1/30)
    if hasattr(strip, 'set_global_brightness'):
        strip.set_global_brightness(max_b)
    apply_color(strip, to_color)

# --- Effect and transition registry ---
effects = {
    "solid": effect_solid,
    "gradient": effect_gradient,
    "breathing": effect_breathing,
    "pulse": effect_pulse,
    "strobe": effect_strobe,
    "chase": effect_chase
}
transitions = {
    "fade": transition_fade,
    "instant": transition_instant,
    "wave": transition_wave,
    "middle-out": transition_middle_out,
    "random_shimmer": transition_random_shimmer,
    "patterned_fade": transition_patterned_fade,
    "brightness_sweep": transition_brightness_sweep
}

def apply_scene(strip, scene_data):
    steps = scene_data.get("steps", [])
    last = scene_data.get("last", steps[0].get("color", [0,0,0]) if steps else [0,0,0])
    for step in steps:
        effect_name = step.get("effect", "solid")
        effect = effects.get(effect_name, effect_solid)
        transition_name = step.get("transition", "fade")
        transition = transitions.get(transition_name, transition_fade)
        # Get effect/transition params
        effect_kwargs = {k: v for k, v in step.items() if k not in ("effect", "transition", "transition_duration")}
        transition_kwargs = {k: v for k, v in step.items() if k not in ("effect", "duration")}
        # Run transition from last to this effect's color
        if transition_name != "instant":
            from_color = last
            to_color = step.get("color", step.get("color_start", last))
            transition(strip, from_color, to_color, step.get("transition_duration", 2), **transition_kwargs)
        # Run effect
        effect(strip, **effect_kwargs)
        last = step.get("color", step.get("color_end", last))
