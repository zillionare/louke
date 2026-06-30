# louke v0.1 — Framework Init Spec

- **Spec ID**: v0.1-001-louke
- **目的**: louke 框架的初始化 spec；作为 verify_issue_schema 的 fixture
- **状态**: fixture（仅供 bats 测试使用，不进入真实工作流）

## 功能需求

<a id="fr-0001"></a>
**FR-0001**: louke 框架定义 12 个专业 agent

<a id="fr-0002"></a>
**FR-0002**: 阶段表 (M-FOUND/M-SPEC/M-TESTPLAN/M-ARCH/M-LOCK/M-DEV/M-E2E/M-BUGFIX/M-SECURITY/M-MILESTONE)

<a id="fr-0003"></a>
**FR-0003**: 每阶段实施者 ≠ 评审者（构建/验收分离）

<a id="fr-0004"></a>
**FR-0004**: `lk` CLI 提供工具强制的 hold point

<a id="fr-0005"></a>
**FR-0005**: spec/acceptance/test-plan 通过 quote dialogue + Lex 审核锁定
