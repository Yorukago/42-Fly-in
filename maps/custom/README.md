# Custom maps

Small, single-purpose maps for walking through the evaluation. Each one is a
few lines long and exercises exactly one rule, so a failure points straight at
the code responsible.

`err_*` maps are **meant to be rejected** - they check that a bad file produces
a clear message and exit status 1 rather than a traceback. `ok_*` maps are
valid and check that a rule is actually enforced.

Run any of them the usual way:

```sh
uv run python3 src maps/custom/err_04_invalid_zone_type.txt --simulate
uv run python3 src err_04                 # partial names work too
```

They also appear under `custom` in the map list (`--list`, or the picker), so
an `err_*` map can be opened from the viewer to show it failing gracefully:
the error prints to the terminal and the list comes back up.

## Rejected files (`err_*`)

Every one exits 1 and prints a single `error:` line. All but the last two are
caught by the parser, with the line number that caused them.

| Map | Message |
| --- | --- |
| `err_01_missing_nb_drones` | `Map file is missing 'nb_drones' definition` |
| `err_02_missing_start_hub` | `Map file is missing 'start_hub' definition` |
| `err_03_missing_end_hub` | `Map file is missing 'end_hub' definition` |
| `err_04_invalid_zone_type` | `Line 5: invalid zone 'storm 1 0' (unknown zone type 'lava')` |
| `err_05_zero_max_drones` | `Line 5: invalid zone 'relay 1 0' (max_drones must be a positive integer, got '0')` |
| `err_06_zero_link_capacity` | `Line 8: invalid connection 'start-relay' (max_link_capacity must be a positive integer, got '0')` |
| `err_07_duplicate_zone_name` | `Line 6: duplicate zone name 'relay'` |
| `err_08_duplicate_connection` | `Line 9: duplicate connection 'relay' <-> 'start'` |
| `err_09_duplicate_start_hub` | `Line 5: duplicate start_hub definition` |
| `err_10_unknown_zone_in_connection` | `Line 7: unknown zone 'ghost' in connection` |
| `err_11_self_connection` | `Line 9: invalid connection 'relay-relay' (a connection cannot link a zone to itself)` |
| `err_12_unknown_keyword` | `Line 5: unrecognised line format: 'zone: relay 1 0'` |
| `err_13_dash_in_zone_name` | `Line 5: invalid zone 'relay-one 1 0' (zone names cannot contain a dash)` |
| `err_14_bad_coordinates` | `Line 5: invalid zone 'relay east 0' (x must be an integer, got 'east')` |
| `err_15_malformed_metadata` | `Line 5: invalid metadata token 'color'` |
| `err_16_nb_drones_not_positive` | `Line 2: nb_drones must be a positive integer, got '0'` |
| `err_17_disconnected_graph` | `D1 could not reach 'goal' within 5000 turns; the map may be unsolvable.` |
| `err_18_blocked_only_route` | `D1 could not reach 'goal' within 5000 turns; the map may be unsolvable.` |

The last two parse cleanly - they are rejected by the simulation, not the
parser, because no route exists. Both answer in well under a second: the
search horizon doubles up to its cap instead of running forever.

## Valid files (`ok_*`)

| Map | Checks | Output |
| --- | --- | --- |
| `ok_01_single_drone` | the smallest working map | `D1-relay` / `D1-goal` |
| `ok_02_capacity_bottleneck` | `max_drones=1` makes three drones queue one per turn; waiting drones print nothing | 4 turns |
| `ok_03_wide_connection` | `max_link_capacity=3` lets the whole fleet cross together | 2 turns |
| `ok_04_restricted_zone` | a restricted zone costs 2 turns, and prints `D1-start-storm` while in flight | 3 turns |
| `ok_05_priority_tiebreak` | two equal-length routes; the `priority` one wins | routes via `express` |
| `ok_06_blocked_detour` | the 2-turn route is blocked, so the 3-turn detour is taken | routes via `detour_a` |
| `ok_07_bare_defaults` | no metadata anywhere: `normal`, `max_drones=1`, `max_link_capacity=1` all default, so D2 waits a turn | 3 turns |
| `ok_08_high_capacity` | very large capacities; six drones move as one group | 2 turns |

`ok_02` and `ok_07` are the two to show for "stationary drones are omitted from
the output": a waiting drone contributes no token to its turn's line.
