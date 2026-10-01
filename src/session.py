import sys
from collections.abc import Callable

import pygame

from maplist import require_maps
from picker import Picker
from simulation import MapError, Simulation, load_simulation
from viewer import Viewer, open_window


def choose_map() -> str | None:
    """Open the map list on its own; return the chosen map, or None if quit."""
    paths = require_maps()
    screen = open_window()
    pygame.display.set_caption("Fly-in - choose a map")
    try:
        return Picker(screen, paths).run()
    finally:
        pygame.quit()


def run_session(
    first_map: str | None, show_plan: Callable[[Simulation], None]
) -> None:
    """Loop between the map list and the viewer until the user quits.

    How a plan is printed is the entry point's business, not this module's,
    so the printer is handed in: that is what keeps every decision about what
    reaches the terminal in one file.

    The two screens take turns owning one pygame window. Creating a second
    window - or re-creating this one - makes SDL tear the window down and
    rebuild it, which a tiling Wayland compositor shows as the window
    closing and reopening.
    """
    paths = require_maps()
    screen = open_window()
    chosen = first_map
    last_seen = first_map or paths[0]

    try:
        while True:
            if chosen is None:
                pygame.display.set_caption("Fly-in - choose a map")
                picker = Picker(screen, paths)
                picker.select(last_seen)
                chosen = picker.run()
                if chosen is None:
                    return
            last_seen = chosen

            try:
                data, simulation = load_simulation(chosen)
            except MapError as exc:
                print(f"error: {exc}", file=sys.stderr)
                chosen = None
                continue

            print(f"--- {chosen} ---")
            show_plan(simulation)

            pygame.display.set_caption(f"Fly-in - {chosen}")
            if Viewer(screen, data, simulation).run() == "quit":
                return
            chosen = None
    finally:
        pygame.quit()
