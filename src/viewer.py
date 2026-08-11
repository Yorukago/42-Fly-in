import math
import sys
from collections import defaultdict

import pygame

from drone import Drone, EventKind
from parser import MapData, parse_map
from simulation import Simulation, SimulationError
from theme import Theme, load_theme
from zone import Zone, ZoneType

WINDOW_SIZE = (900, 700)
WINDOW_SCREEN_FRACTION = 0.85
MIN_WINDOW_SIZE = WINDOW_SIZE
MARGIN = 60
ZONE_RADIUS = 22
BACKGROUND = (24, 26, 32)
LINE_COLOR = (120, 124, 138)
TEXT_COLOR = (235, 235, 240)

DRONE_RADIUS = 8
DRONE_COLOR = (250, 210, 40)
DRONE_LABEL_COLOR = (30, 30, 20)
TURN_DURATION = 0.8

ZONE_TYPE_FILL = {
    ZoneType.NORMAL: (90, 130, 200),
    ZoneType.BLOCKED: (70, 70, 70),
    ZoneType.RESTRICTED: (200, 90, 90),
    ZoneType.PRIORITY: (90, 190, 120),
}

NAMED_COLORS = {
    "red": (200, 60, 60),
    "green": (60, 190, 90),
    "blue": (70, 120, 220),
    "yellow": (225, 195, 60),
    "gray": (130, 130, 130),
    "grey": (130, 130, 130),
    "orange": (230, 140, 50),
    "purple": (160, 90, 200),
    "black": (20, 20, 20),
    "white": (235, 235, 235),
}


