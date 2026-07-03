#!/usr/bin/env bats
# 测试 v0.6-009 agent frontmatter 合规性:
#   FR-0020: 5 个 agent (Warden/Judge/Archer/Librarian/Maestro) 必填 permission 块
#   FR-0030: board.py 透传 permission 字段
#   FR-0040: lk agent lint 校验 + 单一 primary 约束
#   FR-0060.2: 11 个 subagent mode: subagent
#   FR-0060.1: Maestro mode: primary
#   FR-0070.2: 4 交互式 subagent permission.question: allow; 7 非交互式 deny; Maestro deny

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
AGENTS_DIR="$REPO_ROOT/agents"

setup() {
    # Snapshot 一个 agent 用于恢复 (per-test 改动)
    export SNAP_BACKUP=""
    export SNAP_TARGET=""
}

teardown() {
    if [ -n "$SNAP_BACKUP" ] && [ -f "$SNAP_BACKUP" ] && [ -n "$SNAP_TARGET" ]; then
        cp "$SNAP_BACKUP" "$SNAP_TARGET"
        rm -f "$SNAP_BACKUP"
    fi
    # 清理临时文件
    rm -f /tmp/louke_test_parse.py /tmp/louke_inject_debug.py /tmp/louke_inject_unknown.py
}

snapshot_agent() {
    local agent="$1"
    SNAP_TARGET="$AGENTS_DIR/${agent}.md"
    SNAP_BACKUP="$AGENTS_DIR/.${agent}.md.bak"
    cp "$SNAP_TARGET" "$SNAP_BACKUP"
}

# ───────────────────────────────────────────────────────────────────
# FR-0020 + FR-0040: 5 个 agent 必填 permission 块
# ───────────────────────────────────────────────────────────────────

@test "FR-0020: 4 角色 + Maestro 必含 permission 块" {
    for agent in warden judge archer librarian maestro; do
        run grep -q "^permission:" "$AGENTS_DIR/${agent}.md"
        [ "$status" -eq 0 ] || {
            echo "FAIL: $agent missing permission: block"
            false
        }
    done
}

@test "FR-0020: 其余 7 subagent 不强制 permission 块" {
    # 7 subagent: sage lex devon scout shield keeper prism
    # 它们有 permission.question 块 (FR-0070) 但不需要完整的 11 键块
    for agent in sage lex devon scout shield keeper prism; do
        # 至少 mode 必须是 subagent (下面有专门测试)
        run grep -q "^mode: subagent" "$AGENTS_DIR/${agent}.md"
        [ "$status" -eq 0 ]
    done
}

# ───────────────────────────────────────────────────────────────────
# FR-0060.1 + FR-0060.2: mode 字段
# ───────────────────────────────────────────────────────────────────

@test "FR-0060.1: Maestro mode: primary" {
    run grep -E "^mode: primary" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Maestro.md mode must be 'primary'"
        false
    }
}

@test "FR-0060.2: 11 个非 Maestro agent mode: subagent" {
    for agent in sage lex devon scout archer shield keeper prism warden judge librarian; do
        run grep -E "^mode: subagent" "$AGENTS_DIR/${agent}.md"
        [ "$status" -eq 0 ] || {
            echo "FAIL: ${agent}.md mode must be 'subagent'"
            false
        }
    done
}

@test "NFR-0050: 没有 mode: all 残留" {
    for agent in maestro sage lex devon scout archer shield keeper prism warden judge librarian; do
        run grep -E "^mode: all" "$AGENTS_DIR/${agent}.md"
        [ "$status" -ne 0 ] || {
            echo "FAIL: ${agent}.md still has 'mode: all' (deprecated)"
            false
        }
    done
}

# ───────────────────────────────────────────────────────────────────
# FR-0010: 4 角色 permission 块完整性 (11 键)
# ───────────────────────────────────────────────────────────────────

@test "FR-0010.1: Warden 11 键 permission (4 allow + 7 deny)" {
    local f="$AGENTS_DIR/Warden.md"
    for key in bash read edit grep glob task question webfetch websearch external_directory doom_loop; do
        run grep -qE "^  $key: " "$f"
        [ "$status" -eq 0 ] || {
            echo "FAIL: Warden missing permission key: $key"
            false
        }
    done
}

@test "FR-0010.2: Judge 11 键 (含 question: allow)" {
    local f="$AGENTS_DIR/Judge.md"
    for key in bash read edit grep glob task question webfetch websearch external_directory doom_loop; do
        run grep -qE "^  $key: " "$f"
        [ "$status" -eq 0 ] || { echo "FAIL: Judge missing $key"; false; }
    done
    # Judge 特有: question: allow
    run grep -E "^  question: allow" "$f"
    [ "$status" -eq 0 ] || { echo "FAIL: Judge.question must be allow"; false; }
}

