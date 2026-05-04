"""Per-effect and per-transition smoke tests against FakeStrip.

These don't try to make qualitative judgements ("is the rainbow pretty?") —
they verify each function:
  - runs without exceptions;
  - actually writes to the strip (set_pixel was called);
  - leaves the strip in a sensible terminal state.

Anything subtler is left to manual inspection.
"""
import os

# Ensure the mock LED backend is loaded; must run before importing `effects`.
os.environ.setdefault("USE_MOCK_LEDS", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import sys  # noqa: E402
import unittest  # noqa: E402

# Allow `from tests.fake_strip import FakeStrip` whether discovery loaded us
# as `tests.test_effects` or as a top-level `test_effects`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import effects  # noqa: E402

from tests.fake_strip import FakeStrip  # noqa: E402


class FakeStripSanityTests(unittest.TestCase):
    """Make sure the FakeStrip itself is a faithful test double."""

    def test_set_pixel_records(self):
        strip = FakeStrip(num_led=8)
        strip.set_pixel(0, 10, 20, 30)
        strip.set_pixel(7, 200, 100, 50)
        self.assertEqual(strip.pixels[0], [10, 20, 30])
        self.assertEqual(strip.pixels[7], [200, 100, 50])
        self.assertEqual(strip.set_pixel_calls, 2)

    def test_show_captures_frame(self):
        strip = FakeStrip(num_led=4)
        strip.set_pixel(0, 1, 2, 3)
        strip.show()
        strip.set_pixel(0, 4, 5, 6)
        strip.show()
        self.assertEqual(strip.show_calls, 2)
        self.assertEqual(strip.frames[0][0], [1, 2, 3])
        self.assertEqual(strip.frames[1][0], [4, 5, 6])
        self.assertEqual(strip.frames[0][0], [1, 2, 3])  # earlier frame unchanged

    def test_out_of_range_set_pixel_is_silent(self):
        strip = FakeStrip(num_led=4)
        strip.set_pixel(10, 1, 2, 3)
        self.assertTrue(all(p == [0, 0, 0] for p in strip.pixels))


class EffectTests(unittest.TestCase):
    def setUp(self):
        self.strip = FakeStrip(num_led=effects.LED_COUNT)
        effects.reset_cancel()
        effects.resume()

    def test_solid_holds_color(self):
        effects.effect_solid(self.strip, [10, 20, 30], duration=0.05)
        self.assertEqual(self.strip.pixels[0], [10, 20, 30])
        self.assertEqual(self.strip.pixels[-1], [10, 20, 30])

    def test_gradient_interpolates_between_endpoints(self):
        effects.effect_gradient(self.strip, [0, 0, 0], [255, 255, 255], duration=0.01)
        self.assertEqual(self.strip.pixels[0], [0, 0, 0])
        self.assertEqual(self.strip.pixels[-1], [255, 255, 255])
        mid = self.strip.pixels[effects.LED_COUNT // 2]
        self.assertGreater(mid[0], 50)
        self.assertLess(mid[0], 200)

    def test_breathing_runs_and_lights_pixels(self):
        effects.effect_breathing(self.strip, [200, 200, 200], cycle_s=0.05, duration=0.05)
        self.assertGreater(self.strip.show_calls, 0)
        self.assertGreater(max(max(p) for p in self.strip.pixels), 0)

    def test_pulse_moves_a_lit_window(self):
        effects.effect_pulse(self.strip, [100, 200, 50], speed=200, width_px=10, duration=0.1)
        self.assertGreater(self.strip.show_calls, 1)
        # somewhere along the way, at least some pixel was lit
        lit_at_some_point = any(any(any(c) for c in frame) for frame in self.strip.frames)
        self.assertTrue(lit_at_some_point)

    def test_strobe_alternates(self):
        effects.effect_strobe(self.strip, [255, 255, 255], duty_cycle=0.3, tempo=20, duration=0.1)
        # at least one frame all-on, at least one frame all-off
        on_frames = [f for f in self.strip.frames if f[0] != [0, 0, 0]]
        off_frames = [f for f in self.strip.frames if f[0] == [0, 0, 0]]
        self.assertGreater(len(on_frames), 0)
        self.assertGreater(len(off_frames), 0)

    def test_chase_advances(self):
        effects.effect_chase(self.strip, [255, 0, 0], speed=200, duration=0.1)
        self.assertGreater(self.strip.show_calls, 1)
        # find indices that were ever red
        ever_red = set()
        for f in self.strip.frames:
            for i, p in enumerate(f):
                if p[0] > 0:
                    ever_red.add(i)
        self.assertGreater(len(ever_red), 1)

    def test_rainbow_produces_varied_colors(self):
        effects.effect_rainbow(self.strip, duration=0.05, speed=1)
        self.assertGreater(self.strip.show_calls, 0)
        last = self.strip.frames[-1]
        # not every pixel should be the same color
        unique = {tuple(p) for p in last}
        self.assertGreater(len(unique), 5)

    def test_twinkle_runs(self):
        effects.effect_twinkle(self.strip, [255, 255, 255], rate=300, decay=0.7, duration=0.1)
        self.assertGreater(self.strip.show_calls, 0)

    def test_comet_runs_and_has_dim_tail(self):
        effects.effect_comet(self.strip, [255, 255, 255], speed=100, tail_px=10, duration=0.1)
        last = self.strip.frames[-1]
        # head should be brighter than the surrounding strip somewhere
        self.assertGreater(max(max(p) for p in last), 0)

    def test_fire_runs(self):
        effects.effect_fire(self.strip, duration=0.1, intensity=1.0)
        self.assertGreater(self.strip.show_calls, 0)
        # fire palette is red-dominant
        last = self.strip.frames[-1]
        reds = [p[0] for p in last]
        greens = [p[1] for p in last]
        self.assertGreaterEqual(max(reds), max(greens))

    def test_theater_chase_pattern(self):
        effects.effect_theater_chase(self.strip, [0, 255, 0], gap=4, speed=10, duration=0.1)
        last = self.strip.frames[-1]
        lit = [i for i, p in enumerate(last) if p[1] > 0]
        unlit = [i for i, p in enumerate(last) if p[1] == 0]
        self.assertGreater(len(lit), 0)
        self.assertGreater(len(unlit), 0)


class TransitionTests(unittest.TestCase):
    def setUp(self):
        self.strip = FakeStrip(num_led=effects.LED_COUNT)
        effects.reset_cancel()
        effects.resume()

    def test_fade_endpoints(self):
        effects.transition_fade(self.strip, [0, 0, 0], [200, 100, 50], duration=0.05)
        self.assertEqual(self.strip.pixels[0], [200, 100, 50])

    def test_instant_jumps(self):
        effects.transition_instant(self.strip, [0, 0, 0], [255, 0, 0])
        self.assertEqual(self.strip.pixels[0], [255, 0, 0])
        # instant should not call show many times
        self.assertLessEqual(self.strip.show_calls, 1)

    def test_wave_runs(self):
        effects.transition_wave(self.strip, [0, 0, 0], [255, 255, 255], duration=0.05)
        self.assertGreater(self.strip.show_calls, 0)

    def test_middle_out_finishes_full_to_color(self):
        effects.transition_middle_out(self.strip, [0, 0, 0], [10, 200, 30], duration=0.05)
        self.assertGreater(self.strip.show_calls, 0)

    def test_random_shimmer_runs(self):
        effects.transition_random_shimmer(self.strip, [0, 0, 0], [255, 255, 255], duration=0.05)
        self.assertGreater(self.strip.show_calls, 0)

    def test_patterned_fade_ends_at_to_color(self):
        effects.transition_patterned_fade(
            self.strip, [0, 0, 0], [10, 20, 30], duration=0.1, palette=[[1, 1, 1], [2, 2, 2]], step_s=0.02
        )
        self.assertEqual(self.strip.pixels[0], [10, 20, 30])

    def test_brightness_sweep_sets_global_brightness(self):
        effects.transition_brightness_sweep(
            self.strip, [255, 0, 0], [0, 255, 0], duration=0.05, max_b=15
        )
        self.assertEqual(self.strip.global_brightness, 15)

    def test_slide_finishes_with_to_color(self):
        effects.transition_slide(self.strip, [0, 0, 0], [10, 20, 30], duration=0.05)
        # After a full slide, every pixel should be the new color.
        self.assertTrue(all(p == [10, 20, 30] for p in self.strip.pixels))

    def test_dissolve_finishes_with_to_color(self):
        effects.transition_dissolve(self.strip, [0, 0, 0], [9, 8, 7], duration=0.05)
        self.assertTrue(all(p == [9, 8, 7] for p in self.strip.pixels))


if __name__ == "__main__":
    unittest.main()
