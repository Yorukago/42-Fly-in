import pytest

from parser import MapData
from connection import Connection
from drone import EventKind
from graph import Graph
from planner import DronePlanner, UnreachableError
from reservation import ReservationTable
from zone import Zone, ZoneType


def _build(zones: list[Zone], connections: list[Connection]) -> tuple[Graph, ReservationTable]:
    data = MapData()
    data.nb_drones = 1
    for zone in zones:
        data.zones[zone.name] = zone
    data.connections = connections
    graph = Graph(data)
    reservations = ReservationTable(data.zones, connections)
    return graph, reservations


def test_finds_direct_path() -> None:
    """A straight line of normal zones is traversed one turn at a time."""
    zones = [
        Zone(name="a", x=0, y=0, is_start=True),
        Zone(name="b", x=1, y=0),
        Zone(name="c", x=2, y=0, is_end=True),
    ]
    connections = [
        Connection(zone_a="a", zone_b="b"),
        Connection(zone_a="b", zone_b="c"),
    ]
    graph, reservations = _build(zones, connections)
    plan = DronePlanner(graph, reservations, horizon=10).plan("a", "c")

    assert plan.arrival_turn == 2
    kinds = [(e.turn, e.kind, e.zone) for e in plan.events]
    assert kinds == [(1, EventKind.ARRIVE, "b"), (2, EventKind.ARRIVE, "c")]


def test_restricted_zone_takes_two_turns_via_transit() -> None:
    """Moving into a restricted zone produces a TRANSIT then an ARRIVE."""
    zones = [
        Zone(name="a", x=0, y=0, is_start=True),
        Zone(name="b", x=1, y=0, zone_type=ZoneType.RESTRICTED),
    ]
    connections = [Connection(zone_a="a", zone_b="b")]
    graph, reservations = _build(zones, connections)
    plan = DronePlanner(graph, reservations, horizon=10).plan("a", "b")

    kinds = [(e.turn, e.kind) for e in plan.events]
    assert kinds == [(1, EventKind.TRANSIT), (2, EventKind.ARRIVE)]
    assert plan.arrival_turn == 2


def test_unreachable_destination_raises() -> None:
    """A disconnected end zone cannot be planned for."""
    zones = [
        Zone(name="a", x=0, y=0, is_start=True),
        Zone(name="b", x=1, y=0, is_end=True),
    ]
    graph, reservations = _build(zones, [])
    with pytest.raises(UnreachableError):
        DronePlanner(graph, reservations, horizon=10).plan("a", "b")


def test_waits_when_zone_capacity_is_full() -> None:
    """A drone waits a turn rather than moving into a full zone."""
    zones = [
        Zone(name="a", x=0, y=0, is_start=True),
        Zone(name="b", x=1, y=0, max_drones=1),
        Zone(name="c", x=2, y=0, is_end=True),
    ]
    connections = [
        Connection(zone_a="a", zone_b="b"),
        Connection(zone_a="b", zone_b="c"),
    ]
    graph, reservations = _build(zones, connections)
    # occupy "b" at turn 1 so the drone under test must wait there
    reservations.reserve_zone("b", 1)

    plan = DronePlanner(graph, reservations, horizon=10).plan("a", "c")
    kinds = [(e.turn, e.kind, e.zone) for e in plan.events]
    assert kinds[0] == (1, EventKind.WAIT, "a")
    assert kinds[-1] == (plan.arrival_turn, EventKind.ARRIVE, "c")


def test_priority_zones_are_preferred_at_equal_cost() -> None:
    """Among equal-turn-cost paths, the one through more priority zones wins."""
    zones = [
        Zone(name="a", x=0, y=0, is_start=True),
        Zone(name="normal_mid", x=1, y=-1),
        Zone(name="priority_mid", x=1, y=1, zone_type=ZoneType.PRIORITY),
        Zone(name="z", x=2, y=0, is_end=True),
    ]
    connections = [
        Connection(zone_a="a", zone_b="normal_mid"),
        Connection(zone_a="normal_mid", zone_b="z"),
        Connection(zone_a="a", zone_b="priority_mid"),
        Connection(zone_a="priority_mid", zone_b="z"),
    ]
    graph, reservations = _build(zones, connections)
    plan = DronePlanner(graph, reservations, horizon=10).plan("a", "z")

    visited = [e.zone for e in plan.events]
    assert "priority_mid" in visited
    assert plan.arrival_turn == 2


def test_horizon_exhaustion_raises_unreachable() -> None:
    """A path that needs more turns than the horizon allows is unreachable."""
    zones = [
        Zone(name="a", x=0, y=0, is_start=True),
        Zone(name="b", x=1, y=0),
        Zone(name="c", x=2, y=0, is_end=True),
    ]
    connections = [
        Connection(zone_a="a", zone_b="b"),
        Connection(zone_a="b", zone_b="c"),
    ]
    graph, reservations = _build(zones, connections)
    with pytest.raises(UnreachableError):
        DronePlanner(graph, reservations, horizon=1).plan("a", "c")
