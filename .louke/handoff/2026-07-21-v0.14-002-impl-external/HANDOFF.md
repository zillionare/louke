# External Implementer Handoff — v0.14-002-workflow-reflow-design

- **commit pin**: `c654041654a7cdd258f5abb983a8b4386f3804b1` on `releases/0.14.0`
- **spec id**: `v0.14-002-workflow-reflow-design`
- **goal**: 把 spec-002 的 28 FR + 6 NFR = 34 个需求实现到 `louke/v014/002/` 与宿主项目测试目录，并通过验证
- **issue list**: #250–#283，共 34 条 GitHub Issue，全部 OPEN，全部关联 Project 20
- **handoff 给谁**: 任何外部 AI / harness / 人类工程师
- **handoff 范围**: 全部 spec-002 实施 — **`louke/v014/002/*`（runtime/registry/validator/prompts/conracts 实现） + `tests/unit/v014_002/*`（单元测试） + `tests/integration/v014_002/*`（集成测试） + `tests/e2e/v014_002/*`（e2e 测试）**

## 0. 项目现状一句话

- 本项目处于 v0.14 建设期（介于 v0.12 与 v0.14 之间）；不要把"v0.14 Runtime 已激活"作为合法门禁。
- spec-001 已实施完（`v0.14.0-001-impl` tag on `63d0da3`），作为参考骨架。
- spec-002 设计合同已成形（详 §3），B-2（schema 写死 instance 该填的字段）已修复并合入 `c654041`。

## 1. 您需要知道的实质规范（必须遵守）

1. **Story → Spec → Acceptance → Test Plan → Architecture → Interfaces → R-G-R** 工作流顺序保持。
2. **文档编号**：FR-XXXX / NFR-XXXX / AC-FRXXXX-YY / IF-XXX / ARC-XXX 不变。
3. **每个 FR/NFR 一条 GitHub Issue**（已存在 #250–#283）；实施完毕打 `status:done` label（颜色 `0E8A16`，已存在）。
4. **Devon R-G-R 提交格式**：`feat(v014-002): implement FR-XXXX description (#NNN)` 或 `fix(v014-002): ...` 或 `test(v014-002): cover FR-XXXX interface IF-XXX (#NNN)`。**每个 FR 一条 commit**（遵循 spec-001 的实施节奏，28 个 FR + 6 个 NFR = 34 个 commit 是底线；可按需要 fix/test commit 增补）。
5. **每条 commit 必须引用 FR/NFR 编号和 GitHub Issue 编号**。
6. **横向 traceability**：每个 FR 必须有：(a) 实现代码、(b) ≥1 单元测试、(c) ≥1 acceptance 锚点引用、(d) ≥1 test-plan 分配的测试 layer、(e) ≥1 interfaces 入口。
7. **candidate design contract 只作设计 baseline，不激活**。`design-artifacts/**` 内容是 spec-002 的契约，规范在 `interfaces.md` 的 15 个 `IF-####` 中。

## 2. 您不需要做的事

- 不要修改 `.louke/project/specs/v0.14-002-workflow-reflow-design/` 下任何文件（除非是 design-review 之外的实现说明）。
- 不要修改 `.opencode/agents/**`（active deployment）— 这是 activation 阶段的工作。
- 不要 push git；只在本地 commit。
- 不要创建新远程 branch / tag。
- 不要进入 spec-001 / spec-003 范围；只做 spec-002。
- 不要写 .louke/handoff 之类 handoff 文件。

## 3. 实施基线（必须先读）

### 3.1 必读文档（按顺序）
1. `releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/spec.md` — 28 FR + 6 NFR 完整需求
2. `releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/acceptance.md` — 每个 FR 对应 1 条 AC；FR-2200/2300/2500/2600 等带 3+ AC
3. `releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/test-plan.md` — 30 FR + 6 NFR + 34 AC 的 test layer 分配
4. `releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/architecture.md` — 16 ARC-WEB/...ARC-MIGRATION 模块分解
5. `releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/interfaces.md` — 15 IF-XXX 接口定义
6. （可选）`releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/story.md` — 用户叙事；不影响实现

