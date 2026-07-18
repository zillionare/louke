#!/usr/bin/env bats
# Test Archer: test-plan.md must (1) reference verify_issue_schema.py,
# (2) define AC-FRXXX-YY traceability convention, (3) define lk agent archer ci-scan CI gate.
# v0.5-008+: original Probe role merged into Archer.
# v0.5-011 revision: removed FORM-005/006/007 (old "spec is reference / each AC needs UT / no longer parse spec" wording),
# changed to FORM-001 (merged into issue schema reference) / FORM-002 (keep issue form fields) / FORM-004 (change AC-FRXXX-YY naming convention)
# v0.6+ revision: removed FORM-001 / FORM-003 — Lex phase 2 already validates issue schema via verify_issue_schema,
# Archer only reads issue list and closes the loop via `lk agent archer ci-scan` schema reverse lookup; explicit reference to verify_issue_schema
# responsibility has been pushed down to ci-scan, FORM-004 already covers it.

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/louke/agents"
ARCHER="$AGENTS_DIR/Archer.md"

@test "ARCHER-FORM-002: archer_documents_AC_traceability" {
    # AC traceability convention is AC-FRXXX-YY (replaces old "fr_id" field)
    run grep -qE "AC-(FR|NFR|FRXXX)" "$ARCHER"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Archer.md does not define AC-FRXXX-YY traceability convention"
        false
    }
}

@test "ARCHER-FORM-004: archer_documents_CI_gate_command" {
    # The gate comes from the task/host-project contract; Archer must preserve
    # explicit AC traceability without hard-coding a self-host command.
    run grep -q "CI traceability gate" "$ARCHER"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Archer.md does not define the declared CI traceability gate"
        false
    }
}

@test "ARCHER-V014-001: archer closes human-facing interaction contract" {
    run grep -q "面向人的交互" "$ARCHER"
    [ "$status" -eq 0 ]
    run grep -q "surface/context" "$ARCHER"
    [ "$status" -eq 0 ]
    run grep -q "dirty、stale、冲突" "$ARCHER"
    [ "$status" -eq 0 ]
    run grep -q "后续 UI Spec" "$ARCHER"
    [ "$status" -eq 0 ]
}

@test "ARCHER-V014-002: archer is artifact-scoped without embedding Runtime workflow" {
    run grep -q "任务 manifest" "$ARCHER"
    [ "$status" -eq 0 ]
    run grep -q "不把 Runtime 的 dispatch" "$ARCHER"
    [ "$status" -ne 0 ]
    run grep -q "不得自行运行 Git diff" "$ARCHER"
    [ "$status" -eq 0 ]
}

@test "ARCHER-RESPONSIBILITY-001: archer owns technical decisions and does not ask Human" {
    run grep -q "不主动向 Human 提问" "$ARCHER"
    [ "$status" -eq 0 ]
    run grep -q "自行承担架构、接口和测试设计责任" "$ARCHER"
    [ "$status" -eq 0 ]
    run grep -q "Spec 修订阻塞" "$ARCHER"
    [ "$status" -eq 0 ]
    run grep -q "question: deny" "$ARCHER"
    [ "$status" -eq 0 ]
}

@test "ARCHER-RELEASE-001: release identity flows from canonical input to verified artifacts" {
    run grep -q "canonical release identity" "$ARCHER"
    [ "$status" -eq 0 ]
    run grep -q "branch/tag 只是 release identity 的表示" "$ARCHER"
    [ "$status" -eq 0 ]
    run grep -q "安装/部署/运行出口" "$ARCHER"
    [ "$status" -eq 0 ]
    run grep -q "已有项目缺少必要机制时由 Archer 设计补齐" "$ARCHER"
    [ "$status" -eq 0 ]
    run grep -q "输入（至少 tag）" "$ARCHER"
    [ "$status" -ne 0 ]
}

@test "ARCHER-HOST-CI-001: archer designs mandatory managed GitHub CI for host projects" {
    run grep -q "Louke 托管的 GitHub Actions CI（每个宿主项目必做）" "$ARCHER"
    [ "$status" -eq 0 ]
    run grep -q "\.github/workflows/louke-ci.yml" "$ARCHER"
    [ "$status" -eq 0 ]
    run grep -q "Louke CI / required" "$ARCHER"
    [ "$status" -eq 0 ]
    run grep -q "不得自行发明 TOML 字段" "$ARCHER"
    [ "$status" -eq 0 ]
}

@test "ARCHER-HOST-CI-002: archer allocates every AC to required test layers and CI" {
    run grep -q "AC → observable interface → required test layer(s) → CI gate/job" "$ARCHER"
    [ "$status" -eq 0 ]
    run grep -q "较低层测试不能替代必需的 integration/e2e" "$ARCHER"
    [ "$status" -eq 0 ]
    run grep -q "<!--todo:" "$ARCHER"
    [ "$status" -ne 0 ]
}
