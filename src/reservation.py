from collections import defaultdict

from drone import DroneEvent, EventKind
from mapfile import Connection, Zone

Slot = str | frozenset[str]


class ReservationTable:
    """Per-turn occupancy of every zone and connection.

    A slot is a zone name or a connection key. The table is read while a
    drone's path is being searched and mutated only by commit(), once that
    path is final: planning drones strictly one at a time against it is what
    guarantees no two drones ever exceed a capacity.
    """

    def __init__(
        self, zones: dict[str, Zone], connections: list[Connection], nb_drones: int
    ) -> None:
        """Take capacities from the map and start with everything empty.

        The two hubs hold `nb_drones`: every drone starts in one and is
        delivered to the other, so the fleet size *is* their capacity.
        """
        self._capacity: dict[Slot, int] = {
            name: nb_drones if zone.is_hub else zone.max_drones
            for name, zone in zones.items()
        }
        self._capacity.update({conn.key: conn.max_link_capacity for conn in connections})
        self._used: dict[tuple[Slot, int], int] = defaultdict(int)

    def capacity(self, slot: Slot) -> int:
        """Return how many drones a slot may hold at once."""
        return self._capacity[slot]

    def used(self, slot: Slot, turn: int) -> int:
        """Return how many drones occupy a slot on this turn."""
        return self._used[(slot, turn)]

    def has_room(self, slot: Slot, turn: int) -> bool:
        """Return whether one more drone could use a slot on this turn."""
        return self._used[(slot, turn)] < self._capacity[slot]

    def commit(self, events: list[DroneEvent]) -> None:
        """Reserve every occupancy implied by one drone's finished route."""
        for event in events:
            if event.connection_key is not None:
                self._used[(event.connection_key, event.turn)] += 1
            if event.kind is not EventKind.TRANSIT:
                self._used[(event.zone, event.turn)] += 1
