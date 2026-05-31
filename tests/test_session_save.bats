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

@test "UT-010-01: Probe has session save instructions" {
    run grep -q "会话保存" "$AGENTS_DIR/Probe.md"
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

@test "UT-010-01: Cynic has session save instructions" {
    run grep -q "会话保存" "$AGENTS_DIR/Cynic.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Forge has session save instructions" {
    run grep -q "会话保存" "$AGENTS_DIR/Forge.md"
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

@test "UT-010-01: Herald has session save instructions" {
    run grep -q "会话保存" "$AGENTS_DIR/Herald.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Arbiter has session save instructions" {
    run grep -q "会话保存" "$AGENTS_DIR/Arbiter.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Hunter has session save instructions" {
    run grep -q "会话保存" "$AGENTS_DIR/Hunter.md"
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

@test "UT-010-02: wiki page frontmatter fields are documented" {
    run grep -qE "(type:|date:|title:)" "$AGENTS_DIR/Forge.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-03: wiki page wikilink syntax is documented" {
    run grep -qE "\[\[.*\]\]" "$AGENTS_DIR/Forge.md"
    [ "$status" -eq 0 ]
}
