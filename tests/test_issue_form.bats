#!/usr/bin/env bats
# Tests .github/ISSUE_TEMPLATE/feature.yml and louke/_tools/verify_issue_schema.py

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
FORM="$REPO_ROOT/.github/ISSUE_TEMPLATE/feature.yml"
SCRIPT="$REPO_ROOT/louke/_tools/verify_issue_schema.py"

# ---------- Shared helper: generate acceptance.md fixture ----------

make_acceptance_fixture() {
    # $1 = path, $2..$N = FR list, e.g. "0001" "0002"
    local path="$1"; shift
    {
        echo "# Demo acceptance"
        for n in "$@"; do
            echo
            echo "<a id=\"ac-fr-${n}\"></a>"
            echo
            echo "## FR-${n}"
            echo
            echo "### AC-1"
            echo "- Condition 1"
            echo
            echo "### AC-2"
            echo "- Condition 2"
        done
    } > "$path"
}

# ---------- Issue Form existence and basic structure ----------

@test "FORM-001: feature_yml_exists" {
    [ -f "$FORM" ]
}

@test "FORM-002: feature_yml_valid_yaml" {
    run python3 -c "import yaml; yaml.safe_load(open('$FORM'))"
    [ "$status" -eq 0 ]
}

@test "FORM-003: feature_yml_contains_name_Feature" {
    run grep -q "^name: Feature" "$FORM"
    [ "$status" -eq 0 ]
}

@test "FORM-004: feature_yml_contains_labels_Feature" {
    run grep -qE "labels:.*Feature" "$FORM"
    [ "$status" -eq 0 ]
}

@test "FORM-005: feature_yml_contains_3_required_fields" {
    # Requirement ID / Spec Link / Acceptance Criteria
    for field in "Requirement ID" "Spec Link" "Acceptance Criteria"; do
        run grep -q "label: $field" "$FORM"
        [ "$status" -eq 0 ] || { echo "Missing form field: $field" >&2; false; }
    done
}

@test "FORM-006: required_id_field_regex_FR_d4" {
    run grep -qE 'regex: .*\^FR-\\\\d\{4\}\$' "$FORM"
    [ "$status" -eq 0 ]
}

@test "FORM-007: spec_url_field_regex_github_spec_md_fr_anchor" {
    # Spec URL field regex must include spec.md (with multi-volume spec-{name}.md) and (fr|nfr)-
    run python3 -c "
import yaml, sys
y = yaml.safe_load(open('$FORM'))
for f in y['body']:
    if f.get('id') == 'spec_url':
        r = f['validations']['regex']
        # Support single-file spec.md and multi-volume spec(-\w+)?\.md
        assert 'spec(-\\\\w+)?\\\\.md' in r or 'spec(-\\w+)?\\.md' in r, f'spec(-\\w+)?\\.md missing in {r}'
        assert 'fr|nfr' in r, f'fr|nfr missing in {r}'
        assert r.endswith(r'-\d{4}\$'), f'd4 anchor missing in {r}'
        sys.exit(0)
sys.exit(1)
"
    [ "$status" -eq 0 ]
}

@test "FORM-008: acceptance_field_input_with_acceptance_md_anchor" {
    # Acceptance field must be input (not textarea), regex includes acceptance.md + ac-(fr|nfr)-
    run python3 -c "
import yaml, sys
y = yaml.safe_load(open('$FORM'))
for f in y['body']:
    if f.get('id') == 'acceptance_criteria':
        assert f['type'] == 'input', f'expected type=input, got {f[\"type\"]}'
        r = f['validations']['regex']
        assert 'acceptance.md' in r or 'acceptance\\\\.md' in r, f'acceptance.md missing in {r}'
        assert 'ac-(fr|nfr)' in r, f'ac-(fr|nfr) anchor missing in {r}'
        sys.exit(0)
sys.exit(1)
"
    [ "$status" -eq 0 ]
    # Key: must not contain "AC-N: " placeholder (old schema)
    run grep -F "AC-N: " "$FORM"
    [ "$status" -ne 0 ]
}

