#!/usr/bin/env bats

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

@test "serve CLI: help includes project-root flag" {
    run python -m louke serve --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--project-root"* ]]
}

@test "serve CLI: non-louke directory auto-creates setup-only project (FR-1303)" {
    # v0.13 B2 changed behavior: lk serve in a no-project workspace now enters
    # setup-only mode (auto-creates a minimal .louke/project/project.toml and
    # serves the setup wizard) rather than exiting non-zero. This test verifies
    # the new behavior.
    WORK="$(mktemp -d)"
    cd "$WORK" || exit 1

    # Pick a free port and start serve in background
    PORT=$(python -c "import socket; s=socket.socket(); s.bind(('', 0)); print(s.getsockname()[1]); s.close()")
    python -m louke serve --host 127.0.0.1 --port $PORT >/dev/null 2>&1 &
    SERVEPID=$!

    # Wait for /health to respond (up to 10s)
    HEALTHY=0
    for i in $(seq 1 20); do
        if curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
            HEALTHY=1
            break
        fi
        sleep 0.5
    done

    # Assert: server reached a healthy state
    [ "$HEALTHY" -eq 1 ]

    # Assert: setup-only mode auto-created the project.toml
    [ -f "$WORK/.louke/project/project.toml" ]

    # Cleanup
    kill $SERVEPID 2>/dev/null || true
    wait $SERVEPID 2>/dev/null || true
    rm -rf "$WORK" 2>/dev/null || true
}
