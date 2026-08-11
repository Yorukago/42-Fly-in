import re
from pathlib import Path

import pytest

from drone import EventKind
from parser import MapData, parse_map
from connection import Connection
from simulation import Simulation, SimulationError
from zone import Zone, ZoneType

REPO_ROOT = Path(__file__).resolve().parent.parent
EASY_MAPS = sorted((REPO_ROOT / "maps" / "easy").glob("*.txt"))
ALL_BUNDLED_MAPS = sorted((REPO_ROOT / "maps").rglob("*.txt"))

_TURN_TOKEN = re.compile(r"^D\d+-\S+$")


@pytest.mark.parametrize("map_path", EASY_MAPS, ids=lambda p: p.name)
def test_easy_maps_simulate_successfully(map_path: Path) -> None:
    """Every bundled easy map produces a complete, well-formed plan."""
    data = parse_map(str(map_path))
    simulation = Simulation(data)

    assert simulation.total_turns > 0
    assert len(simulation.drones) == data.nb_drones
    for drone in simulation.drones:
        assert drone.plan.arrival_turn > 0


@pytest.mark.parametrize("map_path", ALL_BUNDLED_MAPS, ids=lambda p: p.name)
def test_bundled_maps_never_exceed_declared_capacity(map_path: Path) -> None:
    """No zone or connection is ever occupied beyond its declared capacity.

    This is the core correctness guarantee of the planner/reservation
    system: replaying every drone's committed plan turn-by-turn must never
    show more drones in a zone, or crossing a connection, than it allows.
    """
    data = parse_map(str(map_path))
    simulation = Simulation(data)

    zone_occupancy: dict[tuple[str, int], int] = {}
    conn_occupancy: dict[tuple[frozenset[str], int], int] = {}

    for drone in simulation.drones:
        for event in drone.plan.events:
            if event.kind is EventKind.WAIT:
                zone_occupancy[(event.zone, event.turn)] = (
                    zone_occupancy.get((event.zone, event.turn), 0) + 1
                )
                continue
            if event.connection_key is not None:
                key = (event.connection_key, event.turn)
                conn_occupancy[key] = conn_occupancy.get(key, 0) + 1
            if event.kind is EventKind.ARRIVE:
                zone_occupancy[(event.zone, event.turn)] = (
                    zone_occupancy.get((event.zone, event.turn), 0) + 1
                )

    for (zone_name, _turn), used in zone_occupancy.items():
        zone = data.zones[zone_name]
        if zone.is_start or zone.is_end:
            continue
        assert used <= zone.max_drones, f"{zone_name} over capacity"

    connections_by_key = {
        frozenset((c.zone_a, c.zone_b)): c for c in data.connections
    }
    for (conn_key, _turn), used in conn_occupancy.items():
        conn = connections_by_key[conn_key]
        assert used <= conn.max_link_capacity, f"{conn_key} over capacity"


def test_turn_lines_format_and_length() -> None:
    """turn_lines() emits one line per turn, with well-formed move tokens."""
    map_path = REPO_ROOT / "maps" / "easy" / "02_simple_fork.txt"
    simulation = Simulation(parse_map(str(map_path)))

    lines = simulation.turn_lines()
    assert len(lines) == simulation.total_turns

    for line in lines:
        if not line:
            continue
        for token in line.split():
            assert _TURN_TOKEN.match(token), f"malformed token: {token!r}"


def _map_with(zones: list[Zone], connections: list[Connection], nb_drones: int) -> MapData:
    data = MapData()
    data.nb_drones = nb_drones
    for zone in zones:
        data.zones[zone.name] = zone
    data.connections = connections
    data.start_zone = zones[0]
    data.end_zone = zones[-1]
    return data


def test_disconnected_end_zone_raises_simulation_error() -> None:
    """A start/end pair with no path between them fails cleanly."""
    zones = [
        Zone(name="start", x=0, y=0, is_start=True),
        Zone(name="goal", x=1, y=0, is_end=True),
    ]
    data = _map_with(zones, [], nb_drones=1)
    with pytest.raises(SimulationError):
        Simulation(data, horizon=5)


def test_blocked_zone_is_never_routed_through() -> None:
    """A blocked zone on the only path makes the map unsolvable."""
    zones = [
        Zone(name="start", x=0, y=0, is_start=True),
        Zone(name="mid", x=1, y=0, zone_type=ZoneType.BLOCKED),
        Zone(name="goal", x=2, y=0, is_end=True),
    ]
    connections = [
        Connection(zone_a="start", zone_b="mid"),
        Connection(zone_a="mid", zone_b="goal"),
    ]
    data = _map_with(zones, connections, nb_drones=1)
    with pytest.raises(SimulationError):
        Simulation(data, horizon=5)
