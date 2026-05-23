#!/usr/bin/env bats

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/agents"

@test "SAGE-PR-001: Sage knows how to create a discussion branch" {
    run grep -qE "(git checkout -b|git switch -c).*spec" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Sage.md does not mention creating a spec discussion branch"
        false
    }
}

@test "SAGE-PR-002: Sage knows how to open a Pull Request" {
    run grep -qE "(gh pr create|Pull Request|pull request)" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Sage.md does not mention creating a Pull Request"
        false
    }
}

@test "SAGE-PR-003: Sage posts questions as PR inline comments" {
    run grep -qE "(inline comment|行级评论|line comment|PR.*comment|Files Changed)" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Sage.md does not mention posting questions as PR inline comments"
        false
    }
}

@test "SAGE-PR-004: Sage updates spec.md based on user replies in PR" {
    run grep -qE "(修改 spec|更新 spec|push.*spec|根据.*回复.*修改)" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Sage.md does not mention updating spec.md after PR discussion"
        false
    }
}

@test "LEX-PR-001: Lex reviews spec via GitHub PR Review" {
    run grep -qE "(PR Review|pull request review|Request changes|Approve)" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Lex.md does not mention using GitHub PR Review mechanism"
        false
    }
}

@test "LEX-PR-002: Lex leaves line-specific review comments" {
    run grep -qE "(inline comment|行级|line comment|specific line|行.*评论|review comment)" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Lex.md does not mention line-specific review comments"
        false
    }
}

@test "LEX-PR-003: Lex uses Request changes for blocking issues" {
    run grep -qE "(Request changes|请求修改|request changes)" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Lex.md does not mention Request changes for blocking issues"
        false
    }
}

@test "LEX-PR-004: Lex uses Approve when review passes" {
    run grep -qE "(Approve|批准|approve)" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Lex.md does not mention Approve when review passes"
        false
    }
}
