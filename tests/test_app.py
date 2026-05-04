"""End-to-end tests against the Flask app via test_client."""
import os

os.environ.setdefault("USE_MOCK_LEDS", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import sys  # noqa: E402
import time  # noqa: E402
import unittest  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app  # noqa: E402
import effects  # noqa: E402


class AppTestBase(unittest.TestCase):
    """Shared setUp/tearDown that resets state between tests so order doesn't
    leak running scenes or sticky brightness."""

    def setUp(self):
        self.app = app
        self.client = app.app.test_client()
        # Stop anything still running from a prior test, then reset.
        self.client.post("/stop")
        effects.reset_cancel()
        effects.resume()
        self.client.post("/brightness", json={"value": 31})
        self.client.post("/speed", json={"value": 1.0})
        self.client.post("/set_color", json={"color": [0, 0, 0]})

    def tearDown(self):
        self.client.post("/stop")
        effects.reset_cancel()
        effects.resume()


class StatusAndColorTests(AppTestBase):
    def test_status_idle_at_start(self):
        r = self.client.get("/status")
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        self.assertFalse(body["running"])
        self.assertFalse(body["paused"])

    def test_set_color_propagates_to_pixels(self):
        self.client.post("/set_color", json={"color": [123, 45, 67]})
        pixels = self.client.get("/pixels").get_json()
        self.assertEqual(pixels[0], [123, 45, 67])
        self.assertEqual(pixels[-1], [123, 45, 67])

    def test_off_blanks_pixels(self):
        self.client.post("/set_color", json={"color": [200, 100, 50]})
        self.client.post("/off")
        pixels = self.client.get("/pixels").get_json()
        self.assertEqual(pixels[0], [0, 0, 0])


class SceneLifecycleTests(AppTestBase):
    def test_apply_scene_then_stop(self):
        scene = {
            "name": "lifecycle",
            "steps": [
                {"effect": "solid", "color": [1, 1, 1], "duration": 30, "transition": "instant"},
            ],
        }
        r = self.client.post("/apply_scene", json=scene)
        self.assertEqual(r.status_code, 200)
        time.sleep(0.2)
        self.assertTrue(self.client.get("/status").get_json()["running"])

        r = self.client.post("/stop")
        self.assertEqual(r.status_code, 200)
        time.sleep(0.2)
        self.assertFalse(self.client.get("/status").get_json()["running"])

    def test_double_start_returns_409(self):
        scene = {"steps": [{"effect": "solid", "color": [0, 0, 0], "duration": 10, "transition": "instant"}]}
        self.client.post("/apply_scene", json=scene)
        time.sleep(0.1)
        try:
            r = self.client.post("/apply_scene", json=scene)
            self.assertEqual(r.status_code, 409)
        finally:
            self.client.post("/stop")

    def test_apply_scene_file_rejects_traversal(self):
        for bad in ("../etc/passwd", "/etc/passwd", "subdir/foo.json", "no_extension"):
            r = self.client.post("/apply_scene_file", json={"filename": bad})
            self.assertEqual(r.status_code, 400, f"expected 400 for {bad!r}")

    def test_apply_scene_file_404_for_unknown(self):
        r = self.client.post("/apply_scene_file", json={"filename": "does_not_exist.json"})
        self.assertEqual(r.status_code, 404)

    def test_run_effect_unknown_returns_400(self):
        r = self.client.post("/run_effect", json={"effect": "nonsense"})
        self.assertEqual(r.status_code, 400)


class PauseResumeTests(AppTestBase):
    def test_pause_and_resume_flip_status(self):
        scene = {"steps": [{"effect": "solid", "color": [0, 0, 0], "duration": 30, "transition": "instant"}]}
        self.client.post("/apply_scene", json=scene)
        time.sleep(0.1)
        self.client.post("/pause")
        time.sleep(0.1)
        self.assertTrue(self.client.get("/status").get_json()["paused"])
        self.client.post("/resume")
        time.sleep(0.1)
        self.assertFalse(self.client.get("/status").get_json()["paused"])

    def test_stop_releases_paused_worker(self):
        scene = {"steps": [{"effect": "solid", "color": [0, 0, 0], "duration": 30, "transition": "instant"}]}
        self.client.post("/apply_scene", json=scene)
        time.sleep(0.1)
        self.client.post("/pause")
        time.sleep(0.1)
        # Stop should NOT deadlock the join even though the worker is paused.
        t0 = time.time()
        r = self.client.post("/stop")
        elapsed = time.time() - t0
        self.assertEqual(r.status_code, 200)
        self.assertLess(elapsed, 2.0)


class BrightnessAndSpeedTests(AppTestBase):
    def test_brightness_out_of_range_400(self):
        for bad in (-1, 32, "abc", None):
            r = self.client.post("/brightness", json={"value": bad})
            self.assertEqual(r.status_code, 400, f"expected 400 for {bad!r}")

    def test_brightness_in_range_200_and_status_updates(self):
        r = self.client.post("/brightness", json={"value": 12})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.get("/status").get_json()["brightness"], 12)

    def test_speed_out_of_range_400(self):
        for bad in (0, -1, "abc"):
            r = self.client.post("/speed", json={"value": bad})
            self.assertEqual(r.status_code, 400, f"expected 400 for {bad!r}")

    def test_speed_in_range_200(self):
        r = self.client.post("/speed", json={"value": 2.5})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.get("/status").get_json()["speed"], 2.5)


