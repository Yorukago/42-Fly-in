from pathlib import Path

import pytest

from parser import parse_map
from zone import ZoneType

_VALID_MAP = """
nb_drones: 3

start_hub: start 0 0 [color=green]
hub: mid 1 1 [zone=restricted color=red max_drones=2]
end_hub: goal 2 2 [color=yellow]

connection: start-mid
connection: mid-goal [max_link_capacity=2]
"""


def _write(tmp_path: Path, text: str) -> str:
    path = tmp_path / "map.txt"
    path.write_text(text)
    return str(path)


def test_parses_valid_map(tmp_path: Path) -> None:
    """A well-formed map produces the expected zones and connections."""
    data = parse_map(_write(tmp_path, _VALID_MAP))

    assert data.nb_drones == 3
    assert set(data.zones) == {"start", "mid", "goal"}

    assert data.start_zone is not None
    assert data.start_zone.name == "start"
    assert data.start_zone.is_start

    assert data.end_zone is not None
    assert data.end_zone.name == "goal"
    assert data.end_zone.is_end

    mid = data.zones["mid"]
    assert mid.zone_type is ZoneType.RESTRICTED
    assert mid.color == "red"
    assert mid.max_drones == 2

    assert len(data.connections) == 2
    capacities = {frozenset((c.zone_a, c.zone_b)): c.max_link_capacity for c in data.connections}
    assert capacities[frozenset(("mid", "goal"))] == 2


def test_comments_and_blank_lines_are_ignored(tmp_path: Path) -> None:
    """Comment and blank lines don't affect parsing."""
    text = "# a comment\n\n" + _VALID_MAP + "\n# trailing comment\n"
    data = parse_map(_write(tmp_path, text))
    assert data.nb_drones == 3


def test_missing_file_raises(tmp_path: Path) -> None:
    """A nonexistent path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        parse_map(str(tmp_path / "does-not-exist.txt"))


@pytest.mark.parametrize(
    "broken_map,match",
    [
        ("hub: only 0 0\n", "nb_drones"),
        ("nb_drones: 1\nhub: a 0 0\nend_hub: b 1 1\n", "start_hub"),
        ("nb_drones: 1\nstart_hub: a 0 0\nhub: b 1 1\n", "end_hub"),
        (
            "nb_drones: 1\nstart_hub: a 0 0\nstart_hub: a2 1 1\nend_hub: b 2 2\n",
            "duplicate start_hub",
        ),
        (
            "nb_drones: 1\nstart_hub: a 0 0\nend_hub: a 1 1\n",
            "duplicate zone name",
        ),
        ("nb_drones: 0\nstart_hub: a 0 0\nend_hub: b 1 1\n", "positive integer"),
        (
            "nb_drones: 1\nstart_hub: a 0 0\nend_hub: b 1 1\nconnection: a-c\n",
            "unknown zone",
        ),
        (
            "nb_drones: 1\nstart_hub: a 0 0\nend_hub: b 1 1\n"
            "connection: a-b\nconnection: b-a\n",
            "duplicate connection",
        ),
        (
            "nb_drones: 1\nstart_hub: a 0 0\nend_hub: b 1 1\nconnection: a-b-c\n",
            "exactly one dash",
        ),
        ("nb_drones: 1\nstart_hub: a 0 0 [bad]\nend_hub: b 1 1\n", "missing '='"),
        ("this is not a valid line\n", "unrecognised line"),
    ],
)
def test_invalid_maps_raise_value_error(
    tmp_path: Path, broken_map: str, match: str
) -> None:
    """Every documented failure mode raises a descriptive ValueError."""
    with pytest.raises(ValueError, match=match):
        parse_map(_write(tmp_path, broken_map))
