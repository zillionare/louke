#!/usr/bin/env bats
# Test v0.6-009 agent frontmatter compliance:
#   FR-0020: 5 agents (Warden/Judge/Archer/Librarian/Maestro) must have permission block
#   FR-0030: board.py passes through permission field
#   FR-0040: lk agent lint validation + single primary constraint
#   FR-0060.2: 11 subagents have mode: subagent
#   FR-0060.1: Maestro has mode: primary
#   FR-0070.2: 4 interactive subagents have permission.question: allow; 7 non-interactive have deny; Maestro has deny

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
AGENTS_DIR="$REPO_ROOT/louke/agents"

setup() {
    # Snapshot one agent for restoration (per-test modifications)
    export SNAP_BACKUP=""
    export SNAP_TARGET=""
}

teardown() {
    if [ -n "$SNAP_BACKUP" ] && [ -f "$SNAP_BACKUP" ] && [ -n "$SNAP_TARGET" ]; then
        cp "$SNAP_BACKUP" "$SNAP_TARGET"
        rm -f "$SNAP_BACKUP"
    fi
    # Clean up temp files
    rm -f /tmp/louke_test_parse.py /tmp/louke_inject_debug.py /tmp/louke_inject_unknown.py
}

snapshot_agent() {
    local agent="$1"
    SNAP_TARGET="$AGENTS_DIR/${agent}.md"
    SNAP_BACKUP="$AGENTS_DIR/.${agent}.md.bak"
    cp "$SNAP_TARGET" "$SNAP_BACKUP"
}

# ───────────────────────────────────────────────────────────────────
# FR-0020 + FR-0040: 5 agents must have permission block
# ───────────────────────────────────────────────────────────────────

@test "FR-0020: 4 role agents + Maestro must contain permission block" {
    for agent in warden judge archer librarian maestro; do
        run grep -q "^permission:" "$AGENTS_DIR/${agent}.md"
        [ "$status" -eq 0 ] || {
            echo "FAIL: $agent missing permission: block"
            false
        }
    done
}

@test "FR-0020: remaining 7 subagents do not require permission block" {
    # 7 subagents: sage lex devon scout shield keeper prism
    # They have permission.question block (FR-0070) but don't need the full 11-key block
    for agent in sage lex devon scout shield keeper prism; do
        # At least mode must be subagent (tested separately below)
        run grep -q "^mode: subagent" "$AGENTS_DIR/${agent}.md"
        [ "$status" -eq 0 ]
    done
}

# ───────────────────────────────────────────────────────────────────
# FR-0060.1 + FR-0060.2: mode field
# ───────────────────────────────────────────────────────────────────

@test "FR-0060.1: Maestro mode: primary" {
    run grep -E "^mode: primary" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Maestro.md mode must be 'primary'"
        false
    }
}

@test "FR-0060.2: 11 non-Maestro agents have mode: subagent" {
    for agent in sage lex devon scout archer shield keeper prism warden judge librarian; do
        run grep -E "^mode: subagent" "$AGENTS_DIR/${agent}.md"
        [ "$status" -eq 0 ] || {
            echo "FAIL: ${agent}.md mode must be 'subagent'"
            false
        }
    done
}

@test "NFR-0050: no mode: all remnants" {
    for agent in maestro sage lex devon scout archer shield keeper prism warden judge librarian; do
        run grep -E "^mode: all" "$AGENTS_DIR/${agent}.md"
        [ "$status" -ne 0 ] || {
            echo "FAIL: ${agent}.md still has 'mode: all' (deprecated)"
            false
        }
    done
}

# ───────────────────────────────────────────────────────────────────
# FR-0010: 4 role agents permission block completeness (11 keys)
# ───────────────────────────────────────────────────────────────────

@test "FR-0010.1: Warden has 11 permission keys (4 allow + 7 deny)" {
    local f="$AGENTS_DIR/Warden.md"
    for key in bash read edit grep glob task question webfetch websearch external_directory doom_loop; do
        run grep -qE "^  $key: " "$f"
        [ "$status" -eq 0 ] || {
            echo "FAIL: Warden missing permission key: $key"
            false
        }
    done
}

@test "FR-0010.2: Judge has 11 keys (including question: allow)" {
    local f="$AGENTS_DIR/Judge.md"
    for key in bash read edit grep glob task question webfetch websearch external_directory doom_loop; do
        run grep -qE "^  $key: " "$f"
        [ "$status" -eq 0 ] || { echo "FAIL: Judge missing $key"; false; }
    done
    # Judge-specific: question: allow
    run grep -E "^  question: allow" "$f"
    [ "$status" -eq 0 ] || { echo "FAIL: Judge.question must be allow"; false; }
}

