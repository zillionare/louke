#!/usr/bin/env bats
# 测试 .github/ISSUE_TEMPLATE/feature.yml 和 louke/_tools/verify_issue_schema.py

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
FORM="$REPO_ROOT/.github/ISSUE_TEMPLATE/feature.yml"
SCRIPT="$REPO_ROOT/louke/_tools/verify_issue_schema.py"

# ---------- 公共 helper: 生成 acceptance.md fixture ----------

make_acceptance_fixture() {
    # $1 = 路径, $2..$N = FR 列表, 如 "001" "002"
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
            echo "- 条件 1"
            echo
            echo "### AC-2"
            echo "- 条件 2"
        done
    } > "$path"
}

# ---------- Issue Form 存在性和基本结构 ----------

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
    # 需求 ID / Spec 链接 / 验收标准
    for field in "需求 ID" "Spec 链接" "验收标准"; do
        run grep -q "label: $field" "$FORM"
        [ "$status" -eq 0 ] || { echo "Missing form field: $field" >&2; false; }
    done
}

@test "FORM-006: required_id_field_regex_FR_d3" {
    run grep -qE 'regex: .*\^FR-\\\\d\{3\}\$' "$FORM"
    [ "$status" -eq 0 ]
}

@test "FORM-007: spec_url_field_regex_github_spec_md_fr_anchor" {
    # Spec 链接字段的 regex 中, 同时含 spec.md (含多分册 spec-{name}.md) 和 (fr|nfr)-
    run python3 -c "
import yaml, sys
y = yaml.safe_load(open('$FORM'))
for f in y['body']:
    if f.get('id') == 'spec_url':
        r = f['validations']['regex']
        # 支持单文件 spec.md 与多分册 spec(-\w+)?\.md
        assert 'spec(-\\\\w+)?\\\\.md' in r or 'spec(-\\w+)?\\.md' in r, f'spec(-\\w+)?\\.md missing in {r}'
        assert 'fr|nfr' in r, f'fr|nfr missing in {r}'
        assert r.endswith(r'-\d{3}\$'), f'd3 anchor missing in {r}'
        sys.exit(0)
sys.exit(1)
"
    [ "$status" -eq 0 ]
}

@test "FORM-008: acceptance_field_input_with_acceptance_md_anchor" {
    # 验收标准字段必须是 input(不是 textarea), regex 含 acceptance.md + ac-(fr|nfr)-
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
    # 关键: 不应再含 "AC-N: " 占位符(老 schema)
    run grep -F "AC-N: " "$FORM"
    [ "$status" -ne 0 ]
}

@test "FORM-009: acceptance_field_required_true" {
    run grep -q "required: true" "$FORM"
    [ "$status" -eq 0 ]
}

# ---------- 验证器脚本存在性和语法 ----------

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

# ---------- 验证器离线模式: 正常路径 ----------

