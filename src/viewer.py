import math
from itertools import combinations

import pygame

from drone import Drone, EventKind
from mapfile import MapData, Zone, ZoneType
from simulation import Simulation

WINDOW_SIZE = (1000, 720)
MARGIN = 60
SECONDS_PER_TURN = 0.6
MAX_ZONE_RADIUS = 20
MIN_ZONE_RADIUS = 5

BACKGROUND = (17, 19, 26)
LINE = (92, 98, 116)
TEXT = (231, 234, 242)
WHITE = (255, 255, 255)
DRONE = (250, 210, 40)
DELIVERED = (74, 222, 128)

ZONE_COLOR = {
    ZoneType.NORMAL: (90, 130, 200),
    ZoneType.BLOCKED: (70, 70, 70),
    ZoneType.RESTRICTED: (200, 90, 90),
    ZoneType.PRIORITY: (90, 190, 120),
}

Point = tuple[float, float]


def zone_color(zone: Zone) -> tuple[int, int, int]:
    """Pick a zone's fill colour: its `color=` metadata, else its type's colour.

    A map may name any colour pygame knows (`red`, `darkred`, `cyan`...). An
    unknown name falls back to the type's colour rather than being an error,
    so a typo in a map still draws.
    """
    if zone.color != "none":
        try:
            named = pygame.Color(zone.color)
        except ValueError:
            return ZONE_COLOR[zone.zone_type]
        return (named.r, named.g, named.b)
    return ZONE_COLOR[zone.zone_type]


class MapView:
    """Screen positions for a map's zones, scaled to fit a window."""

    def __init__(self, data: MapData, size: tuple[int, int]) -> None:
        """Fit a map into a window of the given size."""
        self.data = data
        self.positions = self._fit(size)
        self.radius = self._radius()

    def _fit(self, size: tuple[int, int]) -> dict[str, tuple[int, int]]:
        """Scale zone coordinates into centred screen pixels.

        One scale factor serves both axes, so the map keeps its proportions
        instead of being stretched, and the result is centred rather than
        pinned to the top-left - otherwise a map with no vertical spread
        collapses onto y=0.
        """
        zones = self.data.zones.values()
        min_x, max_x = min(z.x for z in zones), max(z.x for z in zones)
        min_y, max_y = min(z.y for z in zones), max(z.y for z in zones)
        span_x, span_y = max_x - min_x, max_y - min_y

        width = max(size[0] - 2 * MARGIN, 1)
        height = max(size[1] - 2 * MARGIN, 1)
        scales = [width / span_x] if span_x else []
        if span_y:
            scales.append(height / span_y)
        scale = min(scales) if scales else 1.0

        left = MARGIN + (width - span_x * scale) / 2
        top = MARGIN + (height - span_y * scale) / 2
        return {
            zone.name: (
                int(left + (zone.x - min_x) * scale),
                int(top + (zone.y - min_y) * scale),
            )
            for zone in zones
        }

    def _radius(self) -> int:
        """Size zones from the closest pair, so dense maps draw smaller circles."""
        gaps = (math.dist(a, b) for a, b in combinations(self.positions.values(), 2))
        closest = min((gap for gap in gaps if gap > 0), default=float("inf"))
        if closest == float("inf"):
            return MAX_ZONE_RADIUS
        return max(MIN_ZONE_RADIUS, min(MAX_ZONE_RADIUS, int(closest * 0.4)))


