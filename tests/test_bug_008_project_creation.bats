#!/usr/bin/env bats

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/agents"

@test "BUG-008-RED: Scout prompt should include project creation instruction" {
    run grep -qE "(创建|create).*(project|Project)" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || { echo "FAIL: Scout.md does not contain project creation instructions" >&2; false; }
}

@test "BUG-008-RED: Scout prompt should handle missing project scenario" {
    run grep -qE "(不存在|missing|not exist|not found).*(创建|create|新建)" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || { echo "FAIL: Scout.md should handle the case where project does not exist" >&2; false; }
}
