#!/usr/bin/env bats
# Test v0.6-009 agent frontmatter compliance:
#   FR-0020: 5 agents (Warden/Judge/Archer/Librarian/Maestro) must have permission block
#   FR-0030: board.py passes through permission field
#   FR-0040: lk agent lint validation + single primary constraint
#   FR-0060.2: 12 subagents have mode: subagent
#   FR-0060.1: Maestro has mode: primary
#   FR-0070.2: 5 interactive subagents have permission.question: allow

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
AGENTS_DIR="$REPO_ROOT/louke/agents"

# Agent filenames in louke/agents/ use TitleCase (Warden.md), but tests
# below iterate with lowercase names for readability. Capitalize the first
# letter before joining the directory so the path resolves on case-sensitive
# filesystems (Linux CI). Uses awk because BSD sed and GNU sed disagree on
# the \U uppercase escape.
agent_file() { echo "${AGENTS_DIR}/$(echo "$1" | awk '{print toupper(substr($0,1,1)) substr($0,2)}').md"; }

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
    SNAP_TARGET="$(agent_file $agent)"
    # Use a distinct suffix so a later sed -i.bak doesn't overwrite our
    # pre-modification backup. Teardown uses SNAP_BACKUP to restore.
    SNAP_BACKUP="${AGENTS_DIR}/.$(echo "$agent" | awk '{print toupper(substr($0,1,1)) substr($0,2)}').md.snapshot.bak"
    cp "$SNAP_TARGET" "$SNAP_BACKUP"
}

# ───────────────────────────────────────────────────────────────────
# FR-0020 + FR-0040: 5 agents must have permission block
# ───────────────────────────────────────────────────────────────────

@test "FR-0020: 4 role agents + Maestro must contain permission block" {
    for agent in warden judge archer librarian maestro; do
        run grep -q "^permission:" "$(agent_file $agent)"
        [ "$status" -eq 0 ] || {
            echo "FAIL: $agent missing permission: block"
            false
        }
    done
}

