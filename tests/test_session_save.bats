#!/usr/bin/env bats

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/agents"

@test "UT-010-01: Scout has session save instructions" {
    run grep -q "会话保存" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Warden has session save instructions" {
    run grep -q "会话保存" "$AGENTS_DIR/Warden.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Sage has session save instructions" {
    run grep -q "会话保存" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Lex has session save instructions" {
    run grep -q "会话保存" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Judge has session save instructions" {
    run grep -q "会话保存" "$AGENTS_DIR/Judge.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Archer has session save instructions" {
    run grep -q "会话保存" "$AGENTS_DIR/Archer.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Devon has session save instructions" {
    run grep -q "会话保存" "$AGENTS_DIR/Devon.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Prism has session save instructions" {
    run grep -q "会话保存" "$AGENTS_DIR/Prism.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Keeper has session save instructions" {
    run grep -q "会话保存" "$AGENTS_DIR/Keeper.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Shield has session save instructions" {
    run grep -q "会话保存" "$AGENTS_DIR/Shield.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Maestro has session save instructions" {
    run grep -q "会话保存" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Librarian has session save instructions" {
    run grep -q "会话保存" "$AGENTS_DIR/Librarian.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-02: session frontmatter fields are documented" {
    run grep -qE "(status:|session:)" "$AGENTS_DIR/Devon.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-03: raw path documented" {
    run grep -q ".holdpoint/raw/" "$AGENTS_DIR/Devon.md"
    [ "$status" -eq 0 ]
}