class Viewer:
    """Plays a planned simulation back in a pygame window."""

    def __init__(
        self, screen: pygame.Surface, data: MapData, simulation: Simulation
    ) -> None:
        """Set up playback of an already-planned simulation.

        The picker and the viewer share one window for the whole session -
        see `open_window()`.
        """
        assert data.start_zone is not None  # guaranteed by a valid Simulation
        self.data = data
        self.drones = simulation.drones
        self.total_turns = simulation.total_turns
        self.start_name = data.start_zone.name

        self.screen = screen
        self.font = pygame.font.SysFont("monospace", 13)
        self.view = MapView(data, self.screen.get_size())
        self.tracks = {d.drone_id: self._track(d) for d in self.drones}
        self.arrival = {d.drone_id: d.arrival_turn for d in self.drones}

        self.time = 0.0
        self.paused = False
        self.running = True
        self.outcome = "quit"

    def _track(self, drone: Drone) -> dict[int, Point]:
        """Map each turn of one drone's route to a screen position.

        A drone in flight toward a restricted zone (a TRANSIT event) sits at
        the midpoint of the connection, so it reads as being in transit.
        """
        positions = self.view.positions
        track: dict[int, Point] = {0: positions[self.start_name]}
        current = self.start_name

        for event in drone.events:
            if event.kind is EventKind.TRANSIT:
                start, end = positions[current], positions[event.zone]
                track[event.turn] = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
            else:
                track[event.turn] = positions[event.zone]
                current = event.zone

        return track

    def _at_turn(self, drone_id: int, turn: int) -> Point:
        """Return a drone's position on a whole turn, fanned out if crowded.

        Drones sharing a zone are spread in rings around it, or 25 of them
        sitting on the start hub would draw as one dot.
        """
        def spot_of(other: int) -> Point:
            return self.tracks[other][max(0, min(turn, self.arrival[other]))]

        spot = spot_of(drone_id)
        sharing = sorted(other for other in self.tracks if spot_of(other) == spot)
        if len(sharing) == 1:
            return spot

        index = sharing.index(drone_id)
        ring = index // 6
        slots = min(6, len(sharing) - ring * 6)
        angle = 2 * math.pi * (index % 6) / slots
        distance = self.view.radius * 0.9 * (ring + 1)
        return (spot[0] + distance * math.cos(angle), spot[1] + distance * math.sin(angle))

    def _position(self, drone_id: int) -> Point:
        """Return a drone's position right now, interpolated between two turns."""
        clock = max(0.0, min(self.time, float(self.arrival[drone_id])))
        turn = int(clock)
        progress = clock - turn
        start = self._at_turn(drone_id, turn)
        end = self._at_turn(drone_id, turn + 1)
        return (
            start[0] + (end[0] - start[0]) * progress,
            start[1] + (end[1] - start[1]) * progress,
        )

    @property
    def turn(self) -> int:
        """Return the whole turn currently on screen."""
        return min(int(self.time), self.total_turns)

    @property
    def delivered(self) -> int:
        """Return how many drones have reached the end hub by now."""
        return sum(1 for d in self.drones if self.arrival[d.drone_id] <= self.time)

    def draw(self) -> None:
        """Draw one full frame: connections, zones, drones, status line."""
        self.screen.fill(BACKGROUND)

        for conn in self.data.connections:
            start = self.view.positions[conn.zone_a]
            end = self.view.positions[conn.zone_b]
            pygame.draw.line(self.screen, LINE, start, end, 2)

        for zone in self.data.zones.values():
            self._draw_zone(zone)

        for drone in self.drones:
            self._draw_drone(drone.drone_id)

        status = (
            f"turn {self.turn}/{self.total_turns}  ·  "
            f"delivered {self.delivered}/{len(self.drones)}"
            f"{'  ·  paused' if self.paused else ''}"
        )
        self.screen.blit(self.font.render(status, True, TEXT), (12, 12))
        hints = "[space] pause  [<- ->] step  [r] restart  [m] maps  [esc] quit"
        self.screen.blit(self.font.render(hints, True, LINE), (12, 32))

    def _draw_zone(self, zone: Zone) -> None:
        """Draw one zone: a circle, a type marker, and a name if it is a hub."""
        pos = self.view.positions[zone.name]
        radius = self.view.radius
        pygame.draw.circle(self.screen, zone_color(zone), pos, radius)

        if zone.zone_type is ZoneType.BLOCKED:  # an X
            arm = radius // 2
            for step in (-1, 1):
                pygame.draw.line(
                    self.screen, WHITE,
                    (pos[0] - arm, pos[1] - arm * step),
                    (pos[0] + arm, pos[1] + arm * step), 2,
                )
        elif zone.zone_type is ZoneType.RESTRICTED:  # an inner ring
            pygame.draw.circle(self.screen, WHITE, pos, max(2, radius - 4), 1)
        elif zone.zone_type is ZoneType.PRIORITY:  # a centre dot
            pygame.draw.circle(self.screen, WHITE, pos, max(2, radius // 4))

        if zone.is_hub:
            pygame.draw.circle(self.screen, WHITE, pos, radius + 4, 2)
            tag = self.font.render(zone.name, True, WHITE)
            self.screen.blit(tag, tag.get_rect(midbottom=(pos[0], pos[1] - radius - 6)))

    def _draw_drone(self, drone_id: int) -> None:
        """Draw one drone as a numbered dot, green once it has landed."""
        x, y = self._position(drone_id)
        landed = self.arrival[drone_id] <= self.time
        center = (int(x), int(y))
        radius = max(4, int(self.view.radius * 0.45))
        pygame.draw.circle(self.screen, DELIVERED if landed else DRONE, center, radius)
        label = self.font.render(str(drone_id), True, BACKGROUND)
        self.screen.blit(label, label.get_rect(center=center))

    def handle(self, event: pygame.event.Event) -> None:
        """Apply one pygame event."""
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.VIDEORESIZE:
            surface = pygame.display.get_surface()
            if surface is not None:
                self.screen = surface
                self.view = MapView(self.data, self.screen.get_size())
                self.tracks = {d.drone_id: self._track(d) for d in self.drones}
        elif event.type == pygame.KEYDOWN:
            self._handle_key(event.key)

    def _handle_key(self, key: int) -> None:
        """Apply one keypress."""
        if key in (pygame.K_ESCAPE, pygame.K_q):
            self.running = False
        elif key in (pygame.K_m, pygame.K_BACKSPACE):
            self.outcome = "back"
            self.running = False
        elif key == pygame.K_SPACE:
            if self.paused and self.time >= self.total_turns:
                self.time = 0.0
            self.paused = not self.paused
        elif key == pygame.K_r:
            self.time = 0.0
            self.paused = False
        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.paused = True
            step = 1 if key == pygame.K_RIGHT else -1
            self.time = float(max(0, min(round(self.time) + step, self.total_turns)))

    def advance(self, dt: float) -> None:
        """Move the clock on by a frame's worth of real time."""
        if self.paused or self.total_turns <= 0:
            return
        self.time = min(self.time + dt / SECONDS_PER_TURN, float(self.total_turns))

    def run(self) -> str:
        """Play the simulation until the user goes back ("back") or quits ("quit")."""
        clock = pygame.time.Clock()
        while self.running:
            dt = clock.tick(60) / 1000
            for event in pygame.event.get():
                self.handle(event)
            self.advance(dt)
            self.draw()
            pygame.display.flip()
        return self.outcome


def open_window() -> pygame.Surface:
    """Create the one window the picker and the viewer share for the session.

    Calling `set_mode` again - to resize, to change flags, or from a resize
    handler - makes SDL destroy the window and build a new one, which under a
    tiling Wayland compositor shows as the window closing and reopening.
    """
    if not pygame.get_init():
        pygame.init()
    return pygame.display.set_mode(WINDOW_SIZE, pygame.RESIZABLE)
