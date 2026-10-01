*This project has been created as part of the 42 curriculum by jzorreta.*

# Fly-In

A drone-fleet router: given a map of zones connected by links, and a number of drones starting at a shared hub, compute a turn-by-turn plan that gets every drone to the end hub as fast as possible without ever exceeding a zone's or connection's capacity, then play that plan back visually.

## Description

Each map is a small graph: zones (nodes) linked by connections (edges). Zones can be `normal`, `restricted` (costs 2 turns to enter instead of 1), `priority` (preferred when routes tie), or `blocked` (impassable). Both zones and connections can carry a capacity, a maximum number of drones allowed to occupy them at the same time so drones sometimes have to wait their turn rather than pathing straight through.

The program reads a map file, plans every drone's route one at a time against a shared occupancy table (so no drone's plan can ever violate a capacity already committed by an earlier drone), and either prints the resulting turn-by-turn schedule or animates it in a `pygame` window.

### Project layout

Twelve modules under `src/`, with the maps beside it at the root. Each module has a single job. The routing core stacks in a straight line - `simulation` drives `planner`, which reads `graph` and `reservation` - and the command line, the map lookup and the `pygame` layer each sit in their own file on top of it.

| Module | Responsibility |
| --- | --- |
| `mapfile.py` | `Zone`, `Connection`, `MapData`, and the `MapParser` that reads a `.txt` map with line-numbered errors |
| `drone.py` | one drone, and its turn-by-turn plan of events |
| `graph.py` | adjacency-list view of the map, blocked zones excluded, plus the reachability check |
| `reservation.py` | per-turn occupancy of every zone and connection |
| `planner.py` | one drone's route: Dijkstra over `(zone, turn)` states |
| `simulation.py` | plans every drone in order, renders the turn-by-turn output |
| `maplist.py` | finding, name-matching and listing the bundled maps |
| `picker.py` | the `pygame` map list |
| `viewer.py` | the `pygame` playback window |
| `session.py` | the list ⇄ viewer loop, over the one shared window |
| `parser.py` | the command-line interface |
| `__main__.py` | the entry point, and everything that reaches the terminal |

All twelve live in `src/`, and `__main__.py` is what makes the folder itself runnable: `uv run python3 src`. `maps/` sits next to it at the repository root, so map paths are written relative to the root - `uv run python3 src maps/easy/01_linear_path.txt`.

Only `picker.py`, `viewer.py` and `session.py` import `pygame`, so everything else - the parser, the graph, the capacity rules and the pathfinding - runs and is tested with no display at all. `__main__.py` imports `session` from inside the branch that needs it rather than at the top of the file, because importing `pygame` prints a banner that would otherwise land in the middle of the plan `--simulate` prints.

Output is the other deliberate seam. `Simulation.turns()` returns the schedule as a list of `Turn` records - the move line, and `(used, capacity)` for every zone and connection on that turn - and decides nothing about how any of it is shown. `session.py` is handed a printer rather than owning one, and `main()` supplies that printer once (`show_plan`), so the viewer path and `--simulate` print identically and an output flag reaches both at once.

## Instructions

Install dependencies and run:

```sh
make install          # uv sync
make run              # opens the map list
```

`make run` opens a list of every map under `maps/`, grouped by difficulty. Arrow keys browse, `enter` opens the highlighted map, `esc` quits. From the viewer, `m` goes back to the list, so you can walk through several maps without relaunching.

To skip the list and open one map directly, name any part of it:

```sh
make maps                  # print the map list to the terminal
make run MAP=maze          # opens maps/hard/01_maze_nightmare.txt
make run MAP=challenger    # opens the 25-drone challenger map
```

Extra flags go in `ARGS`:

```sh
make run MAP=maze ARGS=--simulate
```

or directly with `uv`:

```sh
uv run python3 src                        # the map list, then the viewer
uv run python3 src maze                   # viewer, matched by partial name
uv run python3 src hard/02_capacity_hell  # or by path fragment
uv run python3 src maze --simulate        # print the plan, no window
uv run python3 src --list                 # list the maps and exit
```

`--simulate` only says whether to *skip the window*: the plan is printed to the terminal whichever way you run it, and leaving the map out always opens the map list first, in either mode.

A name matching several maps is rejected with the list of candidates, rather than guessing.

