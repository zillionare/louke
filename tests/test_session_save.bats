#!/usr/bin/env bats

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/louke/agents"

@test "UT-010-01: Scout has session save instructions" {
    run grep -qE "Session [Ss]av(e|ing)" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Warden has session save instructions" {
    run grep -qE "Session [Ss]av(e|ing)" "$AGENTS_DIR/Warden.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Sage has session save instructions" {
    run grep -qE "Session [Ss]av(e|ing)" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Lex has session save instructions" {
    run grep -qE "Session [Ss]av(e|ing)" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Judge has session save instructions" {
    run grep -qE "Session [Ss]av(e|ing)" "$AGENTS_DIR/Judge.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Archer has session save instructions" {
    run grep -qE "Session [Ss]av(e|ing)" "$AGENTS_DIR/Archer.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Devon has session save instructions" {
    run grep -qE "Session [Ss]av(e|ing)" "$AGENTS_DIR/Devon.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Prism has session save instructions" {
    run grep -qE "Session [Ss]av(e|ing)" "$AGENTS_DIR/Prism.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Keeper has session save instructions" {
    run grep -qE "Session [Ss]av(e|ing)" "$AGENTS_DIR/Keeper.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Shield has session save instructions" {
    run grep -qE "Session [Ss]av(e|ing)" "$AGENTS_DIR/Shield.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Maestro has session save instructions" {
    run grep -qE "Session [Ss]av(e|ing)" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-01: Librarian has session save instructions" {
    # v0.6+ revision: Librarian is the wiki engine; its artifacts are wiki/pages (already structured memory).
    # It no longer writes raw sessions (design intent: avoid wiki distillation loop — Librarian
    # distilling its own raw). If a "Librarian decision tracking" requirement is introduced later,
    # add a separate .louke/wiki/decisions/librarian/ directory rather than raw/sources/.
    skip "Librarian intentionally does not write raw sessions — wiki/pages is its memory carrier"
}

@test "UT-010-02: session frontmatter fields are documented" {
    run grep -qE "(status:|session:)" "$AGENTS_DIR/Devon.md"
    [ "$status" -eq 0 ]
}

@test "UT-010-03: raw path documented" {
    run grep -q ".louke/raw/" "$AGENTS_DIR/Devon.md"
    [ "$status" -eq 0 ]
}
