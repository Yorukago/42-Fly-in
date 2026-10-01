from collections import defaultdict
from dataclasses import dataclass

from drone import Drone, DroneEvent, EventKind
from graph import Graph
from mapfile import MapData, parse_map
from planner import DronePlanner, UnreachableError
from reservation import ReservationTable


@dataclass(frozen=True)
class Turn:
    """One turn of the plan: what moved, and how full everything was.

    `zones` and `connections` map a name to its `(used, capacity)` on this
    turn, which is all printing a capacity report needs.
    """

    number: int
    moves: str
    zones: dict[str, tuple[int, int]]
    connections: dict[str, tuple[int, int]]


class SimulationError(Exception):
    """Raised when no valid simulation can be produced for a map."""


MapError: tuple[type[Exception], ...] = (ValueError, FileNotFoundError, SimulationError)


def load_simulation(filepath: str) -> tuple[MapData, "Simulation"]:
    """Parse a map file and plan its simulation.

    Raises:
        ValueError: On malformed map syntax.
        FileNotFoundError: If filepath does not exist.
        SimulationError: If the map cannot be solved.
    """
    data = parse_map(filepath)
    return data, Simulation(data)


class Simulation:
    """Plans and holds the turn-by-turn route of every drone on a map."""

    def __init__(self, data: MapData) -> None:
        """Build the graph, plan every drone in order, and commit its route.

        Raises:
            SimulationError: If the map has no start/end zone, or no route
                at all from the one to the other.
        """
        if data.start_zone is None or data.end_zone is None:
            raise SimulationError("map is missing a start or end zone")

        self.data = data
        self.drones = [Drone(drone_id) for drone_id in range(1, data.nb_drones + 1)]
        self.reservations = ReservationTable(data.zones, data.connections, data.nb_drones)
        self._connection_names = {
            conn.key: f"{conn.zone_a}-{conn.zone_b}" for conn in data.connections
        }
        self._start_name = data.start_zone.name
        self._end_name = data.end_zone.name
        self._graph = Graph(data)

        if not self._graph.reachable(self._start_name, self._end_name):
            raise SimulationError(
                f"no route from {self._start_name!r} to {self._end_name!r}: "
                f"the map is disconnected, or every route into it is blocked"
            )

        self._plan_all()

    def _plan_all(self) -> None:
        """Plan the drones one at a time, each against the routes already fixed.

        Planning in order is what keeps per-drone Dijkstra sufficient: a drone
        never has to reason about drones that have not been planned yet.

        Each search gets a turn limit, because waiting is always allowed and
        the state space would otherwise be infinite. The limit is the turn the
        last drone lands on plus a walk across the whole map: once the others
        have landed nothing is reserved, so a drone can always wait them out
        and then walk a free path, and no reachable route is ever cut off.
        """
        slack = 2 * len(self.data.zones) + 1
        latest = 0

        for drone in self.drones:
            planner = DronePlanner(self._graph, self.reservations, latest + slack)
            try:
                drone.events = planner.plan(self._start_name, self._end_name)
            except UnreachableError as exc:
                raise SimulationError(f"{drone.label} could not be routed: {exc}") from exc
            self.reservations.commit(drone.events)
            latest = max(latest, drone.arrival_turn)

    @property
    def total_turns(self) -> int:
        """Return the turn the last drone arrives on, or 0 if there are none."""
        return max((drone.arrival_turn for drone in self.drones), default=0)

    def turns(self) -> list[Turn]:
        """Render the plan as one `Turn` per turn, in order.

        A move token is "D<id>-<zone>", or "D<id>-<connection>" for a drone
        still in flight toward a restricted zone.
        """
        moves: dict[int, list[str]] = defaultdict(list)
        for drone in self.drones:
            for event in drone.events:
                if event.kind is not EventKind.WAIT:
                    moves[event.turn].append(f"{drone.label}-{self._target(event)}")

        return [
            self._turn(number, " ".join(moves[number]))
            for number in range(1, self.total_turns + 1)
        ]

    def _turn(self, number: int, moves: str) -> Turn:
        """Bundle one turn's moves with how full every zone and connection is."""
        table = self.reservations
        return Turn(
            number=number,
            moves=moves,
            zones={
                name: (table.used(name, number), table.capacity(name))
                for name in self.data.zones
            },
            connections={
                label: (table.used(key, number), table.capacity(key))
                for key, label in self._connection_names.items()
            },
        )

    def _target(self, event: DroneEvent) -> str:
        """Return what a move token points at: a zone, or a connection in flight."""
        if event.kind is EventKind.TRANSIT and event.connection_key is not None:
            return self._connection_names[event.connection_key]
        return event.zone