### 3.2 参考 design bundle
- `releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/`
  - `registry/schemas/*.schema.json` — 7 类 machine contract 程序拥有 schema（release-version / build-artifact / e2e-test / integration-test / pre-commit / github-actions-ci / publish-recovery）
  - `registry/agent-io/{archer-design-task-input,archer-design-result,prism-design-review,prism-design-review-task-input}-1.0.0.schema.json` — Agent I/O schema（前两是 result；后两是 task input）
  - `contracts/*.candidate.json` — 7 类 contract instance 示例
  - `inputs/host-project-facts.snapshot.json` — 宿主项目事实示例
  - `prompts/{prompt-bundle,reviewer-binding,deployment-readback}.candidate.json` — Prompt bundle 候选
  - `runner/project-runner.candidate.json` — Project runner 候选
  - `validation/*.json` — 校验规则与负 fixture
- `releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/design-review.md`（B-2 fix 附录在末尾；原 round 5 verdict 是历史快照，不视为 blocker）

### 3.3 参考 spec-001 已实施的产物
- `louke/v014/` — spec-001 runtime 实现骨架（包含 `lk_serve/`、`m_design/`、`m_dev/`、`dispatch/`、`documents/` 等模块）
- `tests/unit/v014/` — 207 个 spec-001 单元测试
- `tests/runner-manifest.toml` — 测试 runner manifest（请**只追加**，不删除条目）
- `tools/check_ac_traceability.py` — AC 追溯验证工具

## 4. 仓库 / 工具

- **python**: `python3`（外部 Python，3.14）；不要用 `.venv/bin/python3`（pytest 没装）
- **pytest**: 已 `python3 -m pytest` 全装；如缺失 `pip install pytest`
- **jsonschema 4.25.1** 已装
- **branch**: `releases/0.14.0`（**不要创建新分支**；如有需要请用 git worktree）
- **pin commit**: `c654041`（B-2 fix 已合入）
- **头**: `c654041654a7cdd258f5abb983a8b4386f3804b1`

## 5. 实施 PR 计划（按 spec 顺序 + Issue 顺序）

| Order | Issue | One-liner                                                                              |
| ----- | ----- | -------------------------------------------------------------------------------------- |
| 1     | #250  | FR-0100 M-DESIGN entry & design revision identity                                      |
| 2     | #251  | FR-0200 Host project fact inventory snapshot                                           |
| 3     | #252  | FR-0300 Design write authorization & artifact ownership                                |
| 4     | #253  | FR-0400 Test plan design (RUN-TIME: produce `test-plan.md`) — **已经存在，不需要重写** |
| 5     | #254  | FR-0500 Architecture design — **已经存在**                                             |
| 6     | #255  | FR-0600 Interfaces design — **已经存在**                                               |
| 7     | #281  | FR-0700 Machine contract registry (7 contract kinds)                                   |
| 8     | #256  | FR-0800 Integration test contract                                                      |
| 9     | #257  | FR-0900 E2E test contract                                                              |
| 10    | #258  | FR-1000 Pre-commit contract                                                            |
| 11    | #259  | FR-1100 Hosted GitHub Actions CI contract                                              |
| 12    | #260  | FR-1200 Stable required check & enforcement                                            |
| 13    | #261  | FR-1300 CI coexistence / generation / drift                                            |
| 14    | #262  | FR-1400 Canonical release identity & version source                                    |
| 15    | #263  | FR-1500 Build, artifact & post-install version contract                                |
| 16    | #264  | FR-1600 Publish & recovery contract                                                    |
| 17    | #265  | FR-1700 Agent prompt as normative artifact                                             |
| 18    | #282  | FR-1800 Prompt bundle manifest & identity                                              |
| 19    | #266  | FR-1900 Prompt semantics vs machine schema separation                                  |
| 20    | #283  | FR-2000 Prompt deterministic deployment & drift detection                              |
| 21    | #267  | FR-2050 Prompt candidate safe bootstrap & atomic activation                            |
| 22    | #268  | FR-2100 Host project prompt read-only boundary                                         |
| 23    | #269  | FR-2200 Archer normative semantics contract                                            |
| 24    | #270  | FR-2300 Prism design review semantics contract                                         |
| 25    | #271  | FR-2400 Human optional review & direct diff                                            |
| 26    | #272  | FR-2500 Independent review loop & freshness                                            |
| 27    | #273  | FR-2600 Design program validation, gap & stale propagation                             |
| 28    | #274  | FR-2700 Implementation baseline & no second M-LOCK                                     |
| 29    | #275  | NFR-0100 Determinism & reproducibility                                                 |
| 30    | #276  | NFR-0200 Least privilege & secret safety                                               |
| 31    | #277  | NFR-0300 Host tech stack portability                                                   |
| 32    | #278  | NFR-0400 Recoverability & audit                                                        |
| 33    | #279  | NFR-0500 Validation feedback operability                                               |
| 34    | #280  | NFR-0600 State & schema migration compatibility                                        |

