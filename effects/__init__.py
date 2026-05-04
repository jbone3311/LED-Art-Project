import math
import random
import threading
import time

from controller import LED_COUNT, apply_color, apply_fade

# Cooperative cancellation. The web app sets this event to ask a running scene
# to abort; long sleeps inside effects/transitions check it via _sleep().
cancel_event = threading.Event()


def reset_cancel():
    cancel_event.clear()


def cancel():
    cancel_event.set()


def is_cancelled():
    return cancel_event.is_set()


def _sleep(duration):
    """Sleep for `duration` seconds, but wake early if cancellation is requested.

    Returns True if cancelled, False otherwise.
    """
    if duration <= 0:
        return is_cancelled()
    return cancel_event.wait(duration)


# --- Effects ---
def effect_solid(strip, color, duration=0, **kwargs):
    apply_color(strip, color)
    _sleep(duration)


def effect_gradient(strip, color_start, color_end, duration=0, **kwargs):
    steps = LED_COUNT
    for i in range(steps):
        t = i / (steps - 1) if steps > 1 else 0
        r = int(color_start[0] + (color_end[0] - color_start[0]) * t)
        g = int(color_start[1] + (color_end[1] - color_start[1]) * t)
        b = int(color_start[2] + (color_end[2] - color_start[2]) * t)
        strip.set_pixel(i, r, g, b)
    strip.show()
    _sleep(duration)


def effect_breathing(strip, base_color, cycle_s, duration, **kwargs):
    frame_s = 1 / 30
    frames_per_cycle = max(1, int(cycle_s * 30))
    total_frames = int(duration * 30)
    for i in range(total_frames):
        if is_cancelled():
            return
        t = (i % frames_per_cycle) / frames_per_cycle
        brightness = 0.5 + 0.5 * math.sin(2 * math.pi * t)
        apply_color(strip, [int(c * brightness) for c in base_color])
        if _sleep(frame_s):
            return


