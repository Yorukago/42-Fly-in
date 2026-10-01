import argparse


def parse_args() -> argparse.Namespace:
    """Define and parse the command line."""
    parser = argparse.ArgumentParser(
        prog="fly-in",
        description="Visualize or simulate a Fly-in drone network map.",
        epilog="the map may be a path, or any part of a map's name (e.g. 'maze'); "
        "omit it to choose one from the list",
    )
    parser.add_argument(
        "map_path",
        nargs="?",
        metavar="map",
        help="map to open; omit to pick one from the list",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="print the turn-by-turn plan instead of opening the viewer",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list the available maps and exit",
    )
    # parser.add_argument(
    #     "--capacity-info",
    #     action="store_true",
    # )
    return parser.parse_args()
