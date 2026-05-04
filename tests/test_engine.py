"""Tests for the scene runner: cancellation, pause, speed, repeat, validation."""
import os

os.environ.setdefault("USE_MOCK_LEDS", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import sys  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
import unittest  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import effects  # noqa: E402

from tests.fake_strip import FakeStrip  # noqa: E402


def _long_solid_scene(duration=10):
    return {
        "name": "long",
        "steps": [
            {"effect": "solid", "color": [1, 2, 3], "duration": duration, "transition": "instant"},
        ],
    }


class CancelTests(unittest.TestCase):
    def setUp(self):
        effects.reset_cancel()
        effects.resume()

    def test_cancel_aborts_long_solid_promptly(self):
        strip = FakeStrip(num_led=effects.LED_COUNT)

        def trigger():
            time.sleep(0.05)
            effects.cancel()

        threading.Thread(target=trigger, daemon=True).start()
        t0 = time.time()
        effects.effect_solid(strip, [255, 255, 255], duration=10)
        elapsed = time.time() - t0
        self.assertLess(elapsed, 0.5, f"effect didn't abort, took {elapsed:.2f}s")

    def test_cancel_breaks_apply_scene_between_steps(self):
        strip = FakeStrip(num_led=effects.LED_COUNT)
        seen_steps = []

        def on_step(idx, step):
            seen_steps.append(idx)
            if idx == 1:
                effects.cancel()

        scene = {
            "steps": [
                {"effect": "solid", "color": [0, 0, 0], "duration": 0.05, "transition": "instant"},
                {"effect": "solid", "color": [0, 0, 0], "duration": 0.05, "transition": "instant"},
                {"effect": "solid", "color": [0, 0, 0], "duration": 0.05, "transition": "instant"},
            ],
        }
        effects.apply_scene(strip, scene, on_step=on_step)
        self.assertEqual(seen_steps, [1])


class PauseTests(unittest.TestCase):
    def setUp(self):
        effects.reset_cancel()
        effects.resume()

    def tearDown(self):
        effects.resume()
        effects.reset_cancel()

    def test_pause_holds_step_then_resume_completes(self):
        strip = FakeStrip(num_led=effects.LED_COUNT)
        scene = _long_solid_scene(duration=0.2)

        thread = threading.Thread(target=effects.apply_scene, args=(strip, scene), daemon=True)
        thread.start()
        time.sleep(0.05)
        effects.pause()
        # Wait longer than the step's natural duration. If pause doesn't park the
        # worker, the scene would have completed by now.
        time.sleep(0.4)
        self.assertTrue(thread.is_alive(), "scene completed while paused")
        effects.resume()
        thread.join(timeout=1)
        self.assertFalse(thread.is_alive(), "scene didn't complete after resume")


class SpeedAndRepeatTests(unittest.TestCase):
    def setUp(self):
        effects.reset_cancel()
        effects.resume()

    def test_speed_multiplier_shrinks_runtime(self):
        strip = FakeStrip(num_led=effects.LED_COUNT)
        scene = {
            "steps": [
                {"effect": "solid", "color": [0, 0, 0], "duration": 1.0, "transition": "instant"},
            ],
        }
        t0 = time.time()
        effects.apply_scene(strip, scene, speed=10.0)
        elapsed = time.time() - t0
        self.assertLess(elapsed, 0.5)
        self.assertGreater(elapsed, 0.05)

    def test_repeat_runs_n_times(self):
        strip = FakeStrip(num_led=effects.LED_COUNT)
        calls = []

        def on_step(idx, step):
            calls.append(idx)

        scene = {
            "steps": [
                {"effect": "solid", "color": [0, 0, 0], "duration": 0.01, "transition": "instant"},
            ],
        }
        effects.apply_scene(strip, scene, on_step=on_step, repeat=3)
        self.assertEqual(calls, [1, 1, 1])

    def test_repeat_forever_string_loops(self):
        strip = FakeStrip(num_led=effects.LED_COUNT)
        iterations = [0]

        def on_step(idx, step):
            iterations[0] += 1
            if iterations[0] >= 3:
                effects.cancel()

        scene = {
            "steps": [
                {"effect": "solid", "color": [0, 0, 0], "duration": 0.01, "transition": "instant"},
            ],
        }
        effects.apply_scene(strip, scene, on_step=on_step, repeat="forever")
        self.assertGreaterEqual(iterations[0], 3)


class EstimateDurationTests(unittest.TestCase):
    def test_simple_sum(self):
        steps = [
            {"effect": "solid", "duration": 5, "transition_duration": 2},
            {"effect": "solid", "duration": 3},  # default transition_duration assumed 0
        ]
        # 5 + 2 + 3 + 0 = 10
        self.assertEqual(effects.estimate_duration(steps), 10)

    def test_speed_divides(self):
        steps = [{"effect": "solid", "duration": 10}]
        self.assertEqual(effects.estimate_duration(steps, speed=2.0), 5)

    def test_speed_zero_does_not_divide_by_zero(self):
        steps = [{"effect": "solid", "duration": 10}]
        # Implementation clamps speed to >= 0.01
        self.assertGreater(effects.estimate_duration(steps, speed=0), 0)


class ValidateSceneTests(unittest.TestCase):
    def test_clean_scene_has_no_warnings(self):
        scene = {
            "steps": [
                {"effect": "solid", "color": [0, 0, 0], "duration": 1, "transition": "fade"},
                {"effect": "rainbow", "duration": 2, "transition": "slide"},
            ],
        }
        self.assertEqual(effects.validate_scene(scene), [])

    def test_unknown_effect_flagged(self):
        scene = {"steps": [{"effect": "nonsense", "duration": 1}]}
        warnings = effects.validate_scene(scene)
        self.assertEqual(len(warnings), 1)
        self.assertIn("nonsense", warnings[0])

    def test_unknown_transition_flagged(self):
        scene = {"steps": [{"effect": "solid", "transition": "warp", "duration": 1}]}
        warnings = effects.validate_scene(scene)
        self.assertEqual(len(warnings), 1)
        self.assertIn("warp", warnings[0])

    def test_empty_steps_flagged(self):
        self.assertEqual(effects.validate_scene({"steps": []}), ["scene has no steps"])
        self.assertEqual(effects.validate_scene({}), ["scene has no steps"])

    def test_non_dict_step_flagged(self):
        warnings = effects.validate_scene({"steps": ["nope"]})
        self.assertTrue(any("not an object" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