注：#253/#254/#255 已经写好（test-plan.md / architecture.md / interfaces.md 已存在），所以 FR-0400/0500/0600 的"实施"是：写实现 + 写测试，让 acceptance 通过。

## 6. 验证清单（您提交时的可执行校对）

完成 34 个 commit 后，跑下面四个验证并把 exit code 贴回来：

```bash
cd /Users/openclaw/workspace/louke
git checkout c654041
# 1. 单元测试
python3 -m pytest tests/unit/v014_002 -q
# 期望：全部 PASS（target 至少 207 条；上限您自己决定）

# 2. 集成测试
python3 -m pytest tests/integration/v014_002 -q
# 期望：全部 PASS；如发现 runner manifest 不识别，调用
# python3 -c "import tomllib; print(tomllib.loads(open('tests/runner-manifest.toml').read())['suites'])"

# 3. e2e 测试
python3 -m pytest tests/e2e/v014_002 -q
# 期望：全部 PASS；fixture 必须在 `design-artifacts/inputs/host-project-facts.snapshot.json` 注册

# 4. AC 追溯
python3 tools/check_ac_traceability.py \
  --acceptance .louke/project/specs/v0.14-002-workflow-reflow-design/acceptance.md \
  --tests tests/unit/v014_002,tests/integration/v014_002,tests/e2e/v014_002
# 期望：34/34 covered

# 5. 全套回归
python3 -m pytest tests/unit -q
# 期望：spec-001 已通过的 657 + 2 skipped 仍不变（不破回归）
```

## 7. 您应交付给我的内容

按 spec-001 实施报告的格式写一份 markdown 给我（committed to `releases/0.14.0`，不 push）：

```markdown
# v0.14-002 External Implementation Report

## Per-issue commit list (table)

| Issue | FR/NFR | Commit(s) | Message |
| ----- | ------ | --------- | ------- |

## Test run evidence
- Initial baseline (no v0.14-002 work): pytest exit
- Per-issue RED: pytest exit for each FR/NFR
- Per-issue GREEN: pytest exit for each FR/NFR
- Final v0.14-002 unit/integration/e2e: pytest exit + counts
- AC traceability: tool exit + coverage ratio
- Full regression: pytest exit + counts

## Verification summary
(FR/NFR → AC anchors → commit(s) table)

## Deviations (none / document them)

## Blockers (none expected — if any, file:line evidence + minimal fix path)

## Follow-up issues (recommended next batch tag)
- Tag suggestion: `v0.14.0-002-impl`

## Assumptions
- test framework: pytest
- AC ID format: AC-(FR|NFR)\d{4}-\d{2}
- module placement: new `louke/v014/002/` namespace
- issue label conventions
```

## 8. 必要边界提醒

- **不要把 `tests/runner-manifest.toml` 的现有条目删除或改写**。如要新增 v0.14-002 suites，只追加。
- **不要修改 `.opencode/agents/**`**（active deployment）。
- **不要 push git**；tag 创建前我会和您对齐。
- **不要 create new branch**；如需隔离请用 git worktree（不影响主线）。
- **不要补 secret**：`LOUKE_*_TOKEN` / `PYPI_API_TOKEN` 等已存在 placeholder，请继续 placeholder。
- **`status:done` label**：commit 落地 + 测试通过后再加；不要在 RED 阶段就标。

## 9. Reference setup（外部代理可以立刻按这个开工）

```bash
cd /Users/openclaw/workspace/louke
git fetch origin releases/0.14.0
git checkout c654041     # pin B-2 fix
git status              # 期望：clean（除 .louke/handoff/ 未跟踪）
git worktree add .worktrees/v014-002 c654041 -b local/v014-002-impl
cd .worktrees/v014-002
# 在这个 worktree 里继续开发；不需要再 checkout；commit 会进入 local/v014-002-impl
```

或者就地开发（如不开并行 issue）：

```bash
git checkout c654041
# 直接 commit 到 releases/0.14.0（仍不 push）
```

## 10. 完成后

请把交付报告 markdown 直接写到 `.louke/handoff/2026-07-21-v0.14-002-impl-external/REPORT.md`（本地、不进 git），告诉我文件位置。我会读、归档原始 commit list，然后打 `v0.14.0-002-impl` 标签。

---

## 附录 A — Issue 列表的 Quick Lookup（全部 GitHub URL）

