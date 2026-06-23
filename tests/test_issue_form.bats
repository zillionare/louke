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

@test "FORM-007: Spec 链接字段的 regex 含 GitHub URL + spec.md + fr- 锚点" {
    # Spec 链接字段的 regex 中, 同时含 spec.md 和 (fr|nfr)-
    run python3 -c "
import yaml, sys
y = yaml.safe_load(open('$FORM'))
for f in y['body']:
    if f.get('id') == 'spec_url':
        r = f['validations']['regex']
        assert 'spec.md' in r or 'spec\\\\.md' in r, f'spec.md missing in {r}'
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
