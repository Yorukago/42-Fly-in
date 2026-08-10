import os
from dataclasses import dataclass

import pygame

WINDOW_SIZE = (600, 500)
BACKGROUND = (24, 26, 32)
TEXT_COLOR = (235, 235, 240)
HEADER_COLOR = (140, 144, 158)
HIGHLIGHT_BG = (90, 130, 200)
HIGHLIGHT_TEXT = (20, 20, 24)
ROW_HEIGHT = 24
MARGIN = 20


@dataclass
class MapEntry:
    path: str
    label: str


@dataclass
class Row:
    kind: str
    text: str
    entry: MapEntry | None = None


def _discover_maps(root: str) -> list[Row]:
    """Scan a maps directory and build the menu's header/entry rows.

    Args:
        root: The directory containing one subfolder of .txt maps per category.

    Returns:
        A flat list of header and entry rows, grouped by category.
    """
    rows: list[Row] = []
    if not os.path.isdir(root):
        return rows

    for category in sorted(os.listdir(root)):
        category_path = os.path.join(root, category)
        if not os.path.isdir(category_path):
            continue
        files = sorted(f for f in os.listdir(category_path) if f.endswith(".txt"))
        if not files:
            continue
        rows.append(Row("header", category.upper()))
        for filename in files:
            entry = MapEntry(os.path.join(category_path, filename), filename[:-4])
            rows.append(Row("entry", entry.label, entry))

    return rows


def select_map(root: str = "maps", default_path: str | None = None) -> str | None:
    """Open a small pygame menu letting the user pick a map file.

    Args:
        root: The directory to scan for map categories/files.
        default_path: If given and found, the cursor starts on this map.

    Returns:
        The chosen map's path, or None if the user quit without choosing.
    """
    rows = _discover_maps(root)
    selectable = [i for i, row in enumerate(rows) if row.kind == "entry"]
    if not selectable:
        return None

    cursor = 0
    if default_path is not None:
        target = os.path.normpath(default_path)
        for i, index in enumerate(selectable):
            entry = rows[index].entry
            if entry is not None and os.path.normpath(entry.path) == target:
                cursor = i
                break

    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption("Fly-in — choose a map")
    font = pygame.font.SysFont("monospace", 16)
    header_font = pygame.font.SysFont("monospace", 16, bold=True)
    clock = pygame.time.Clock()

    selected_path: str | None = None
    running = True
    while running:
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_UP:
                    cursor = (cursor - 1) % len(selectable)
                elif event.key == pygame.K_DOWN:
                    cursor = (cursor + 1) % len(selectable)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    entry = rows[selectable[cursor]].entry
                    if entry is not None:
                        selected_path = entry.path
                    running = False

        screen.fill(BACKGROUND)
        title = header_font.render("Fly-in — choose a map", True, TEXT_COLOR)
        screen.blit(title, (MARGIN, MARGIN))

        y = MARGIN + ROW_HEIGHT * 2
        for i, row in enumerate(rows):
            if row.kind == "header":
                label = header_font.render(row.text, True, HEADER_COLOR)
                screen.blit(label, (MARGIN, y))
            else:
                is_selected = selectable[cursor] == i
                if is_selected:
                    rect = pygame.Rect(MARGIN, y - 2, WINDOW_SIZE[0] - 2 * MARGIN, ROW_HEIGHT)
                    pygame.draw.rect(screen, HIGHLIGHT_BG, rect, border_radius=4)
                color = HIGHLIGHT_TEXT if is_selected else TEXT_COLOR
                label = font.render(f"  {row.text}", True, color)
                screen.blit(label, (MARGIN + 10, y))
            y += ROW_HEIGHT

        hint = font.render("[up/down] move   [enter] select   [esc] quit", True, HEADER_COLOR)
        screen.blit(hint, (MARGIN, WINDOW_SIZE[1] - MARGIN - ROW_HEIGHT))

        pygame.display.flip()

    pygame.quit()
    return selected_path
