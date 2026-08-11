from parser import MapData
from connection import Connection
from graph import Graph
from zone import Zone, ZoneType


def _map_with(zones: list[Zone], connections: list[Connection]) -> MapData:
    data = MapData()
    data.nb_drones = 1
    for zone in zones:
        data.zones[zone.name] = zone
    data.connections = connections
    data.start_zone = zones[0]
    data.end_zone = zones[-1]
    return data


def test_neighbors_both_directions() -> None:
    """A connection appears in both endpoints' neighbor lists."""
    a = Zone(name="a", x=0, y=0)
    b = Zone(name="b", x=1, y=0)
    conn = Connection(zone_a="a", zone_b="b")
    graph = Graph(_map_with([a, b], [conn]))

    assert graph.neighbors("a") == [conn]
    assert graph.neighbors("b") == [conn]


def test_blocked_zone_excluded_as_destination() -> None:
    """A blocked zone is never offered as a reachable neighbor."""
    a = Zone(name="a", x=0, y=0)
    blocked = Zone(name="blocked", x=1, y=0, zone_type=ZoneType.BLOCKED)
    c = Zone(name="c", x=2, y=0)
    conn_ab = Connection(zone_a="a", zone_b="blocked")
    conn_bc = Connection(zone_a="blocked", zone_b="c")
    graph = Graph(_map_with([a, blocked, c], [conn_ab, conn_bc]))

    assert graph.neighbors("a") == []
    assert graph.neighbors("c") == []
    # the blocked zone itself still "sees" its connections; it's only
    # ever excluded as a destination, never as an origin
    assert graph.neighbors("blocked") == [conn_ab, conn_bc]


def test_zone_lookup() -> None:
    """zone() returns the registered Zone by name."""
    a = Zone(name="a", x=0, y=0)
    b = Zone(name="b", x=1, y=0)
    graph = Graph(_map_with([a, b], [Connection(zone_a="a", zone_b="b")]))
    assert graph.zone("a") is a


def test_connection_key_is_order_independent() -> None:
    """connection_key() ignores endpoint order."""
    conn = Connection(zone_a="a", zone_b="b")
    assert Graph.connection_key(conn) == frozenset(("b", "a"))
