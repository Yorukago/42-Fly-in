import pytest
from pydantic import ValidationError

from zone import Zone, ZoneType


def test_defaults() -> None:
    """A minimal zone falls back to normal/unnamed-color/1-capacity."""
    zone = Zone(name="hub", x=1, y=2)
    assert zone.zone_type is ZoneType.NORMAL
    assert zone.color == "none"
    assert zone.max_drones == 1
    assert zone.is_start is False
    assert zone.is_end is False


def test_is_frozen() -> None:
    """Zones are immutable once built."""
    zone = Zone(name="hub", x=0, y=0)
    with pytest.raises(ValidationError):
        zone.x = 5


@pytest.mark.parametrize(
    "max_drones",
    [0, -1],
)
def test_max_drones_must_be_positive(max_drones: int) -> None:
    """max_drones is validated as >= 1."""
    with pytest.raises(ValidationError):
        Zone(name="hub", x=0, y=0, max_drones=max_drones)


def test_name_cannot_be_empty() -> None:
    """An empty zone name is rejected."""
    with pytest.raises(ValidationError):
        Zone(name="", x=0, y=0)


@pytest.mark.parametrize(
    "zone_type,expected_cost",
    [
        (ZoneType.NORMAL, 1),
        (ZoneType.PRIORITY, 1),
        (ZoneType.RESTRICTED, 2),
        (ZoneType.BLOCKED, 1),
    ],
)
def test_movement_cost(zone_type: ZoneType, expected_cost: int) -> None:
    """Only restricted zones cost 2 turns to move into."""
    assert zone_type.movement_cost() == expected_cost