Beside the four bundled difficulty categories there is a `custom` one, holding
small single-purpose maps for testing: `err_*` files that must be rejected with
a clear message, and `ok_*` files that each pin down one rule (capacity,
movement cost, zone type, parser defaults). See
[`maps/custom/README.md`](maps/custom/README.md) for what each checks and the
exact message or schedule it produces.

`make lint` runs `flake8` and `mypy`; `make lint-strict` runs `mypy --strict`.

### The map list

| Key | Action |
| --- | --- |
| `up` / `down` | browse (wraps at both ends) |
| `page up` / `page down`, `home` / `end` | jump |
| `enter` | open the highlighted map |
| `esc` | quit |

### The viewer

| Key | Action |
| --- | --- |
| `space` | pause / resume (replays from the start once finished) |
| `left` / `right` | step one whole turn back / forward, and pause |
| `r` | restart |
| `m` (or `backspace`) | back to the map list |
| `esc` (or `q`) | quit |

The map list and the viewer share **one** window for the whole session, created once by `viewer.open_window()` and handed to both. The window is resizable, and the map is re-fitted to it. `VIDEORESIZE` is handled by re-fetching the surface SDL has already resized, never by calling `set_mode` - calling `set_mode` again makes SDL destroy and rebuild the window, which under a tiling Wayland compositor (Hyprland, sway) shows up as the window closing and reopening in a loop, because the compositor resizes it again the moment it is re-mapped.

## Resources

