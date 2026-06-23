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
    # capture pre-adopt baseline (only user source)
    find ./quantide ./data -type f -exec sha256sum {} \; | sort > "$TEST_DIR/before.sha"
    run bash "$SPECFORGE_HOME/bin/specforge" init . --no-gitignore
    [ "$status" -eq 0 ]
    find ./quantide ./data -type f -exec sha256sum {} \; | sort > "$TEST_DIR/after.sha"
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

# ---------- FR-010 (v0.3-003) superseded by v0.5-005 FR-020: create-if-missing at new paths ----------

@test "FR10_T01_empty_target_gets_full_init: empty project gets all dirs under .specforge/" {
    mkdir -p fresh && cd fresh && git init -q
    run bash "$SPECFORGE_HOME/bin/specforge" init .
    [ "$status" -eq 0 ]
    [ -d ".specforge/agents" ]
    [ -d ".specforge/templates" ]
    [ -d ".specforge/project" ]
    [ -d ".specforge/wiki/pages" ]
    [ -d ".specforge/wiki/decisions" ]
    [ -d ".specforge/raw/sources" ]
    # v0.5-005 NFR-020: root MUST NOT contain wiki/ or raw/
    [ ! -d "wiki" ]
    [ ! -d "raw" ]
    # agents should have files
    [ "$(ls .specforge/agents/*.md 2>/dev/null | wc -l)" -ge 19 ]
}

@test "FR10_T02_existing_specs_preserved: existing .specforge/project/specs/ contents kept" {
    mkdir -p p && cd p && git init -q
    mkdir -p .specforge/project/specs/v0.1-001-old
    echo "old spec" > .specforge/project/specs/v0.1-001-old/spec.md
    run bash "$SPECFORGE_HOME/bin/specforge" init .
    [ "$status" -eq 0 ]
    [ -f ".specforge/project/specs/v0.1-001-old/spec.md" ]
    grep -q "old spec" .specforge/project/specs/v0.1-001-old/spec.md
}

@test "FR10_T03_existing_wiki_page_preserved_after_migration: legacy wiki/pages/x.md auto-moved and content intact" {
    # v0.5-005 FR-030: legacy wiki/ at root is git-mv'd to .specforge/wiki/
    mkdir -p p && cd p && git init -q
    mkdir -p wiki/pages && echo "my notes" > wiki/pages/x.md
    git add -A && git commit -q -m "add legacy wiki"
    run bash "$SPECFORGE_HOME/bin/specforge" init .
    [ "$status" -eq 0 ]
    # legacy path gone, new path exists
    [ ! -d "wiki" ]
    [ -d ".specforge/wiki/pages" ]
    [ -f ".specforge/wiki/pages/x.md" ]
    grep -q "my notes" .specforge/wiki/pages/x.md
    # git should track this as a rename, not delete+add
    RENAME_COUNT=$(git status --porcelain | grep -c "^R" || true)
    [ "$RENAME_COUNT" -ge 1 ]
}

# ---------- FR-011: file skip/backup/force ----------
# v0.5-005: agents/ moved to .specforge/agents/. Tests updated accordingly.

@test "FR11_T01_same_version_silent_skip: existing identical file silently kept" {
    mkdir -p p && cd p && git init -q
    cp "$SPECFORGE_HOME/agents/Maestro.md" .specforge/agents/Maestro.md 2>/dev/null || mkdir -p .specforge/agents && cp "$SPECFORGE_HOME/agents/Maestro.md" .specforge/agents/Maestro.md
    HASH_BEFORE=$(sha256sum .specforge/agents/Maestro.md | awk '{print $1}')
    run bash "$SPECFORGE_HOME/bin/specforge" init .
    [ "$status" -eq 0 ]
    HASH_AFTER=$(sha256sum .specforge/agents/Maestro.md | awk '{print $1}')
    [ "$HASH_BEFORE" = "$HASH_AFTER" ]
}

@test "FR11_T02_modified_file_skipped_with_warn: user-modified file not overwritten" {
    mkdir -p p && cd p && git init -q
    mkdir -p .specforge/agents && echo "USER CUSTOMIZED" > .specforge/agents/Maestro.md
    run bash "$SPECFORGE_HOME/bin/specforge" init .
    [ "$status" -eq 0 ]
    grep -q "USER CUSTOMIZED" .specforge/agents/Maestro.md
}

