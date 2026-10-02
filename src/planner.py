import heapq
from itertools import count

from drone import DroneEvent, EventKind
from graph import Graph
from mapfile import ZoneType
from reservation import ReservationTable

_State = tuple[str, int]                      # (zone, turn)
_Step = tuple[str, int, "frozenset[str] | None", int, int]
_Predecessor = tuple[str, int, "frozenset[str] | None"]


class UnreachableError(Exception):
    """Raised when a drone cannot reach its destination within the horizon."""


class DronePlanner:
    """Finds one drone's route: Dijkstra over (zone, turn) states.

    The turn has to be part of the state because a move can be blocked by
    capacity at one specific turn. The search reads a shared
    ReservationTable, so a route never violates a capacity already committed
    by an earlier drone. Among equal-turn routes, fewer moves wins, and among
    those, more priority zones: a drone with time to spare waits instead of
    wandering, but still prefers a priority zone when it costs no extra move.
    """

    def __init__(self, graph: Graph, reservations: ReservationTable, horizon: int) -> None:
        """Search `graph` against already-committed `reservations`, up to `horizon`."""
        self._graph = graph
        self._reservations = reservations
        self._horizon = horizon

    def plan(self, start_zone: str, end_zone: str, start_turn: int = 0) -> list[DroneEvent]:
        """Return the earliest-arriving, capacity-respecting route for one drone.

        Raises:
            UnreachableError: If no valid route exists within the horizon.
        """
        seq = count()
        best: dict[_State, tuple[int, int]] = {(start_zone, start_turn): (0, 0)}
        predecessor: dict[_State, _Predecessor] = {}
        # Heap key: earliest turn first, then fewest moves, then most priority
        # zones. The tie-break counter keeps the ordering total so zone names
        # are never compared.
        heap: list[tuple[int, int, int, int, str]] = [
            (start_turn, 0, 0, next(seq), start_zone)
        ]

        while heap:
            turn, hops, neg_priority, _, zone = heapq.heappop(heap)
            priority_count = -neg_priority

            if zone == end_zone:
                return self._route(predecessor, (zone, turn), (start_zone, start_turn))
            if best.get((zone, turn)) != (hops, neg_priority):
                continue  # a better route to this state was queued later
            if turn >= self._horizon:
                continue

            for new_zone, new_turn, conn_key, new_priority, new_hops in self._successors(
                zone, turn, priority_count, hops
            ):
                state = (new_zone, new_turn)
                key = (new_hops, -new_priority)
                if key >= best.get(state, (self._horizon + 1, 1)):
                    continue
                best[state] = key
                predecessor[state] = (zone, turn, conn_key)
                heapq.heappush(
                    heap, (new_turn, new_hops, -new_priority, next(seq), new_zone)
                )

        raise UnreachableError(
            f"no path from {start_zone!r} to {end_zone!r} found within {self._horizon} turns"
        )

    def _successors(
        self, zone: str, turn: int, priority_count: int, hops: int
    ) -> list[_Step]:
        """Return the states reachable from (zone, turn): waiting, or one move."""
        results: list[_Step] = []

        wait_turn = turn + 1
        if wait_turn <= self._horizon and self._reservations.has_room(zone, wait_turn):
            results.append((zone, wait_turn, None, priority_count, hops))

        for conn in self._graph.neighbors(zone):
            neighbor = conn.other(zone)
            neighbor_type = self._graph.zone(neighbor).zone_type
            arrival = turn + neighbor_type.movement_cost()
            if arrival > self._horizon:
                continue
            # The drone holds the connection for every turn it is in flight,
            # which is two turns when the far zone is restricted.
            crossing = range(turn + 1, arrival + 1)
            if not all(self._reservations.has_room(conn.key, t) for t in crossing):
                continue
            if not self._reservations.has_room(neighbor, arrival):
                continue

            bonus = 1 if neighbor_type is ZoneType.PRIORITY else 0
            results.append((neighbor, arrival, conn.key, priority_count + bonus, hops + 1))

        return results

    def _route(
        self, predecessor: dict[_State, _Predecessor], end: _State, start: _State
    ) -> list[DroneEvent]:
        """Walk the predecessor chain back to the start into ordered events."""
        events: list[DroneEvent] = []
        state = end

        while state != start:
            zone, turn = state
            prev_zone, prev_turn, conn_key = predecessor[state]

            if conn_key is None:
                events.append(DroneEvent(turn, EventKind.WAIT, zone))
            else:
                events.append(DroneEvent(turn, EventKind.ARRIVE, zone, conn_key))
                if turn - prev_turn == 2:  # restricted zone: a turn spent in flight
                    events.append(DroneEvent(turn - 1, EventKind.TRANSIT, zone, conn_key))

            state = (prev_zone, prev_turn)

        events.reverse()
        return events
