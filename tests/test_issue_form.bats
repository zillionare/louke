#!/usr/bin/env bats
# 测试 .github/ISSUE_TEMPLATE/feature.yml 和 tools/verify_issue_schema.py

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
FORM="$REPO_ROOT/.github/ISSUE_TEMPLATE/feature.yml"
SCRIPT="$REPO_ROOT/tools/verify_issue_schema.py"

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

@test "FORM-001: feature.yml 存在" {
    [ -f "$FORM" ]
}

@test "FORM-002: feature.yml 是合法 YAML" {
    run python3 -c "import yaml; yaml.safe_load(open('$FORM'))"
    [ "$status" -eq 0 ]
}

@test "FORM-003: feature.yml 包含 name: Feature" {
    run grep -q "^name: Feature" "$FORM"
    [ "$status" -eq 0 ]
}

@test "FORM-004: feature.yml 包含 labels: [Feature]" {
    run grep -qE "labels:.*Feature" "$FORM"
    [ "$status" -eq 0 ]
}

@test "FORM-005: feature.yml 包含 3 个必填字段 (需求 ID / Spec 链接 / 验收标准)" {
    for field in "需求 ID" "Spec 链接" "验收标准"; do
        run grep -q "label: $field" "$FORM"
        [ "$status" -eq 0 ] || { echo "Missing form field: $field" >&2; false; }
    done
}

@test "FORM-006: 需求 ID 字段的 regex 校验 ^FR-\\d{3}$" {
    run grep -qE 'regex: .*\^FR-\\\\d\{3\}\$' "$FORM"
    [ "$status" -eq 0 ]
}

