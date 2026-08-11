from pathlib import Path

from menu import _discover_maps, select_map


def _make_maps_tree(root: Path) -> None:
    easy = root / "easy"
    hard = root / "hard"
    empty = root / "empty_category"
    easy.mkdir()
    hard.mkdir()
    empty.mkdir()

    (easy / "01_first.txt").write_text("nb_drones: 1\n")
    (easy / "02_second.txt").write_text("nb_drones: 1\n")
    (hard / "01_only.txt").write_text("nb_drones: 1\n")
    (hard / "notes.md").write_text("not a map")  # non-.txt files are ignored


def test_discover_maps_groups_by_category(tmp_path: Path) -> None:
    """Categories become headers, and .txt files inside become entries."""
    _make_maps_tree(tmp_path)
    rows = _discover_maps(str(tmp_path))

    kinds_and_text = [(row.kind, row.text) for row in rows]
    assert kinds_and_text == [
        ("header", "EASY"),
        ("entry", "01_first"),
        ("entry", "02_second"),
        ("header", "HARD"),
        ("entry", "01_only"),
    ]


def test_discover_maps_skips_empty_categories(tmp_path: Path) -> None:
    """A category folder with no .txt files produces no header at all."""
    _make_maps_tree(tmp_path)
    rows = _discover_maps(str(tmp_path))
    assert "EMPTY_CATEGORY" not in [row.text for row in rows if row.kind == "header"]


def test_discover_maps_missing_root_returns_empty(tmp_path: Path) -> None:
    """A nonexistent root directory yields no rows at all."""
    assert _discover_maps(str(tmp_path / "does-not-exist")) == []


def test_entry_paths_are_joined_correctly(tmp_path: Path) -> None:
    """Each entry's path points at the real file, label strips '.txt'."""
    _make_maps_tree(tmp_path)
    rows = _discover_maps(str(tmp_path))
    first_entry = next(row for row in rows if row.kind == "entry")
    assert first_entry.entry is not None
    assert first_entry.entry.label == "01_first"
    assert Path(first_entry.entry.path).is_file()


def test_select_map_returns_none_without_any_maps(tmp_path: Path) -> None:
    """With no discoverable maps, select_map bails out before opening pygame."""
    assert select_map(root=str(tmp_path)) is None
