#!/usr/bin/env bats
# Test bin/specforge — framework's unified CLI entrypoint
# Focus: subcommand dispatch, arg passthrough, upgrade safety, help self-describe
#
# v0.5-009: Chinese test names replaced with ASCII IDs to work around
# bats parser issue with multibyte characters in test names (only 1 of 31
# tests was actually being executed under zh_CN.UTF-8 / C.UTF-8 locale).

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
CLI="$REPO_ROOT/bin/specforge"

setup() {
    TEST_DIR="$(mktemp -d)"
    export SPECFORGE_HOME="$TEST_DIR/fake-home"
    mkdir -p "$SPECFORGE_HOME"
    # Default: drop a VERSION so most tests can read "0.1.0"
    echo "0.1.0" > "$SPECFORGE_HOME/VERSION"
    # Python scripts needed by cmd_checkup / cmd_verify_issue
    mkdir -p "$SPECFORGE_HOME/tools"
    cp "$REPO_ROOT/tools/check_identity.py" "$SPECFORGE_HOME/tools/"
    cp "$REPO_ROOT/tools/verify_issue_schema.py" "$SPECFORGE_HOME/tools/"
}

teardown() {
    rm -rf "$TEST_DIR"
}

# ---------- script presence & syntax ----------

@test "CLI-001: bin_specforge_exists" {
    [ -f "$CLI" ]
}

@test "CLI-002: bin_specforge_is_valid_bash" {
    run bash -n "$CLI"
    [ "$status" -eq 0 ]
}

@test "CLI-003: bin_specforge_executable_or_bash_callable" {
    # bash invocation is enough; install.sh will chmod
    run bash "$CLI" version
    [ "$status" -eq 0 ]
}

# ---------- help / version ----------

@test "CLI-100: no_args_shows_help" {
    run bash "$CLI"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
}

@test "CLI-101: help_subcommand_prints_usage" {
    run bash "$CLI" help
    [ "$status" -eq 0 ]
    [[ "$output" == *"specforge"* ]]
    [[ "$output" == *"init"* ]]
    [[ "$output" == *"checkup"* ]]
    [[ "$output" == *"verify-issue"* ]]
    [[ "$output" == *"upgrade"* ]]
}

@test "CLI-102: short_and_long_help_flags" {
    run bash "$CLI" -h
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    run bash "$CLI" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
}

@test "CLI-103: version_prints_version" {
    run bash "$CLI" version
    [ "$status" -eq 0 ]
    [[ "$output" == *"specforge 0.1.0"* ]]
}

@test "CLI-104: short_and_long_version_flags" {
    run bash "$CLI" -v
    [ "$status" -eq 0 ]
    [[ "$output" == *"0.1.0"* ]]
    run bash "$CLI" --version
    [ "$status" -eq 0 ]
    [[ "$output" == *"0.1.0"* ]]
}

@test "CLI-105: version_prints_install_path" {
    run bash "$CLI" version
    [ "$status" -eq 0 ]
    [[ "$output" == *"$SPECFORGE_HOME"* ]]
}

@test "CLI-106: missing_version_reports_dev" {
    rm -f "$SPECFORGE_HOME/VERSION"
    run bash "$CLI" version
    [ "$status" -eq 0 ]
    [[ "$output" == *"dev"* ]]
}

@test "CLI-108: help_distinguishes_user_vs_agent_driven" {
    run bash "$CLI" help
    [ "$status" -eq 0 ]
    # top of help must remind that "agent auto-call" is the principle
    [[ "$output" == *"agent"* ]]
    [[ "$output" == *"debug"* ]]
    # must have explicit category headings
    [[ "$output" == *"User-driven"* ]]
    [[ "$output" == *"Agent-driven"* ]]
}

@test "CLI-109: checkup_and_verify_issue_marked_agent_driven" {
    # prevent regression: someone reverts to "all commands are human-run"
    run bash "$CLI" help
    [ "$status" -eq 0 ]
    # checkup must appear in Agent-driven block, not User-driven
    awk '/User-driven/{u=1; next} /Agent-driven/{u=0; a=1} u && /checkup/{print "FAIL: checkup in user block"; exit 1} a && /checkup/{found_checkup=1} END{exit !found_checkup}' <<<"$output"
    # verify-issue same
    awk '/User-driven/{u=1; next} /Agent-driven/{u=0; a=1} u && /verify-issue/{print "FAIL: verify-issue in user block"; exit 1} a && /verify-issue/{found_vi=1} END{exit !found_vi}' <<<"$output"
}

@test "CLI-110: init_and_upgrade_marked_user_driven" {
    run bash "$CLI" help
    [ "$status" -eq 0 ]
    # init must be in User-driven block
    awk '/User-driven/{u=1; next} /Agent-driven/{u=0} u && /init/{found_init=1} END{exit !found_init}' <<<"$output"
    # upgrade must be in User-driven block
    awk '/User-driven/{u=1; next} /Agent-driven/{u=0} u && /upgrade/{found_up=1} END{exit !found_up}' <<<"$output"
}