class SaveSceneTests(AppTestBase):
    TEST_FILENAME = "_unittest_save.json"

    def tearDown(self):
        super().tearDown()
        path = os.path.join(self.app.SCENES_DIR, self.TEST_FILENAME)
        if os.path.exists(path):
            os.remove(path)

    def _scene(self):
        return {"name": "t", "steps": [{"effect": "solid", "color": [1, 2, 3], "duration": 1}]}

    def test_save_round_trip(self):
        r = self.client.post("/save_scene", json={"filename": self.TEST_FILENAME, "data": self._scene()})
        self.assertEqual(r.status_code, 200)
        names = [s["filename"] for s in self.client.get("/scenes").get_json()]
        self.assertIn(self.TEST_FILENAME, names)

    def test_save_overwrite_protection_then_force(self):
        scene = self._scene()
        self.client.post("/save_scene", json={"filename": self.TEST_FILENAME, "data": scene})
        r = self.client.post("/save_scene", json={"filename": self.TEST_FILENAME, "data": scene})
        self.assertEqual(r.status_code, 409)
        self.assertTrue(r.get_json().get("exists"))
        r = self.client.post(
            "/save_scene",
            json={"filename": self.TEST_FILENAME, "data": scene, "overwrite": True},
        )
        self.assertEqual(r.status_code, 200)

    def test_save_rejects_invalid_filename(self):
        for bad in ("../etc/passwd", "no_ext", "subdir/x.json", ".hidden.json"):
            r = self.client.post("/save_scene", json={"filename": bad, "data": self._scene()})
            self.assertEqual(r.status_code, 400, f"expected 400 for {bad!r}")

    def test_save_rejects_invalid_scene(self):
        r = self.client.post(
            "/save_scene",
            json={
                "filename": self.TEST_FILENAME,
                "data": {"steps": [{"effect": "nope", "duration": 1}]},
            },
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("warnings", r.get_json())


class PlaylistTests(AppTestBase):
    def test_list_playlists(self):
        r = self.client.get("/playlists")
        self.assertEqual(r.status_code, 200)
        items = r.get_json()
        self.assertIsInstance(items, list)
        # The bundled meditation_set.json should be present and parseable.
        names = [p["filename"] for p in items]
        self.assertIn("meditation_set.json", names)

    def test_apply_playlist_starts_run(self):
        r = self.client.post("/apply_playlist", json={"filename": "meditation_set.json"})
        self.assertEqual(r.status_code, 200)
        time.sleep(0.2)
        s = self.client.get("/status").get_json()
        self.assertTrue(s["running"])
        self.assertEqual(s["playlist"], "Meditation Set")
        self.assertEqual(s["playlist_total"], 3)
        self.assertGreaterEqual(s["playlist_step"], 1)
        self.client.post("/stop")

    def test_apply_playlist_rejects_traversal(self):
        r = self.client.post("/apply_playlist", json={"filename": "../etc/passwd"})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
