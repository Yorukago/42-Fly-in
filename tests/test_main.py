import re
from pathlib import Path

import pytest

import main

_TURN_TOKEN = re.compile(r"^D\d+-\S+$")

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_parse_args_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no CLI arguments, map_path is None and both flags are off."""
    monkeypatch.setattr("sys.argv", ["main.py"])
    args = main.parse_args()
    assert args.map_path is None
    assert args.simulate is False
    assert args.capacity_info is False


def test_parse_args_reads_map_path_and_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    """A positional map path and both flags are parsed correctly."""
    monkeypatch.setattr(
        "sys.argv", ["main.py", "maps/easy/01_linear_path.txt", "--simulate", "--capacity-info"]
    )
    args = main.parse_args()
    assert args.map_path == "maps/easy/01_linear_path.txt"
    assert args.simulate is True
    assert args.capacity_info is True


def test_run_simulation_prints_turn_lines(capsys: pytest.CaptureFixture[str]) -> None:
    """A valid map prints one line per turn to stdout."""
    map_path = str(REPO_ROOT / "maps" / "easy" / "01_linear_path.txt")
    main._run_simulation(map_path)
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert len(lines) > 0
    for line in lines:
        for token in line.split():
            assert _TURN_TOKEN.match(token), f"malformed token: {token!r}"


def test_run_simulation_prints_capacity_info(capsys: pytest.CaptureFixture[str]) -> None:
    """--capacity-info adds indented capacity lines under turns that use them."""
    map_path = str(REPO_ROOT / "maps" / "easy" / "03_basic_capacity.txt")
    main._run_simulation(map_path, capacity_info=True)
    out = capsys.readouterr().out
    assert any(line.startswith("  ") for line in out.splitlines())


def test_run_simulation_exits_on_bad_map(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A malformed map prints an error to stderr and exits with status 1."""
    bad_map = tmp_path / "broken.txt"
    bad_map.write_text("not a valid map file\n")

    with pytest.raises(SystemExit) as exc_info:
        main._run_simulation(str(bad_map))

    assert exc_info.value.code == 1
    assert "error:" in capsys.readouterr().err