@test "FORM-009: acceptance_field_required_true" {
    run grep -q "required: true" "$FORM"
    [ "$status" -eq 0 ]
}

# ---------- Validator script existence and syntax ----------

@test "VERIFY-001: verify_issue_schema_py_exists" {
    [ -f "$SCRIPT" ]
}

@test "VERIFY-002: verify_issue_schema_py_valid_python_3" {
    run python3 -c "import ast; ast.parse(open('$SCRIPT').read())"
    [ "$status" -eq 0 ]
}

@test "VERIFY-003: validator_supports_offline_mode" {
    run python3 "$SCRIPT" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--offline"* ]]
}

@test "VERIFY-004: validator_supports_spec_arg" {
    run python3 "$SCRIPT" --help
    [[ "$output" == *"--spec"* ]]
}

@test "VERIFY-005: validator_supports_acceptance_file_arg" {
    run python3 "$SCRIPT" --help
    [[ "$output" == *"--acceptance-file"* ]]
}

# ---------- Validator offline mode: happy path ----------

@test "VERIFY-100: offline_all_compliant_issues_pass" {
    # Use minimal spec fixture (only FR-0001) to avoid L8 bidirectional coverage interference
    SPEC_FIX="$BATS_TEST_TMPDIR/min_spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# Min Spec
<a id="fr-0001"></a>
**FR-0001**: minimal fixture
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/min_acc.md"
    make_acceptance_fixture "$ACC_FIX" "0001"
    FIXTURE="$BATS_TEST_TMPDIR/good_issues.json"
    cat > "$FIXTURE" <<'EOF'
[
  {
    "number": 42,
    "title": "[FR-0001] User Login",
    "body": "### Requirement ID\nFR-0001\n\n### Spec Link\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/0001-test/spec.md#fr-0001\n\n### Acceptance Criteria\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/0001-test/acceptance.md#ac-fr-0001\n",
    "state": "open"
  }
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[PASS]"* ]]
}

@test "VERIFY-110: verify_issue_filters_by_spec_id_offline_mode" {
    # fix #110: --spec should only validate issues whose Spec Link points to that
    # spec_id; historical dirty issues from other specs are ignored.
    SPEC_FIX="$BATS_TEST_TMPDIR/v0.11_spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# Web IDE Spec
<a id="fr-0001"></a>
**FR-0001**: minimal fixture
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/v0.11_acc.md"
    make_acceptance_fixture "$ACC_FIX" "0001"
    FIXTURE="$BATS_TEST_TMPDIR/mixed_issues.json"
    cat > "$FIXTURE" <<'EOF'
[
  {
    "number": 10,
    "title": "[FR-0001] Web IDE Feature",
    "body": "### Requirement ID\nFR-0001\n\n### Spec Link\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.11-001-web-ide/spec.md#fr-0001\n\n### Acceptance Criteria\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.11-001-web-ide/acceptance.md#ac-fr-0001\n",
    "state": "open"
  },
  {
    "number": 99,
    "title": "[FR-002] dirty historical issue (wrong title format)",
    "body": "### Requirement ID\nFR-002\n\n### Spec Link\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.8-001-old/spec.md#fr-0002\n\n### Acceptance Criteria\nNone\n",
    "state": "open"
  }
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec v0.11-001-web-ide \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[PASS]"* ]]
    [[ "$output" == *"1 PASS"* ]]
    [[ "$output" != *"#99"* ]]
    [[ "$output" != *"FR-002"* ]]
}

# ---------- Validator offline mode: error paths ----------

# Shared acceptance fixture (contains fr-0001 and fr-0005) for error-path tests to reuse, avoiding L7 interference
setup_acc_with_001_005() {
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    make_acceptance_fixture "$ACC_FIX" "0001" "0005"
    export ACC_FIX
}

@test "VERIFY-201: bad_title_detected_L1" {
    setup_acc_with_001_005
    FIXTURE="$BATS_TEST_TMPDIR/bad_title.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "FR-1 User Login (no brackets)", "body": "### Requirement ID\nFR-0001\n\n### Spec Link\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/0001-test/spec.md#fr-0001\n\n### Acceptance Criteria\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/0001-test/acceptance.md#ac-fr-0001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$REPO_ROOT/.louke/project/specs/v0.1-001-louke/spec.md" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L1"* ]]
}

@test "VERIFY-202: missing_spec_url_detected_L3" {
    setup_acc_with_001_005
    FIXTURE="$BATS_TEST_TMPDIR/missing_url.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 2, "title": "[FR-0001] x", "body": "### Requirement ID\nFR-0001\n\n### Acceptance Criteria\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/0001-test/acceptance.md#ac-fr-0001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$REPO_ROOT/.louke/project/specs/v0.1-001-louke/spec.md" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L3"* ]]
}

@test "VERIFY-203: spec_url_fragment_uppercase_detected_L3" {
    setup_acc_with_001_005
    FIXTURE="$BATS_TEST_TMPDIR/upper_fragment.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 3, "title": "[FR-0001] x", "body": "### Requirement ID\nFR-0001\n\n### Spec Link\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/0001-test/spec.md#FR-0001\n\n### Acceptance Criteria\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/0001-test/acceptance.md#ac-fr-0001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$REPO_ROOT/.louke/project/specs/v0.1-001-louke/spec.md" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L3"* ]]
}

@test "VERIFY-204: acceptance_url_missing_detected_L7" {
    setup_acc_with_001_005
    FIXTURE="$BATS_TEST_TMPDIR/missing_ac.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 4, "title": "[FR-0001] x", "body": "### Requirement ID\nFR-0001\n\n### Spec Link\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/0001-test/spec.md#fr-0001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$REPO_ROOT/.louke/project/specs/v0.1-001-louke/spec.md" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L7"* ]]
}

@test "VERIFY-205: legacy_AC_N_text_detected_L7" {
    setup_acc_with_001_005
    FIXTURE="$BATS_TEST_TMPDIR/old_ac_text.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 5, "title": "[FR-0001] x", "body": "### Requirement ID\nFR-0001\n\n### Spec Link\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/0001-test/spec.md#fr-0001\n\n### Acceptance Criteria\nAC-1: x\nAC-2: y\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$REPO_ROOT/.louke/project/specs/v0.1-001-louke/spec.md" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L7"* ]]
}

@test "VERIFY-206: ac_anchor_missing_in_acceptance_md_L7" {
    # Acceptance URL references ac-fr-9999 but acceptance.md has no such anchor
    setup_acc_with_001_005
    FIXTURE="$BATS_TEST_TMPDIR/bad_ac_anchor.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 6, "title": "[FR-0001] x", "body": "### Requirement ID\nFR-0001\n\n### Spec Link\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/0001-test/spec.md#fr-0001\n\n### Acceptance Criteria\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/0001-test/acceptance.md#ac-fr-9999\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$REPO_ROOT/.louke/project/specs/v0.1-001-louke/spec.md" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L7"* ]]
    [[ "$output" == *"ac-fr-9999"* ]]
}

@test "VERIFY-207: fr_999_anchor_not_in_spec_L5" {
    # Use the real spec.md, but issue references fr-9999 (non-existent)
    setup_acc_with_001_005
    # Prepare acceptance.md with ac-fr-9999, but L5 must still fail
    ACC_FULL="$BATS_TEST_TMPDIR/acc_full.md"
    make_acceptance_fixture "$ACC_FULL" "0001" "0005" "9999"
    FIXTURE="$BATS_TEST_TMPDIR/bad_anchor.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 6, "title": "[FR-9999] x", "body": "### Requirement ID\nFR-9999\n\n### Spec Link\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.1-001-louke/spec.md#fr-9999\n\n### Acceptance Criteria\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.1-001-louke/acceptance.md#ac-fr-9999\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$REPO_ROOT/.louke/project/specs/v0.1-001-louke/spec.md" \
        --acceptance-file "$ACC_FULL" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L5"* ]]
}

# ---------- Validator on real spec instance ----------

@test "VERIFY-300: v0_1_001_spec_md_contains_5_a_id_anchors" {
    # v0.6+ revision: the actual spec (v0.1-001-louke) now contains 5 FR anchors (FR-0001..FR-0005)
    # Original test assumed 11 but spec has been rewritten multiple times in v0.5+ phase, anchor count changes are expected.
    # The existence of anchors themselves is the core contract (not the specific number), the number is kept as sanity check.
    run grep -cE '<a id="fr-[0-9]+"></a>' "$REPO_ROOT/.louke/project/specs/v0.1-001-louke/spec.md"
    [ "$status" -eq 0 ]
    [ "$output" -eq 5 ]
}

@test "VERIFY-301: offline_simulated_spec_5_good_issues_pass" {
    SPEC_FIX="$BATS_TEST_TMPDIR/acc_full.md"
    make_acceptance_fixture "$SPEC_FIX" 0001 0002 0003 0004 0005
    FIXTURE="$BATS_TEST_TMPDIR/all_good.json"
    python3 -c "
import json
issues = []
for i in range(1, 6):
    issues.append({
        'number': 100 + i,
        'title': f'[FR-{i:04d}] test',
        'body': f'### Requirement ID\nFR-{i:04d}\n\n### Spec Link\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.1-001-louke/spec.md#fr-{i:04d}\n\n### Acceptance Criteria\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.1-001-louke/acceptance.md#ac-fr-{i:04d}\n',
        'state': 'open',
    })
print(json.dumps(issues, ensure_ascii=False))
" > "$FIXTURE"
    run python3 "$SCRIPT" --offline \
        --spec-file "$REPO_ROOT/.louke/project/specs/v0.1-001-louke/spec.md" \
        --acceptance-file "$SPEC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[PASS]"* ]]
    [[ "$output" == *"5 PASS"* ]]
}