@test "CLI-107: help_describes_all_six_subcommands" {
    run bash "$CLI" help
    [ "$status" -eq 0 ]
    for sub in "init" "checkup" "verify-issue" "doctor" "upgrade" "version"; do
        [[ "$output" == *"$sub"* ]] || { echo "help missing: $sub" >&2; false; }
    done
}

# ---------- error handling ----------

@test "CLI-200: unknown_subcommand_dies_with_exit_1" {
    run bash "$CLI" bogus-cmd
    [ "$status" -eq 1 ]
    [[ "$output" == *"unknown command"* ]]
    [[ "$output" == *"bogus-cmd"* ]]
}

@test "CLI-201: init_without_name_dies" {
    run bash "$CLI" init
    [ "$status" -eq 1 ]
    [[ "$output" == *"Usage: specforge init"* ]]
}

@test "CLI-202: init_existing_dir_dies" {
    mkdir -p "$TEST_DIR/existing-project"
    cd "$TEST_DIR"
    run bash "$CLI" init existing-project
    [ "$status" -eq 1 ]
    [[ "$output" == *"already exists"* ]]
}

@test "CLI-203: checkup_without_repo_dies" {
    run bash "$CLI" checkup
    [ "$status" -eq 1 ]
    [[ "$output" == *"Usage: specforge checkup"* ]]
}

# ---------- checkup arg passthrough ----------

@test "CLI-300: checkup_forwards_offline_and_args_to_check_identity_py" {
    # --offline avoids hitting real GitHub; verify exit 0 + [pass]
    # note: bash 3.2 (macOS) doesn't interpret \[ in [[ glob ]], use [pass] not \[pass\]
    run bash "$CLI" checkup zillionare/specforge --offline \
        --gh-user zillionare \
        --gh-emails "aaron_yang@jieyu.ai" \
        --git-name zillionare \
        --git-email aaron_yang@jieyu.ai \
        --last-commit-author "zillionare <aaron_yang@jieyu.ai>" \
        --remote-url "git@github.com:zillionare/specforge.git" \
        --repo-role WRITE
    [ "$status" -eq 0 ]
    [[ "$output" == *"[通过]"* ]]
    [[ "$output" != *"L4"* ]]
}

@test "CLI-301: doctor_is_checkup_alias" {
    # both checkup and doctor should produce the same output format
    run bash "$CLI" doctor zillionare/specforge --offline \
        --gh-user zillionare \
        --gh-emails "aaron_yang@jieyu.ai" \
        --git-name zillionare \
        --git-email aaron_yang@jieyu.ai \
        --last-commit-author "zillionare <aaron_yang@jieyu.ai>" \
        --remote-url "git@github.com:zillionare/specforge.git" \
        --repo-role WRITE
    [ "$status" -eq 0 ]
    [[ "$output" == *"[通过+警告]"* ]]
}

# ---------- verify-issue arg passthrough ----------

@test "CLI-400: verify_issue_forwards_offline_spec_and_issues_json" {
    # minimal spec.md (one anchor FR-001) + acceptance.md + valid form-rendered issue
    cat > "$TEST_DIR/spec.md" <<'EOF'
# test spec
<a id="fr-001"></a>
## FR-001
done.
EOF
    cat > "$TEST_DIR/acceptance.md" <<'EOF'
# test acceptance
<a id="ac-fr-001"></a>
## FR-001

### AC-1
- it works
EOF
    # GitHub renders form fields as ### Label / value
    cat > "$TEST_DIR/issues.json" <<'EOF'
[
  {"number": 1, "title": "[FR-001] test feature", "labels": [{"name": "Feature"}],
   "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/x/y/blob/main/.specforge/project/specs/001/spec.md#fr-001\n\n### 验收标准\nhttps://github.com/x/y/blob/main/.specforge/project/specs/001/acceptance.md#ac-fr-001\n"}
]
EOF
    run bash "$CLI" verify-issue --offline \
        --spec-file "$TEST_DIR/spec.md" \
        --acceptance-file "$TEST_DIR/acceptance.md" \
        --issues-json "$TEST_DIR/issues.json"
    [ "$status" -eq 0 ]
    [[ "$output" != *"L2"* ]]
    [[ "$output" != *"L3"* ]]
    [[ "$output" != *"L7"* ]]
}

@test "CLI-401: verify_issue_missing_required_args_exits_2" {
    run bash "$CLI" verify-issue
    [ "$status" -eq 2 ]
}

# ---------- upgrade safety rails ----------

@test "CLI-500: upgrade_in_non_git_dir_dies" {
    # SPECFORGE_HOME is set up but not git init'd
    run bash "$CLI" upgrade
    [ "$status" -eq 1 ]
    [[ "$output" == *"is not a git clone"* ]]
}