- [Dijkstra's algorithm](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm) - the base algorithm behind `DronePlanner.plan()`, adapted here to search over `(zone, turn)` states instead of plain nodes so that time-dependent capacity can block a move.
- [Python `heapq` documentation](https://docs.python.org/3/library/heapq.html) - the binary heap used to always expand the earliest-arriving state first.
- [Pygame-CE documentation](https://pyga.me/docs/) - used for the map viewer (`viewer.py`).
- [mypy documentation](https://mypy.readthedocs.io/) - used to satisfy the project's mandatory strict type-checking.

## Algorithm explanation

Each drone's route is found with **Dijkstra's algorithm** over a state space of `(zone, turn)` pairs rather than just zones, since the cost of entering a zone depends on its type, and a move can be blocked by capacity at a *specific* turn, the turn number has to be part of the search state.
This is implemented in `DronePlanner.plan()` (`planner.py`) with a binary heap (`heapq`) keyed on turn, so the search always expands the earliest-arriving state first - the first time it pops the destination zone, that's the fastest valid arrival.

Successor generation (`_successors`) accounts for:

- **normal/priority zones**: cost 1 turn to enter.
- **restricted zones**: cost 2 turns, modeled as a `TRANSIT` state mid-connection followed by an `ARRIVE` state, so a drone is genuinely "in flight" (and occupying the connection) for both turns.
- **blocked zones**: excluded from the graph entirely (`Graph.__init__` never adds an edge into one).
- **waiting**: a drone may stay in its current zone for a turn if that zone still has room, letting it wait out a capacity conflict instead of failing to path.
- a **priority-zone tie-break**: among equal-turn-cost options, the search lexicographically prefers paths that pass through more `priority` zones (tracked as a bonus count alongside the arrival turn).

**Hub capacity**: every other zone holds its `max_drones` (default 1), but the two hubs hold `nb_drones` - the whole fleet starts in one and is delivered to the other, so the fleet size *is* their capacity (`ReservationTable.__init__`). Sequential planning keeps that from ever binding: when drone *k* is planned only *k-1* routes are committed, so a hub can always take one more.

**Capacity and drone ordering**: drones are planned strictly one at a time, in `D1..Dn` order (`Simulation.__init__`). Each finished plan is immediately committed to a shared `ReservationTable` (`reservation.py`), which every subsequent drone's search consults via `has_room`. Planning sequentially rather than jointly is what makes per-drone Dijkstra sufficient, no drone's search ever needs to reason about drones that haven't been planned yet, since those come later and won't shrink its capacity.

**Search horizon**: `DronePlanner` needs a turn limit, because waiting is always allowed and the `(zone, turn)` state space would otherwise be infinite. `Simulation._plan_all` sets it to the turn the last planned drone lands on, plus one walk across the whole map (`2 * zones + 1`). That bound is provably enough rather than a guess: once the earlier drones have landed, nothing is reserved any more, so a drone can always wait them out and then walk a free path - no reachable route is ever cut off for being too late.

**Unsolvable maps**: the only way a map can fail is for no path to exist at all, since capacity can delay a drone but never strand it. `Graph.reachable()` - a plain breadth-first search over the same adjacency list - checks that once, up front, so a disconnected map or one whose only route runs through a `blocked` zone is reported immediately and by name instead of being discovered by an exhausted search.

## Performance

The subject's reference targets are turn counts to match or beat. Measured against the bundled maps with `--simulate`:

| Map | Drones | Target | Actual | Result |
| --- | --- | --- | --- | --- |
| `easy/01_linear_path` | 2 | ≤6 | 4 | met |
| `easy/02_simple_fork` | 4 | ≤8 | 4 | met |
| `easy/03_basic_capacity` | 4 | ≤6 | 4 | met |
| `medium/01_dead_end_trap` | 5 | ≤12 | 8 | met |
| `medium/02_circular_loop` | 6 | ≤15 | 15 | met |
| `medium/03_priority_puzzle` | 5 | ≤12 | 7 | met |
| `hard/01_maze_nightmare` | 8 | ≤30 | 13 | met |
| `hard/02_capacity_hell` | 12 | ≤35 | 16 | met |
| `hard/03_ultimate_challenge` | 15 | ≤45 | 26 | met |
| `challenger/01_the_impossible_dream` (bonus, optional) | 25 | ≤45 | 43 | met |

Every mandatory target is met, and the optional Challenger map beats the 45-turn reference record.

## Visual representation

The `pygame` viewer (`viewer.py`) is deliberately small: two classes, and no options to configure.

`MapView` places zones at their `(x, y)` map coordinates, scaled to fit the window. One scale factor is used for both axes so the map keeps its proportions, and the result is centred rather than pinned to a corner - otherwise a map with no vertical spread collapses onto the top edge. It also measures the closest pair of zones and derives the zone radius from that gap, so a sparse map draws large circles while a dense one (the challenger map packs 40+ zones into a narrow band) shrinks them instead of drawing them on top of each other.

`Viewer` draws the frame and runs the loop. Connections are grey lines; zones are circles coloured by `zone_type` (blue = normal, red = restricted, green = priority, grey = blocked, with an X drawn on blocked zones); the two hubs get a white ring and their name. Drones are numbered dots that turn green once delivered.

**Drones are animated, not teleported.** Each drone's position is interpolated between its turn-N and turn-N+1 positions, so a move reads as a flight rather than a jump. A drone mid-flight toward a restricted zone sits at the midpoint of the connection it is crossing (its `TRANSIT` event), so the two-turn traversal genuinely shows as two turns of movement. Drones sharing a zone are fanned out around it, which keeps all 25 drones of the challenger map individually visible while they queue on the start hub.

A status line shows the current turn and how many drones have been delivered. Playback can be paused, restarted, and stepped one turn at a time in either direction - which makes it possible to walk a peer reviewer through a map turn by turn, matching exactly what `--simulate` prints.

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

Running `uv run python3 src --simulate maps/easy/01_linear_path.txt`:

```
D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
```

Each line is one turn; each `D<id>-<zone>` token means that drone arrived at that zone this turn. A drone still in flight toward a `restricted` zone prints `D<id>-<connection>` instead (the connection's declared `zoneA-zoneB` name) on its transit turn, then the zone name on the turn it lands - so the two-turn traversal is distinguishable in the output. This linear map has no restricted zones, so every token here is a zone; see `maps/medium/03_priority_puzzle.txt` for an example that exercises it. Here, `D1` and `D2` both start at `start` (turn 0, not printed) and take turns crossing the single-capacity connections one at a time - D2 has to wait a turn at `start` before it can follow D1 onto`waypoint1`, since every connection here defaults to `max_link_capacity: 1`.

**AI usage**: AI was used in an exploratory, conceptual capacity during development - mainly to talk through how to model the pathfinding search (e.g. why the state needs to include the turn number, not just the zone) and to sanity-check design decisions, rather than to generate the core implementation. It was also used to..end flake8's misery and mypy errors that I and too annoyed to correct them every time i sneezed or smth