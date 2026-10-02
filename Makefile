.PHONY: help install run debug clean lint lint-strict maps bench errors check
.DEFAULT_GOAL := help

# Which map to open: make run MAP=hard/01_maze_nightmare
# A partial name works too: make run MAP=maze
# Extra flags go in ARGS: make run MAP=maze ARGS=--simulate
MAP ?=
ARGS ?=

PY = uv run python3


BENCH = \
	easy/01_linear_path:6 \
	easy/02_simple_fork:8 \
	easy/03_basic_capacity:6 \
	medium/01_dead_end_trap:12 \
	medium/02_circular_loop:15 \
	medium/03_priority_puzzle:12 \
	hard/01_maze_nightmare:30 \
	hard/02_capacity_hell:35 \
	hard/03_ultimate_challenge:45 \
	challenger/01_the_impossible_dream:45

help:
	@printf '  \033[36m%-12s\033[0m %s\n' \
		install     'sync dependencies with uv' \
		run         'open a map in the viewer (MAP=maze ARGS=--simulate)' \
		maps        'list the bundled maps' \
		bench       'replay every graded map, check it against its target' \
		errors      'show the message every malformed map produces' \
		lint        'flake8 + a lenient mypy' \
		lint-strict 'flake8 + mypy --strict' \
		check       'lint-strict, bench and errors together' \
		debug       'run under pdb' \
		clean       'drop __pycache__ and .mypy_cache'

install:
	uv sync

run:
	$(PY) src $(MAP) $(ARGS)

debug:
	$(PY) -m pdb src/__main__.py $(MAP) $(ARGS)

maps:
	$(PY) src --list

bench:
	@printf '%-38s %7s %7s  %s\n' MAP TURNS TARGET ''
	@fails=0; \
	for entry in $(BENCH); do \
		map=$${entry%%:*}; target=$${entry##*:}; \
		turns=$$($(PY) src --simulate maps/$$map.txt | tail -1 | tr -dc '0-9'); \
		if [ "$$turns" -le "$$target" ]; then mark='\033[32mmet\033[0m'; \
		else mark='\033[31mOVER\033[0m'; fails=$$((fails+1)); fi; \
		printf '%-38s %7s %7s  ' "$$map" "$$turns" "<=$$target"; printf "$$mark\n"; \
	done; \
	echo; \
	if [ $$fails -eq 0 ]; then echo "all targets met"; \
	else echo "$$fails map(s) over target"; exit 1; fi

errors:
	@for map in maps/custom/err_*.txt; do \
		printf '\033[36m%-34s\033[0m ' "$$(basename $$map .txt)"; \
		$(PY) src --simulate $$map 2>&1 >/dev/null | head -1; \
	done

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict

check: lint-strict bench errors

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .mypy_cache
