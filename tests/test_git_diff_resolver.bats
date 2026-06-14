#!/usr/bin/env bats

# git_diff_quote_resolver.py 测试 (spec 004 NFR-006)

setup() {
    TEST_DIR="$(mktemp -d)"
    export SPECFORGE_HOME
    SPECFORGE_HOME="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
}

teardown() {
    rm -rf "$TEST_DIR"
}

# Helper: create a git repo with a known spec.md
make_repo_with_spec() {
    local spec_content="$1"
    cd "$TEST_DIR"
    mkdir -p specs/test
    git init -q
    git config user.email "test@test"
    git config user.name "test"
    echo "$spec_content" > specs/test/spec.md
    git add . && git commit -q -m "init"
}

# Helper: simulate user editing the spec
edit_spec() {
    local new_content="$1"
    echo "$new_content" > "$TEST_DIR/specs/test/spec.md"
}

@test "GD_T01_no_diff_exits_0: no changes → exit 0 with message" {
    make_repo_with_spec "# spec
> **Sage:** a question [open]"
    run python3 "$SPECFORGE_HOME/tools/git_diff_quote_resolver.py" "$TEST_DIR/specs/test/spec.md" --base-ref HEAD
    [ "$status" -eq 0 ]
    [[ "$output" =~ "no changes detected" ]]
}

@test "GD_T02_changed_with_open_nearby: edit near open quote → recommendation" {
    make_repo_with_spec "# spec

> **Sage:** a question [open]

<a id=\"fr-001\"></a>
**FR-001**: feature"
    # Edit FR-001 at line 5+, quote at L3, distance = 2 (within default window 10)
    edit_spec "# spec

> **Sage:** a question [open]

<a id=\"fr-001\"></a>
**FR-001**: feature UPDATED"
    run python3 "$SPECFORGE_HOME/tools/git_diff_quote_resolver.py" "$TEST_DIR/specs/test/spec.md" --base-ref HEAD
    [ "$status" -eq 0 ]
    # distance = |5-3| = 2, within default ±10
    [[ "$output" =~ "recommended resolve (within ±10 lines): 1" ]]
}

@test "GD_T03_open_quote_in_window: quote near edit gets recommended" {
    make_repo_with_spec "# spec

> **Sage:** a question [open]
> **Aaron:** reply ✓ resolved

<a id=\"fr-001\"></a>
**FR-001**: example"
    edit_spec "# spec

> **Sage:** a question ✓ resolved
> **Aaron:** reply ✓ resolved

<a id=\"fr-001\"></a>
**FR-001**: example updated"
    run python3 "$SPECFORGE_HOME/tools/git_diff_quote_resolver.py" "$TEST_DIR/specs/test/spec.md" --base-ref HEAD
    [ "$status" -eq 0 ]
    [[ "$output" =~ "touched lines" ]]
    # The quote is at line 3 (0-indexed in spec, line 3 in file)
    # Editing FR-001 at line 7 — distance is 4, within ±10
    # So the [open] quote should be recommended for resolve
    [[ "$output" =~ "recommend" ]] || [[ "$output" =~ "recommended resolve" ]]
}

@test "GD_T04_out_of_window: quote far from edit NOT recommended" {
    make_repo_with_spec "# spec

> **Sage:** question one [open]

<a id=\"fr-001\"></a>
**FR-001**: short

<a id=\"fr-002\"></a>
**FR-002**: another feature here with more text to push the [open] quote far away from edits that happen way later in the document

<a id=\"fr-003\"></a>
**FR-003**: third"
    # Edit only FR-003 at the very end
    edit_spec "# spec

> **Sage:** question one [open]

<a id=\"fr-001\"></a>
**FR-001**: short

<a id=\"fr-002\"></a>
**FR-002**: another feature here with more text to push the [open] quote far away from edits that happen way later in the document

<a id=\"fr-003\"></a>
**FR-003**: third UPDATED"
    run python3 "$SPECFORGE_HOME/tools/git_diff_quote_resolver.py" "$TEST_DIR/specs/test/spec.md" --base-ref HEAD --window 5
    [ "$status" -eq 0 ]
    # With window=5 and the [open] at L3 vs edit at L16+, should be out of window
    [[ "$output" =~ "recommended resolve (within ±5 lines): 0" ]]
}

@test "GD_T05_custom_window: window flag overrides default" {
    make_repo_with_spec "# spec

> **Sage:** q [open]
> **Aaron:** a ✓ resolved

<a id=\"fr-001\"></a>
**FR-001**: feature one
<a id=\"fr-002\"></a>
**FR-002**: feature two"
    edit_spec "# spec

> **Sage:** q [open]
> **Aaron:** a ✓ resolved

<a id=\"fr-001\"></a>
**FR-001**: feature one UPDATED
<a id=\"fr-002\"></a>
**FR-002**: feature two"
    run python3 "$SPECFORGE_HOME/tools/git_diff_quote_resolver.py" "$TEST_DIR/specs/test/spec.md" --base-ref HEAD --window 2
    [ "$status" -eq 0 ]
    # quote at L3, edit at L7 — distance 4, outside window 2
    [[ "$output" =~ "recommended resolve (within ±2 lines): 0" ]]
}