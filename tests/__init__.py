"""Tests run with the mock LED backend.

Using the real apa102-pi driver requires SPI hardware, so we set
USE_MOCK_LEDS=1 here so every test module that imports `effects` or `app`
gets the pygame-based mock. SDL_VIDEODRIVER=dummy keeps pygame headless.

Both must be set BEFORE the project modules are imported, which happens
the moment a test module is loaded; this package's __init__.py runs first
under unittest's test discovery.
"""
import os

os.environ.setdefault("USE_MOCK_LEDS", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
