import argparse
import sys

from parser import parse_map
from simulation import Simulation, SimulationError

DEFAULT_MAP = "maps/easy/01_linear_path.txt"


def parse_args() -> argparse.Namespace:
    """Define and parse the command-line interface."""
    parser = argparse.ArgumentParser(
        description="Visualize or simulate a Fly-in drone network map.",
    )
    parser.add_argument(
        "map_path",
        nargs="?",
        default=None,
        help="path to the map .txt file; omit to choose one from a menu",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="run the routing simulation and print the turn-by-turn plan "
        "instead of opening the map viewer",
    )
    parser.add_argument(
        "--capacity-info",
        action="store_true",
        help="alongside the turn-by-turn plan, print per-turn zone and "
        "connection capacity usage",
    )
    return parser.parse_args()


def _run_simulation(map_path: str, capacity_info: bool = False) -> None:
    """Parse a map, simulate it, and print the turn-by-turn output.

    Args:
        map_path: Path to the map .txt file to simulate.
        capacity_info: If True, also print per-turn capacity usage.
    """
    try:
        simulation = Simulation(parse_map(map_path))
    except (ValueError, FileNotFoundError, SimulationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    for turn, line in enumerate(simulation.turn_lines(), start=1):
        print(line)
        if capacity_info:
            for info in simulation.capacity_lines(turn):
                print(f"  {info}")


def main() -> None:
    """Parse CLI arguments and start the viewer or simulation."""
    args = parse_args()
    map_path = args.map_path

    if map_path is None:
        from menu import select_map

        map_path = select_map(default_path=DEFAULT_MAP)
        if map_path is None:
            return

    if args.simulate or args.capacity_info:
        _run_simulation(map_path, capacity_info=args.capacity_info)
    else:
        from viewer import run

        run(map_path)


if __name__ == "__main__":
    main()