@test "VERIFY-100: offline_all_compliant_issues_pass" {
    # 用一个最小 spec fixture(只含 FR-001),避免 L8 双向覆盖干扰
    SPEC_FIX="$BATS_TEST_TMPDIR/min_spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# Min Spec
<a id="fr-001"></a>
**FR-001**: minimal fixture
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/min_acc.md"
    make_acceptance_fixture "$ACC_FIX" "001"
    FIXTURE="$BATS_TEST_TMPDIR/good_issues.json"
    cat > "$FIXTURE" <<'EOF'
[
  {
    "number": 42,
    "title": "[FR-001] 用户登录",
    "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/001-test/spec.md#fr-001\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/001-test/acceptance.md#ac-fr-001\n",
    "state": "open"
  }
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[通过]"* ]]
}

# ---------- 验证器离线模式: 异常路径 ----------

# 公共 acceptance fixture (含 fr-001 和 fr-005),供异常测试复用避免 L7 干扰
setup_acc_with_001_005() {
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    make_acceptance_fixture "$ACC_FIX" "001" "005"
    export ACC_FIX
}

@test "VERIFY-201: bad_title_detected_L1" {
    setup_acc_with_001_005
    FIXTURE="$BATS_TEST_TMPDIR/bad_title.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "FR-1 用户登录 (无方括号)", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/001-test/spec.md#fr-001\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/001-test/acceptance.md#ac-fr-001\n", "state": "open"}
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
  {"number": 2, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/001-test/acceptance.md#ac-fr-001\n", "state": "open"}
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
  {"number": 3, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/001-test/spec.md#FR-001\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/001-test/acceptance.md#ac-fr-001\n", "state": "open"}
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
  {"number": 4, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/001-test/spec.md#fr-001\n", "state": "open"}
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
  {"number": 5, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/001-test/spec.md#fr-001\n\n### 验收标准\nAC-1: x\nAC-2: y\n", "state": "open"}
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
    # 验收标准 URL 引用了 ac-fr-999 但 acceptance.md 中没有该锚点
    setup_acc_with_001_005
    FIXTURE="$BATS_TEST_TMPDIR/bad_ac_anchor.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 6, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/001-test/spec.md#fr-001\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/001-test/acceptance.md#ac-fr-999\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$REPO_ROOT/.louke/project/specs/v0.1-001-louke/spec.md" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L7"* ]]
    [[ "$output" == *"ac-fr-999"* ]]
}

@test "VERIFY-207: fr_999_anchor_not_in_spec_L5" {
    # 用同一份真实 spec.md,但 issue 引用 fr-999(不存在)
    setup_acc_with_001_005
    # 准备一份 acceptance.md,含 ac-fr-999 但 L5 仍要失败
    ACC_FULL="$BATS_TEST_TMPDIR/acc_full.md"
    make_acceptance_fixture "$ACC_FULL" "001" "005" "999"
    FIXTURE="$BATS_TEST_TMPDIR/bad_anchor.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 6, "title": "[FR-999] x", "body": "### 需求 ID\nFR-999\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.1-001-louke/spec.md#fr-999\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.1-001-louke/acceptance.md#ac-fr-999\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$REPO_ROOT/.louke/project/specs/v0.1-001-louke/spec.md" \
        --acceptance-file "$ACC_FULL" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L5"* ]]
}

# ---------- 验证器在 spec 实例上跑通 ----------

@test "VERIFY-300: v0_1_001_spec_md_contains_5_a_id_anchors" {
    # v0.6+ 修订: 实际 spec (v0.1-001-louke) 现含 5 个 FR 锚点 (FR-001..FR-005)
    # 原测试假定 11 个但 spec 已在 v0.5+ 阶段多次重写, 锚点数量变化是预期的。
    # 锚点本身的存在性是核心契约 (而不是具体数字), 数字作为 sanity check 保留。
    run grep -cE '<a id="fr-[0-9]+"></a>' "$REPO_ROOT/.louke/project/specs/v0.1-001-louke/spec.md"
    [ "$status" -eq 0 ]
    [ "$output" -eq 5 ]
}

@test "VERIFY-301: offline_simulated_spec_5_good_issues_pass" {
    SPEC_FIX="$BATS_TEST_TMPDIR/acc_full.md"
    make_acceptance_fixture "$SPEC_FIX" 001 002 003 004 005
    FIXTURE="$BATS_TEST_TMPDIR/all_good.json"
    python3 -c "
import json
issues = []
for i in range(1, 6):
    issues.append({
        'number': 100 + i,
        'title': f'[FR-{i:03d}] test',
        'body': f'### 需求 ID\nFR-{i:03d}\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.1-001-louke/spec.md#fr-{i:03d}\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.1-001-louke/acceptance.md#ac-fr-{i:03d}\n',
        'state': 'open',
    })
print(json.dumps(issues, ensure_ascii=False))
" > "$FIXTURE"
    run python3 "$SCRIPT" --offline \
        --spec-file "$REPO_ROOT/.louke/project/specs/v0.1-001-louke/spec.md" \
        --acceptance-file "$SPEC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[通过]"* ]]
    [[ "$output" == *"5 个"* ]]
}

# ---------- 多分册 spec (issue #69 场景) ----------

@test "VERIFY-400: multi_volume_spec_offline_pass" {
    # 模拟 millionaire 项目: spec_id=v0.2-001, 文件名 spec-strategy.md
    SPEC_FIX="$BATS_TEST_TMPDIR/multi_spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# Strategy Spec
<a id="fr-010"></a>
**FR-010**: 策略一
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/multi_acc.md"
    make_acceptance_fixture "$ACC_FIX" "010"
    FIXTURE="$BATS_TEST_TMPDIR/multi_issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {
    "number": 7,
    "title": "[FR-010] 策略一",
    "body": "### 需求 ID\nFR-010\n\n### Spec 链接\nhttps://github.com/zillionare/millionaire/blob/release/v0.2/.louke/project/v0.2-001-strategy-framework/spec-strategy.md#fr-010\n\n### 验收标准\nhttps://github.com/zillionare/millionaire/blob/release/v0.2/.louke/project/v0.2-001-strategy-framework/acceptance.md#ac-fr-010\n",
    "state": "open"
  }
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[通过]"* ]]
}

@test "VERIFY-401: multi_volume_filename_without_vol_suffix_allowed" {
    # spec.md (无 -vol) 走 /specs/{id}/ 路径 (spec 004+ 默认)
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# spec
<a id="fr-001"></a>
**FR-001**: x
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    make_acceptance_fixture "$ACC_FIX" "001"
    FIXTURE="$BATS_TEST_TMPDIR/issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/x/y/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-001\n\n### 验收标准\nhttps://github.com/x/y/blob/main/.louke/project/specs/v0.4-004/acceptance.md#ac-fr-001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[通过]"* ]]
}

