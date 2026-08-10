from connection import Connection
from parser import MapData
from zone import Zone, ZoneType


class Graph:
    """Adjacency-list view of a parsed map, with blocked zones excluded."""

    def __init__(self, data: MapData) -> None:
        """Build the graph from parsed map data.

        Args:
            data: The parsed MapData whose zones/connections form the graph.
        """
        self._zones = data.zones
        self._adjacency: dict[str, list[Connection]] = {name: [] for name in data.zones}

        for conn in data.connections:
            zone_a = data.zones[conn.zone_a]
            zone_b = data.zones[conn.zone_b]
            if zone_b.zone_type is not ZoneType.BLOCKED:
                self._adjacency[conn.zone_a].append(conn)
            if zone_a.zone_type is not ZoneType.BLOCKED:
                self._adjacency[conn.zone_b].append(conn)

    def zone(self, name: str) -> Zone:
        """Return the Zone registered under the given name.

        Args:
            name: The zone's name.

        Returns:
            The corresponding Zone.
        """
        return self._zones[name]

    def neighbors(self, zone_name: str) -> list[Connection]:
        """Return the connections leading to traversable neighbors of a zone.

        Args:
            zone_name: The zone to look up.

        Returns:
            Connections whose far endpoint (from zone_name) is not blocked.
        """
        return self._adjacency[zone_name]

    @staticmethod
    def connection_key(conn: Connection) -> frozenset[str]:
        """Return an order-independent identity key for a connection.

        Args:
            conn: The connection to key.

        Returns:
            A frozenset of the two zone names it links.
        """
        return frozenset((conn.zone_a, conn.zone_b))