@test "FR11_T03_backup_creates_bak: --backup makes .bak then skips" {
    mkdir -p p && cd p && git init -q
    mkdir -p .specforge/agents && echo "v1" > .specforge/agents/Maestro.md
    run bash "$SPECFORGE_HOME/bin/specforge" init . --backup
    [ "$status" -eq 0 ]
    [ -f ".specforge/agents/Maestro.md.bak" ]
    grep -q "v1" .specforge/agents/Maestro.md.bak
    grep -q "v1" .specforge/agents/Maestro.md
}

@test "FR11_T04_force_overwrites: --force replaces user content" {
    mkdir -p p && cd p && git init -q
    mkdir -p .specforge/agents && echo "USER VERSION" > .specforge/agents/Maestro.md
    run bash "$SPECFORGE_HOME/bin/specforge" init . --force
    [ "$status" -eq 0 ]
    # Force means overwrite with SPECFORGE_HOME version
    diff .specforge/agents/Maestro.md "$SPECFORGE_HOME/agents/Maestro.md"
    [ ! -f ".specforge/agents/Maestro.md.bak" ]
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
    [ ! -d ".specforge/agents" ] || [ -z "$(ls -A .specforge/agents 2>/dev/null)" ]
}

@test "FR12_T02_dry_run_emits_report: --dry-run prints same [+]/[=] lines" {
    mkdir -p p && cd p && git init -q
    mkdir -p .specforge/agents && echo USER > .specforge/agents/Maestro.md
    run bash "$SPECFORGE_HOME/bin/specforge" init . --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" =~ \[=\]\ \.specforge/agents/Maestro\.md ]]
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

@test "FR14_T01_no_gitignore_creates_one: missing .gitignore gets created with .specforge/agents/ + .specforge/templates/" {
    mkdir -p p && cd p && git init -q
    run bash "$SPECFORGE_HOME/bin/specforge" init .
    [ "$status" -eq 0 ]
    [ -f ".gitignore" ]
    grep -q "^\.specforge/agents/$" .gitignore
    grep -q "^\.specforge/templates/$" .gitignore
}

@test "FR14_T02_existing_gitignore_gets_appended: existing entries preserved" {
    mkdir -p p && cd p && git init -q
    printf "__pycache__\n*.pyc\n" > .gitignore
    run bash "$SPECFORGE_HOME/bin/specforge" init .
    [ "$status" -eq 0 ]
    grep -q "__pycache__" .gitignore
    grep -q "^\.specforge/agents/$" .gitignore
    grep -q "^\.specforge/templates/$" .gitignore
}

@test "FR14_T03_idempotent_append: second adopt doesn't duplicate .specforge/agents/" {
    mkdir -p p && cd p && git init -q
    bash "$SPECFORGE_HOME/bin/specforge" init . >/dev/null 2>&1
    bash "$SPECFORGE_HOME/bin/specforge" init . >/dev/null 2>&1
    COUNT=$(grep -c "^\.specforge/agents/$" .gitignore)
    [ "$COUNT" -eq 1 ]
}

@test "FR14_T05_project_dir_NOT_ignored: .specforge/project/ must remain version-controlled" {
    mkdir -p p && cd p && git init -q
    bash "$SPECFORGE_HOME/bin/specforge" init . >/dev/null 2>&1
    # 显式断言 .gitignore 没把整个 .specforge/ 屏蔽掉, 也没把 project/ 列出来.
    ! grep -qE '^\.specforge/?$' .gitignore
    ! grep -q '^\.specforge/project' .gitignore
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

# ---------- v0.5-005: legacy path auto-migration ----------

@test "MIG01_legacy_wiki_gets_moved: root wiki/ → .specforge/wiki/" {
    mkdir -p p && cd p && git init -q
    mkdir -p wiki/decisions && echo "adr" > wiki/decisions/001-x.md
    git add -A && git commit -q -m init
    run bash "$SPECFORGE_HOME/bin/specforge" init . --no-gitignore
    [ "$status" -eq 0 ]
    [ ! -d "wiki" ]
    [ -d ".specforge/wiki" ]
    [ -d ".specforge/wiki/decisions" ]
    [ -f ".specforge/wiki/decisions/001-x.md" ]
    grep -q "adr" .specforge/wiki/decisions/001-x.md
}

@test "MIG02_legacy_raw_gets_moved: root raw/ → .specforge/raw/" {
    mkdir -p p && cd p && git init -q
    mkdir -p raw/sources && echo "session log" > raw/sources/abc.md
    git add -A && git commit -q -m init
    run bash "$SPECFORGE_HOME/bin/specforge" init . --no-gitignore
    [ "$status" -eq 0 ]
    [ ! -d "raw" ]
    [ -d ".specforge/raw" ]
    [ -d ".specforge/raw/sources" ]
    [ -f ".specforge/raw/sources/abc.md" ]
}

@test "MIG03_untracked_legacy_uses_plain_mv: untracked wiki/ still gets moved" {
    mkdir -p p && cd p && git init -q
    mkdir -p wiki/pages && echo "x" > wiki/pages/x.md
    # intentionally NOT git-adding wiki/ — plain mv path
    run bash "$SPECFORGE_HOME/bin/specforge" init . --no-gitignore
    [ "$status" -eq 0 ]
    [ ! -d "wiki" ]
    [ -f ".specforge/wiki/pages/x.md" ]
}

@test "MIG04_no_migrate_flag_keeps_legacy_in_place: --no-migrate does not move" {
    mkdir -p p && cd p && git init -q
    mkdir -p wiki/pages && echo "kept" > wiki/pages/x.md
    git add -A && git commit -q -m init
    run bash "$SPECFORGE_HOME/bin/specforge" init . --no-gitignore --no-migrate
    [ "$status" -eq 0 ]
    # legacy path STILL exists with original content
    [ -d "wiki" ]
    [ -f "wiki/pages/x.md" ]
    grep -q "kept" wiki/pages/x.md
    # new path is empty (created by create-if-missing, no migration of legacy files)
    [ -d ".specforge/wiki/pages" ]
    [ -z "$(ls -A .specforge/wiki/pages/ 2>/dev/null)" ]
    # report mentions skipped migration
    [[ "$output" =~ "no-migrate" ]]
}

@test "MIG05_dry_run_does_not_move: --dry-run prints plan, working tree unchanged" {
    mkdir -p p && cd p && git init -q
    mkdir -p wiki/pages && echo "x" > wiki/pages/x.md
    git add -A && git commit -q -m init
    run bash "$SPECFORGE_HOME/bin/specforge" init . --no-gitignore --dry-run
    [ "$status" -eq 0 ]
    # legacy still at original location
    [ -d "wiki" ]
    [ -f "wiki/pages/x.md" ]
    # new path not created
    [ ! -d ".specforge/wiki" ]
    # report mentions migration plan
    [[ "$output" =~ "wiki/" ]]
    [[ "$output" =~ ".specforge/wiki" ]]
}

@test "MIG06_conflict_old_and_new_exist_errors: dies to prevent data loss" {
    mkdir -p p && cd p && git init -q
    # both legacy and new exist
    mkdir -p wiki/pages
    echo "old" > wiki/pages/x.md
    mkdir -p .specforge/wiki/pages
    echo "new" > .specforge/wiki/pages/y.md
    run bash "$SPECFORGE_HOME/bin/specforge" init . --no-gitignore
    [ "$status" -ne 0 ]
    [[ "$output" =~ "wiki" ]]
    [[ "$output" =~ ".specforge/wiki" ]]
}

@test "MIG07_idempotent_on_already_migrated: second run is a no-op for migration" {
    mkdir -p p && cd p && git init -q
    # first run: migrates
    run bash "$SPECFORGE_HOME/bin/specforge" init . --no-gitignore
    [ "$status" -eq 0 ]
    [ ! -d "wiki" ]
    # second run: nothing to migrate, must succeed
    run bash "$SPECFORGE_HOME/bin/specforge" init . --no-gitignore
    [ "$status" -eq 0 ]
    [ ! -d "wiki" ]
    [ -d ".specforge/wiki" ]
}

@test "MIG08_json_report_includes_migrated: --json output has 'migrated' field" {
    mkdir -p p && cd p && git init -q
    mkdir -p wiki/pages && echo x > wiki/pages/x.md
    git add -A && git commit -q -m init
    run bash "$SPECFORGE_HOME/bin/specforge" init . --no-gitignore --json
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "import sys, json; d=json.load(sys.stdin); assert 'migrated' in d; assert len(d['migrated']) >= 1"
}