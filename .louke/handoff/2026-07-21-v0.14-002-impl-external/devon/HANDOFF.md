# External Devon Handoff — v0.14-002 Implementation (TDD)

- **recipient**: 外部 AI / 工程师，承担"Devon"角色（Red-Green-Refactor 实施者）
- **scope**: spec `v0.14-002-workflow-reflow-design` 的 **运行时实现** + **单元测试**
- **commit pin**: `c654041654a7cdd258f5abb983a8b4386f3804b1` on `releases/0.14.0`
- **issue list（本批您只管这些，不要扩）**: #250, #251, #252, #253, #254, #255, #256, #257, #258, #259, #260, #261, #262, #263, #264, #265, #266, #267, #268, #269, #270, #271, #272, #273, #274, #275, #276, #277, #278, #279, #280, #281, #282, #283

## 1. 您的范围

- ✅ 实现 `louke/v014/002/` 下所有 runtime 模块
- ✅ 写 `tests/unit/v014_002/` 单元测试
- ✅ 维护 `tests/runner-manifest.toml`（只追加，不删）
- ❌ 不要写 `tests/integration/v014_002/` — 那是 Shield 的活儿
- ❌ 不要写 `tests/e2e/v014_002/` — 那是 Shield 的活儿
- ❌ 不要修改 `.louke/project/specs/v0.14-002-workflow-reflow-design/**` 任何文件
- ❌ 不要修改 `.opencode/agents/**`（active deployment）
- ❌ 不要 push git

## 2. 工作流（严格 R-G-R）

每个 FR/NFR 一个 commit。流程：

1. **RED** — 在 `tests/unit/v014_002/` 写至少 1 个 failing test，引用 AC 锚点 ID（`AC-FRXXXX-YY` / `AC-NFRXXXX-YY`）
2. **GREEN** — 最小实现让测试通过
3. **REFACTOR** — 整理、commit
4. **commit 格式**：
   ```
   feat(v014-002): implement FR-XXXX description (#NNN)
   fix(v014-002): FR-XXXX minimal fix (#NNN)
   test(v014-002): cover FR-XXXX AC-FRXXXX-YY (#NNN)
   ```
   每条 commit body 或 footer 引用 FR/NFR + issue 号
5. **issue 标记**：commit 落地后 `gh issue edit NNN --add-label "status:done"`

## 3. 实施顺序（按 spec 顺序）

```
#250  FR-0100  M-DESIGN 入口与 Revision 身份
#251  FR-0200  宿主项目事实盘点与自主技术选择
#252  FR-0300  设计写入授权与工件归属
#253  FR-0400  Test Plan 设计 — 设计已存在；写实现支撑
#254  FR-0500  Architecture 设计 — 设计已存在；写实现支撑
#255  FR-0600  Interfaces 设计 — 设计已存在；写实现支撑
#281  FR-0700  Machine Contract Registry（7 contract kinds）
#256  FR-0800  Integration Test Contract
#257  FR-0900  E2E Test Contract
#258  FR-1000  Pre-commit Contract
#259  FR-1100  托管 GitHub Actions CI Contract
#260  FR-1200  稳定 Required Check 与强制策略
#261  FR-1300  CI 共存、生成与漂移生命周期
#262  FR-1400  Canonical Release Identity 与版本源
#263  FR-1500  Build、Artifact 与安装后版本合同
#264  FR-1600  Publish 与恢复合同
#265  FR-1700  Agent Prompt 作为规范性工件
#282  FR-1800  Prompt Bundle Manifest 与身份
#266  FR-1900  Prompt 语义与机器 Schema 分离
#283  FR-2000  Prompt 确定性部署与 Drift 检测
#267  FR-2050  Prompt Candidate 的安全自举与原子激活
#268  FR-2100  Host Project 中的 Prompt 只读边界
#269  FR-2200  Archer 规范性语义合同
#270  FR-2300  Prism 设计评审语义合同
#271  FR-2400  Human 可选 Review 与 Direct Diff
#272  FR-2500  独立 Review Loop 与 Freshness
#273  FR-2600  设计程序校验、Gap 与 Stale 传播
#274  FR-2700  Implementation Baseline 与无第二 M-LOCK
#275  NFR-0100  确定性与可复现性
#276  NFR-0200  最小权限与 Secret 安全
#277  NFR-0300  宿主技术栈可移植性
#278  NFR-0400  可恢复性与审计
#279  NFR-0500  校验反馈可操作性
#280  NFR-0600  状态与 Schema 迁移兼容性
```

注：FR-0400/0500/0600 的 test-plan.md / architecture.md / interfaces.md 已经写好（spec stage），您的工作是**写实现 + 写测试**让 AC 通过，不是重写设计。

## 4. 必读设计文档（按顺序）

1. `releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/spec.md` — 28 FR + 6 NFR 完整需求
2. `releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/acceptance.md` — 34 AC 锚点
3. `releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/test-plan.md` — test layer 分配
4. `releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/architecture.md` — 16 ARC 模块
5. `releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/interfaces.md` — 15 IF-XXX 接口定义

候选 contract 仅作参考（不要复制到实现里）：

- `releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/registry/schemas/*.schema.json` — 7 类 machine contract schema
- `releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/registry/agent-io/{archer,prism}*.schema.json` — Agent I/O schema
- `releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/contracts/*.candidate.json` — contract instance 示例

