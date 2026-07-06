#!/usr/bin/env bats

@test "NFR-0020 AC-1 pyproject declares pre-commit dependency" {
    run grep -q 'pre-commit' pyproject.toml
    [ "$status" -eq 0 ]
}

@test "NFR-0020 AC-1 pre-commit lower bound is >= 3.0" {
    run grep -Eq 'pre-commit\s*>=\s*3\.' pyproject.toml
    [ "$status" -eq 0 ]
}

@test "NFR-0020 AC-1 pre-commit upper bound is < 5.0" {
    run grep -Eq 'pre-commit.*<\s*5\.0' pyproject.toml
    [ "$status" -eq 0 ]
}