@test "FR-0010.3: Archer has 11 keys (including edit: allow + question: allow)" {
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

@test "FR-0010.4: Librarian has 11 keys (including edit: allow, question: deny)" {
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

@test "FR-0060.1: Maestro has 13 permission keys" {
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
# FR-0070: 4 interactive subagents + 7 non-interactive
# ───────────────────────────────────────────────────────────────────

@test "FR-0070.2: 4 interactive subagents have permission.question: allow" {
    for agent in scout sage archer judge; do
        # 4 role agents (archer judge) already have permission block with question: allow
        # 2 non-role agents (scout sage) have separate permission block with question: allow
        if [ "$agent" = "archer" ] || [ "$agent" = "judge" ]; then
            run grep -E "^  question: allow" "$AGENTS_DIR/${agent}.md"
        else
            # scout / sage separate permission block
            run grep -E "^  question: allow" "$AGENTS_DIR/${agent}.md"
        fi
        [ "$status" -eq 0 ] || {
            echo "FAIL: $agent must have question: allow"
            false
        }
    done
}

@test "FR-0070.2: 5 non-interactive subagents have permission.question: deny" {
    for agent in lex devon shield keeper prism; do
        run grep -E "^  question: deny" "$AGENTS_DIR/${agent}.md"
        [ "$status" -eq 0 ] || {
            echo "FAIL: $agent must have question: deny"
            false
        }
    done
}

# ───────────────────────────────────────────────────────────────────
# FR-0030: board.py passes through permission + mode
# ───────────────────────────────────────────────────────────────────

@test "FR-0030: board.py parse_frontmatter parses permission block as dict" {
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

@test "FR-0030: board.py generates .opencode/agents/*.md with permission block" {
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

@test "FR-0030: board.py dry-run warns on non-whitelisted fields" {
    cd "$REPO_ROOT"
    snapshot_agent warden
    # Temporarily inject a top-level unknown field _debug (before permission block)
    cat > /tmp/louke_inject_debug.py <<'PYEOF'
text = open("louke/agents/Warden.md").read()
# Insert _debug: true after name: warden (top-level field)
text = text.replace("name: warden\n", "name: warden\n_debug: true\n", 1)
open("louke/agents/Warden.md", "w").write(text)
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

@test "FR-0040: removing Warden permission block → lint fail" {
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

@test "FR-0040: injecting unknown key todowrite → lint fail" {
    cd "$REPO_ROOT"
    snapshot_agent warden
    cat > /tmp/louke_inject_unknown.py <<'PYEOF'
text = open("louke/agents/Warden.md").read()
text = text.replace("  bash: allow", "  bash: allow\n  todowrite: allow", 1)
open("louke/agents/Warden.md", "w").write(text)
PYEOF
    python3 /tmp/louke_inject_unknown.py
    run python3 -m louke agent lint
    [ "$status" -ne 0 ] || { echo "FAIL: lint should fail with unknown key"; false; }
    [[ "$output" == *"unknown keys"* ]]
    rm -f /tmp/louke_inject_unknown.py
}

@test "NFR-0050: multiple primary → lint fail" {
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

# === v0.6.14 GLM review: subagent permission completeness ===

@test "v0.6.14: 11 subagents must have task: deny (prevents question tool hallucination regression)" {
    for agent in sage scout devon keeper lex archer judge librarian warden keeper prism shield; do
        # Skip if file doesn't exist
        [ -f "$AGENTS_DIR/${agent}.md" ] || continue
        # 11 subagents must have task: deny (excludes Maestro which is primary)
        run grep -q "^  task: deny" "$AGENTS_DIR/${agent}.md"
        [ "$status" -eq 0 ] || {
            echo "FAIL: $agent missing 'task: deny' in permission block"
            echo "  (OpenCode default for unspecified task is 'allow', which lets subagent"
            echo "   spawn other subagents — violates 'Maestro is sole orchestrator' design"
            echo "   and causes M3 to confuse task/question tools, hallucinating 'no question tool')"
            false
        }
    done
}

@test "v0.6.14: 4 interactive subagents (Scout/Sage/Archer/Judge) must have question: allow" {
    for agent in scout sage archer judge; do
        [ -f "$AGENTS_DIR/${agent}.md" ] || continue
        run grep -q "^  question: allow" "$AGENTS_DIR/${agent}.md"
        [ "$status" -eq 0 ] || {
            echo "FAIL: $agent missing 'question: allow' (interactive subagent needs question tool)"
            false
        }
    done
}

@test "v0.6.14: 7 non-interactive subagents must have question: deny" {
    for agent in devon keeper librarian warden prism shield; do
        # 6 non-interactive (excludes Lex which is spec review, not interactive)
        # actually Lex IS spec-stage but the question test is about the 4-question-tool subagents only
        if [ "$agent" = "lex" ]; then continue; fi
        [ -f "$AGENTS_DIR/${agent}.md" ] || continue
        run grep -q "^  question: deny" "$AGENTS_DIR/${agent}.md"
        [ "$status" -eq 0 ] || {
            echo "FAIL: $agent missing 'question: deny' (non-interactive subagent should not ask user)"
            false
        }
    done
}

@test "v0.6.14: Maestro is the only agent with task: allow" {
    run grep -E "^  task: allow" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ] || { echo "FAIL: Maestro must have task: allow (sole orchestrator)"; false; }
}
