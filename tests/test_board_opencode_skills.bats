#!/usr/bin/env bats

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

@test "board opencode installs prefixed skills and rewrites agent skill references" {
    cd "$REPO_ROOT"
    rm -rf .opencode

    run python3 -m louke board opencode --quiet
    [ "$status" -eq 0 ] || {
        echo "FAIL: lk board opencode exited $status: $output"
        false
    }

    for skill in lk-inline-discussion lk-reserve-memory lk-security-checklist; do
        f=".opencode/skill/${skill}/SKILL.md"
        [ -f "$f" ] || { echo "FAIL: $f not generated"; false; }
        run grep -E "^name: ${skill}$" "$f"
        [ "$status" -eq 0 ] || { echo "FAIL: $f missing renamed skill frontmatter"; false; }
    done

    run grep -F '**lk-inline-discussion**' ".opencode/agents/archer.md"
    [ "$status" -eq 0 ] || { echo "FAIL: archer.md should reference lk-inline-discussion"; false; }

    run grep -F '`lk-reserve-memory` skill' ".opencode/agents/maestro.md"
    [ "$status" -eq 0 ] || { echo "FAIL: maestro.md should reference lk-reserve-memory"; false; }

    run grep -F '.opencode/skill/lk-inline-discussion/SKILL.md' ".opencode/agents/sage.md"
    [ "$status" -eq 0 ] || { echo "FAIL: sage.md should point to installed skill path"; false; }

    run grep -F 'lk-lk-inline-discussion' ".opencode/agents/sage.md"
    [ "$status" -ne 0 ] || { echo "FAIL: duplicate lk- prefix found in generated agents"; false; }
}
