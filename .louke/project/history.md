# Project History (Archived Versions)

> 由 M-MILESTONE 收尾触发，Maestro 把 `project-info.md` 的当前版本段追加到此文件。
> agent 不解析此文件（仅人类查阅）。

## v0.13.0 (2026-07-16) - web-ui-foundation

- **Story**: v0.13-001-web-ui-foundation: 在 v0.12 runtime 之上建立单页 workbench（toolbar/sidebar/tabs），Chat、Dev Docs、End User Docs、Wiki、Runs 全部可在浏览器端到端体验。
- **Version**: 0.13.0
- **Repo**: github.com/zillionare/louke
- **Project**: louke-v0.13 (#18)
- **Spec ID**: v0.13-001-web-ui-foundation
- **Release Branch**: `releases/0.13`
- **Created**: 2026-07-15
- **Tag**: `v0.13.0`
- **Baseline SHA**: `7e08f91` (Batch F head)
- **Evidence**:
  - `docs/v0.13-out-of-scope.md`
  - `tests/integration/web/test_batch_{a..f}_*.py` (66 integration tests)
  - `tests/e2e/test_v013_chromium_journey_e2e.py` (Chromium journey)
- **Rationale**: gap-analysis §4 Batch 1-6 修完后，按 standard pipeline 走 v0.13 M-SPEC → M-LOCK → M-DEV → M-E2E → M-MILESTONE。18 FRs 全部 closed, 476 tests pass, 4/4 validators PASS, tag v0.13.0 cut.
- **Pre-release bugs fixed**: discuss.py reopen-blocks-readiness (e7994b1), multi-doc gate for cmd_record_lock + lex.py (dc206f7).

## v0.13.1 (2026-07-16) - project-local install + AC@version + pre-commit gate

- **Story**: v0.13.1-002-project-local-install-experience: 补 v0.13.0 之后识别的两个紧耦合缺口——用户在 5 分钟内把 louke 装到新项目，全局 louke 用户能迁移到项目内 louke（不动全局），release 时构建产物的 louke 包版本自动与 git tag 同步。
- **Version**: 0.13.1
- **Repo**: github.com/zillionare/louke
- **Project**: louke-0.13.1 (#19)
- **Spec ID**: v0.13.1-002-project-local-install-experience
- **Release Branch**: `releases/0.13.1`
- **Created**: 2026-07-16
- **Tag**: `v0.13.1`
- **Evidence**:
  - FR-1501..FR-1512、NFR-1502..NFR-1506；acceptance 53 AC；Lex verify-acceptance 5/5 PASS；verify-issue 16/16；verify-project PASS。
  - 新增 issue #223 (NFR-1505 AC@version)、#224 (NFR-1506 pre-commit gate)。
  - 提交范围：`5bef15b..51f37c2`（含 M-ARCH 合同、AC@version 与 pre-commit 质量门实现、workbench/事件流校验与回归修复，均按 codex/用户授权收尾）。
  - DoD: project-local install + AC@version + pre-commit gate（AC trace + commit-msg + anti-pattern + diff-only + full-scan fallback）。
- **Rationale**: 在 v0.13.0 之上修复安装与发布身份同步两个紧耦合缺口，并通过 pre-commit hook 把质量门前置到提交时，缩短反馈环；不再依赖 M-DEV 末端的 Keeper gate 才能发现问题。
- **Pre-release fixes**: v0.13 web foundation gaps 闭环（3d4fcab），v0.13.1 spec gaps 闭合（fff536b），install runtime versions 校验（51f37c2）；workbench 真实事件流与 chat 接线（8baad1e, 9426c31）。