@test "FR-0010.3: Archer 11 键 (含 edit: allow + question: allow)" {
    local f="$AGENTS_DIR/Archer.md"
    for key in bash read edit grep glob task question webfetch websearch external_directory doom_loop; do
        run grep -qE "^  $key: " "$f"
        [ "$status" -eq 0 ] || { echo "FAIL: Archer missing $key"; false; }
    done
    run grep -E "^  edit: allow" "$f"
    [ "$status" -eq 0 ] || { echo "FAIL: Archer.edit must be allow"; false; }
    run grep -E "^  question: allow" "$f"
    [ "$status" -eq 0 ] || { echo "FAIL: Archer.question must be allow"; false; }
}

@test "FR-0010.4: Librarian 11 键 (含 edit: allow, question: deny)" {
    local f="$AGENTS_DIR/Librarian.md"
    for key in bash read edit grep glob task question webfetch websearch external_directory doom_loop; do
        run grep -qE "^  $key: " "$f"
        [ "$status" -eq 0 ] || { echo "FAIL: Librarian missing $key"; false; }
    done
    run grep -E "^  edit: allow" "$f"
    [ "$status" -eq 0 ] || { echo "FAIL: Librarian.edit must be allow"; false; }
    run grep -E "^  question: deny" "$f"
    [ "$status" -eq 0 ] || { echo "FAIL: Librarian.question must be deny"; false; }
}

@test "FR-0060.1: Maestro 13 键 permission" {
    local f="$AGENTS_DIR/Maestro.md"
    for key in bash read edit grep glob task question webfetch websearch skill lsp external_directory doom_loop; do
        run grep -qE "^  $key: " "$f"
        [ "$status" -eq 0 ] || { echo "FAIL: Maestro missing $key"; false; }
    done
    run grep -E "^  task: allow" "$f"
    [ "$status" -eq 0 ] || { echo "FAIL: Maestro.task must be allow"; false; }
    run grep -E "^  question: deny" "$f"
    [ "$status" -eq 0 ] || { echo "FAIL: Maestro.question must be deny"; false; }
}

# ───────────────────────────────────────────────────────────────────
# FR-0070: 4 交互式 subagent + 7 非交互式
# ───────────────────────────────────────────────────────────────────

@test "FR-0070.2: 4 交互式 subagent permission.question: allow" {
    for agent in scout sage archer judge; do
        # 4 角色 (archer judge) 已有 permission 块含 question: allow
        # 2 非角色 (scout sage) 单独的 permission 块也含 question: allow
        if [ "$agent" = "archer" ] || [ "$agent" = "judge" ]; then
            run grep -E "^  question: allow" "$AGENTS_DIR/${agent}.md"
        else
            # scout / sage 单独 permission 块
            run grep -E "^  question: allow" "$AGENTS_DIR/${agent}.md"
        fi
        [ "$status" -eq 0 ] || {
            echo "FAIL: $agent must have question: allow"
            false
        }
    done
}

@test "FR-0070.2: 5 个非交互式 subagent permission.question: deny" {
    for agent in lex devon shield keeper prism; do
        run grep -E "^  question: deny" "$AGENTS_DIR/${agent}.md"
        [ "$status" -eq 0 ] || {
            echo "FAIL: $agent must have question: deny"
            false
        }
    done
}

# ───────────────────────────────────────────────────────────────────
# FR-0030: board.py 透传 permission + mode
# ───────────────────────────────────────────────────────────────────

@test "FR-0030: board.py parse_frontmatter 解析 permission 块为 dict" {
    cat > /tmp/louke_test_parse.py <<'PYEOF'
import sys
sys.path.insert(0, "REPO_ROOT_PLACEHOLDER")
from louke.board import parse_frontmatter
fm, body = parse_frontmatter(open("AGENTS_DIR_PLACEHOLDER/Warden.md").read())
assert "permission" in fm, "permission missing"
assert isinstance(fm["permission"], dict), f"permission not dict: {type(fm['permission'])}"
assert fm["permission"]["bash"] == "allow"
assert fm["permission"]["edit"] == "deny"
assert fm["mode"] == "subagent"
print("OK")
PYEOF
    sed -i '' "s|REPO_ROOT_PLACEHOLDER|$REPO_ROOT|g; s|AGENTS_DIR_PLACEHOLDER|$AGENTS_DIR|g" /tmp/louke_test_parse.py
    run python3 /tmp/louke_test_parse.py
    [ "$status" -eq 0 ] || { echo "FAIL: parse test exit $status: $output"; false; }
    rm -f /tmp/louke_test_parse.py
}