# ---------- Multi-volume spec (issue #69 scenario) ----------

@test "VERIFY-400: multi_volume_spec_offline_pass" {
    # Simulate millionaire project: spec_id=v0.2-001, filename spec-strategy.md
    SPEC_FIX="$BATS_TEST_TMPDIR/multi_spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# Strategy Spec
<a id="fr-0010"></a>
**FR-0010**: Strategy One
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/multi_acc.md"
    make_acceptance_fixture "$ACC_FIX" "0010"
    FIXTURE="$BATS_TEST_TMPDIR/multi_issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {
    "number": 7,
    "title": "[FR-0010] Strategy One",
    "body": "### Requirement ID\nFR-0010\n\n### Spec Link\nhttps://github.com/zillionare/millionaire/blob/release/v0.2/.louke/project/v0.2-001-strategy-framework/spec-strategy.md#fr-0010\n\n### Acceptance Criteria\nhttps://github.com/zillionare/millionaire/blob/release/v0.2/.louke/project/v0.2-001-strategy-framework/acceptance.md#ac-fr-0010\n",
    "state": "open"
  }
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[PASS]"* ]]
}

@test "VERIFY-401: multi_volume_filename_without_vol_suffix_allowed" {
    # spec.md (no -vol suffix) uses /specs/{id}/ path (spec 004+ default)
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# spec
<a id="fr-0001"></a>
**FR-0001**: x
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    make_acceptance_fixture "$ACC_FIX" "0001"
    FIXTURE="$BATS_TEST_TMPDIR/issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-0001] x", "body": "### Requirement ID\nFR-0001\n\n### Spec Link\nhttps://github.com/x/y/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-0001\n\n### Acceptance Criteria\nhttps://github.com/x/y/blob/main/.louke/project/specs/v0.4-004/acceptance.md#ac-fr-0001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[PASS]"* ]]
}

