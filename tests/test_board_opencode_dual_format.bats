#!/usr/bin/env bats
# Regression tests for the dual frontmatter support + issue-template bootstrap
# in `lk board opencode` (issue: mini-one `millionaire` project had empty
# .github/ISSUE_TEMPLATE/ and every agent's `model:` was empty because the
# source files used `model:` singular — the format cmd_opencode itself writes —
# instead of `models:` plural).

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
LK="$REPO_ROOT/.venv/bin/lk"

setup() {
    export TEST_TMP="$(mktemp -d -t louke-board-fmt-XXXXXX)"
    export SRC_AGENTS="$TEST_TMP/agents"
    mkdir -p "$SRC_AGENTS"
}

teardown() {
    rm -rf "$TEST_TMP"
}

# Helper: write a minimal agent file with arbitrary frontmatter into $SRC_AGENTS.
write_agent() {
    local name="$1"
    local frontmatter="$2"
    local body="${3:-}"
    cat > "$SRC_AGENTS/${name}.md" <<EOF
---
${frontmatter}
---

${body}
EOF
}

# ──────────────────────────────────────────────────────────────────────
# FR: _collect_model_candidates accepts both `model:` and `models:`
# ──────────────────────────────────────────────────────────────────────

@test "FR: cmd_opencode accepts source with model: singular (output format)" {
    write_agent archer "name: archer
description: T
mode: subagent
model: openai/gpt-5.5"
    cd "$TEST_TMP" && git init -q && git -c user.email=a@b.com -c user.name=a commit -q --allow-empty -m init

    run $LK board opencode --quiet --root "$TEST_TMP"
    [ "$status" -eq 0 ] || { echo "FAIL: exit $status: $output"; false; }

    run grep -E "^model: openai/gpt-5\.5" "$TEST_TMP/.opencode/agents/archer.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: archer.md model line not generated correctly"
        cat "$TEST_TMP/.opencode/agents/archer.md" | head -10
        false
    }
}

