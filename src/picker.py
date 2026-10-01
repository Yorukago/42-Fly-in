import os

import pygame

ROW_HEIGHT = 24
HEADER_HEIGHT = 22
TOP = 70
LEFT = 40

BACKGROUND = (17, 19, 26)
TEXT = (231, 234, 242)
DIM = (138, 145, 163)
FAINT = (96, 102, 119)
ACCENT = (96, 165, 250)


class Picker:
    """Lets the user pick one map from a list, in the session's window."""

    def __init__(self, screen: pygame.Surface, paths: list[str]) -> None:
        """Set up the list over an already-discovered set of maps."""
        self.screen = screen
        self.paths = paths
        self.font = pygame.font.SysFont("monospace", 14)
        self.bold = pygame.font.SysFont("monospace", 14, bold=True)
        self.title_font = pygame.font.SysFont("monospace", 22, bold=True)

        self.cursor = 0
        self.chosen: str | None = None
        self.running = True

    def select(self, path: str) -> None:
        """Move the highlight onto a map, so reopening the list keeps your place."""
        if path in self.paths:
            self.cursor = self.paths.index(path)

    def _rows(self) -> list[tuple[str, str | None]]:
        """Return (text, path) lines to draw; a None path marks a category header."""
        rows: list[tuple[str, str | None]] = []
        current = ""
        for path in self.paths:
            category = os.path.basename(os.path.dirname(path))
            if category != current:
                rows.append((category.upper(), None))
                current = category
            rows.append((os.path.basename(path)[:-4], path))
        return rows

    def _visible(self, rows: list[tuple[str, str | None]]) -> list[tuple[str, str | None]]:
        """Return the rows that fit on screen, keeping the highlight among them.

        The list is longer than the window once enough maps are bundled, so it
        scrolls with the cursor rather than drawing off the bottom edge.
        """
        room = max(1, (self.screen.get_height() - TOP - 40) // ROW_HEIGHT)
        if len(rows) <= room:
            return rows
        chosen = self.paths[self.cursor]
        selected = next(i for i, (_, path) in enumerate(rows) if path == chosen)
        first = min(max(0, selected - room // 2), len(rows) - room)
        return rows[first:first + room]

    def draw(self) -> None:
        """Draw the whole list, with the current map highlighted."""
        self.screen.fill(BACKGROUND)
        self.screen.blit(self.title_font.render("FLY-IN", True, TEXT), (LEFT, 24))
        counter = f"{self.cursor + 1}/{len(self.paths)} maps"
        count = self.font.render(counter, True, FAINT)
        self.screen.blit(count, (LEFT + 110, 31))

        y = TOP
        for text, path in self._visible(self._rows()):
            if path is None:
                self.screen.blit(self.font.render(text, True, FAINT), (LEFT, y + 4))
                y += HEADER_HEIGHT
                continue

            selected = path == self.paths[self.cursor]
            if selected:
                marker = pygame.Rect(LEFT + 8, y + 3, 4, ROW_HEIGHT - 8)
                pygame.draw.rect(self.screen, ACCENT, marker, border_radius=2)
            font = self.bold if selected else self.font
            label = font.render(text, True, ACCENT if selected else DIM)
            self.screen.blit(label, (LEFT + 24, y + 2))
            y += ROW_HEIGHT

        hints = self.font.render(
            "[up/down] browse   [enter] open   [esc] quit", True, FAINT
        )
        self.screen.blit(hints, (LEFT, self.screen.get_height() - 34))

    def handle(self, event: pygame.event.Event) -> None:
        """Apply one pygame event."""
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.VIDEORESIZE:
            surface = pygame.display.get_surface()
            if surface is not None:
                self.screen = surface
        elif event.type == pygame.KEYDOWN:
            self._handle_key(event.key)

    def _handle_key(self, key: int) -> None:
        """Apply one keypress."""
        if key in (pygame.K_ESCAPE, pygame.K_q):
            self.running = False
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.chosen = self.paths[self.cursor]
            self.running = False
        elif key in (pygame.K_UP, pygame.K_DOWN):
            step = 1 if key == pygame.K_DOWN else -1
            self.cursor = (self.cursor + step) % len(self.paths)
        elif key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
            step = 5 if key == pygame.K_PAGEDOWN else -5
            self.cursor = max(0, min(self.cursor + step, len(self.paths) - 1))
        elif key == pygame.K_HOME:
            self.cursor = 0
        elif key == pygame.K_END:
            self.cursor = len(self.paths) - 1

    def run(self) -> str | None:
        """Show the list until the user picks a map or quits."""
        clock = pygame.time.Clock()
        while self.running:
            clock.tick(60)
            for event in pygame.event.get():
                self.handle(event)
            self.draw()
            pygame.display.flip()
        return self.chosen
