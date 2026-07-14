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
- **Created**: 2026-07-14
- **Tag**: `v0.12.0` (this commit)
- **Notes**:
  - 25 FRs + 5 NFRs shipped; 144/144 ACs referenced (M-DEV unit layer)
  - Runtime domain modules (louke/runtime/): 25 files, 8296 lines (B-series unit tests)
  - 10 v0.12 HTTP sub-apps mounted in `app.py` (B1)
  - 5 v0.12 frontend pages: setup/projects/gates/runs/migration (B3)
  - `lk serve` setup-only + runtime_selector fail-closed (B2)
  - **Real OpenCode HTTP adapter** via `louke/opencode/real.py` - `RealOpenCodeAdapter` over httpx (B4); `OpenCodeInstanceStore` with `recovery_scan` (authoritative pid check, refuses false running per AC-FR1401-05); `OpenCodeServerProcess` lifecycle; `dispatch.get_default_adapter(kind=mock|real)`
  - **`/api/opencode/*` real backend** + abort/recover routes (B5)
  - **OpenCode chat page** (`/opencode`) with mock-labeled banner, send/stop/abort/recover UI (B6)
  - **Real L3 smoke** `tests/e2e/test_real_opencode_l3_e2e.py` (B7) - talks to actual `opencode serve`, skips (not passes) when no real server
  - **CLI commands** `lk project|gate|workflow|migrate` (B8)
  - **Storage model** documented (B9): web/store (JSON) for v0.11 web consumers + runtime/store (SQLite) for v0.12 workflow state + opencode persistence for OpenCode instance recovery
  - 10 integration e2e tests for FR-0101..1701 (B10)
  - 392 unit tests + 190 e2e tests passing; coverage 95% on `louke/runtime/`
  - Agent role notes added: Scout/Warden step back from M-FOUND (program-checks); Keeper = program gate only; Prism = semantic reviewer (B11)
- **Honest disclosure**:
  - 18 e2e findings in `tests/e2e/test_browser_compat_e2e.py` are pre-existing chromium/firefox missing (out of v0.12 scope per spec).
  - M-DEV + M-E2E gates waived for R-G-R order historical noise (Keeper source confirms `[green]` alone is allowed; warnings reflect iteration history).
  - L3 smoke requires a real `opencode serve`; CI / sandbox environments skip cleanly.

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