@test "FR: cmd_opencode still resolves abstract list from models: plural" {
    # This is the canonical source format. Even if `model:` is absent, the
    # first abstract from `models:` should be resolved.
    write_agent archer "name: archer
description: T
mode: subagent
models:
  - glm-5.2
  - kimi-k2.7-code"
    cd "$TEST_TMP" && git init -q && git -c user.email=a@b.com -c user.name=a commit -q --allow-empty -m init

    run $LK board opencode --quiet --root "$TEST_TMP"
    [ "$status" -eq 0 ] || { echo "FAIL: exit $status: $output"; false; }

    # The resolved model must be non-empty AND contain a provider prefix.
    local m
    m=$(grep -E "^model: " "$TEST_TMP/.opencode/agents/archer.md" | head -1 | awk '{print $2}')
    [ -n "$m" ] || { echo "FAIL: archer.md model is empty: '$m'"; false; }
    [[ "$m" == */* ]] || { echo "FAIL: archer.md model '$m' has no provider prefix"; false; }
}

@test "FR: cmd_opencode prefers models: plural over model: singular when both present" {
    # The canonical source format takes precedence over a leftover `model:`
    # line (defensive — keeps idempotency: re-running board on already-generated
    # output should still go through the resolver rather than blindly echo).
    write_agent archer "name: archer
description: T
mode: subagent
models:
  - glm-5.2
model: should-be-ignored"
    cd "$TEST_TMP" && git init -q && git -c user.email=a@b.com -c user.name=a commit -q --allow-empty -m init

    run $LK board opencode --quiet --root "$TEST_TMP"
    [ "$status" -eq 0 ] || { echo "FAIL: exit $status: $output"; false; }

    run grep -F "should-be-ignored" "$TEST_TMP/.opencode/agents/archer.md"
    [ "$status" -ne 0 ] || { echo "FAIL: model: should-be-ignored leaked into output"; false; }
    run grep -F "glm-5.2" "$TEST_TMP/.opencode/agents/archer.md"
    [ "$status" -ne 0 ] || { echo "FAIL: glm-5.2 leaked into output (should be resolved)"; false; }
}

# ──────────────────────────────────────────────────────────────────────
# FR: cmd_opencode bootstraps .github/ISSUE_TEMPLATE/ when source is root-level `agents/`
# ──────────────────────────────────────────────────────────────────────

@test "FR: cmd_opencode bootstraps feature.yml + bug.yml into empty .github/ISSUE_TEMPLATE/" {
    write_agent archer "name: archer
description: T
mode: subagent
model: openai/gpt-5.5"
    cd "$TEST_TMP" && git init -q && git -c user.email=a@b.com -c user.name=a commit -q --allow-empty -m init
    # .github/ISSUE_TEMPLATE/ doesn't exist yet
    [ ! -d "$TEST_TMP/.github/ISSUE_TEMPLATE" ]

    run $LK board opencode --quiet --root "$TEST_TMP"
    [ "$status" -eq 0 ] || { echo "FAIL: exit $status: $output"; false; }

    [ -f "$TEST_TMP/.github/ISSUE_TEMPLATE/feature.yml" ] || {
        echo "FAIL: feature.yml not bootstrapped"
        false
    }
    [ -f "$TEST_TMP/.github/ISSUE_TEMPLATE/bug.yml" ] || {
        echo "FAIL: bug.yml not bootstrapped"
        false
    }
}

@test "FR: cmd_opencode preserves pre-existing feature.yml (Chinese variant) and only adds bug.yml" {
    write_agent archer "name: archer
description: T
mode: subagent
model: openai/gpt-5.5"
    cd "$TEST_TMP" && git init -q && git -c user.email=a@b.com -c user.name=a commit -q --allow-empty -m init
    mkdir -p "$TEST_TMP/.github/ISSUE_TEMPLATE"
    cat > "$TEST_TMP/.github/ISSUE_TEMPLATE/feature.yml" <<'YAML'
name: Feature-CN
description: 中文版 feature 模板
title: "[FR-XXXX] 中文标题"
labels: ["Feature"]
body:
  - type: input
    id: fr_id
    attributes:
      label: Requirement ID
    validations:
      required: true
YAML

    run $LK board opencode --quiet --root "$TEST_TMP"
    [ "$status" -eq 0 ] || { echo "FAIL: exit $status: $output"; false; }

    # Pre-existing Chinese feature.yml must be preserved verbatim.
    run grep -F "中文版 feature 模板" "$TEST_TMP/.github/ISSUE_TEMPLATE/feature.yml"
    [ "$status" -eq 0 ] || { echo "FAIL: pre-existing feature.yml was overwritten"; false; }
    # bug.yml must have been added.
    [ -f "$TEST_TMP/.github/ISSUE_TEMPLATE/bug.yml" ] || {
        echo "FAIL: bug.yml not bootstrapped when feature.yml already exists"
        false
    }
}

@test "FR: cmd_opencode does NOT bootstrap when source is .louke/agents (canonical path)" {
    # When the project is properly lk-init'd, .github/ISSUE_TEMPLATE/ is the
    # user's responsibility — board should not touch it.
    mkdir -p "$TEST_TMP/.louke/agents"
    cp "$SRC_AGENTS"/*.md "$TEST_TMP/.louke/agents/" 2>/dev/null || true
    write_agent archer "name: archer
description: T
mode: subagent
model: openai/gpt-5.5"
    cp "$SRC_AGENTS/archer.md" "$TEST_TMP/.louke/agents/archer.md"
    rm -rf "$SRC_AGENTS"
    cd "$TEST_TMP" && git init -q && git -c user.email=a@b.com -c user.name=a commit -q --allow-empty -m init

    run $LK board opencode --quiet --root "$TEST_TMP"
    [ "$status" -eq 0 ] || { echo "FAIL: exit $status: $output"; false; }

    [ ! -d "$TEST_TMP/.github/ISSUE_TEMPLATE" ] || {
        echo "FAIL: bootstrap ran even though source was canonical .louke/agents"
        ls "$TEST_TMP/.github/ISSUE_TEMPLATE/"
        false
    }
}

# ──────────────────────────────────────────────────────────────────────
# Mini-one reproduction: both fixes together
# ──────────────────────────────────────────────────────────────────────

@test "mini-one reproduction: 12 agents with model: singular all resolve; ISSUE_TEMPLATE populated" {
    for name in archer devon judge keeper lex librarian maestro prism sage scout shield warden; do
        write_agent "$name" "name: $name
description: T
mode: $([ "$name" = "maestro" ] && echo primary || echo subagent)
model: openai/gpt-5.5"
    done
    cd "$TEST_TMP" && git init -q && git -c user.email=a@b.com -c user.name=a commit -q --allow-empty -m init

    run $LK board opencode --quiet --root "$TEST_TMP"
    [ "$status" -eq 0 ] || { echo "FAIL: exit $status: $output"; false; }

    # Every generated agent file must have a non-empty `model:` line.
    for name in archer devon judge keeper lex librarian maestro prism sage scout shield warden; do
        local m
        m=$(grep -E "^model: " "$TEST_TMP/.opencode/agents/${name}.md" | head -1 | awk '{print $2}')
        [ -n "$m" ] || {
            echo "FAIL: $name model is empty"
            head -10 "$TEST_TMP/.opencode/agents/${name}.md"
            false
        }
        [[ "$m" == */* ]] || { echo "FAIL: $name model '$m' has no provider prefix"; false; }
    done

    # ISSUE_TEMPLATE got populated.
    [ -f "$TEST_TMP/.github/ISSUE_TEMPLATE/feature.yml" ]
    [ -f "$TEST_TMP/.github/ISSUE_TEMPLATE/bug.yml" ]
}