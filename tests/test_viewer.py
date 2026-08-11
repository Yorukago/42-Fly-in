import pygame

from drone import Drone, DroneEvent, EventKind
from parser import MapData
from zone import Zone, ZoneType
import viewer


def _map_with(zones: list[Zone]) -> MapData:
    data = MapData()
    data.nb_drones = 1
    for zone in zones:
        data.zones[zone.name] = zone
    data.start_zone = zones[0]
    data.end_zone = zones[-1]
    return data


def test_layout_centers_a_flat_map_instead_of_pinning_to_the_top() -> None:
    """Regression test: a flat map is vertically centered, not pinned to the top."""
    zones = [
        Zone(name="a", x=0, y=5, is_start=True),
        Zone(name="b", x=10, y=5, is_end=True),
    ]
    window = (900, 700)
    layout = viewer.MapLayout(_map_with(zones), window)

    _, py_a = layout.positions["a"]
    _, py_b = layout.positions["b"]
    draw_h = window[1] - 2 * viewer.MARGIN

    assert py_a == py_b
    assert py_a == viewer.MARGIN + draw_h // 2


def test_layout_scales_and_centers_deterministically() -> None:
    """A known map/window combination maps to exact, hand-computed pixels."""
    zones = [
        Zone(name="a", x=0, y=0, is_start=True),
        Zone(name="b", x=10, y=0),
        Zone(name="c", x=20, y=0, is_end=True),
    ]
    # draw area is 100x80; with span_x=20, span_y=0 the scale is fully
    # x-constrained (5 px/unit), so content fills the width exactly and
    # is centered vertically within the 80px-tall draw area.
    layout = viewer.MapLayout(_map_with(zones), (220, 200))

    assert layout.positions["a"] == (60, 100)
    assert layout.positions["b"] == (110, 100)
    assert layout.positions["c"] == (160, 100)


def test_layout_single_zone_centers_in_window() -> None:
    """A single zone (zero span on both axes) sits dead center."""
    zones = [Zone(name="only", x=3, y=3, is_start=True, is_end=True)]
    window = (900, 700)
    layout = viewer.MapLayout(_map_with(zones), window)

    assert layout.positions["only"] == (window[0] // 2, window[1] // 2)


def test_zone_fill_color_prefers_named_color() -> None:
    """A recognised color name overrides the zone-type default fill."""
    zone = Zone(name="a", x=0, y=0, zone_type=ZoneType.NORMAL, color="red")
    assert viewer.zone_fill_color(zone) == viewer.NAMED_COLORS["red"]


def test_zone_fill_color_falls_back_to_zone_type() -> None:
    """An unrecognised or absent color falls back to the zone type's fill."""
    unknown_color = Zone(name="a", x=0, y=0, zone_type=ZoneType.RESTRICTED, color="chartreuse")
    no_color = Zone(name="b", x=0, y=0, zone_type=ZoneType.PRIORITY, color="none")

    assert viewer.zone_fill_color(unknown_color) == viewer.ZONE_TYPE_FILL[ZoneType.RESTRICTED]
    assert viewer.zone_fill_color(no_color) == viewer.ZONE_TYPE_FILL[ZoneType.PRIORITY]


def test_drone_track_places_transit_at_connection_midpoint() -> None:
    """A TRANSIT event lands halfway between the zones it's flying between."""
    zones = [
        Zone(name="a", x=0, y=0, is_start=True),
        Zone(name="b", x=10, y=0),
        Zone(name="c", x=20, y=0, is_end=True),
    ]
    layout = viewer.MapLayout(_map_with(zones), (220, 200))

    key = frozenset({"b", "c"})
    drone = Drone(1)
    drone.plan.events = [
        DroneEvent(1, EventKind.ARRIVE, "b"),
        DroneEvent(2, EventKind.TRANSIT, "c", key),
        DroneEvent(3, EventKind.ARRIVE, "c", key),
    ]

    track = viewer._drone_track(drone, layout, "a")

    assert track[0] == layout.positions["a"]
    assert track[1] == layout.positions["b"]
    assert track[2] == (
        (layout.positions["b"][0] + layout.positions["c"][0]) / 2,
        (layout.positions["b"][1] + layout.positions["c"][1]) / 2,
    )
    assert track[3] == layout.positions["c"]


def test_initial_window_size_falls_back_when_display_info_unavailable() -> None:
    """If desktop resolution can't be read, the fixed default is used."""
    pygame.init()
    size = viewer._initial_window_size()
    assert size[0] >= viewer.MIN_WINDOW_SIZE[0]
    assert size[1] >= viewer.MIN_WINDOW_SIZE[1]
    pygame.quit()
