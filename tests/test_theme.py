from pathlib import Path

import pygame

from theme import load_theme
from zone import ZoneType

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_missing_assets_dir_yields_all_none() -> None:
    """No asset files means every themed surface falls back to None."""
    theme = load_theme(zone_radius=10, drone_radius=5, assets_dir="/no/such/assets")
    assert theme.background is None
    assert theme.drone is None
    assert set(theme.zone_images) == set(ZoneType)
    assert all(image is None for image in theme.zone_images.values())


def test_existing_background_loads_as_surface() -> None:
    """The bundled background.png loads into a real pygame Surface."""
    pygame.init()
    pygame.display.set_mode((10, 10))
    theme = load_theme(
        zone_radius=10, drone_radius=5, assets_dir=str(REPO_ROOT / "assets")
    )
    assert isinstance(theme.background, pygame.Surface)
    # no zone/drone sprites are bundled, so those still fall back to None
    assert theme.drone is None
    assert all(image is None for image in theme.zone_images.values())
    pygame.quit()