```
#250 [FR-0100] M-DESIGN 入口与 Revision 身份 https://github.com/zillionare/louke/issues/250
#251 [FR-0200] 宿主项目事实盘点与自主技术选择 https://github.com/zillionare/louke/issues/251
#252 [FR-0300] 设计写入授权与工件归属 https://github.com/zillionare/louke/issues/252
#253 [FR-0400] Test Plan 设计 https://github.com/zillionare/louke/issues/253
#254 [FR-0500] Architecture 设计 https://github.com/zillionare/louke/issues/254
#255 [FR-0600] Interfaces 设计 https://github.com/zillionare/louke/issues/255
#256 [FR-0800] Integration Test Contract https://github.com/zillionare/louke/issues/256
#257 [FR-0900] E2E Test Contract https://github.com/zillionare/louke/issues/257
#258 [FR-1000] Pre-commit Contract https://github.com/zillionare/louke/issues/258
#259 [FR-1100] 托管 GitHub Actions CI Contract https://github.com/zillionare/louke/issues/259
#260 [FR-1200] 稳定 Required Check 与强制策略 https://github.com/zillionare/louke/issues/260
#261 [FR-1300] CI 共存、生成与漂移生命周期 https://github.com/zillionare/louke/issues/261
#262 [FR-1400] Canonical Release Identity 与版本源 https://github.com/zillionare/louke/issues/262
#263 [FR-1500] Build、Artifact 与安装后版本合同 https://github.com/zillionare/louke/issues/263
#264 [FR-1600] Publish 与恢复合同 https://github.com/zillionare/louke/issues/264
#265 [FR-1700] Agent Prompt 作为规范性工件 https://github.com/zillionare/louke/issues/265
#266 [FR-1900] Prompt 语义与机器 Schema 分离 https://github.com/zillionare/louke/issues/266
#267 [FR-2050] Prompt Candidate 的安全自举与原子激活 https://github.com/zillionare/louke/issues/267
#268 [FR-2100] Host Project 中的 Prompt 只读边界 https://github.com/zillionare/louke/issues/268
#269 [FR-2200] Archer 规范性语义合同 https://github.com/zillionare/louke/issues/269
#270 [FR-2300] Prism 设计评审语义合同 https://github.com/zillionare/louke/issues/270
#271 [FR-2400] Human 可选 Review 与 Direct Diff https://github.com/zillionare/louke/issues/271
#272 [FR-2500] 独立 Review Loop 与 Freshness https://github.com/zillionare/louke/issues/272
#273 [FR-2600] 设计程序校验、Gap 与 Stale 传播 https://github.com/zillionare/louke/issues/273
#274 [FR-2700] Implementation Baseline 与无第二 M-LOCK https://github.com/zillionare/louke/issues/274
#275 [NFR-0100] 确定性与可复现性 https://github.com/zillionare/louke/issues/275
#276 [NFR-0200] 最小权限与 Secret 安全 https://github.com/zillionare/louke/issues/276
#277 [NFR-0300] 宿主技术栈可移植性 https://github.com/zillionare/louke/issues/277
#278 [NFR-0400] 可恢复性与审计 https://github.com/zillionare/louke/issues/278
#279 [NFR-0500] 校验反馈可操作性 https://github.com/zillionare/louke/issues/279
#280 [NFR-0600] 状态与 Schema 迁移兼容性 https://github.com/zillionare/louke/issues/280
#281 [FR-0700] Machine Contract Registry https://github.com/zillionare/louke/issues/281
#282 [FR-1800] Prompt Bundle Manifest 与身份 https://github.com/zillionare/louke/issues/282
#283 [FR-2000] Prompt 确定性部署与 Drift 检测 https://github.com/zillionare/louke/issues/283
```

## 附录 B — B-2 fix 落地说明（外部代理忽略此节，仅信息）

`design-artifacts/registry/agent-io/archer-design-task-input-1.0.0.schema.json` 和 `…/prism-design-review-task-input-1.0.0.schema.json` 在 `c654041` 中已被修复：原本写死在 schema 里的 `spec.id`、`design_revision.identity/revision`、`allowed_write_set` path pattern、`output_contract.artifact_manifest_path`、Prism 的 `reviewer_binding.reviewed_candidate.design_manifest_identity/revision` 和 `reviewer_execution.deployment_path` 全部从 `const` 改为 `type + pattern`，由 Runtime 在签 instance 时填具体值。`dispatch.authority = Runtime/program`、`dispatch.role`、`artifact_kind`、`schema_version`、`binding_state`、`freshness.policy`、以及 schema identity const **保持不变**。

外部代理不需要再修改 schema；只需要按 `interfaces.md` 中的 `IF-DES-01/02/…` 接口，把 Runtime 签 instance 的代码写出来。
