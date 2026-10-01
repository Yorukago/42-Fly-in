import re
from dataclasses import dataclass
from enum import Enum


def is_positive_int(text: str) -> bool:
    """Return whether `text` is a positive whole number.

    Drone counts and both kinds of capacity all take this one form.
    """
    return text.isdigit() and int(text) > 0


class ZoneType(Enum):
    """The four kinds of zone a map may declare."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    def movement_cost(self) -> int:
        """Return the turn cost to move INTO this zone type: 2 if restricted, else 1."""
        return 2 if self is ZoneType.RESTRICTED else 1


@dataclass(frozen=True)
class Zone:
    """A single zone (node) in the drone network."""

    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: str = "none"
    max_drones: int = 1
    is_start: bool = False
    is_end: bool = False

    @property
    def is_hub(self) -> bool:
        """Return whether this is the start or the end zone.

        The hubs are the one place the whole fleet may gather: every drone
        begins in the start zone and is delivered to the end zone, so
        `ReservationTable` gives both a capacity of `nb_drones`.
        """
        return self.is_start or self.is_end


@dataclass(frozen=True)
class Connection:
    """A single connection (edge) between two zones."""

    zone_a: str
    zone_b: str
    max_link_capacity: int = 1

    @property
    def key(self) -> frozenset[str]:
        """Return an order-independent identity: `a-b` and `b-a` are one link."""
        return frozenset((self.zone_a, self.zone_b))

    def other(self, name: str) -> str:
        """Return the endpoint at the far side from `name`."""
        return self.zone_b if name == self.zone_a else self.zone_a


class MapData:
    """Everything parsed from a map file."""

    def __init__(self) -> None:
        """Start empty, with no drones, zones or connections."""
        self.nb_drones: int = 0
        self.zones: dict[str, Zone] = {}  # name -> Zone
        self.connections: list[Connection] = []
        self.start_zone: Zone | None = None
        self.end_zone: Zone | None = None
        self._connection_keys: set[frozenset[str]] = set()

    def add_zone(self, zone: Zone, line_number: int) -> None:
        """Register a zone.

        Raises:
            ValueError: If the name is taken, or a second start/end hub.
        """
        if zone.is_start and self.start_zone is not None:
            raise ValueError(f"Line {line_number}: duplicate start_hub definition")
        if zone.is_end and self.end_zone is not None:
            raise ValueError(f"Line {line_number}: duplicate end_hub definition")
        if zone.name in self.zones:
            raise ValueError(f"Line {line_number}: duplicate zone name {zone.name!r}")

        self.zones[zone.name] = zone
        if zone.is_start:
            self.start_zone = zone
        if zone.is_end:
            self.end_zone = zone

    def add_connection(self, conn: Connection, line_number: int) -> None:
        """Register a connection.

        Raises:
            ValueError: If the same pair is already connected, either way round.
        """
        if conn.key in self._connection_keys:
            raise ValueError(
                f"Line {line_number}: duplicate connection "
                f"{conn.zone_a!r} <-> {conn.zone_b!r}"
            )
        self._connection_keys.add(conn.key)
        self.connections.append(conn)


class MapParser:
    """Reads a map .txt file line by line into a `MapData`.

    Every line is `keyword: content [optional metadata]`. The hub keywords
    map to the (is_start, is_end) flags they imply, so one zone-parsing
    method handles all three.
    """

    HUB_KEYWORDS = {
        "hub": (False, False),
        "start_hub": (True, False),
        "end_hub": (False, True),
    }
    KEYWORDS = {"nb_drones", "connection"} | HUB_KEYWORDS.keys()

    def parse(self, filepath: str) -> MapData:
        """Read and parse a map file.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: On any syntax or logic error in the file.
        """
        data = MapData()

        with open(filepath, "r", encoding="utf-8") as handle:
            lines = handle.readlines()

        for number, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue  # skip blank lines and comments

            keyword, separator, content = line.partition(":")
            if not separator or keyword not in self.KEYWORDS:
                raise ValueError(f"Line {number}: unrecognised line format: {line!r}")
            content = content.strip()

            if keyword == "nb_drones":
                data.nb_drones = self._drone_count(content, number)
            elif keyword == "connection":
                data.add_connection(self._connection(content, number, data.zones), number)
            else:
                is_start, is_end = self.HUB_KEYWORDS[keyword]
                data.add_zone(self._zone(content, number, is_start, is_end), number)

        for required, missing in (
            ("nb_drones", data.nb_drones == 0),
            ("start_hub", data.start_zone is None),
            ("end_hub", data.end_zone is None),
        ):
            if missing:
                raise ValueError(f"Map file is missing '{required}' definition")

        return data

    def _drone_count(self, content: str, number: int) -> int:
        """Parse the `nb_drones:` value, which must be a positive integer."""
        if not is_positive_int(content):
            raise ValueError(
                f"Line {number}: nb_drones must be a positive integer, got {content!r}"
            )
        return int(content)

    def _zone(self, line: str, number: int, is_start: bool, is_end: bool) -> Zone:
        """Parse one `hub:`/`start_hub:`/`end_hub:` line into a `Zone`."""
        line, metadata = self._split_metadata(line, number)
        parts = line.split()
        if len(parts) < 3:
            raise ValueError(
                f"Line {number}: zone line needs at least name, x, y - got {line!r}"
            )

        name, x_text, y_text = parts[0], parts[1], parts[2]
        detail = self._zone_problem(name, x_text, y_text, metadata)
        if detail is not None:
            raise ValueError(f"Line {number}: invalid zone {line!r} ({detail})")

        return Zone(
            name=name,
            x=int(x_text),
            y=int(y_text),
            zone_type=ZoneType(metadata.get("zone", "normal")),
            color=metadata.get("color", "none"),
            max_drones=int(metadata.get("max_drones", "1")),
            is_start=is_start,
            is_end=is_end,
        )

    def _zone_problem(
        self, name: str, x_text: str, y_text: str, metadata: dict[str, str]
    ) -> str | None:
        """Return why a zone's fields are invalid, or None if they are fine."""
        if "-" in name:
            return "zone names cannot contain a dash"
        for label, text in (("x", x_text), ("y", y_text)):
            if not re.fullmatch(r"[+-]?\d+", text):
                return f"{label} must be an integer, got {text!r}"
        if metadata.get("zone", "normal") not in {t.value for t in ZoneType}:
            return f"unknown zone type {metadata['zone']!r}"
        capacity = metadata.get("max_drones", "1")
        if not is_positive_int(capacity):
            return f"max_drones must be a positive integer, got {capacity!r}"
        return None

    def _connection(
        self, line: str, number: int, known_zones: dict[str, Zone]
    ) -> Connection:
        """Parse one `connection:` line into a `Connection`."""
        line, metadata = self._split_metadata(line, number)
        parts = line.split()
        if len(parts) != 1:
            raise ValueError(
                f"Line {number}: expected exactly one 'zoneA-zoneB' token, got {line!r}"
            )

        pair = parts[0]
        if pair.count("-") != 1:
            raise ValueError(
                f"Line {number}: connection must be 'zoneA-zoneB' (exactly one dash), "
                f"got {pair!r}"
            )

        zone_a, zone_b = pair.split("-")
        for name in (zone_a, zone_b):
            if name not in known_zones:
                raise ValueError(f"Line {number}: unknown zone {name!r} in connection")
        if zone_a == zone_b:
            raise ValueError(
                f"Line {number}: invalid connection {pair!r} "
                f"(a connection cannot link a zone to itself)"
            )

        capacity = metadata.get("max_link_capacity", "1")
        if not is_positive_int(capacity):
            raise ValueError(
                f"Line {number}: invalid connection {pair!r} "
                f"(max_link_capacity must be a positive integer, got {capacity!r})"
            )

        return Connection(zone_a=zone_a, zone_b=zone_b, max_link_capacity=int(capacity))

    def _split_metadata(self, line: str, number: int) -> tuple[str, dict[str, str]]:
        """Split a line into its content and its optional trailing [...] block."""
        bracket = re.search(r"\[.*?\]", line)
        if not bracket:
            return line, {}
        return line[: bracket.start()].strip(), self._metadata(bracket.group(), number)

    def _metadata(self, raw: str, number: int) -> dict[str, str]:
        """Parse a `[key=value key=value]` block into its pairs.

        `raw` always arrives bracketed, because the caller found it with a
        bracket-matching regex, so only the tokens inside still need checking.
        """
        result: dict[str, str] = {}
        for token in raw[1:-1].split():
            key, _, value = token.partition("=")
            if not key or not value:
                raise ValueError(f"Line {number}: invalid metadata token {token!r}")
            result[key] = value

        return result


def parse_map(filepath: str) -> MapData:
    """Read and parse a drone network map file into a `MapData`.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: On any syntax or logic error in the file.
    """
    return MapParser().parse(filepath)