@test "FR-0030: board.py 生成的 .opencode/agents/*.md 含 permission 块" {
    cd "$REPO_ROOT"
    rm -rf .opencode
    python3 -m louke board opencode --quiet
    for agent in warden judge archer librarian maestro; do
        f=".opencode/agents/${agent}.md"
        [ -f "$f" ] || { echo "FAIL: $f not generated"; false; }
        run grep -E "^permission:" "$f"
        [ "$status" -eq 0 ] || { echo "FAIL: $f missing permission:"; false; }
    done
    run grep -E "^mode: primary" ".opencode/agents/maestro.md"
    [ "$status" -eq 0 ] || { echo "FAIL: maestro.md mode must be primary in generated"; false; }
}

@test "FR-0030: board.py dry-run 警告未白名单字段" {
    cd "$REPO_ROOT"
    snapshot_agent warden
    # 临时注入一个顶层未知字段 _debug (在 permission 块之前)
    cat > /tmp/louke_inject_debug.py <<'PYEOF'
text = open("agents/Warden.md").read()
# 在 name: warden 之后插入 _debug: true (顶层字段)
text = text.replace("name: warden\n", "name: warden\n_debug: true\n", 1)
open("agents/Warden.md", "w").write(text)
PYEOF
    python3 /tmp/louke_inject_debug.py
    run python3 -m louke board opencode --dry-run
    [[ "$output" == *"dropped unknown frontmatter key"* ]]
    rm -f /tmp/louke_inject_debug.py
}

# ───────────────────────────────────────────────────────────────────
# FR-0040: lk agent lint
# ───────────────────────────────────────────────────────────────────

@test "FR-0040: lk agent lint 12 agents pass" {
    cd "$REPO_ROOT"
    run python3 -m louke agent lint
    [ "$status" -eq 0 ] || { echo "FAIL: lint exit $status"; false; }
    [[ "$output" == *"12 agents pass lint"* ]] || {
        echo "FAIL: expected '12 agents pass lint' in output, got: $output"
        false
    }
}

@test "FR-0040: lk agent lint --check-opencode-version 1.17.11 >= 1.1.1" {
    cd "$REPO_ROOT"
    run python3 -m louke agent lint --check-opencode-version
    [ "$status" -eq 0 ]
    [[ "$output" == *"opencode 1.17.11 >= MIN_OPENCODE_VERSION 1.1.1"* ]] || \
    [[ "$output" == *"opencode --version unavailable"* ]] || {
        echo "FAIL: opencode version check failed: $output"
        false
    }
}

@test "FR-0040: 删 Warden permission 块 → lint fail" {
    cd "$REPO_ROOT"
    snapshot_agent warden
    # Remove permission block
    python3 -c "
text = open('$AGENTS_DIR/Warden.md').read()
lines = text.split('\\n')
new = []
in_p = False
for line in lines:
    if line.strip() == 'permission:':
        in_p = True
        continue
    if in_p and line.strip() == '':
        in_p = False
        continue
    if in_p:
        continue
    new.append(line)
open('$AGENTS_DIR/Warden.md', 'w').write('\\n'.join(new))
"
    run python3 -m louke agent lint
    [ "$status" -ne 0 ] || { echo "FAIL: lint should fail with missing permission"; false; }
    [[ "$output" == *"missing permission block for warden"* ]]
}

@test "FR-0040: 注入未知键 todowrite → lint fail" {
    cd "$REPO_ROOT"
    snapshot_agent warden
    cat > /tmp/louke_inject_unknown.py <<'PYEOF'
text = open("agents/Warden.md").read()
text = text.replace("  bash: allow", "  bash: allow\n  todowrite: allow", 1)
open("agents/Warden.md", "w").write(text)
PYEOF
    python3 /tmp/louke_inject_unknown.py
    run python3 -m louke agent lint
    [ "$status" -ne 0 ] || { echo "FAIL: lint should fail with unknown key"; false; }
    [[ "$output" == *"unknown keys"* ]]
    rm -f /tmp/louke_inject_unknown.py
}

@test "NFR-0050: 多 primary → lint fail" {
    cd "$REPO_ROOT"
    snapshot_agent sage
    # Make Sage primary (duplicate of Maestro)
    sed -i '' 's/^mode: subagent$/mode: primary/' "$AGENTS_DIR/Sage.md" 2>/dev/null || \
    sed -i 's/^mode: subagent$/mode: primary/' "$AGENTS_DIR/Sage.md"
    run python3 -m louke agent lint
    [ "$status" -ne 0 ] || { echo "FAIL: lint should fail with multiple primary"; false; }
    [[ "$output" == *"only maestro can be primary"* ]]
    # teardown will restore Sage via snapshot_agent
}