@test "FR-0020: remaining 8 subagents do not require permission block" {
    # 8 subagents: scribe sage lex devon scout shield keeper prism
    # They have permission.question block (FR-0070) but don't need the full 11-key block
    for agent in scribe sage lex devon scout shield keeper prism; do
        # At least mode must be subagent (tested separately below)
        run grep -q "^mode: subagent" "$(agent_file $agent)"
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

@test "FR-0060.2: 12 non-Maestro agents have mode: subagent" {
    for agent in scribe sage lex devon scout archer shield keeper prism warden judge librarian; do
        run grep -E "^mode: subagent" "$(agent_file $agent)"
        [ "$status" -eq 0 ] || {
            echo "FAIL: ${agent}.md mode must be 'subagent'"
            false
        }
    done
}

@test "NFR-0050: no mode: all remnants" {
    for agent in maestro scribe sage lex devon scout archer shield keeper prism warden judge librarian; do
        run grep -E "^mode: all" "$(agent_file $agent)"
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

@test "FR-0060.1: Maestro has current primary-agent permission keys" {
    local f="$AGENTS_DIR/Maestro.md"
    for key in bash read edit grep glob task question webfetch websearch external_directory doom_loop; do
        run grep -qE "^  $key: " "$f"
        [ "$status" -eq 0 ] || { echo "FAIL: Maestro missing $key"; false; }
    done
    run grep -E "^  task: allow" "$f"
    [ "$status" -eq 0 ] || { echo "FAIL: Maestro.task must be allow"; false; }
    run grep -E "^  question: allow" "$f"
    [ "$status" -eq 0 ] || { echo "FAIL: Maestro.question must be allow"; false; }
}

# ───────────────────────────────────────────────────────────────────
# FR-0070: interactive and non-interactive subagents
# ───────────────────────────────────────────────────────────────────

@test "FR-0070.2: 5 interactive subagents have permission.question: allow" {
    for agent in scribe scout sage archer judge; do
        # Role agents (archer/judge) and authoring agents declare question explicitly.
        if [ "$agent" = "archer" ] || [ "$agent" = "judge" ]; then
            run grep -E "^  question: allow" "$(agent_file $agent)"
        else
            # scribe / scout / sage separate permission block
            run grep -E "^  question: allow" "$(agent_file $agent)"
        fi
        [ "$status" -eq 0 ] || {
            echo "FAIL: $agent must have question: allow"
            false
        }
    done
}

@test "FR-0070.2: 5 non-interactive subagents have permission.question: deny" {
    for agent in lex devon shield keeper prism; do
        run grep -E "^  question: deny" "$(agent_file $agent)"
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
    sed -i.bak "s|REPO_ROOT_PLACEHOLDER|$REPO_ROOT|g; s|AGENTS_DIR_PLACEHOLDER|$AGENTS_DIR|g" /tmp/louke_test_parse.py
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

@test "FR-0040: lk agent lint passes" {
    cd "$REPO_ROOT"
    run python3 -m louke agent lint
    [ "$status" -eq 0 ] || { echo "FAIL: lint exit $status: $output"; false; }
    # Robust: parse the agent count from output rather than hard-coding it.
    # Output format: '✓ OK N agents pass lint (K with permission)'. When
    # new agent .md files are added (e.g. Story.md added 2026-07 by user),
    # this test stays green.
    local agent_count
    agent_count=$(echo "$output" | grep -oE '[0-9]+ agents pass lint' | head -1 | grep -oE '[0-9]+' || true)
    if [ -z "$agent_count" ]; then
        echo "FAIL: could not parse agent count from lint output: $output"
        false
    elif [ "$agent_count" -lt 1 ]; then
        echo "FAIL: expected >=1 agents, got $agent_count"
        false
    fi
    # Also assert the success marker
    [[ "$output" == *"pass lint"* ]] || {
        echo "FAIL: expected 'pass lint' in output, got: $output"
        false
    }
}

@test "FR-0040: lk agent lint --check-opencode-version reports compatible version" {
    cd "$REPO_ROOT"
    run python3 -m louke agent lint --check-opencode-version
    [ "$status" -eq 0 ]
    [[ "$output" == *"opencode "*">= MIN_OPENCODE_VERSION 1.1.1"* ]] || \
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

@test "FR-0040: lint validates a declared permission block even when it is not required" {
    cd "$REPO_ROOT"
    snapshot_agent scribe
    python3 -c "
text = open('$AGENTS_DIR/Scribe.md').read()
text = text.replace('  bash: allow', '  bash: allow\\n  todowrite: allow', 1)
open('$AGENTS_DIR/Scribe.md', 'w').write(text)
"
    run python3 -m louke agent lint
    [ "$status" -ne 0 ] || { echo "FAIL: lint should validate Scribe permission keys"; false; }
    [[ "$output" == *"scribe: permission has unknown keys"* ]]
}

@test "v0.14: Scribe/Sage/Lex descriptions cover their current workflow roles" {
    run grep -E '^description: .*Go/Park/No-Go recommendation$' "$AGENTS_DIR/Scribe.md"
    [ "$status" -eq 0 ]
    run grep -E '^description: Story peer review and requirements authoring .*Spec and Acceptance contracts$' "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ]
    run grep -E '^description: Requirements semantic reviewer .*Spec/Acceptance assertability.*$' "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ]
}

@test "NFR-0050: multiple primary → lint fail" {
    cd "$REPO_ROOT"
    snapshot_agent sage
    # Make Sage primary (duplicate of Maestro). Use -i.bak which works on
    # both GNU sed (Linux) and BSD sed (macOS); the .bak file holds the
    # MODIFIED content and is cleaned up here. Snapshot backup is at
    # .Sage.md.snapshot.bak (see snapshot_agent), so this doesn't collide.
    sed -i.bak 's/^mode: subagent$/mode: primary/' "$AGENTS_DIR/Sage.md"
    rm -f "$AGENTS_DIR/Sage.md.bak"
    run python3 -m louke agent lint
    [ "$status" -ne 0 ] || { echo "FAIL: lint should fail with multiple primary"; false; }
    [[ "$output" == *"only maestro can be primary"* ]]
    # teardown will restore Sage via snapshot_agent
}

# === v0.6.14 GLM review: subagent permission completeness ===

@test "v0.6.14: 12 subagents must have task: deny (prevents question tool hallucination regression)" {
    for agent in scribe sage scout devon keeper lex archer judge librarian warden prism shield; do
        # Skip if file doesn't exist
        [ -f "$(agent_file $agent)" ] || continue
        # 12 subagents must have task: deny (excludes Maestro which is primary)
        run grep -q "^  task: deny" "$(agent_file $agent)"
        [ "$status" -eq 0 ] || {
            echo "FAIL: $agent missing 'task: deny' in permission block"
            echo "  (OpenCode default for unspecified task is 'allow', which lets subagent"
            echo "   spawn other subagents — violates 'Maestro is sole orchestrator' design"
            echo "   and causes M3 to confuse task/question tools, hallucinating 'no question tool')"
            false
        }
    done
}

@test "v0.6.14: 5 interactive subagents (Scribe/Scout/Sage/Archer/Judge) must have question: allow" {
    for agent in scribe scout sage archer judge; do
        [ -f "$(agent_file $agent)" ] || continue
        run grep -q "^  question: allow" "$(agent_file $agent)"
        [ "$status" -eq 0 ] || {
            echo "FAIL: $agent missing 'question: allow' (interactive subagent needs question tool)"
            false
        }
    done
}

@test "v0.6.14: 6 non-interactive subagents must have question: deny" {
    for agent in devon keeper librarian warden prism shield; do
        [ -f "$(agent_file $agent)" ] || continue
        run grep -q "^  question: deny" "$(agent_file $agent)"
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