def effect_pulse(strip, color, speed, width_px, duration, **kwargs):
    frame_s = 1 / 30
    total_frames = int(duration * 30)
    half_width = max(1, int(width_px) // 2)
    for i in range(total_frames):
        if is_cancelled():
            return
        pos = int((i * speed / 30) % LED_COUNT)
        for j in range(LED_COUNT):
            if abs(j - pos) < half_width:
                strip.set_pixel(j, *color)
            else:
                strip.set_pixel(j, 0, 0, 0)
        strip.show()
        if _sleep(frame_s):
            return


def effect_strobe(strip, color, duty_cycle, tempo, duration, **kwargs):
    period = 1 / max(tempo, 0.01)
    on_time = period * duty_cycle
    off_time = period - on_time
    t_end = time.time() + duration
    while time.time() < t_end:
        if is_cancelled():
            return
        apply_color(strip, color)
        if _sleep(on_time):
            return
        apply_color(strip, [0, 0, 0])
        if _sleep(off_time):
            return


def effect_chase(strip, color, speed, duration, **kwargs):
    frame_s = 1 / 30
    total_frames = int(duration * 30)
    for i in range(total_frames):
        if is_cancelled():
            return
        pos = int((i * speed / 30) % LED_COUNT)
        for j in range(LED_COUNT):
            if j == pos:
                strip.set_pixel(j, *color)
            else:
                strip.set_pixel(j, 0, 0, 0)
        strip.show()
        if _sleep(frame_s):
            return


# --- Transitions ---
def transition_fade(strip, from_color, to_color, duration, **kwargs):
    apply_fade(strip, from_color, to_color, duration, should_cancel=is_cancelled)


def transition_instant(strip, from_color, to_color, duration=0, **kwargs):
    apply_color(strip, to_color)


def transition_wave(strip, from_color, to_color, duration, wavelength_px=20, speed=1, **kwargs):
    frame_s = 1 / 30
    steps = max(1, int(duration * 30))
    for t in range(steps):
        if is_cancelled():
            return
        for i in range(LED_COUNT):
            phase = 2 * math.pi * (i / wavelength_px - speed * t / steps)
            mix = 0.5 + 0.5 * math.sin(phase)
            color = [int(from_color[j] + (to_color[j] - from_color[j]) * mix) for j in range(3)]
            strip.set_pixel(i, *color)
        strip.show()
        if _sleep(frame_s):
            return


def transition_middle_out(strip, from_color, to_color, duration, **kwargs):
    frame_s = 1 / 30
    steps = max(1, int(duration * 30))
    mid = LED_COUNT // 2
    for t in range(steps):
        if is_cancelled():
            return
        spread = int((t / steps) * mid)
        for i in range(LED_COUNT):
            if abs(i - mid) <= spread:
                strip.set_pixel(i, *to_color)
            else:
                strip.set_pixel(i, *from_color)
        strip.show()
        if _sleep(frame_s):
            return


def transition_random_shimmer(strip, from_color, to_color, duration, jitter_pct=0.05, **kwargs):
    frame_s = 1 / 30
    steps = max(1, int(duration * 30))
    for t in range(steps):
        if is_cancelled():
            return
        mix = t / steps
        base = [int(from_color[j] + (to_color[j] - from_color[j]) * mix) for j in range(3)]
        for i in range(LED_COUNT):
            jitter = [
                min(255, max(0, int(c + random.uniform(-jitter_pct, jitter_pct) * 255)))
                for c in base
            ]
            strip.set_pixel(i, *jitter)
        strip.show()
        if _sleep(frame_s):
            return


def transition_patterned_fade(strip, from_color, to_color, duration, palette=None, step_s=1, **kwargs):
    if not palette:
        palette = [from_color, to_color]
    steps = max(1, int(duration / max(step_s, 0.01)))
    for i in range(steps):
        if is_cancelled():
            return
        apply_color(strip, palette[i % len(palette)])
        if _sleep(step_s):
            return
    apply_color(strip, to_color)


def transition_brightness_sweep(strip, from_color, to_color, duration, min_b=8, max_b=20, **kwargs):
    frame_s = 1 / 30
    steps = max(1, int(duration * 30))
    for t in range(steps):
        if is_cancelled():
            return
        brightness = int(min_b + (max_b - min_b) * 0.5 * (1 - math.cos(math.pi * t / steps)))
        color = [int(from_color[j] + (to_color[j] - from_color[j]) * (t / steps)) for j in range(3)]
        if hasattr(strip, 'set_global_brightness'):
            strip.set_global_brightness(brightness)
        apply_color(strip, color)
        if _sleep(frame_s):
            return
    if hasattr(strip, 'set_global_brightness'):
        strip.set_global_brightness(max_b)
    apply_color(strip, to_color)


# --- Registries (renamed to avoid shadowing the package name `effects`) ---
EFFECTS = {
    "solid": effect_solid,
    "gradient": effect_gradient,
    "breathing": effect_breathing,
    "pulse": effect_pulse,
    "strobe": effect_strobe,
    "chase": effect_chase,
}

TRANSITIONS = {
    "fade": transition_fade,
    "instant": transition_instant,
    "wave": transition_wave,
    "middle-out": transition_middle_out,
    "random_shimmer": transition_random_shimmer,
    "patterned_fade": transition_patterned_fade,
    "brightness_sweep": transition_brightness_sweep,
}


_STEP_RESERVED = {"effect", "transition", "transition_duration", "narrative", "step"}
_TRANSITION_RESERVED = {"effect", "duration", "narrative", "step"}


def effect_kwargs(step):
    """Return the step's params with bookkeeping fields stripped out."""
    return {k: v for k, v in step.items() if k not in _STEP_RESERVED}


def transition_kwargs(step):
    return {k: v for k, v in step.items() if k not in _TRANSITION_RESERVED}


def estimate_duration(steps):
    """Best-effort total runtime in seconds for a list of steps."""
    return int(sum(s.get("duration", 2) + s.get("transition_duration", 0) for s in steps))


def apply_scene(strip, scene_data, on_step=None):
    """Run a scene synchronously on the calling thread. Honors cancel_event.

    `on_step(idx, step)` is invoked (1-based idx) before each step's transition
    starts, giving callers a chance to update UI/status state.
    """
    steps = scene_data.get("steps", [])
    if not steps:
        return
    last = scene_data.get("last", steps[0].get("color", [0, 0, 0]))
    for idx, step in enumerate(steps, start=1):
        if is_cancelled():
            return
        if on_step is not None:
            on_step(idx, step)
        transition_name = step.get("transition", "fade")
        if transition_name != "instant":
            from_color = last
            to_color = step.get("color", step.get("color_start", last))
            transition_fn = TRANSITIONS.get(transition_name, transition_fade)
            transition_fn(
                strip,
                from_color,
                to_color,
                step.get("transition_duration", 2),
                **transition_kwargs(step),
            )
            if is_cancelled():
                return
        effect_name = step.get("effect", "solid")
        effect_fn = EFFECTS.get(effect_name, effect_solid)
        effect_fn(strip, **effect_kwargs(step))
        last = step.get("color", step.get("color_end", last))