@test "FORM-007: Spec 链接字段的 regex 含 GitHub URL + spec(.md|-\w+)/?md + fr- 锚点" {
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

@test "FORM-008: 验收标准字段是 input 配 acceptance.md#ac-fr- 锚点 URL" {
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

@test "FORM-009: 验收标准字段有 required: true" {
    run grep -q "required: true" "$FORM"
    [ "$status" -eq 0 ]
}

# ---------- 验证器脚本存在性和语法 ----------

@test "VERIFY-001: verify_issue_schema.py 存在" {
    [ -f "$SCRIPT" ]
}

@test "VERIFY-002: verify_issue_schema.py 是合法 Python 3" {
    run python3 -c "import ast; ast.parse(open('$SCRIPT').read())"
    [ "$status" -eq 0 ]
}

@test "VERIFY-003: 验证器支持 --offline 模式" {
    run python3 "$SCRIPT" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--offline"* ]]
}

@test "VERIFY-004: 验证器支持 --spec 参数" {
    run python3 "$SCRIPT" --help
    [[ "$output" == *"--spec"* ]]
}

@test "VERIFY-005: 验证器支持 --acceptance-file 参数" {
    run python3 "$SCRIPT" --help
    [[ "$output" == *"--acceptance-file"* ]]
}

# ---------- 验证器离线模式: 正常路径 ----------

@test "VERIFY-100: 离线模式 - 全部合规的 issue 通过" {
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
    "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/001-test/spec.md#fr-001\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/001-test/acceptance.md#ac-fr-001\n",
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

@test "VERIFY-201: 标题格式错误被检出 (L1)" {
    setup_acc_with_001_005
    FIXTURE="$BATS_TEST_TMPDIR/bad_title.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 1, "title": "FR-1 用户登录 (无方括号)", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/001-test/spec.md#fr-001\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/001-test/acceptance.md#ac-fr-001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$REPO_ROOT/.specforge/project/specs/v0.1-001-specforge/spec.md" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L1"* ]]
}

@test "VERIFY-202: 缺 Spec 链接字段被检出 (L3)" {
    setup_acc_with_001_005
    FIXTURE="$BATS_TEST_TMPDIR/missing_url.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 2, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/001-test/acceptance.md#ac-fr-001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$REPO_ROOT/.specforge/project/specs/v0.1-001-specforge/spec.md" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L3"* ]]
}

@test "VERIFY-203: Spec 链接 fragment 大写被检出 (L3)" {
    setup_acc_with_001_005
    FIXTURE="$BATS_TEST_TMPDIR/upper_fragment.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 3, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/001-test/spec.md#FR-001\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/001-test/acceptance.md#ac-fr-001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$REPO_ROOT/.specforge/project/specs/v0.1-001-specforge/spec.md" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L3"* ]]
}

@test "VERIFY-204: 验收标准 URL 缺失被检出 (L7)" {
    setup_acc_with_001_005
    FIXTURE="$BATS_TEST_TMPDIR/missing_ac.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 4, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/001-test/spec.md#fr-001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$REPO_ROOT/.specforge/project/specs/v0.1-001-specforge/spec.md" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L7"* ]]
}

@test "VERIFY-205: 验收标准 URL 用了老 AC-N: 文本被检出 (L7)" {
    setup_acc_with_001_005
    FIXTURE="$BATS_TEST_TMPDIR/old_ac_text.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 5, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/001-test/spec.md#fr-001\n\n### 验收标准\nAC-1: x\nAC-2: y\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$REPO_ROOT/.specforge/project/specs/v0.1-001-specforge/spec.md" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L7"* ]]
}

@test "VERIFY-206: AC 锚点在 acceptance.md 中不存在被检出 (L7)" {
    # 验收标准 URL 引用了 ac-fr-999 但 acceptance.md 中没有该锚点
    setup_acc_with_001_005
    FIXTURE="$BATS_TEST_TMPDIR/bad_ac_anchor.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 6, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/001-test/spec.md#fr-001\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/001-test/acceptance.md#ac-fr-999\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$REPO_ROOT/.specforge/project/specs/v0.1-001-specforge/spec.md" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L7"* ]]
    [[ "$output" == *"ac-fr-999"* ]]
}

@test "VERIFY-207: 锚点不存在被检出 (L5) - 引用 spec 中没有的 fr-999" {
    # 用同一份真实 spec.md,但 issue 引用 fr-999(不存在)
    setup_acc_with_001_005
    # 准备一份 acceptance.md,含 ac-fr-999 但 L5 仍要失败
    ACC_FULL="$BATS_TEST_TMPDIR/acc_full.md"
    make_acceptance_fixture "$ACC_FULL" "001" "005" "999"
    FIXTURE="$BATS_TEST_TMPDIR/bad_anchor.json"
    cat > "$FIXTURE" <<'EOF'
[
  {"number": 6, "title": "[FR-999] x", "body": "### 需求 ID\nFR-999\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/v0.1-001-specforge/spec.md#fr-999\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/v0.1-001-specforge/acceptance.md#ac-fr-999\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$REPO_ROOT/.specforge/project/specs/v0.1-001-specforge/spec.md" \
        --acceptance-file "$ACC_FULL" \
        --issues-json "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"L5"* ]]
}

# ---------- 验证器在 spec 实例上跑通 ----------

@test "VERIFY-300: .specforge/project/specs/v0.1-001-specforge/spec.md 含 11 个 <a id> 锚点" {
    run grep -cE '<a id="fr-[0-9]+"></a>' "$REPO_ROOT/.specforge/project/specs/v0.1-001-specforge/spec.md"
    [ "$status" -eq 0 ]
    [ "$output" -eq 11 ]
}

@test "VERIFY-301: 离线模拟 spec 实例, 11 个好 issue 全部通过" {
    SPEC_FIX="$BATS_TEST_TMPDIR/acc_full.md"
    make_acceptance_fixture "$SPEC_FIX" 001 002 003 004 005 006 007 008 009 010 011
    FIXTURE="$BATS_TEST_TMPDIR/all_good.json"
    python3 -c "
import json
issues = []
for i in range(1, 12):
    issues.append({
        'number': 100 + i,
        'title': f'[FR-{i:03d}] test',
        'body': f'### 需求 ID\nFR-{i:03d}\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/v0.1-001-specforge/spec.md#fr-{i:03d}\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/v0.1-001-specforge/acceptance.md#ac-fr-{i:03d}\n',
        'state': 'open',
    })
print(json.dumps(issues, ensure_ascii=False))
" > "$FIXTURE"
    run python3 "$SCRIPT" --offline \
        --spec-file "$REPO_ROOT/.specforge/project/specs/v0.1-001-specforge/spec.md" \
        --acceptance-file "$SPEC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[通过]"* ]]
    [[ "$output" == *"11 个"* ]]
}

# ---------- 多分册 spec (issue #69 场景) ----------

@test "VERIFY-400: 多分册 spec (spec-{vol}.md) 离线模式通过" {
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
    "body": "### 需求 ID\nFR-010\n\n### Spec 链接\nhttps://github.com/zillionare/millionaire/blob/release/v0.2/.specforge/project/v0.2-001-strategy-framework/spec-strategy.md#fr-010\n\n### 验收标准\nhttps://github.com/zillionare/millionaire/blob/release/v0.2/.specforge/project/v0.2-001-strategy-framework/acceptance.md#ac-fr-010\n",
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

@test "VERIFY-401: 多分册 spec 文件名但无 vol_suffix 仍允许" {
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
  {"number": 1, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/x/y/blob/main/.specforge/project/specs/v0.4-004/spec.md#fr-001\n\n### 验收标准\nhttps://github.com/x/y/blob/main/.specforge/project/specs/v0.4-004/acceptance.md#ac-fr-001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[通过]"* ]]
}

@test "VERIFY-402: /specs/ 路径与裸 {id}/ 路径同时被允许" {
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
  {"number": 1, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/x/y/blob/main/.specforge/project/v0.2-001/spec.md#fr-001\n\n### 验收标准\nhttps://github.com/x/y/blob/main/.specforge/project/v0.2-001/acceptance.md#ac-fr-001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[通过]"* ]]
}

@test "VERIFY-403: L3 拒绝非 spec(.md|-\w+.md) 形式的文件名" {
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
  {"number": 1, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/x/y/blob/main/.specforge/project/specs/v0.4-004/requirements.md#fr-001\n\n### 验收标准\nhttps://github.com/x/y/blob/main/.specforge/project/specs/v0.4-004/acceptance.md#ac-fr-001\n", "state": "open"}
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

@test "VERIFY-500: L7 形式 (c) — 验收标准=无 + FR 在 No Acceptance 列表中 → pass" {
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
  {"number": 1, "title": "[FR-050] 撮合", "body": "### 需求 ID\nFR-050\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/v0.4-004/spec.md#fr-050\n\n### 验收标准\n无\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[通过]"* ]]
}

@test "VERIFY-501: L7 形式 (c) — 验收标准=无 + FR 不在 No Acceptance 列表中 → fail" {
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
  {"number": 1, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/v0.4-004/spec.md#fr-001\n\n### 验收标准\n无\n", "state": "open"}
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

@test "VERIFY-502: L7 形式 (c) — acceptance.md 缺 No Acceptance 节 → fail" {
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
  {"number": 1, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/v0.4-004/spec.md#fr-001\n\n### 验收标准\n无\n", "state": "open"}
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

@test "VERIFY-503: L7 形式 (b) — spec-fragment URL + 锚点存在 + 上下文含 FR-XXX → pass" {
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
  {"number": 1, "title": "[FR-185] 加权均价", "body": "### 需求 ID\nFR-185\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/v0.4-004/spec.md#fr-185\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/v0.4-004/spec.md#fr-185\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[通过]"* ]]
}

@test "VERIFY-504: L7 形式 (b) — spec-fragment URL + spec 锚点不存在 → fail" {
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
  {"number": 1, "title": "[FR-999] 不存在", "body": "### 需求 ID\nFR-999\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/v0.4-004/spec.md#fr-999\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/v0.4-004/spec.md#fr-999\n", "state": "open"}
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

@test "VERIFY-505: L7 形式 (b) — spec-fragment URL + 锚点上下文无 FR-XXX → fail" {
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
  {"number": 1, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/v0.4-004/spec.md#fr-001\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/v0.4-004/spec.md#fr-001\n", "state": "open"}
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

@test "VERIFY-506: L7 形式 (a) 旧 URL 形式仍正常 (向后兼容)" {
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
  {"number": 1, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/v0.4-004/spec.md#fr-001\n\n### 验收标准\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/v0.4-004/acceptance.md#ac-fr-001\n", "state": "open"}
]
EOF
    run python3 "$SCRIPT" --offline \
        --spec-file "$SPEC_FIX" \
        --acceptance-file "$ACC_FIX" \
        --issues-json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[通过]"* ]]
}

@test "VERIFY-507: L7 字段值是其它文本 (非三种合法形式) → fail 并提示三种" {
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
  {"number": 1, "title": "[FR-001] x", "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/foo/bar/blob/main/.specforge/project/specs/v0.4-004/spec.md#fr-001\n\n### 验收标准\n随便写点啥\n", "state": "open"}
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

@test "FORM-010: 验收标准字段 regex 接受 无 / spec-fragment / acceptance-fragment" {
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