## 5. 实现目录建议

```
louke/v014/002/
├── m_design/        # ARC-DESIGN: 入口、revision、授权、CAS
│   ├── entry.py
│   ├── revision.py
│   ├── write_auth.py
│   └── diff_ownership.py
├── facts/           # ARC-FACTS: 宿主项目事实盘点
│   ├── inventory.py
│   └── snapshot.py
├── contracts/       # ARC-REGISTRY + ARC-CONTRACTS: registry + 7 类 contract
│   ├── registry.py
│   ├── compile.py
│   ├── integration_test.py
│   ├── e2e_test.py
│   ├── pre_commit.py
│   ├── github_actions_ci.py
│   ├── release_version.py
│   ├── build_artifact.py
│   └── publish_recovery.py
├── ci/              # ARC-CI: CI 生成与 readback
├── precommit/       # ARC-PRECOMMIT: pre-commit 适配
├── version/         # ARC-VERSION: release identity
├── build/           # ARC-BUILD: build/artifact 验证
├── publish/         # ARC-PUBLISH: publish + rollback ledger
├── prompts/         # ARC-PROMPTS: prompt bundle 管理
│   ├── canonical.py
│   ├── bundle.py
│   ├── deployment.py
│   └── atomic_activation.py
├── review/          # ARC-REVIEW: 独立 review loop
│   ├── archer_contract.py
│   ├── prism_contract.py
│   ├── human_diff.py
│   └── freshness.py
├── validator/       # ARC-VALIDATE: 设计程序校验
│   ├── trace.py
│   ├── parity.py
│   ├── secret_scan.py
│   └── stale.py
├── store/           # ARC-STORE: revision/evidence 持久化
└── migration/       # ARC-MIGRATION: 旧 stage/schema 兼容

tests/unit/v014_002/
├── test_fr0100_entry_revision.py
├── test_fr0200_host_facts.py
├── test_fr0300_write_auth.py
├── test_fr0400_test_plan_design.py
├── ...
├── test_nfr0600_schema_migration.py
└── conftest.py
```

模块命名严格按 architecture.md §2.1 的 `ARC-*` 与 interfaces.md 的 `IF-XXX`。

## 6. 验证（commit 后必须跑）

```bash
cd /Users/openclaw/workspace/louke
git checkout c654041          # 或您 worktree 的 pin
# 1. 单元测试
python3 -m pytest tests/unit/v014_002 -q
# 期望：全部 PASS（target ≥ 207 条）

# 2. AC 追溯
python3 tools/check_ac_traceability.py \
  --acceptance .louke/project/specs/v0.14-002-workflow-reflow-design/acceptance.md \
  --tests tests/unit/v014_002
# 期望：34/34 covered

# 3. 全套回归（不破 spec-001）
python3 -m pytest tests/unit -q
# 期望：spec-001 的 657 pass + 2 skip 仍不变
```

## 7. B-2 修复（您不需要再做）

`design-artifacts/registry/agent-io/archer-design-task-input-1.0.0.schema.json` 和 `…/prism-design-review-task-input-1.0.0.schema.json` 已在 commit `c654041` 修复：原本硬编码在 schema 里的 `spec.id`、`design_revision.{identity,revision}`、`allowed_write_set` 路径 pattern、`output_contract.artifact_manifest_path`、Prism 的 `reviewer_binding.reviewed_candidate.design_manifest_*` 和 `reviewer_execution.deployment_path` 全部从 `const` 改为 `type + pattern`，由 Runtime 签 instance 时填具体值。

**您写实现时**：当 Runtime 给 Archer/Prism 签 task instance 时，把 spec.id / design_revision / path 字段填进去，schema 会接受。如发现 schema 还报 const 错误，先 git log 确认是基于 `c654041` 之后的工作。

## 8. 您应交付给我

请把交付报告写到 `.louke/handoff/2026-07-21-v0.14-002-impl-external/devon/REPORT.md`（本地、不进 git），包含：

```markdown
# v0.14-002 Devon Implementation Report

## Per-issue commit list
| Issue | FR/NFR | Commit(s) | Message |
|---|---|---|---|

## Test run evidence
- baseline: pytest exit
- per-issue RED: per FR/NFR
- per-issue GREEN: per FR/NFR
- final v0.14-002 unit: pytest exit + counts
- AC traceability: tool exit + ratio
- full regression: pytest exit + counts

## Verification summary
(FR/NFR → AC anchors → commit(s) table)

## Deviations / Blockers / Follow-ups
```

## 9. Reference 实施节奏（来自 spec-001）

spec-001 的 28 个 commit 的格式与粒度可作为参考：

```bash
git log 1d88e61..63d0da3 --oneline | head -30
```

主要规则：每 FR 一条 `feat(v014): ... (#NNN)`，fix/test commit 数量自由但每条都要 commit body 引用 FR/NFR。

## 10. 启动命令

```bash
cd /Users/openclaw/workspace/louke
git fetch origin releases/0.14.0
git checkout c654041
# 强烈建议 worktree 隔离
git worktree add .worktrees/devon c654041 -b local/devon-v014-002
cd .worktrees/devon
# 实施完成后报告路径：/Users/openclaw/workspace/louke/.louke/handoff/2026-07-21-v0.14-002-impl-external/devon/REPORT.md
```
