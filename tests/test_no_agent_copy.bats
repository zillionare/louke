#!/usr/bin/env bats
# Codifies the "agents are package-owned" design (per FR discussion on
# mini-one `millionaire`):
#
# 1. `lk init` MUST NOT copy agents to `.louke/agents/` or anywhere in the
#    project — the package's `louke/agents/` is the single source of truth.
# 2. `lk board opencode` MUST read agents from the installed package, NOT
#    from any project-level `agents/` or `.louke/agents/`.
# 3. A stale, custom `agents/` in the project (e.g. the mini-one hack that
#    copied `.opencode/agents/*.md` back to source) MUST NOT affect what
#    `lk board opencode` writes to `.opencode/agents/`.

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
LK="$REPO_ROOT/.venv/bin/lk"

setup() {
    export TEST_TMP="$(mktemp -d -t louke-no-agent-copy-XXXXXX)"
    cd "$TEST_TMP" && git init -q && git -c user.email=a@b.com -c user.name=a commit -q --allow-empty -m init
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "lk init does NOT create .louke/agents/" {
    run "$LK" init . --no-cron
    [ "$status" -eq 0 ] || { echo "FAIL: exit $status: $output"; false; }
    [ ! -d "$TEST_TMP/.louke/agents" ] || {
        echo "FAIL: lk init created .louke/agents/ — agents must be package-owned"
        ls "$TEST_TMP/.louke/agents/"
        false
    }
}

@test "lk init does NOT copy agents to project root agents/" {
    run "$LK" init . --no-cron
    [ "$status" -eq 0 ]
    [ ! -d "$TEST_TMP/agents" ] || {
        echo "FAIL: lk init created project-root agents/ — agents must be package-owned"
        ls "$TEST_TMP/agents/"
        false
    }
}

@test "lk board opencode reads agents from package, ignores stale project agents/" {
    # Simulate the mini-one hack: copy the OUTPUT format into project-root agents/.
    # cmd_opencode must NOT use these.
    mkdir -p "$TEST_TMP/agents"
    for name in archer devon judge keeper lex librarian maestro prism sage scout shield warden; do
        cat > "$TEST_TMP/agents/${name}.md" <<EOF
---
description: stale hack — output format committed as source
mode: $([ "$name" = "maestro" ] && echo primary || echo subagent)
model: bogus-provider/bogus-model
permission:
  bash: allow
  read: allow
---
This file is in OUTPUT format (model: singular) and was incorrectly committed as source.
EOF
    done

    run "$LK" board opencode --quiet
    [ "$status" -eq 0 ] || { echo "FAIL: exit $status: $output"; false; }

    # Every generated agent file must have a NON-bogus, non-empty model.
    for name in archer devon judge keeper lex librarian maestro prism sage scout shield warden; do
        local m
        m=$(grep -E "^model: " "$TEST_TMP/.opencode/agents/${name}.md" | head -1 | awk '{print $2}')
        [ -n "$m" ] || { echo "FAIL: $name model is empty"; false; }
        [[ "$m" != *"bogus"* ]] || { echo "FAIL: $name leaked the bogus stale format"; false; }
        [[ "$m" == */* ]] || { echo "FAIL: $name model '$m' has no provider prefix"; false; }
    done

    # The stale project agents/ must still NOT influence the output — verify by
    # checking that the generated archer.md description matches the PACKAGE one
    # (the "Test plan + architecture design" wording), not the stale hack wording.
    local desc
    desc=$(grep -E "^description: " "$TEST_TMP/.opencode/agents/archer.md" | head -1)
    [[ "$desc" == *"Test plan + architecture design"* ]] || {
        echo "FAIL: archer.md description came from the stale project agents/: $desc"
        false
    }
    [[ "$desc" != *"stale hack"* ]] || {
        echo "FAIL: stale hack description leaked into output"
        false
    }
}

@test "lk board opencode ignores .louke/agents/ (gitignored location must NOT be authoritative)" {
    # Even if someone manually populates .louke/agents/ (which is gitignored
    # and not the canonical location), cmd_opencode must still read from the
    # package.
    mkdir -p "$TEST_TMP/.louke/agents"
    cat > "$TEST_TMP/.louke/agents/Maestro.md" <<'EOF'
---
description: WRONG — this would-be override must be ignored
mode: primary
models:
  - should-not-be-used
permission:
  bash: allow
---
EOF
    run "$LK" board opencode --quiet
    [ "$status" -eq 0 ]

    local desc
    desc=$(grep -E "^description: " "$TEST_TMP/.opencode/agents/maestro.md" | head -1)
    [[ "$desc" != *"WRONG"* ]] || {
        echo "FAIL: .louke/agents/Maestro.md description leaked into output"
        false
    }
    [[ "$desc" == *"Pipeline orchestrator"* ]] || {
        echo "FAIL: package Maestro.md description did not make it to output: $desc"
        false
    }
}
