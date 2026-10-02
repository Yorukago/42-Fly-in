import sys
from collections.abc import Callable

from maplist import format_maps, resolve_map
from parser import parse_args
from simulation import MapError, Simulation, load_simulation


def print_plan(simulation: Simulation, capacity_info: bool = False) -> None:
    for turn in simulation.turns():
        print(turn.moves)
        # if not capacity_info:
        #     continue
        # for name, (used, capacity) in turn.zones.items():
        #     print(f"  Zone {name}: {used}/{capacity} drones")
        # for name, (used, capacity) in turn.connections.items():
        #     print(f"  Connection {name}: {used}/{capacity} capacity used")
    print(f"Total turns: {simulation.total_turns}")


def run_simulation(
    map_path: str | None, show_plan: Callable[[Simulation], None]
) -> None:
    """Print one map's plan, offering the map list first if none was named.

    Raises:
        SystemExit: If the map cannot be read or solved.
    """
    if map_path is None:
        from session import choose_map

        map_path = choose_map()
        if map_path is None:
            return

    try:
        _, simulation = load_simulation(map_path)
    except MapError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    show_plan(simulation)


def main() -> None:
    """List the maps, print a plan, or open the viewer."""
    args = parse_args()

    if args.list:
        print(format_maps())
        return

    chosen = resolve_map(args.map_path) if args.map_path is not None else None
    show_plan = print_plan

    # def show_plan(simulation: Simulation) -> None:
    #     print_plan(simulation, args.capacity_info)

    if args.simulate:
        run_simulation(chosen, show_plan)
        return

    from session import run_session
    run_session(chosen, show_plan)


if __name__ == "__main__":
    main()