@test "VERIFY-402: specs_path_and_bare_id_path_both_allowed" {
    # /specs/{id}/ (spec 004+) 与 /{id}/ (millionaire 等) 都要支持
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# x
<a id="fr-001"></a>
**FR-001**: x
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    make_acceptance_fixture "$ACC_FIX" "001"
    FIXTURE="$BATS_TEST_TMPDIR/issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/x/y/blob/main/.louke/project/v0.2-001/spec.md#fr-001\n\n### 验收标准\nhttps://github.com/x/y/blob/main/.louke/project/v0.2-001/acceptance.md#ac-fr-001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[通过]"* ]]
}

@test "VERIFY-403: L3_rejects_non_spec_md_filename" {
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# x
<a id="fr-001"></a>
**FR-001**: x
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    make_acceptance_fixture "$ACC_FIX" "001"
    FIXTURE="$BATS_TEST_TMPDIR/bad_filename.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/x/y/blob/main/.louke/project/specs/v0.4-004/requirements.md#fr-001\n\n### 验收标准\nhttps://github.com/x/y/blob/main/.louke/project/specs/v0.4-004/acceptance.md#ac-fr-001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L3"* ]]
}

# ---------- v0.5-006: L7 三模式 (无 / spec-fragment / acceptance URL) ----------

# 公共 helper: 生成含 No Acceptance 列表的 acceptance.md
# 接受 3 位数字 (如 "050"),输出 FR-050 (3 位零填充, 与 RE_FR_ID 一致)
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
            echo "- 条件 1"
        done
        echo
        echo "## No Acceptance"
        echo
        echo "以下 FR 无专属 acceptance (AC 在 test-plan 中描述):"
        echo
        for n in "$@"; do
            echo "- FR-${n} (no AC, ground truth 覆盖)"
        done
    } > "$path"
}

@test "VERIFY-500: L7_form_c_none_in_no_acceptance_list_pass" {
    # acceptance.md 含 FR-001 的 ac 锚 + No Acceptance 列表含 FR-050/060
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# Min
<a id="fr-050"></a>
**FR-050**: 撮合 ground truth
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    make_acceptance_with_no_acc "$ACC_FIX" "050"
    FIXTURE="$BATS_TEST_TMPDIR/issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-050] 撮合", "body": "### 需求 ID\nFR-050\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-050\n\n### 验收标准\n无\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[通过]"* ]]
}

@test "VERIFY-501: L7_form_c_none_not_in_no_acceptance_list_fail" {
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# Min
<a id="fr-001"></a>
**FR-001**: x
EOF
    # No Acceptance 列表里只有 FR-050, 不含 FR-001
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    make_acceptance_with_no_acc "$ACC_FIX" "050"
    FIXTURE="$BATS_TEST_TMPDIR/issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-001\n\n### 验收标准\n无\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L7"* ]]
    [[ "$output" == *"No Acceptance"* ]]
    [[ "$output" == *"FR-001"* ]]
}

@test "VERIFY-502: L7_form_c_no_acceptance_section_missing_fail" {
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# Min
<a id="fr-001"></a>
**FR-001**: x
EOF
    # 走默认的 make_acceptance_fixture, 没有 No Acceptance 节
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    make_acceptance_fixture "$ACC_FIX" "001"
    FIXTURE="$BATS_TEST_TMPDIR/issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-001\n\n### 验收标准\n无\n", "state": "open"}
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
<a id="fr-185"></a>