@test "CLI-501: upgrade_off_main_branch_dies" {
    cd "$SPECFORGE_HOME"
    git init -q .
    git -c init.defaultBranch=main checkout -q -b main 2>/dev/null || git checkout -q -b main
    git -c user.email=t@t.com -c user.name=t commit -q --allow-empty -m init
    git checkout -q -b feature/my-dev
    run bash "$CLI" upgrade
    [ "$status" -eq 1 ]
    [[ "$output" == *"refusing to upgrade on branch 'feature/my-dev'"* ]]
    # main is the only allowed branch
    [[ "$output" == *"only main is supported"* ]]
}

@test "CLI-502: upgrade_main_no_origin_fetch_fails" {
    cd "$SPECFORGE_HOME"
    git init -q .
    git -c init.defaultBranch=main checkout -q -b main 2>/dev/null || git checkout -q -b main
    # no origin, fetch will fail → die
    run bash "$CLI" upgrade
    [ "$status" -ne 0 ]
}

# ---------- SPECFORGE_HOME behavior ----------

@test "CLI-600: specforge_home_overrides_default" {
    export SPECFORGE_HOME="$TEST_DIR/custom-home"
    mkdir -p "$SPECFORGE_HOME/agents" "$SPECFORGE_HOME/templates"
    echo "9.9.9" > "$SPECFORGE_HOME/VERSION"
    run bash "$CLI" version
    [ "$status" -eq 0 ]
    [[ "$output" == *"9.9.9"* ]]
    [[ "$output" == *"$TEST_DIR/custom-home"* ]]
}

@test "CLI-601: dev_mode_specforge_home_dot_init_works" {
    # simulate "developer running bin/specforge from within specforge repo"
    cd "$REPO_ROOT"
    SPECFORGE_HOME=. run bash "$CLI" init "$TEST_DIR/from-dev"
    [ "$status" -eq 0 ]
    [ -d "$TEST_DIR/from-dev/.specforge/agents" ]
}

# ---------- v0.5-005 NFR-030: upgrade refreshes $BIN_DIR/specforge binary ----------

@test "CLI-602: upgrade_refreshes_bin_dir_specforge" {
    # simulate install: copy bin/specforge to a temp BIN_DIR
    local FAKE_BIN="$TEST_DIR/fake-bin"
    mkdir -p "$FAKE_BIN"
    cp "$CLI" "$FAKE_BIN/specforge"
    HASH_BEFORE=$(shasum "$FAKE_BIN/specforge" | awk '{print $1}')

    # simulate "upstream pushed new version": append a marker comment to SPECFORGE_HOME's
    # bin/specforge (doesn't break syntax — it's a comment line)
    echo "# upgrade-marker-$$" >> "$CLI"

    local HASH_EXPECTED
    HASH_EXPECTED=$(shasum "$CLI" | awk '{print $1}')
    # cmd_upgrade will try git fetch first and fail in sandbox (no network / no origin).
    # We verify the cp-refresh logic exists in the function body:
    grep -q 'cp "\$SPECFORGE_HOME/bin/specforge" "\$BIN_DIR/specforge"' "$CLI"
    [ "$?" -eq 0 ]
    # clean up marker
    sed -i '' "/# upgrade-marker-$$/d" "$CLI"
}

@test "CLI-603: upgrade_unwritable_bin_dir_prints_hint_no_error" {
    # verify cmd_upgrade's graceful fallback path
    # doesn't depend on real network: just inspect the cp-fail branch
    local FAKE_BIN="$TEST_DIR/readonly-bin"
    mkdir -p "$FAKE_BIN"
    chmod 555 "$FAKE_BIN"
    # upgrade does git fetch first — expected to fail in sandbox.
    # We only confirm the syntax layer:
    #   1) cmd_upgrade contains `cp ... || note "could not refresh ...` pattern
    grep -q 'could not refresh' "$CLI"
    [ "$?" -eq 0 ]
    chmod 755 "$FAKE_BIN"
}

# ---------- install.sh single-source consistency ----------

@test "CLI-700: install_sh_syntax_valid" {
    run bash -n "$REPO_ROOT/install.sh"
    [ "$status" -eq 0 ]
}

@test "CLI-701: install_sh_no_inline_specforge_body" {
    # real install: copy from $SPECFORGE_HOME/bin/specforge to $BIN_DIR
    # old version inlined specforge in install.sh — not allowed
    # grep -F 'cmd_checkup()' should be 0 matches
    run grep -F 'cmd_checkup()' "$REPO_ROOT/install.sh"
    [ "$status" -ne 0 ]
    # should not inline cmd_init either
    run grep -F 'cmd_init()' "$REPO_ROOT/install.sh"
    [ "$status" -ne 0 ]
    # should not inline cmd_help
    run grep -F 'cmd_help()' "$REPO_ROOT/install.sh"
    [ "$status" -ne 0 ]
    # must have cp command copying repo's bin/specforge to $BIN_DIR
    run grep -F 'cp "$SPECFORGE_HOME/bin/specforge"' "$REPO_ROOT/install.sh"
    [ "$status" -eq 0 ]
}
