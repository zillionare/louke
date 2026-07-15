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
