import pytest

from drone import Drone, DroneEvent, DronePlan, EventKind


def test_drone_plan_arrival_turn_empty() -> None:
    """An empty plan has arrived at turn 0."""
    assert DronePlan().arrival_turn == 0


def test_drone_plan_arrival_turn_uses_last_event() -> None:
    """arrival_turn reflects the turn of the last recorded event."""
    plan = DronePlan(
        events=[
            DroneEvent(1, EventKind.ARRIVE, "a"),
            DroneEvent(3, EventKind.ARRIVE, "b"),
        ]
    )
    assert plan.arrival_turn == 3


def test_drone_label() -> None:
    """A drone's label is D<id>."""
    assert Drone(1).label == "D1"
    assert Drone(42).label == "D42"


def test_drone_starts_with_empty_plan() -> None:
    """A freshly built drone has an empty plan."""
    drone = Drone(7)
    assert drone.plan.events == []
    assert drone.plan.arrival_turn == 0


def test_drone_event_equality_and_immutability() -> None:
    """DroneEvent is a frozen, value-equal dataclass."""
    a = DroneEvent(1, EventKind.ARRIVE, "zone", frozenset({"x", "y"}))
    b = DroneEvent(1, EventKind.ARRIVE, "zone", frozenset({"y", "x"}))
    assert a == b
    with pytest.raises(AttributeError):
        a.turn = 2  # type: ignore[misc]
