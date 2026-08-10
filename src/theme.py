import os
from dataclasses import dataclass, field

import pygame

from zone import ZoneType

ASSETS_DIR = "assets"


@dataclass
class Theme:
    background: pygame.Surface | None = None
    drone: pygame.Surface | None = None
    zone_images: dict[ZoneType, pygame.Surface | None] = field(default_factory=dict)


def _load_image(path: str, size: tuple[int, int] | None) -> pygame.Surface | None:
    if not os.path.isfile(path):
        return None
    try:
        image = pygame.image.load(path).convert_alpha()
    except pygame.error:
        return None
    if size is None:
        return image
    return pygame.transform.smoothscale(image, size)


def load_theme(
    zone_radius: int,
    drone_radius: int,
    assets_dir: str = ASSETS_DIR,
) -> Theme:
    zone_size = (zone_radius * 2, zone_radius * 2)
    drone_size = (drone_radius * 2, drone_radius * 2)

    zone_images = {
        zone_type: _load_image(
            os.path.join(assets_dir, f"zone_{zone_type.value}.png"), zone_size
        )
        for zone_type in ZoneType
    }

    return Theme(
        background=_load_image(os.path.join(assets_dir, "background.png"), None),
        drone=_load_image(os.path.join(assets_dir, "drone.png"), drone_size),
        zone_images=zone_images,
    )