@test "VERIFY-402: specs_path_and_bare_id_path_both_allowed" {
    # Both /specs/{id}/ (spec 004+) and /{id}/ (millionaire etc.) must be supported
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# x
<a id="fr-0001"></a>
**FR-0001**: x
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    make_acceptance_fixture "$ACC_FIX" "0001"
    FIXTURE="$BATS_TEST_TMPDIR/issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-0001] x", "body": "### Requirement ID\nFR-0001\n\n### Spec Link\nhttps://github.com/x/y/blob/main/.louke/project/v0.2-001/spec.md#fr-0001\n\n### Acceptance Criteria\nhttps://github.com/x/y/blob/main/.louke/project/v0.2-001/acceptance.md#ac-fr-0001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[PASS]"* ]]
}

@test "VERIFY-403: L3_rejects_non_spec_md_filename" {
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# x
<a id="fr-0001"></a>
**FR-0001**: x
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    make_acceptance_fixture "$ACC_FIX" "0001"
    FIXTURE="$BATS_TEST_TMPDIR/bad_filename.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-0001] x", "body": "### Requirement ID\nFR-0001\n\n### Spec Link\nhttps://github.com/x/y/blob/main/.louke/project/specs/v0.4-004/requirements.md#fr-0001\n\n### Acceptance Criteria\nhttps://github.com/x/y/blob/main/.louke/project/specs/v0.4-004/acceptance.md#ac-fr-0001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L3"* ]]
}

