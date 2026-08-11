import os

# Force headless SDL backends before any test imports/initializes pygame,
# so running the suite never pops up a real window or touches audio.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
