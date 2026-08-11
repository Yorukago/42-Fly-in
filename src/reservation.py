from collections import defaultdict

from connection import Connection
from drone import DronePlan, EventKind
from zone import Zone

UNCAPACITATED = 10 ** 9


class ReservationTable:
    """Tracks per-turn zone and connection occupancy across all planned drones.

    The table is only ever read while a single drone's path is being
    searched, and only ever mutated via commit_plan() once that drone's
    path has been finalized. Planning drones strictly one at a time against
    this table is what guarantees zero capacity conflicts between drones.
    """

    def __init__(self, zones: dict[str, Zone], connections: list[Connection]) -> None:
        """Initialize capacities from the map and start with empty occupancy.

        Args:
            zones: All zones in the map, keyed by name.
            connections: All connections in the map.
        """
        self._zone_capacity: dict[str, int] = {
            name: UNCAPACITATED if (zone.is_start or zone.is_end) else zone.max_drones
            for name, zone in zones.items()
        }
        self._connection_capacity: dict[frozenset[str], int] = {
            frozenset((conn.zone_a, conn.zone_b)): conn.max_link_capacity
            for conn in connections
        }
        self._zone_occupancy: dict[tuple[str, int], int] = defaultdict(int)
        self._connection_occupancy: dict[tuple[frozenset[str], int], int] = defaultdict(int)

    def zone_capacity(self, zone_name: str) -> int:
        """Return the maximum number of drones a zone may hold at once.

        Args:
            zone_name: The zone to look up.

        Returns:
            The zone's capacity (UNCAPACITATED for start/end zones).
        """
        return self._zone_capacity[zone_name]

    def connection_capacity(self, conn_key: frozenset[str]) -> int:
        """Return the maximum number of drones a connection may carry at once.

        Args:
            conn_key: The connection's order-independent identity key.

        Returns:
            The connection's capacity.
        """
        return self._connection_capacity[conn_key]

    def has_zone_room(self, zone_name: str, turn: int) -> bool:
        """Check whether a zone has free capacity at a given turn.

        Args:
            zone_name: The zone to check.
            turn: The turn to check.

        Returns:
            True if at least one more drone could occupy the zone at turn.
        """
        return self._zone_occupancy[(zone_name, turn)] < self._zone_capacity[zone_name]

    def has_connection_room(self, conn_key: frozenset[str], turn: int) -> bool:
        """Check whether a connection has free capacity at a given turn.

        Args:
            conn_key: The connection's order-independent identity key.
            turn: The turn to check.

        Returns:
            True if at least one more drone could traverse the connection at turn.
        """
        return (
            self._connection_occupancy[(conn_key, turn)] < self._connection_capacity[conn_key]
        )

    def zone_occupancy(self, zone_name: str, turn: int) -> int:
        """Return how many drones occupy a zone at a given turn.

        Args:
            zone_name: The zone to check.
            turn: The turn to check.

        Returns:
            The number of drones occupying the zone at that turn.
        """
        return self._zone_occupancy[(zone_name, turn)]

    def connection_occupancy(self, conn_key: frozenset[str], turn: int) -> int:
        """Return how many drones traverse a connection at a given turn.

        Args:
            conn_key: The connection's order-independent identity key.
            turn: The turn to check.

        Returns:
            The number of drones traversing the connection at that turn.
        """
        return self._connection_occupancy[(conn_key, turn)]

    def reserve_zone(self, zone_name: str, turn: int) -> None:
        """Record that one drone occupies a zone at a given turn.

        Args:
            zone_name: The zone being occupied.
            turn: The turn of occupancy.
        """
        self._zone_occupancy[(zone_name, turn)] += 1

    def reserve_connection(self, conn_key: frozenset[str], turn: int) -> None:
        """Record that one drone traverses a connection at a given turn.

        Args:
            conn_key: The connection's order-independent identity key.
            turn: The turn of traversal.
        """
        self._connection_occupancy[(conn_key, turn)] += 1

    def commit_plan(self, plan: DronePlan) -> None:
        """Reserve every zone/connection occupancy implied by a finalized plan.

        Args:
            plan: The drone's finalized plan.
        """
        for event in plan.events:
            if event.kind is EventKind.WAIT:
                self.reserve_zone(event.zone, event.turn)
                continue
            if event.connection_key is not None:
                self.reserve_connection(event.connection_key, event.turn)
            if event.kind is EventKind.ARRIVE:
                self.reserve_zone(event.zone, event.turn)