# ---------- v0.5-006: L7 three modes (None / spec-fragment / acceptance URL) ----------

# Shared helper: generate acceptance.md with No Acceptance list
# Accepts 3-digit numbers (e.g. "0050"), outputs FR-0050 (3-digit zero-padded, consistent with RE_FR_ID)
make_acceptance_with_no_acc() {
    local path="$1"; shift
    {
        echo "# Demo acceptance"
        for n in "$@"; do
            echo
            echo "<a id=\"ac-fr-${n}\"></a>"
            echo
            echo "## FR-${n}"
            echo
            echo "### AC-1"
            echo "- Condition 1"
        done
        echo
        echo "## No Acceptance"
        echo
        echo "The following FRs have no dedicated acceptance (AC described in test-plan):"
        echo
        for n in "$@"; do
            echo "- FR-${n} (no AC, ground truth covered)"
        done
    } > "$path"
}

@test "VERIFY-500: L7_form_c_none_in_no_acceptance_list_pass" {
    # acceptance.md has ac anchor for FR-0001 + No Acceptance list containing FR-0050/060
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# Min
<a id="fr-0050"></a>
**FR-0050**: Matching ground truth
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    make_acceptance_with_no_acc "$ACC_FIX" "0050"
    FIXTURE="$BATS_TEST_TMPDIR/issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-0050] Matching", "body": "### Requirement ID\nFR-0050\n\n### Spec Link\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-0050\n\n### Acceptance Criteria\nNone\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[PASS]"* ]]
}

@test "VERIFY-501: L7_form_c_none_not_in_no_acceptance_list_fail" {
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# Min
<a id="fr-0001"></a>
**FR-0001**: x
EOF
    # No Acceptance list only has FR-0050, not FR-0001
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    make_acceptance_with_no_acc "$ACC_FIX" "0050"
    FIXTURE="$BATS_TEST_TMPDIR/issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-0001] x", "body": "### Requirement ID\nFR-0001\n\n### Spec Link\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-0001\n\n### Acceptance Criteria\nNone\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L7"* ]]
    [[ "$output" == *"No Acceptance"* ]]
    [[ "$output" == *"FR-0001"* ]]
}

@test "VERIFY-502: L7_form_c_no_acceptance_section_missing_fail" {
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# Min
<a id="fr-0001"></a>
**FR-0001**: x
EOF
    # Use default make_acceptance_fixture, no No Acceptance section
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    make_acceptance_fixture "$ACC_FIX" "0001"
    FIXTURE="$BATS_TEST_TMPDIR/issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-0001] x", "body": "### Requirement ID\nFR-0001\n\n### Spec Link\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-0001\n\n### Acceptance Criteria\nNone\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L7"* ]]
    [[ "$output" == *"No Acceptance"* ]]
}

@test "VERIFY-503: L7_form_b_spec_fragment_anchor_with_FR_pass" {
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# Min
<a id="fr-0185"></a>

### FR-0185 Weighted Average Classic Scheme A

Formula F-CB-1: ...
EOF
    # spec-fragment does not need acceptance.md to provide ac-fr-0185 anchor
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    echo "# No acceptance" > "$ACC_FIX"
    FIXTURE="$BATS_TEST_TMPDIR/issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-0185] Weighted Average", "body": "### Requirement ID\nFR-0185\n\n### Spec Link\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-0185\n\n### Acceptance Criteria\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-0185\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[PASS]"* ]]
}

