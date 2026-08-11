import heapq
from itertools import count

from drone import DroneEvent, DronePlan, EventKind
from graph import Graph
from reservation import ReservationTable
from zone import ZoneType

_HeapEntry = tuple[int, int, int, str]
_State = tuple[str, int]
_Predecessor = tuple[str, int, "frozenset[str] | None"]


class UnreachableError(Exception):
    """Raised when a drone cannot reach its destination within the horizon."""


class DronePlanner:
    """Finds a single drone's turn-by-turn plan via Dijkstra over (zone, turn) states.

    The search respects a shared ReservationTable so that a drone's plan
    never violates zone or connection capacity already committed by
    previously-planned drones. Among equal-turn-cost options, paths through
    more `priority` zones are preferred via a lexicographic tie-break.
    """

    def __init__(self, graph: Graph, reservations: ReservationTable, horizon: int) -> None:
        """Initialize the planner.

        Args:
            graph: The map's topology.
            reservations: The shared, previously-committed occupancy table.
            horizon: The last turn the search is allowed to consider.
        """
        self._graph = graph
        self._reservations = reservations
        self._horizon = horizon

    def plan(self, start_zone: str, end_zone: str, start_turn: int = 0) -> DronePlan:
        """Find the earliest-arriving, capacity-respecting plan for one drone.

        Args:
            start_zone: The zone the drone begins in.
            end_zone: The zone the drone must reach.
            start_turn: The turn at which the drone begins (usually 0).

        Returns:
            The drone's finalized plan.

        Raises:
            UnreachableError: If no valid path exists within the horizon.
        """
        seq = count()
        best_priority: dict[_State, int] = {(start_zone, start_turn): 0}
        predecessor: dict[_State, _Predecessor] = {}
        heap: list[_HeapEntry] = [(start_turn, 0, next(seq), start_zone)]

        while heap:
            turn, neg_priority, _, zone = heapq.heappop(heap)
            priority_count = -neg_priority

            if zone == end_zone:
                return self._reconstruct(predecessor, (zone, turn), (start_zone, start_turn))

            if best_priority.get((zone, turn)) != priority_count:
                continue  # stale entry, already superseded

            if turn >= self._horizon:
                continue

            for new_zone, new_turn, conn_key, new_priority in self._successors(
                zone, turn, priority_count
            ):
                state = (new_zone, new_turn)
                if new_priority <= best_priority.get(state, -1):
                    continue
                best_priority[state] = new_priority
                predecessor[state] = (zone, turn, conn_key)
                heapq.heappush(heap, (new_turn, -new_priority, next(seq), new_zone))

        raise UnreachableError(
            f"no path from {start_zone!r} to {end_zone!r} found within {self._horizon} turns"
        )

    def _successors(
        self, zone: str, turn: int, priority_count: int
    ) -> list[tuple[str, int, "frozenset[str] | None", int]]:
        """Generate valid successor states reachable from (zone, turn).

        Args:
            zone: The current zone.
            turn: The current turn.
            priority_count: The number of priority-zone visits so far.

        Returns:
            A list of (new_zone, new_turn, connection_key, new_priority_count) tuples.
        """
        results: list[tuple[str, int, "frozenset[str] | None", int]] = []

        wait_turn = turn + 1
        if wait_turn <= self._horizon and self._reservations.has_zone_room(zone, wait_turn):
            results.append((zone, wait_turn, None, priority_count))

        for conn in self._graph.neighbors(zone):
            neighbor = conn.other(zone)
            neighbor_zone = self._graph.zone(neighbor)
            conn_key = Graph.connection_key(conn)
            cost = neighbor_zone.zone_type.movement_cost()

            if neighbor_zone.zone_type is ZoneType.RESTRICTED:
                t1, t2 = turn + 1, turn + 2
                if (
                    t2 <= self._horizon
                    and self._reservations.has_connection_room(conn_key, t1)
                    and self._reservations.has_connection_room(conn_key, t2)
                    and self._reservations.has_zone_room(neighbor, t2)
                ):
                    results.append((neighbor, t2, conn_key, priority_count))
            else:
                new_turn = turn + cost
                if (
                    new_turn <= self._horizon
                    and self._reservations.has_connection_room(conn_key, new_turn)
                    and self._reservations.has_zone_room(neighbor, new_turn)
                ):
                    bonus = 1 if neighbor_zone.zone_type is ZoneType.PRIORITY else 0
                    results.append((neighbor, new_turn, conn_key, priority_count + bonus))

        return results

    def _reconstruct(
        self,
        predecessor: dict[_State, _Predecessor],
        end_state: _State,
        start_state: _State,
    ) -> DronePlan:
        """Rebuild a DronePlan by walking the predecessor chain back to the start.

        Args:
            predecessor: Maps a state to the (zone, turn, connection_key) it came from.
            end_state: The (zone, turn) state where the drone arrived.
            start_state: The (zone, turn) state where the drone began.

        Returns:
            The finalized plan, with events in chronological order.
        """
        events: list[DroneEvent] = []
        state = end_state

        while state != start_state:
            zone, turn = state
            prev_zone, prev_turn, conn_key = predecessor[state]

            if conn_key is None:
                events.append(DroneEvent(turn, EventKind.WAIT, zone))
            elif turn - prev_turn == 2:
                # Events are collected walking backward from the end state,
                # then reversed once as a whole at the end — so within a
                # single two-turn hop the events must also be appended in
                # reverse-chronological order (ARRIVE before TRANSIT) for
                # the final list to come out in turn order.
                events.append(DroneEvent(turn, EventKind.ARRIVE, zone, conn_key))
                events.append(DroneEvent(turn - 1, EventKind.TRANSIT, zone, conn_key))
            else:
                events.append(DroneEvent(turn, EventKind.ARRIVE, zone, conn_key))

            state = (prev_zone, prev_turn)

        events.reverse()
        return DronePlan(events)