class MapLayout:
    """Computes screen positions for zones, scaled to fit the window."""

    def __init__(self, data: MapData, window_size: tuple[int, int]) -> None:
        """Build a layout from parsed map data.

        Args:
            data: The parsed MapData whose zones will be positioned.
            window_size: The current (width, height) of the window to fit.
        """
        self.data = data
        self.window_size = window_size
        self.positions: dict[str, tuple[int, int]] = {}
        self._compute_positions()

    def _compute_positions(self) -> None:
        """Map each zone's (x, y) map coordinates to screen pixels.

        A single scale factor is used for both axes (picking whichever is
        more constrained) so the map keeps its true proportions instead of
        being stretched independently to fill the window. The scaled
        content is then centered in the drawable area, rather than
        anchored to the top-left corner — otherwise a map with little or
        no vertical spread (e.g. a straight line) collapses to y=0 and
        ends up pinned to the top regardless of window size.
        """
        xs = [zone.x for zone in self.data.zones.values()]
        ys = [zone.y for zone in self.data.zones.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        span_x = max_x - min_x
        span_y = max_y - min_y

        draw_w = max(self.window_size[0] - 2 * MARGIN, 1)
        draw_h = max(self.window_size[1] - 2 * MARGIN, 1)

        candidate_scales = []
        if span_x > 0:
            candidate_scales.append(draw_w / span_x)
        if span_y > 0:
            candidate_scales.append(draw_h / span_y)
        scale = min(candidate_scales) if candidate_scales else 1.0

        content_w = span_x * scale
        content_h = span_y * scale
        offset_x = MARGIN + (draw_w - content_w) / 2
        offset_y = MARGIN + (draw_h - content_h) / 2

        for zone in self.data.zones.values():
            px = offset_x + (zone.x - min_x) * scale
            py = offset_y + (zone.y - min_y) * scale
            self.positions[zone.name] = (int(px), int(py))


def zone_fill_color(zone: Zone) -> tuple[int, int, int]:
    """Pick an RGB fill color for a zone from its metadata or type.

    Args:
        zone: The zone to color.

    Returns:
        An (r, g, b) tuple.
    """
    if zone.color != "none" and zone.color in NAMED_COLORS:
        return NAMED_COLORS[zone.color]
    return ZONE_TYPE_FILL[zone.zone_type]


def draw_map(
    screen: pygame.Surface,
    font: pygame.font.Font,
    data: MapData,
    layout: MapLayout,
    theme: Theme,
) -> None:
    """Draw all connections and zones of the map onto the screen.

    Args:
        screen: The pygame surface to draw on.
        font: Font used for zone labels.
        data: The parsed map data.
        layout: Precomputed screen positions for each zone.
        theme: Optional custom artwork; falls back to plain shapes.
    """
    if theme.background is not None:
        background = pygame.transform.smoothscale(theme.background, screen.get_size())
        screen.blit(background, (0, 0))
    else:
        screen.fill(BACKGROUND)

    for conn in data.connections:
        start = layout.positions[conn.zone_a]
        end = layout.positions[conn.zone_b]
        pygame.draw.line(screen, LINE_COLOR, start, end, 2)

        if conn.max_link_capacity > 1:
            mid = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
            cap_label = font.render(f"x{conn.max_link_capacity}", True, (200, 200, 90))
            screen.blit(cap_label, cap_label.get_rect(center=mid))

    for zone in data.zones.values():
        pos = layout.positions[zone.name]
        image = theme.zone_images.get(zone.zone_type)
        if image is not None:
            screen.blit(image, image.get_rect(center=pos))
        else:
            fill = zone_fill_color(zone)
            pygame.draw.circle(screen, fill, pos, ZONE_RADIUS)

        if zone.is_start or zone.is_end:
            ring_color = (255, 255, 255)
            pygame.draw.circle(screen, ring_color, pos, ZONE_RADIUS + 4, 3)

        if zone.max_drones > 1:
            cap_label = font.render(str(zone.max_drones), True, (20, 20, 20))
            screen.blit(cap_label, cap_label.get_rect(center=pos))

        name_label = font.render(zone.name, True, TEXT_COLOR)
        label_pos = (pos[0] - name_label.get_width() // 2, pos[1] + ZONE_RADIUS + 6)
        screen.blit(name_label, label_pos)


def _drone_track(
    drone: Drone, layout: MapLayout, start_zone: str
) -> dict[int, tuple[float, float]]:
    """Precompute a drone's screen position for every turn of its plan.

    A drone mid-flight on a 2-turn restricted move (a TRANSIT event) is
    placed at the midpoint of the connection it's traversing, so the
    animation shows it "in flight" rather than stuck in place.

    Args:
        drone: The drone whose plan to trace.
        layout: Precomputed zone screen positions.
        start_zone: The name of the map's start zone.

    Returns:
        A mapping of turn number (0..arrival_turn) to a screen position.
    """
    track: dict[int, tuple[float, float]] = {0: layout.positions[start_zone]}
    current_zone = start_zone

    for event in drone.plan.events:
        if event.kind is EventKind.TRANSIT:
            start_pos = layout.positions[current_zone]
            end_pos = layout.positions[event.zone]
            track[event.turn] = (
                (start_pos[0] + end_pos[0]) / 2,
                (start_pos[1] + end_pos[1]) / 2,
            )
        else:
            track[event.turn] = layout.positions[event.zone]
            current_zone = event.zone

    return track


def draw_drones(
    screen: pygame.Surface,
    font: pygame.font.Font,
    drones: list[Drone],
    tracks: dict[int, dict[int, tuple[float, float]]],
    turn: int,
    theme: Theme,
) -> None:
    """Draw every drone at its position for the given simulation turn.

    Args:
        screen: The pygame surface to draw on.
        font: Font used for drone id labels.
        drones: All drones in the simulation.
        tracks: Each drone's precomputed per-turn screen position.
        turn: The simulation turn currently being displayed.
        theme: Optional custom artwork; falls back to a plain circle.
    """
    grouped: dict[tuple[int, int], list[Drone]] = defaultdict(list)
    for drone in drones:
        clamped_turn = min(turn, drone.plan.arrival_turn)
        x, y = tracks[drone.drone_id][clamped_turn]
        grouped[(int(x), int(y))].append(drone)

    spread = DRONE_RADIUS * 1.4
    for (x, y), group in grouped.items():
        for i, drone in enumerate(group):
            if len(group) == 1:
                pos = (x, y)
            else:
                angle = 2 * math.pi * i / len(group)
                pos = (
                    x + int(spread * math.cos(angle)),
                    y + int(spread * math.sin(angle)),
                )
            if theme.drone is not None:
                screen.blit(theme.drone, theme.drone.get_rect(center=pos))
            else:
                pygame.draw.circle(screen, DRONE_COLOR, pos, DRONE_RADIUS)
            label = font.render(str(drone.drone_id), True, DRONE_LABEL_COLOR)
            screen.blit(label, label.get_rect(center=pos))


def draw_hud(
    screen: pygame.Surface,
    font: pygame.font.Font,
    turn: int,
    total_turns: int,
    drones: list[Drone],
    paused: bool,
) -> None:
    """Draw the turn counter, delivery count, and control hints.

    Args:
        screen: The pygame surface to draw on.
        font: Font used for the HUD text.
        turn: The simulation turn currently being displayed.
        total_turns: The total number of turns in the simulation.
        drones: All drones in the simulation.
        paused: Whether playback is currently paused.
    """
    delivered = sum(1 for drone in drones if drone.plan.arrival_turn <= turn)
    status = "paused" if paused else "playing"
    lines = [
        f"turn {turn}/{total_turns} ({status})",
        f"delivered {delivered}/{len(drones)}",
        "[space] pause/resume   [r] restart   [esc] quit",
    ]
    for i, text in enumerate(lines):
        label = font.render(text, True, TEXT_COLOR)
        screen.blit(label, (10, 10 + i * 16))


def _initial_window_size() -> tuple[int, int]:
    """Pick a startup window size that fills most of the current screen.

    Big maps get cramped in a small, fixed-size window. Sizing off the
    actual desktop resolution (pygame must already be initialized) gives
    the visualizer room to breathe on any monitor, while still falling
    back to WINDOW_SIZE if that resolution can't be determined.
    """
    try:
        info = pygame.display.Info()
        screen_w, screen_h = info.current_w, info.current_h
    except pygame.error:
        return WINDOW_SIZE

    if screen_w <= 0 or screen_h <= 0:
        return WINDOW_SIZE

    width = max(int(screen_w * WINDOW_SCREEN_FRACTION), MIN_WINDOW_SIZE[0])
    height = max(int(screen_h * WINDOW_SCREEN_FRACTION), MIN_WINDOW_SIZE[1])
    return (width, height)


def run(filepath: str) -> None:
    """Load a map file, simulate it, and play back the drone routes.

    Args:
        filepath: Path to the map .txt file to visualize.
    """
    try:
        data = parse_map(filepath)
        simulation = Simulation(data)
    except (ValueError, FileNotFoundError, SimulationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return

    assert data.start_zone is not None  # guaranteed by a successful Simulation build

    def build_layout(window_size: tuple[int, int]) -> tuple[
        MapLayout, dict[int, dict[int, tuple[float, float]]]
    ]:
        assert data.start_zone is not None
        new_layout = MapLayout(data, window_size)
        new_tracks = {
            drone.drone_id: _drone_track(drone, new_layout, data.start_zone.name)
            for drone in simulation.drones
        }
        return new_layout, new_tracks

    total_turns = simulation.total_turns

    pygame.init()
    initial_size = _initial_window_size()
    layout, tracks = build_layout(initial_size)
    screen = pygame.display.set_mode(initial_size, pygame.RESIZABLE)
    pygame.display.set_caption(f"Fly-in map viewer — {filepath}")
    font = pygame.font.SysFont("monospace", 14)
    clock = pygame.time.Clock()
    theme = load_theme(ZONE_RADIUS, DRONE_RADIUS)

    current_turn = 0
    elapsed = 0.0
    paused = False

    running = True
    while running:
        dt = clock.tick(30) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                resized_surface = pygame.display.get_surface()
                if resized_surface is not None:
                    screen = resized_surface
                layout, tracks = build_layout(screen.get_size())
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    current_turn = 0
                    elapsed = 0.0
                    paused = False

        if not paused and current_turn < total_turns:
            elapsed += dt
            if elapsed >= TURN_DURATION:
                elapsed = 0.0
                current_turn += 1

        draw_map(screen, font, data, layout, theme)
        draw_drones(screen, font, simulation.drones, tracks, current_turn, theme)
        draw_hud(screen, font, current_turn, total_turns, simulation.drones, paused)
        pygame.display.flip()

    pygame.quit()