@test "VERIFY-504: L7_form_b_spec_fragment_anchor_missing_fail" {
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# Min
<a id="fr-0001"></a>
**FR-0001**: x
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    echo "# None" > "$ACC_FIX"
    FIXTURE="$BATS_TEST_TMPDIR/issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-9999] Non-existent", "body": "### Requirement ID\nFR-9999\n\n### Spec Link\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-9999\n\n### Acceptance Criteria\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-9999\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    # L5 fails first (because spec_url also references fr-9999, anchor doesn't exist)
    [[ "$output" == *"L5"* || "$output" == *"L7"* ]]
    [[ "$output" == *"fr-9999"* ]]
}

@test "VERIFY-505: L7_form_b_spec_fragment_no_FR_in_context_fail" {
    # Anchor exists but context doesn't contain FR-XXX (anchor misuse)
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# Min
<a id="fr-0001"></a>
# This is anchor fr-0001 but surrounded by other content
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    echo "# None" > "$ACC_FIX"
    FIXTURE="$BATS_TEST_TMPDIR/issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-0001] x", "body": "### Requirement ID\nFR-0001\n\n### Spec Link\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-0001\n\n### Acceptance Criteria\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-0001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    # L6 (from spec_url check) also fails, either is acceptable
    [[ "$output" == *"L6"* || "$output" == *"L7"* ]]
    [[ "$output" == *"FR-0001"* ]]
}

@test "VERIFY-506: L7_form_a_old_url_still_works_backcompat" {
    # Use same fixture as VERIFY-100, confirm acceptance.md#ac-fr-XXX form still passes
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# Min
<a id="fr-0001"></a>
**FR-0001**: x
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    make_acceptance_fixture "$ACC_FIX" "0001"
    FIXTURE="$BATS_TEST_TMPDIR/issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-0001] x", "body": "### Requirement ID\nFR-0001\n\n### Spec Link\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-0001\n\n### Acceptance Criteria\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/acceptance.md#ac-fr-0001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[PASS]"* ]]
}

@test "VERIFY-507: L7_field_other_text_not_three_valid_forms_fail" {
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# Min
<a id="fr-0001"></a>
**FR-0001**: x
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    make_acceptance_fixture "$ACC_FIX" "0001"
    FIXTURE="$BATS_TEST_TMPDIR/issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-0001] x", "body": "### Requirement ID\nFR-0001\n\n### Spec Link\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-0001\n\n### Acceptance Criteria\nsome random text\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L7"* ]]
    [[ "$output" == *"expected one of"* ]]  # Hint: three valid forms
}

# ---------- v0.5-006: form template regex accepts three forms ----------

@test "FORM-010: acceptance_field_regex_accepts_three_forms" {
    run python3 -c "
import yaml, sys
y = yaml.safe_load(open('$FORM'))
for f in y['body']:
    if f.get('id') == 'acceptance_criteria':
        r = f['validations']['regex']
        # Must include all three form signatures
        assert 'None' in r, f'None missing in regex: {r}'
        assert 'spec(-\\\\w+)?\\\\.md' in r or 'spec(-\\w+)?\\.md' in r, f'spec-fragment form missing in {r}'
        assert 'acceptance\\\\.md' in r or 'acceptance.md' in r, f'acceptance-fragment form missing in {r}'
        # Field description should explain all three forms
        desc = f['attributes']['description']
        assert 'acceptance.md#ac-fr-XXXX' in desc or 'ac-fr-XXXX' in desc or 'ac-fr-0001' in desc, f'description missing acceptance URL example'
        assert 'spec' in desc and ('fr-XXXX' in desc or 'fr-0001' in desc), f'description missing spec-fragment explanation'
        assert 'None' in desc, f'description missing "None" mode explanation'
        sys.exit(0)
sys.exit(1)
"
    [ "$status" -eq 0 ]
}
