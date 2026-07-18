#!/usr/bin/env bats

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
AGENTS_DIR="$REPO_ROOT/louke/agents"
STORY="$REPO_ROOT/.louke/project/specs/v0.14-002-workflow-reflow-design/story.md"

@test "HOST-CI-AGENT-001: Devon implements the locked managed workflow without redesigning CI" {
    run grep -q "\.github/workflows/louke-ci.yml" "$AGENTS_DIR/Devon.md"
    [ "$status" -eq 0 ]
    run grep -q "自行设计 CI" "$AGENTS_DIR/Devon.md"
    [ "$status" -eq 0 ]
    run grep -q "Louke CI / required" "$AGENTS_DIR/Devon.md"
    [ "$status" -eq 0 ]
}

@test "HOST-CI-AGENT-002: Shield implements every required integration/e2e layer" {
    run grep -q "AC → observable interface → required test layer(s) → CI gate/job" "$AGENTS_DIR/Shield.md"
    [ "$status" -eq 0 ]
    run grep -q "其它层已有测试不能替代" "$AGENTS_DIR/Shield.md"
    [ "$status" -eq 0 ]
}

@test "HOST-CI-AGENT-003: Prism reviews both CI design and implementation" {
    run grep -q "托管 GitHub CI 可实施" "$AGENTS_DIR/Prism.md"
    [ "$status" -eq 0 ]
    run grep -q "CI 实现审查" "$AGENTS_DIR/Prism.md"
    [ "$status" -eq 0 ]
    run grep -q "AC required layers 闭合" "$AGENTS_DIR/Prism.md"
    [ "$status" -eq 0 ]
}

@test "HOST-CI-STORY-001: v0.14-002 contains the host managed CI program story" {
    run grep -q "Story 2：Louke 为宿主项目托管强制性的 GitHub Actions CI" "$STORY"
    [ "$status" -eq 0 ]
    run grep -q "Machine-readable CI contract" "$STORY"
    [ "$status" -eq 0 ]
    run grep -q "GitHub 强制启用与回读" "$STORY"
    [ "$status" -eq 0 ]
}
