#!/usr/bin/env bats
# Test louke/_tools/check_identity.py

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
SCRIPT="$REPO_ROOT/louke/_tools/check_identity.py"

# ---------- Script existence and syntax ----------

@test "ID-001: check_identity_py_exists" {
    [ -f "$SCRIPT" ]
}

@test "ID-002: check_identity_py_valid_python_3" {
    run python3 -c "import ast; ast.parse(open('$SCRIPT').read())"
    [ "$status" -eq 0 ]
}

@test "ID-003: check_identity_py_offline_mode_supported" {
    run python3 "$SCRIPT" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--offline"* ]]
}

@test "ID-004: check_identity_py_repo_arg_supported" {
    run python3 "$SCRIPT" --help
    [[ "$output" == *"--repo"* ]]
}

# ---------- L1-L5 check items coverage ----------

@test "ID-100: source_mentions_L1_gh_auth" {
    run grep -q "L1" "$SCRIPT"
    [ "$status" -eq 0 ]
}

@test "ID-101: source_mentions_L2_viewerPermission" {
    run grep -q "L2" "$SCRIPT"
    [ "$status" -eq 0 ]
}

@test "ID-102: source_mentions_L3_git_user_name_email" {
    run grep -q "L3" "$SCRIPT"
    [ "$status" -eq 0 ]
}

@test "ID-103: source_mentions_L4_commit_author_email_vs_gh" {
    run grep -q "L4" "$SCRIPT"
    [ "$status" -eq 0 ]
}

@test "ID-104: source_mentions_L5_remote_owner_vs_gh_advisory" {
    run grep -q "L5" "$SCRIPT"
    [ "$status" -eq 0 ]
}

# ---------- Offline mode: good cases ----------

@test "ID-200: offline_single_identity_WRITE_role_pass_exit_0" {
    run python3 "$SCRIPT" --offline \
        --repo zillionare/specforge \
        --gh-user zillionare \
        --gh-emails "aaron_yang@jieyu.ai" \
        --git-name zillionare \
        --git-email aaron_yang@jieyu.ai \
        --last-commit-author "zillionare <aaron_yang@jieyu.ai>" \
        --remote-url "git@github.com:zillionare/specforge.git" \
        --repo-role WRITE
    [ "$status" -eq 0 ]
    [[ "$output" == *"[PASS]"* || "$output" == *"[PASS+warning]"* ]]
    [[ "$output" != *"L4"* ]]
}

# ---------- Offline mode: bad cases ----------

@test "ID-301: offline_two_identities_L4_fail_reject_exit_1" {
    run python3 "$SCRIPT" --offline \
        --repo zillionare/specforge \
        --gh-user quantclaws \
        --gh-emails "quantclaws@elsewhere.com" \
        --git-name zillionare \
        --git-email aaron_yang@jieyu.ai \
        --last-commit-author "zillionare <aaron_yang@jieyu.ai>" \
        --remote-url "git@github.com:zillionare/specforge.git" \
        --repo-role WRITE
    [ "$status" -eq 1 ]
    [[ "$output" == *"[REJECT]"* ]]
    [[ "$output" == *"L4"* ]]
}

@test "ID-302: offline_READ_role_L2_fail_reject_exit_1" {
    run python3 "$SCRIPT" --offline \
        --repo zillionare/specforge \
        --gh-user quantclaws \
        --gh-emails "aaron_yang@jieyu.ai" \
        --git-name zillionare \
        --git-email aaron_yang@jieyu.ai \
        --last-commit-author "zillionare <aaron_yang@jieyu.ai>" \
        --remote-url "git@github.com:zillionare/specforge.git" \
        --repo-role READ
    [ "$status" -eq 1 ]
    [[ "$output" == *"[REJECT]"* ]]
    [[ "$output" == *"L2"* ]]
}

@test "ID-303: offline_gh_not_authenticated_L1_fail_reject_exit_1" {
    run python3 "$SCRIPT" --offline \
        --repo zillionare/specforge \
        --gh-user "" \
        --gh-emails "" \
        --git-name zillionare \
        --git-email aaron_yang@jieyu.ai \
        --last-commit-author "zillionare <aaron_yang@jieyu.ai>" \
        --remote-url "git@github.com:zillionare/specforge.git" \
        --repo-role WRITE
    [ "$status" -eq 1 ]
    [[ "$output" == *"L1"* ]]
}

@test "ID-304: offline_git_user_email_unset_L3_fail_reject_exit_1" {
    run python3 "$SCRIPT" --offline \
        --repo zillionare/specforge \
        --gh-user zillionare \
        --gh-emails "aaron_yang@jieyu.ai" \
        --git-name "" \
        --git-email "" \
        --last-commit-author "" \
        --remote-url "git@github.com:zillionare/specforge.git" \
        --repo-role WRITE
    [ "$status" -eq 1 ]
    [[ "$output" == *"L3"* ]]
}

# ---------- Offline mode: advisory (L5 non-blocking) ----------

@test "ID-400: offline_remote_owner_differs_from_gh_pass_with_warning_exit_0" {
    # Simulate valid scenario: personal token operating on org repo
    run python3 "$SCRIPT" --offline \
        --repo zillionare/specforge \
        --gh-user quantclaws \
        --gh-emails "aaron_yang@jieyu.ai" \
        --git-name zillionare \
        --git-email aaron_yang@jieyu.ai \
        --last-commit-author "zillionare <aaron_yang@jieyu.ai>" \
        --remote-url "git@github.com:zillionare/specforge.git" \
        --repo-role WRITE
    [ "$status" -eq 0 ]
    [[ "$output" == *"[PASS+warning]"* ]]
    [[ "$output" == *"L5"* ]]
    # L4 should not trigger (commit email is in gh known emails)
    [[ "$output" != *"L4"* ]]
}