### FR-185 加权均价经典方案 A

公式 F-CB-1: ...
EOF
    # spec-fragment 不需要 acceptance.md 提供 ac-fr-185 锚
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    echo "# 无 acceptance" > "$ACC_FIX"
    FIXTURE="$BATS_TEST_TMPDIR/issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-185] 加权均价", "body": "### 需求 ID\nFR-185\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-185\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-185\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[通过]"* ]]
}

@test "VERIFY-504: L7_form_b_spec_fragment_anchor_missing_fail" {
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# Min
<a id="fr-001"></a>
**FR-001**: x
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    echo "# 无" > "$ACC_FIX"
    FIXTURE="$BATS_TEST_TMPDIR/issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-999] 不存在", "body": "### 需求 ID\nFR-999\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-999\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-999\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    # L5 在前面会先 fail (因为 spec_url 也引用了 fr-999, 锚点不存在)
    [[ "$output" == *"L5"* || "$output" == *"L7"* ]]
    [[ "$output" == *"fr-999"* ]]
}

@test "VERIFY-505: L7_form_b_spec_fragment_no_FR_in_context_fail" {
    # 锚点存在但上下文不含 FR-XXX (锚点误复用)
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# Min
<a id="fr-001"></a>
# 这是锚点 fr-001 但周围是别的东西
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    echo "# 无" > "$ACC_FIX"
    FIXTURE="$BATS_TEST_TMPDIR/issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-001\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    # L6 (来自 spec_url 检查) 也会 fail, 选其一
    [[ "$output" == *"L6"* || "$output" == *"L7"* ]]
    [[ "$output" == *"FR-001"* ]]
}

@test "VERIFY-506: L7_form_a_old_url_still_works_backcompat" {
    # 用现有 VERIFY-100 的同等 fixture, 确认 acceptance.md#ac-fr-XXX 形式仍 pass
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# Min
<a id="fr-001"></a>
**FR-001**: x
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    make_acceptance_fixture "$ACC_FIX" "001"
    FIXTURE="$BATS_TEST_TMPDIR/issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-001\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/acceptance.md#ac-fr-001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[通过]"* ]]
}

@test "VERIFY-507: L7_field_other_text_not_three_valid_forms_fail" {
    SPEC_FIX="$BATS_TEST_TMPDIR/spec.md"
    cat > "$SPEC_FIX" <<'EOF'
# Min
<a id="fr-001"></a>
**FR-001**: x
EOF
    ACC_FIX="$BATS_TEST_TMPDIR/acc.md"
    make_acceptance_fixture "$ACC_FIX" "001"
    FIXTURE="$BATS_TEST_TMPDIR/issue.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.louke/project/specs/v0.4-004/spec.md#fr-001\n\n### 验收标准\n随便写点啥\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L7"* ]]
    [[ "$output" == *"三种"* ]]  # 提示用户有三种合法形式
}

# ---------- v0.5-006: form 模板 regex 接受三种形式 ----------

@test "FORM-010: acceptance_field_regex_accepts_three_forms" {
    run python3 -c "
import yaml, sys
y = yaml.safe_load(open('$FORM'))
for f in y['body']:
    if f.get('id') == 'acceptance_criteria':
        r = f['validations']['regex']
        # 必须包含三种形式的特征
        assert '无' in r, f'无 missing in regex: {r}'
        assert 'spec(-\\\\w+)?\\\\.md' in r or 'spec(-\\w+)?\\.md' in r, f'spec-fragment form missing in {r}'
        assert 'acceptance\\\\.md' in r or 'acceptance.md' in r, f'acceptance-fragment form missing in {r}'
        # 字段 description 应该说明三种形式
        desc = f['attributes']['description']
        assert 'acceptance.md#ac-fr-XXX' in desc or 'ac-fr-XXX' in desc, f'description missing acceptance URL 示例'
        assert 'spec' in desc and 'fr-XXX' in desc, f'description missing spec-fragment 说明'
        assert '无' in desc, f'description missing \"无\" 模式说明'
        sys.exit(0)
sys.exit(1)
"
    [ "$status" -eq 0 ]
}
