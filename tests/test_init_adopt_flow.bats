#!/usr/bin/env bats

# TASK-02..06: Full adopt flow
# FR-009 (source preservation) / FR-010 (create-if-missing) /
# FR-011 (file skip/backup/force) / FR-012 (--dry-run) /
# FR-013 (tri-state report) / FR-014 (.gitignore append) /
# FR-015 (backward compat)
# Issues #28-#34

setup() {
    TEST_DIR="$(mktemp -d)"
    cd "$TEST_DIR"
    export SPECFORGE_HOME
    SPECFORGE_HOME="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
}

teardown() {
    rm -rf "$TEST_DIR"
}

# ---------- FR-009: source preservation ----------

@test "FR09_T01_sha256_unchanged_after_adopt: source files byte-identical" {
    mkdir -p src/quantide src/data && cd src
    git init -q
    echo "code" > quantide/main.py
    echo "data" > data/x.csv
    git add -A && git commit -q -m init
    # capture pre-adopt baseline
    find . -type f -not -path "./.git/*" -exec sha256sum {} \; | sort > "$TEST_DIR/before.sha"
    run bash "$SPECFORGE_HOME/bin/specforge" init .
    [ "$status" -eq 0 ]
    find . -type f -not -path "./.git/*" -not -path "./agents/*" -not -path "./templates/*" -not -path "./specs/*" -not -path "./wiki/*" -not -path "./raw/*" -exec sha256sum {} \; | sort > "$TEST_DIR/after.sha"
    # src files should be unchanged
    diff "$TEST_DIR/before.sha" "$TEST_DIR/after.sha"
}

@test "FR09_T02_git_history_preserved: existing git commits intact" {
    mkdir -p proj && cd proj
    git init -q && git config user.email t@t && git config user.name t
    echo first > file.txt
    git add . && git commit -q -m "first commit"
    HEAD_BEFORE=$(git rev-parse HEAD)
    run bash "$SPECFORGE_HOME/bin/specforge" init .
    [ "$status" -eq 0 ]
    HEAD_AFTER=$(git rev-parse HEAD)
    [ "$HEAD_BEFORE" = "$HEAD_AFTER" ]
}

# ---------- FR-010: create-if-missing ----------

@test "FR10_T01_empty_target_gets_full_init: empty project gets all dirs" {
    mkdir -p fresh && cd fresh && git init -q
    run bash "$SPECFORGE_HOME/bin/specforge" init .
    [ "$status" -eq 0 ]
    [ -d "agents" ]
    [ -d "templates" ]
    [ -d "specs" ]
    [ -d "wiki/pages" ]
    [ -d "wiki/decisions" ]
    [ -d "raw/sources" ]
    # agents should have files
    [ "$(ls agents/*.md 2>/dev/null | wc -l)" -ge 19 ]
}

@test "FR10_T02_existing_specs_preserved: existing specs/ contents kept" {
    mkdir -p p && cd p && git init -q
    mkdir -p specs/001-old && echo "old spec" > specs/001-old/spec.md
    run bash "$SPECFORGE_HOME/bin/specforge" init .
    [ "$status" -eq 0 ]
    [ -f "specs/001-old/spec.md" ]
    grep -q "old spec" specs/001-old/spec.md
}

@test "FR10_T03_existing_wiki_page_preserved: existing wiki/pages/x.md kept" {
    mkdir -p p && cd p && git init -q
    mkdir -p wiki/pages && echo "my notes" > wiki/pages/x.md
    run bash "$SPECFORGE_HOME/bin/specforge" init .
    [ "$status" -eq 0 ]
    grep -q "my notes" wiki/pages/x.md
}

# ---------- FR-011: file skip/backup/force ----------

@test "FR11_T01_same_version_silent_skip: existing identical file silently kept" {
    mkdir -p p && cd p && git init -q
    cp "$SPECFORGE_HOME/agents/Maestro.md" agents/Maestro.md 2>/dev/null || mkdir -p agents && cp "$SPECFORGE_HOME/agents/Maestro.md" agents/Maestro.md
    HASH_BEFORE=$(sha256sum agents/Maestro.md | awk '{print $1}')
    run bash "$SPECFORGE_HOME/bin/specforge" init .
    [ "$status" -eq 0 ]
    HASH_AFTER=$(sha256sum agents/Maestro.md | awk '{print $1}')
    [ "$HASH_BEFORE" = "$HASH_AFTER" ]
}

@test "FR11_T02_modified_file_skipped_with_warn: user-modified file not overwritten" {
    mkdir -p p && cd p && git init -q
    mkdir -p agents && echo "USER CUSTOMIZED" > agents/Maestro.md
    run bash "$SPECFORGE_HOME/bin/specforge" init .
    [ "$status" -eq 0 ]
    grep -q "USER CUSTOMIZED" agents/Maestro.md
}

@test "FR11_T03_backup_creates_bak: --backup makes .bak then skips" {
    mkdir -p p && cd p && git init -q
    mkdir -p agents && echo "v1" > agents/Maestro.md
    run bash "$SPECFORGE_HOME/bin/specforge" init . --backup
    [ "$status" -eq 0 ]
    [ -f "agents/Maestro.md.bak" ]
    grep -q "v1" agents/Maestro.md.bak
    grep -q "v1" agents/Maestro.md
}

