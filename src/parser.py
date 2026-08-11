import re
from pydantic import PositiveInt, TypeAdapter, ValidationError
from connection import Connection
from zone import Zone

_positive_int = TypeAdapter(PositiveInt)


def _format_validation_error(error: ValidationError) -> str:
    parts = []
    for err in error.errors():
        field = ".".join(str(loc) for loc in err["loc"]) or "value"
        parts.append(f"{field}: {err['msg']}")
    return "; ".join(parts)


def _parse_metadata(raw: str) -> dict[str, str]:
    raw = raw.strip()
    if not raw.startswith("[") or not raw.endswith("]"):
        raise ValueError(f"Malformed metadata block: {raw!r}")

    inside = raw[1:-1].strip()
    result: dict[str, str] = {}

    for token in inside.split():
        if "=" not in token:
            raise ValueError(f"Invalid metadata token (missing '='): {token!r}")
        key, _, value = token.partition("=")
        if not key or not value:
            raise ValueError(f"Invalid metadata token: {token!r}")
        result[key] = value

    return result


def _parse_zone_line(
    line: str,
    line_number: int,
    is_start: bool = False,
    is_end: bool = False,
) -> Zone:
    bracket_match = re.search(r"\[.*?\]", line)
    metadata: dict[str, str] = {}

    if bracket_match:
        metadata = _parse_metadata(bracket_match.group())
        line = line[:bracket_match.start()].strip()

    parts = line.split()
    if len(parts) < 3:
        raise ValueError(
            f"Line {line_number}: zone line needs at least name, x, y — got {line!r}"
        )

    name, x_str, y_str = parts[0], parts[1], parts[2]

    try:
        return Zone.model_validate({
            "name": name,
            "x": x_str,
            "y": y_str,
            "zone_type": metadata.get("zone", "normal"),
            "color": metadata.get("color", "none"),
            "max_drones": metadata.get("max_drones", "1"),
            "is_start": is_start,
            "is_end": is_end,
        })
    except ValidationError as e:
        raise ValueError(
            f"Line {line_number}: invalid zone {line!r} ({_format_validation_error(e)})"
        ) from e


def _parse_connection_line(
    line: str,
    line_number: int,
    known_zones: dict[str, Zone],
) -> Connection:
    bracket_match = re.search(r"\[.*?\]", line)
    metadata: dict[str, str] = {}

    if bracket_match:
        metadata = _parse_metadata(bracket_match.group())
        line = line[:bracket_match.start()].strip()

    # the connection name is "zoneA-zoneB" — split on the dash
    parts = line.split()
    if len(parts) != 1:
        raise ValueError(
            f"Line {line_number}: expected exactly one 'zoneA-zoneB' token, "
            f"got {line!r}"
        )

    pair = parts[0]
    # count dashes to find the split point
    # zone names cannot contain dashes, so exactly one dash expected
    if pair.count("-") != 1:
        raise ValueError(
            f"Line {line_number}: connection must be 'zoneA-zoneB' (exactly one dash), "
            f"got {pair!r}"
        )

    zone_a, zone_b = pair.split("-")

    if zone_a not in known_zones:
        raise ValueError(
            f"Line {line_number}: unknown zone {zone_a!r} in connection"
        )
    if zone_b not in known_zones:
        raise ValueError(
            f"Line {line_number}: unknown zone {zone_b!r} in connection"
        )

    try:
        return Connection.model_validate({
            "zone_a": zone_a,
            "zone_b": zone_b,
            "max_link_capacity": metadata.get("max_link_capacity", "1"),
        })
    except ValidationError as e:
        raise ValueError(
            f"Line {line_number}: invalid connection {pair!r} ({_format_validation_error(e)})"
        ) from e


def _register_zone(data: "MapData", zone: Zone, line_number: int) -> None:
    if zone.name in data.zones:
        raise ValueError(f"Line {line_number}: duplicate zone name {zone.name!r}")
    data.zones[zone.name] = zone


class MapData:
    """Holds everything parsed from a map file."""

    def __init__(self) -> None:
        """Initialize empty map data."""
        self.nb_drones: int = 0
        self.zones: dict[str, Zone] = {}        # name -> Zone
        self.connections: list[Connection] = []
        self.start_zone: Zone | None = None
        self.end_zone: Zone | None = None

    def __repr__(self) -> str:
        """Return summary string."""
        return (
            f"MapData(drones={self.nb_drones}, "
            f"zones={len(self.zones)}, "
            f"connections={len(self.connections)}, "
            f"start={self.start_zone}, end={self.end_zone})"
        )


def parse_map(filepath: str) -> MapData:
    """Read and parse a drone network map file.

    Args:
        filepath: Path to the map .txt file.

    Returns:
        A MapData object with all zones and connections.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: On any syntax or logic error in the file.
    """
    data = MapData()
    seen_connections: set[frozenset[str]] = set()  # duplicate detection

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        # skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        if line.startswith("nb_drones:"):
            value = line[len("nb_drones:"):].strip()
            try:
                data.nb_drones = _positive_int.validate_python(value)
            except ValidationError as e:
                raise ValueError(
                    f"Line {line_number}: nb_drones must be a positive integer, "
                    f"got {value!r}"
                ) from e
            continue

        if line.startswith("start_hub:"):
            if data.start_zone is not None:
                raise ValueError(
                    f"Line {line_number}: duplicate start_hub definition"
                )
            content = line[len("start_hub:"):].strip()
            zone = _parse_zone_line(content, line_number, is_start=True)
            _register_zone(data, zone, line_number)
            data.start_zone = zone
            continue

        if line.startswith("end_hub:"):
            if data.end_zone is not None:
                raise ValueError(
                    f"Line {line_number}: duplicate end_hub definition"
                )
            content = line[len("end_hub:"):].strip()
            zone = _parse_zone_line(content, line_number, is_end=True)
            _register_zone(data, zone, line_number)
            data.end_zone = zone
            continue

        if line.startswith("hub:"):
            content = line[len("hub:"):].strip()
            zone = _parse_zone_line(content, line_number)
            _register_zone(data, zone, line_number)
            continue

        if line.startswith("connection:"):
            content = line[len("connection:"):].strip()
            conn = _parse_connection_line(content, line_number, data.zones)

            # check for duplicates (a-b and b-a are the same)
            pair_key: frozenset[str] = frozenset([conn.zone_a, conn.zone_b])
            if pair_key in seen_connections:
                raise ValueError(
                    f"Line {line_number}: duplicate connection "
                    f"{conn.zone_a!r} <-> {conn.zone_b!r}"
                )
            seen_connections.add(pair_key)
            data.connections.append(conn)
            continue

        raise ValueError(
            f"Line {line_number}: unrecognised line format: {line!r}"
        )

    # final validation
    if data.nb_drones == 0:
        raise ValueError("Map file is missing 'nb_drones' definition")
    if data.start_zone is None:
        raise ValueError("Map file is missing 'start_hub' definition")
    if data.end_zone is None:
        raise ValueError("Map file is missing 'end_hub' definition")

    return data
