# Fly-In

A drone-fleet router: given a map of zones connected by links, and a number of drones starting at a shared hub, compute a turn-by-turn plan that gets every drone to the end hub as fast as possible without ever exceeding a zone's or connection's capacity, then play that plan back visually.

## Description

Each map is a small graph: zones (nodes) linked by connections (edges). Zones can be `normal`, `restricted` (costs 2 turns to enter instead of 1), `priority` (preferred when routes tie), or `blocked` (impassable). Both zones and connections can carry a capacity, a maximum number of drones allowed to occupy them at the same time so drones sometimes have to wait their turn rather than pathing straight through.

The program reads a map file, plans every drone's route one at a time against a shared occupancy table (so no drone's plan can ever violate a capacity already committed by an earlier drone), and either prints the resulting turn-by-turn schedule or animates it in a `pygame` window.

## Instructions

Install dependencies and run:

```sh
make install          # uv sync
make run              # opens the map picker menu
```

or directly with `uv`:

```sh
uv run python src/main.py                       # menu, then viewer
uv run python src/main.py maps/easy/01_linear_path.txt   # viewer, given map
uv run python src/main.py --simulate maps/easy/01_linear_path.txt        # text output only
uv run python src/main.py --capacity-info maps/easy/01_linear_path.txt   # text output + per-turn capacity usage
```

With no map path, a terminal menu lets you pick one from `maps/` (`easy/`, `medium/`, `hard/`, `challenger/`, `custom/`). In the viewer: `space` pauses/resumes, `r` restarts, `esc` quits.

`make lint` runs `flake8` and `mypy`; `make lint-strict` runs `mypy --strict`.

## Algorithm explanation

Each drone's route is found with **Dijkstra's algorithm** over a state space of `(zone, turn)` pairs rather than just zones, since the cost of entering a zone depends on its type, and a move can be blocked by capacity at a *specific* turn, the turn number has to be part of the search state.
This is implemented in `DronePlanner.plan()` (`src/planner.py`) with a binary heap (`heapq`) keyed on turn, so the search always expands the earliest-arriving state first — the first time it pops the destination zone, that's the fastest valid arrival.

Successor generation (`_successors`) accounts for:

- **normal/priority zones**: cost 1 turn to enter.
- **restricted zones**: cost 2 turns, modeled as a `TRANSIT` state mid-connection followed by an `ARRIVE` state, so a drone is genuinely "in flight" (and occupying the connection) for both turns.
- **blocked zones**: excluded from the graph entirely (`Graph.__init__` never adds an edge into one).
- **waiting**: a drone may stay in its current zone for a turn if that zone still has room, letting it wait out a capacity conflict instead of failing to path.
- a **priority-zone tie-break**: among equal-turn-cost options, the search lexicographically prefers paths that pass through more `priority` zones (tracked as a bonus count alongside the arrival turn).

**Capacity and drone ordering**: drones are planned strictly one at a time, in `D1..Dn` order (`Simulation._plan_all`). Each finished plan is immediately committed to a shared `ReservationTable` (`src/reservation.py`), which every subsequent drone's search consults via `has_zone_room` / `has_connection_room`. Planning sequentially rather than jointly is what makes per-drone Dijkstra sufficient, no drone's search ever needs to reason about drones that haven't been planned yet, since those come later and won't shrink its capacity.

**Search horizon**: `DronePlanner` needs a turn limit to keep the state space finite. `Simulation` starts with a horizon proportional to map size and drone count and doubles it on `UnreachableError` (up to a hard cap), so most maps solve on the first pass and pathological ones get retried with more room before being declared unsolvable.

## Visual representation

The `pygame` viewer (`src/viewer.py`) renders zones at their `(x, y)` map coordinates, scaled to fit the window, connected by lines. Zones are colored either by their explicit `color=` metadata or, failing that, by `zone_type` (blue=normal, red=restricted, green=priority, gray=blocked), the type-based fill is only a fallback, used when no explicit `color=` or custom theme artwork is present. Start/end hubs get a white ring so they're identifiable at a glance, and zones/connections with capacity greater than 1 show their capacity number directly on the map, so bottlenecks are visible before playback even starts.

Drones are drawn as labeled circles that move turn-by-turn along each map's precomputed track (`_drone_track`); a drone mid-flight through a restricted zone is drawn at the connection's midpoint rather than snapping between endpoints, so the two-turn traversal actually reads as movement. Drones sharing a zone are fanned out in a small circle instead of overlapping. A HUD in the corner shows the current turn, delivery count, and playback controls. Optional custom artwork can be dropped into `assets/` (`background.png`, `drone.png`, `zone_<type>.png`) and is picked up automatically by `theme.py`; without it, the viewer falls back to plain shapes, so the visuals degrade gracefully rather than breaking.

## Example input and output

Input (`maps/easy/01_linear_path.txt`):

```
# Easy Level 1: Simple linear path
nb_drones: 2

start_hub: start 0 0 [color=green]
hub: waypoint1 1 0 [color=blue]
hub: waypoint2 2 0 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-waypoint1
connection: waypoint1-waypoint2
connection: waypoint2-goal
```

Running `uv run python src/main.py --simulate maps/easy/01_linear_path.txt`:

```
D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
```

Each line is one turn; each `D<id>-<zone>` token means that drone arrived at that zone this turn. Here, `D1` and `D2` both start at `start` (turn 0, not printed) and take turns crossing the single-capacity connections one at a time — D2 has to wait a turn at `start` before it can follow D1 onto`waypoint1`, since every connection here defaults to `max_link_capacity: 1`.
Adding `--capacity-info` prints per-turn zone/connection occupancy alongside the same schedule, e.g. `Connection start-waypoint1: 1/1 capacity used` — see `--capacity-info` in the Instructions section above.
