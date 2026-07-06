#!/usr/bin/env bats

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

@test "NFR-0030 AC-1: README.md contains pre-commit quality gate subsection" {
    run grep -q "pre-commit 质量门禁" "$REPO_ROOT/README.md"
    [ "$status" -eq 0 ]
}

@test "NFR-0030 AC-1: README.zh.md contains pre-commit quality gate subsection" {
    run grep -q "pre-commit 质量门禁" "$REPO_ROOT/README.zh.md"
    [ "$status" -eq 0 ]
}

@test "NFR-0030 AC-5: agents/Archer.md section 6 lists .pre-commit-config.yaml" {
    run grep -q "\.pre-commit-config.yaml" "$REPO_ROOT/louke/agents/Archer.md"
    [ "$status" -eq 0 ]
}
