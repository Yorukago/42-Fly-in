from collections import defaultdict
from dataclasses import dataclass

from drone import Drone, DronePlan, EventKind
from graph import Graph
from parser import MapData
from planner import DronePlanner, UnreachableError
from reservation import ReservationTable


class SimulationError(Exception):
    """Raised when a valid simulation cannot be produced for a map."""


@dataclass
class SimulationMetrics:
    """Secondary, non-mandatory performance metrics for a simulation run."""

    total_turns: int
    turns_per_drone: dict[int, int]
    average_turns_per_drone: float
    total_movement_cost: int
    moves_per_turn: dict[int, int]


class Simulation:
    """Plans and holds the turn-by-turn routes for every drone on a map."""

    DEFAULT_MIN_HORIZON = 100
    DEFAULT_HORIZON_FACTOR = 15
    MAX_HORIZON = 5000

    def __init__(self, data: MapData, horizon: int | None = None) -> None:
        """Build the graph, plan every drone, and commit their reservations.

        Args:
            data: The parsed map to simulate.
            horizon: Optional override for the initial search horizon.

        Raises:
            SimulationError: If the map has no start/end zone, or a drone
                cannot reach the end zone within the maximum horizon.
        """
        if data.start_zone is None or data.end_zone is None:
            raise SimulationError("map is missing a start or end zone")

        self._data = data
        self._start_name = data.start_zone.name
        self._end_name = data.end_zone.name
        self._graph = Graph(data)
        self._reservations = ReservationTable(data.zones, data.connections)
        self._horizon = horizon if horizon is not None else self._default_horizon()

        self.drones = self._drone_order()
        self._plan_all()

    def _default_horizon(self) -> int:
        """Compute a starting horizon sized to the map's topology and fleet.

        Returns:
            The initial turn horizon to search within.
        """
        estimate = self.DEFAULT_HORIZON_FACTOR * (len(self._data.zones) + self._data.nb_drones)
        return min(max(self.DEFAULT_MIN_HORIZON, estimate), self.MAX_HORIZON)

    def _drone_order(self) -> list[Drone]:
        """Return the drones in the order they will be planned.

        Returns:
            Drones D1..Dn, planned in ascending id order.
        """
        return [Drone(drone_id) for drone_id in range(1, self._data.nb_drones + 1)]

    def _plan_all(self) -> None:
        """Plan every drone in order, committing each finalized plan in turn."""
        for drone in self.drones:
            drone.plan = self._plan_one_with_retries(drone)
            self._reservations.commit_plan(drone.plan)

    def _plan_one_with_retries(self, drone: Drone) -> DronePlan:
        """Plan a single drone, growing the horizon if it's initially too small.

        Args:
            drone: The drone to plan.

        Returns:
            The drone's finalized plan.

        Raises:
            SimulationError: If no path is found even at the maximum horizon.
        """
        horizon = self._horizon
        while True:
            search = DronePlanner(self._graph, self._reservations, horizon)
            try:
                return search.plan(self._start_name, self._end_name)
            except UnreachableError:
                if horizon >= self.MAX_HORIZON:
                    raise SimulationError(
                        f"{drone.label} could not reach {self._end_name!r} within "
                        f"{horizon} turns; the map may be unsolvable."
                    ) from None
                horizon = min(horizon * 2, self.MAX_HORIZON)

    @property
    def total_turns(self) -> int:
        """Return the number of turns the full simulation takes.

        Returns:
            The latest arrival turn across all drones, or 0 if there are none.
        """
        if not self.drones:
            return 0
        return max(drone.plan.arrival_turn for drone in self.drones)

    def turn_lines(self) -> list[str]:
        """Render the required per-turn output lines.

        Returns:
            One line per turn (1..total_turns), each a space-separated list
            of "D<id>-<zone>" tokens for drones that moved that turn.
        """
        by_turn: dict[int, list[str]] = defaultdict(list)
        for drone in self.drones:
            for event in drone.plan.events:
                if event.kind is EventKind.WAIT:
                    continue
                by_turn[event.turn].append(f"{drone.label}-{event.zone}")

        return [" ".join(by_turn.get(turn, [])) for turn in range(1, self.total_turns + 1)]

    def capacity_lines(self, turn: int) -> list[str]:
        """Render capacity usage for every zone/connection with traffic at a turn.

        Args:
            turn: The turn to report on.

        Returns:
            One "Zone X: Y/Z drones" or "Connection A-B: Y/Z capacity used"
            entry per zone/connection occupied at that turn.
        """
        lines: list[str] = []

        for name, zone in self._data.zones.items():
            if zone.is_start or zone.is_end:
                continue  # uncapacitated; "X/1000000000" isn't useful info
            used = self._reservations.zone_occupancy(name, turn)
            if used:
                cap = self._reservations.zone_capacity(name)
                lines.append(f"Zone {name}: {used}/{cap} drones")

        for conn in self._data.connections:
            key = frozenset((conn.zone_a, conn.zone_b))
            used = self._reservations.connection_occupancy(key, turn)
            if used:
                cap = self._reservations.connection_capacity(key)
                lines.append(
                    f"Connection {conn.zone_a}-{conn.zone_b}: {used}/{cap} capacity used"
                )

        return lines

    def metrics(self) -> SimulationMetrics:
        """Compute optional secondary performance metrics for this run.

        Returns:
            A SimulationMetrics summarizing turns, cost, and throughput.
        """
        turns_per_drone = {drone.drone_id: drone.plan.arrival_turn for drone in self.drones}
        moves_per_turn: dict[int, int] = defaultdict(int)
        total_cost = 0

        for drone in self.drones:
            for event in drone.plan.events:
                if event.kind is EventKind.WAIT:
                    continue
                moves_per_turn[event.turn] += 1
                if event.kind is EventKind.ARRIVE:
                    total_cost += self._graph.zone(event.zone).zone_type.movement_cost()

        average = (
            sum(turns_per_drone.values()) / len(turns_per_drone) if turns_per_drone else 0.0
        )

        return SimulationMetrics(
            total_turns=self.total_turns,
            turns_per_drone=turns_per_drone,
            average_turns_per_drone=average,
            total_movement_cost=total_cost,
            moves_per_turn=dict(moves_per_turn),
        )
