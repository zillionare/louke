# Project History (Archived Versions)

> 由 M-MILESTONE 收尾触发，Maestro 把 `project-info.md` 的当前版本段追加到此文件。
> agent 不解析此文件（仅人类查阅）。

## v0.12 (2026-07-14) — programmatic-workflow-runtime

- **Story**: 以程序固定 workflow、持久状态、两次不可跳过的人类批准（requirements approval + M-LOCK）和完整证据闭环；Agent 只做受限语义工作。产品包含 Projects UI、OpenCode session/context、new feature 与 bug fix 的完整闭环、旧 workspace 显式采用，以及项目内 Louke 安装/明确 global 回退。
- **Version**: 0.12
- **Repo**: github.com/zillionare/louke
- **Project**: louke-v0.12 (#15) [owner: quantclaws]
- **Spec ID**: v0.12-001-programmatic-workflow-runtime
- **Release Branch**: `main`
- **Test Issue**: #161 (M-MILESTONE v0.12.0 真实 OpenCode L3 smoke)
- **Test PR**: #162 (M-MILESTONE v0.12.0 真实 OpenCode L3 smoke PR)
- **Created**: 2026-07-14
- **Notes**: 18 issues shipped (FR-0901..2401 + NFR-0301/0401). 199 unit tests + 180 e2e tests pass; ruff/mypy clean; coverage ≥95%. M-DEV and M-E2E closed with explicit waiver (R-G-R order historical noise from #157 iteration; AC-trace 79/144 at e2e layer is by design per test-plan §6 layer matrix). M-SECURITY disabled in DoD. Browser-compat matrix out of scope per spec.

## v0.4 (2026-06-15) — quote-dialogue 实战测试

- **Story**: 通过 markdown quote 语法完成 spec 澄清，免去 PR 流程；sage 用 > 提问、用户用 >> 回答，按 > 个数缩进。
- **Version**: 0.4
- **Repo**: github.com/zillionare/specforge
- **Project**: specforge-v0.4 (#7) [owner: quantclaws]
- **Spec ID**: v0.4-004-quote-dialogue
- **Release Branch**: `releases/v0.4`
- **Created**: 2026-06-15

## v0.2 (2026-06-02) — Agent 模型分配

- **Story**: 在 specforge init 时，提示用户输入可用模型，自动为各 Agent 分配 model，第一版默认支持 OpenCode
- **Version**: 0.2
- **Repo**: github.com/zillionare/specforge
- **Project**: specforge-v0.2 (#4)
- **Spec ID**: v0.2-002-specforge
- **Test Issue**: #15 (closed)
- **Test PR**: #16 (closed)
- **Created**: 2026-06-02

## v0.1 (2026-05-23) — specforge 自举

- **Story**: 一个以 TDD 为核心，以双人评审为质量门禁，以 Github project/issues 为流程管理工具的多 Agent 开发流程，并且实现自举
- **Version**: 0.1
- **Repo**: github.com/zillionare/specforge
- **Project**: specforge-0.1 (#3)
- **Spec ID**: v0.1-001-specforge
- **Test Issue**: #12 (closed)
- **Test PR**: #13 (open — Sage spec discussion, 间接验证)
- **Created**: 2026-05-23
