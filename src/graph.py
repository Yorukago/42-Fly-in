from collections import deque

from mapfile import Connection, MapData, Zone, ZoneType


class Graph:
    """Adjacency-list view of a parsed map, with blocked zones excluded."""

    def __init__(self, data: MapData) -> None:
        """Build the adjacency list from parsed map data."""
        self._zones = data.zones
        self._adjacency: dict[str, list[Connection]] = {name: [] for name in data.zones}

        for conn in data.connections:
            if data.zones[conn.zone_b].zone_type is not ZoneType.BLOCKED:
                self._adjacency[conn.zone_a].append(conn)
            if data.zones[conn.zone_a].zone_type is not ZoneType.BLOCKED:
                self._adjacency[conn.zone_b].append(conn)

    def zone(self, name: str) -> Zone:
        """Return the Zone registered under this name."""
        return self._zones[name]

    def neighbors(self, zone_name: str) -> list[Connection]:
        """Return the connections leading to traversable neighbors of a zone."""
        return self._adjacency[zone_name]

    def reachable(self, start: str, end: str) -> bool:
        """Return whether `end` can be walked to from `start`, ignoring capacity.

        A plain breadth-first search: capacities only ever delay a drone, so
        this is the one thing that can make a map unsolvable.
        """
        seen = {start}
        queue = deque([start])
        while queue:
            zone = queue.popleft()
            if zone == end:
                return True
            for conn in self.neighbors(zone):
                neighbor = conn.other(zone)
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        return False
