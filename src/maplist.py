import os
import sys

MAPS_DIR = "maps"
CATEGORY_ORDER = ("easy", "medium", "hard", "challenger", "custom")


def find_maps(root: str = MAPS_DIR) -> list[str]:
    """Return every map under the maps directory, easiest category first."""

    def rank(path: str) -> tuple[int, str]:
        """Sort known categories by difficulty, unknown ones alphabetically."""
        category = os.path.basename(os.path.dirname(path)).lower()
        if category in CATEGORY_ORDER:
            return (CATEGORY_ORDER.index(category), path)
        return (len(CATEGORY_ORDER), path)

    found = [
        os.path.join(directory, name)
        for directory, _, names in os.walk(root)
        for name in sorted(names)
        if name.endswith(".txt")
    ]
    return sorted(found, key=rank)


def require_maps() -> list[str]:
    """Return every bundled map.

    Raises:
        SystemExit: If there are no maps to offer.
    """
    paths = find_maps()
    if not paths:
        print(f"error: no maps found under {MAPS_DIR}/", file=sys.stderr)
        raise SystemExit(1)
    return paths


def resolve_map(wanted: str) -> str:
    """Turn what the user typed into a map path.

    A real path is used as given; anything else is matched against the
    bundled maps, so `maze` finds `maps/hard/01_maze_nightmare.txt`.

    Raises:
        SystemExit: If nothing matches, or the name is ambiguous. Both list
            the candidates, rather than guessing.
    """
    if os.path.isfile(wanted):
        return wanted

    matches = [path for path in find_maps() if wanted.lower() in path.lower()]
    if len(matches) == 1:
        return matches[0]

    if not matches:
        print(f"error: no map matching {wanted!r}", file=sys.stderr)
        print(f"\navailable maps:\n{format_maps()}", file=sys.stderr)
    else:
        print(f"error: {wanted!r} matches {len(matches)} maps:", file=sys.stderr)
        print("\n".join(f"  {path}" for path in matches), file=sys.stderr)
    raise SystemExit(1)


def format_maps() -> str:
    """Return the bundled maps as a printable list, grouped by category."""
    lines: list[str] = []
    current = ""
    for path in find_maps():
        category = os.path.basename(os.path.dirname(path))
        if category != current:
            lines.append(f"\n{category}:")
            current = category
        lines.append(f"  {os.path.basename(path)[:-4]:<28} {path}")
    return "\n".join(lines).lstrip("\n")
