.PHONY: install run debug clean lint lint-strict maps

# Which map to open: make run MAP=hard/01_maze_nightmare
# A partial name works too: make run MAP=maze
# Extra flags go in ARGS: make run MAP=maze ARGS=--simulate
MAP ?=
ARGS ?=

install:
	uv sync

run:
	uv run python3 src $(MAP) $(ARGS)

debug:
	uv run python3 -m pdb src/__main__.py $(MAP) $(ARGS)

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .mypy_cache

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict

maps:
	uv run python3 src --list