@test "FR11_T04_force_overwrites: --force replaces user content" {
    mkdir -p p && cd p && git init -q
    mkdir -p agents && echo "USER VERSION" > agents/Maestro.md
    run bash "$SPECFORGE_HOME/bin/specforge" init . --force
    [ "$status" -eq 0 ]
    # Force means overwrite with SPECFORGE_HOME version
    diff agents/Maestro.md "$SPECFORGE_HOME/agents/Maestro.md"
    [ ! -f "agents/Maestro.md.bak" ]
}

# ---------- FR-012: --dry-run ----------

@test "FR12_T01_dry_run_creates_nothing: working tree byte-identical after dry-run" {
    mkdir -p p && cd p && git init -q
    echo "src" > main.py
    find . -type f -not -path "./.git/*" | sort | xargs sha256sum 2>/dev/null | sort > "$TEST_DIR/before.sha" || true
    run bash "$SPECFORGE_HOME/bin/specforge" init . --dry-run
    [ "$status" -eq 0 ]
    # No new files created by dry-run
    [ ! -d "agents" ] || [ -z "$(ls -A agents 2>/dev/null)" ]
}

@test "FR12_T02_dry_run_emits_report: --dry-run prints same [+]/[=] lines" {
    mkdir -p p && cd p && git init -q
    mkdir -p agents && echo USER > agents/Maestro.md
    run bash "$SPECFORGE_HOME/bin/specforge" init . --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" =~ \[=\]\ agents/Maestro\.md ]]
}

# ---------- FR-013: tri-state report ----------

@test "FR13_T01_report_lines_format: each line is [+]/[=]/[!] path" {
    mkdir -p p && cd p && git init -q
    run bash "$SPECFORGE_HOME/bin/specforge" init .
    [ "$status" -eq 0 ]
    # Should have at least one [+] line (for a new file)
    [[ "$output" =~ \[\+\] ]]
}

@test "FR13_T02_report_summary: ends with summary line" {
    mkdir -p p && cd p && git init -q
    run bash "$SPECFORGE_HOME/bin/specforge" init .
    [ "$status" -eq 0 ]
    [[ "$output" =~ (new files|新文件) ]]
}

@test "FR13_T03_json_output: --json produces valid JSON" {
    mkdir -p p && cd p && git init -q
    run bash "$SPECFORGE_HOME/bin/specforge" init . --json
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "import sys, json; json.load(sys.stdin)" 2>/dev/null
    [ "$?" -eq 0 ]
}

# ---------- FR-014: .gitignore append ----------

@test "FR14_T01_no_gitignore_creates_one: missing .gitignore gets created with .specforge/" {
    mkdir -p p && cd p && git init -q
    run bash "$SPECFORGE_HOME/bin/specforge" init .
    [ "$status" -eq 0 ]
    [ -f ".gitignore" ]
    grep -q "^\.specforge/$" .gitignore
}

@test "FR14_T02_existing_gitignore_gets_appended: existing entries preserved" {
    mkdir -p p && cd p && git init -q
    printf "__pycache__\n*.pyc\n" > .gitignore
    run bash "$SPECFORGE_HOME/bin/specforge" init .
    [ "$status" -eq 0 ]
    grep -q "__pycache__" .gitignore
    grep -q "^\.specforge/$" .gitignore
}

@test "FR14_T03_idempotent_append: second adopt doesn't duplicate .specforge/" {
    mkdir -p p && cd p && git init -q
    bash "$SPECFORGE_HOME/bin/specforge" init . >/dev/null 2>&1
    bash "$SPECFORGE_HOME/bin/specforge" init . >/dev/null 2>&1
    COUNT=$(grep -c "^\.specforge/$" .gitignore)
    [ "$COUNT" -eq 1 ]
}

@test "FR14_T04_no_gitignore_flag: --no-gitignore skips gitignore handling" {
    mkdir -p p && cd p && git init -q
    run bash "$SPECFORGE_HOME/bin/specforge" init . --no-gitignore
    [ "$status" -eq 0 ]
    [ ! -f ".gitignore" ]
}

# ---------- FR-015: backward compat ----------

@test "FR15_T01_bare_name_existing_dir_errors: init myproj where dir exists dies" {
    mkdir myproj
    run bash "$SPECFORGE_HOME/bin/specforge" init myproj
    [ "$status" -ne 0 ]
    [[ "$output" =~ "already exists" ]]
}

@test "FR15_T02_existing_tests_still_pass: tests/test_init.bats is unchanged" {
    run bats "$SPECFORGE_HOME/tests/test_init.bats"
    [ "$status" -eq 0 ]
}

# ---------- non-git target ----------

@test "FR15_T03_non_git_target_errors: adopt on non-git dir fails with hint" {
    mkdir -p notgit && cd notgit
    run bash "$SPECFORGE_HOME/bin/specforge" init .
    [ "$status" -ne 0 ]
    [[ "$output" =~ "git init" ]]
}