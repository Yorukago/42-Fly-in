from drone import DroneEvent, DronePlan, EventKind
from connection import Connection
from reservation import UNCAPACITATED, ReservationTable
from zone import Zone


def _table() -> ReservationTable:
    zones = {
        "start": Zone(name="start", x=0, y=0, is_start=True),
        "mid": Zone(name="mid", x=1, y=0, max_drones=1),
        "end": Zone(name="end", x=2, y=0, is_end=True),
    }
    connections = [
        Connection(zone_a="start", zone_b="mid", max_link_capacity=1),
        Connection(zone_a="mid", zone_b="end", max_link_capacity=2),
    ]
    return ReservationTable(zones, connections)


def test_start_and_end_zones_are_uncapacitated() -> None:
    """Start/end zones ignore their declared max_drones and never fill up."""
    table = _table()
    assert table.zone_capacity("start") == UNCAPACITATED
    assert table.zone_capacity("end") == UNCAPACITATED
    assert table.zone_capacity("mid") == 1


def test_zone_room_frees_up_per_turn() -> None:
    """Reserving a zone at one turn doesn't affect other turns."""
    table = _table()
    assert table.has_zone_room("mid", 1)
    table.reserve_zone("mid", 1)
    assert not table.has_zone_room("mid", 1)
    assert table.has_zone_room("mid", 2)


def test_connection_room_respects_capacity() -> None:
    """A connection stops offering room once its capacity is used up."""
    table = _table()
    key = frozenset(("mid", "end"))
    assert table.connection_capacity(key) == 2

    table.reserve_connection(key, 5)
    assert table.has_connection_room(key, 5)
    table.reserve_connection(key, 5)
    assert not table.has_connection_room(key, 5)


def test_commit_plan_reserves_wait_and_arrive_but_not_transit_zone() -> None:
    """A TRANSIT event only occupies the connection, not a zone."""
    table = _table()
    key = frozenset(("mid", "end"))
    plan = DronePlan(
        events=[
            DroneEvent(1, EventKind.WAIT, "start"),
            DroneEvent(2, EventKind.TRANSIT, "end", key),
            DroneEvent(3, EventKind.ARRIVE, "end", key),
        ]
    )
    table.commit_plan(plan)

    assert table.zone_occupancy("start", 1) == 1
    assert table.zone_occupancy("end", 2) == 0  # still in flight, not occupying yet
    assert table.zone_occupancy("end", 3) == 1
    assert table.connection_occupancy(key, 2) == 1
    assert table.connection_occupancy(key, 3) == 1
