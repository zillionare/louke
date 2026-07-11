# louke Makefile — minimal entry points used by CI.
# v0.10+: tests live directly in `tests/*.bats`; this Makefile is a thin
# wrapper so `make test` keeps working as a stable CI command.

.PHONY: test test-bats lint format build clean

test: test-bats

test-bats:
	@if ! command -v bats >/dev/null 2>&1; then \
		echo "bats not installed; install with: sudo apt-get install -y bats"; \
		exit 1; \
	fi
	bats tests/*.bats

lint:
	ruff check louke/ tests/
	mypy louke/

format:
	ruff format louke/ tests/

build:
	python -m build

clean:
	rm -rf build/ dist/ louke.egg-info/ .mypy_cache/ .pytest_cache/ .ruff_cache/
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
