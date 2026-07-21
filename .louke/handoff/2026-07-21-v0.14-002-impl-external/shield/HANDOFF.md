# External Shield Handoff — v0.14-002 Host-Project Integration / E2E Tests

- **recipient**: 外部 AI / 工程师，承担"Shield"角色（集成/e2e 测试编写者）
- **scope**: spec `v0.14-002-workflow-reflow-design` 的 **host-project 集成 + e2e 测试**
- **commit pin**: `c654041654a7cdd258f5abb983a8b4386f3804b1` on `releases/0.14.0`
- **issue list（本批您只管这些）**: #250..#283（**只取 integration/e2e 相关的 FR**，不是全部 34 个都做）

## 1. 您的范围

- ✅ 写 `tests/integration/v014_002_*/` 集成测试
- ✅ 写 `tests/e2e/v014_002_*/` e2e 测试
- ✅ 写 host-project fixtures（`.worktrees/test-host/` 或您自建的临时项目）
- ✅ 维护 `tests/runner-manifest.toml`（只追加新 suite，不删旧）
- ❌ 不要写 `tests/unit/v014_002/` — 那是 Devon 的活儿
- ❌ 不要写 `louke/v014/002/*` 实现代码
- ❌ 不要修改 `.louke/project/specs/v0.14-002-workflow-reflow-design/**`
- ❌ 不要 push git

## 2. 与 Devon 的协调

Devon 在**另一个 worktree**（如 `.worktrees/devon/`）做 `louke/v014/002/` 实现 + 单元测试。**您与 Devon 不共享文件改动**——您写的测试只需要在 v0.14 worktree 集成时跑通。

**重要**：Devon 提交前您**不能**立即跑全套 integration/e2e（因为依赖未实现）。两种工作模式二选一：

### 模式 A：同步等待
1. 您按 spec 写完测试（RED 状态，符合 acceptance）
2. 等待 Devon 通知某 FR 已实现（您可以读 Devon 的 REPORT.md 跟踪）
3. 跑您的 integration/e2e，确认 GREEN
4. 标 issue `status:done`

### 模式 B：mock 先行（推荐）
1. 您用 `unittest.mock` 或 pytest fixture mock 出 `louke.v014.002.*` 模块的接口
2. 测试写为"集成 / e2e 接口契约"，不依赖实现细节
3. Devon 实现后，您只需调整 fixture 让真实模块注入
4. 不阻塞 Devon 节奏

**建议模式 B**，因为 v0.14 是建设期，host-project 集成测试的 mock 边界由 interfaces.md 的 15 个 `IF-XXX` 显式定义。

## 3. 集成 + E2E 测试的 FR 范围

按 spec-002 acceptance.md 中的 test-plan 分配，**unit 优先的 FR 不需要您做 integration/e2e**。需要集成/e2e 的 FR 包括（不限于）：

| FR | 集成 / e2e 责任 | 测试位置 |
|---|---|---|
| FR-0100 | e2e: 进入 M-DESIGN 入口；revision identity 跨模块一致 | `tests/e2e/v014_002_entry/` |
| FR-0200 | integration: facts snapshot 对真实仓库（Louke 自己）盘点的产物可读 | `tests/integration/v014_002_facts/` |
| FR-0300 | integration: 写授权 + CAS 拒绝越界；e2e: 完整 diff 归属 | `tests/integration/v014_002_write_auth/`, `tests/e2e/v014_002_write_auth/` |
| FR-0400/0500/0600 | e2e: 三个设计文档的链路（test-plan → architecture → interfaces）AC 闭合 | `tests/e2e/v014_002_design_chain/` |
| FR-0700 | integration: 7 类 machine contract schema 全部 meta-valid + 1 instance 校验 | `tests/integration/v014_002_registry/` |
| FR-0800 | integration: integration contract 的可执行性（runner/setup/run） | `tests/integration/v014_002_int_contract/` |
| FR-0900 | e2e: e2e contract 的可执行性（公开入口/旅程） | `tests/e2e/v014_002_e2e_contract/` |
| FR-1000 | integration: pre-commit hook 与既有 hooks 的合并/保留 | `tests/integration/v014_002_precommit/` |
| FR-1100 | e2e: GitHub Actions workflow 真实可生成（dry-run） | `tests/e2e/v014_002_ci/` |
| FR-1200 | integration: 稳定 required check 列表 | `tests/integration/v014_002_required/` |
| FR-1300 | integration: CI 漂移检测 | `tests/integration/v014_002_drift/` |
| FR-1400 | integration: release identity 跨 Python/Node 通用 | `tests/integration/v014_002_version/` |
| FR-1500 | integration: build artifact 真实产出 + 验证 | `tests/integration/v014_002_build/` |
| FR-1600 | e2e: publish recovery 流程（dry-run + rollback） | `tests/e2e/v014_002_publish/` |
| FR-1700 | integration: canonical prompt source readback | `tests/integration/v014_002_prompts/` |
| FR-1800 | integration: prompt bundle manifest identity | `tests/integration/v014_002_bundle/` |
| FR-1900 | integration: schema 与 prompt 分离 | `tests/integration/v014_002_separation/` |
| FR-2000 | integration: deployment drift detection | `tests/integration/v014_002_deployment/` |
| FR-2050 | integration: atomic activation fail-closed | `tests/integration/v014_002_atomic/` |
| FR-2100 | integration: host-project prompt 只读 | `tests/integration/v014_002_readonly/` |
| FR-2200 | integration: archer task/result 契约 | `tests/integration/v014_002_archer/` |
| FR-2300 | integration: prism task/result 契约 | `tests/integration/v014_002_prism/` |
| FR-2400 | integration: human direct diff 路径 | `tests/integration/v014_002_human/` |
| FR-2500 | e2e: 完整 revise loop（dispatch → result → revise → dispatch） | `tests/e2e/v014_002_revise_loop/` |
| FR-2600 | integration: validator 行为（gap/stale/secret） | `tests/integration/v014_002_validator/` |
| FR-2700 | integration: baseline & no second M-LOCK | `tests/integration/v014_002_baseline/` |
| NFR-0100 | integration: 确定性 + 跨运行一致 | `tests/integration/v014_002_determinism/` |
| NFR-0200 | integration: 权限 + secret 扫描 | `tests/integration/v014_002_secret/` |
| NFR-0300 | integration: 异构 host（Node fixture） | `tests/integration/v014_002_heterogeneous/` |
| NFR-0400 | integration: 恢复 + 审计 | `tests/integration/v014_002_audit/` |
| NFR-0500 | integration: validator 反馈可读 | `tests/integration/v014_002_feedback/` |
| NFR-0600 | integration: schema migration 兼容 | `tests/integration/v014_002_migration/` |

参考 spec-001 实施里 Devon 留下的"runner manifest 修改"已知 gap（详见 spec-001 Devon report 的 follow-ups #3）：

- `tests/e2e/run_e2e.py` 与 `tests/e2e/run-project-venv` 应该读 `tests/runner-manifest.toml`
- 您**可以**修改这两个 runner，让它们读 manifest（如必要请在 commit 中说明）

## 4. 必读

### 4.1 设计文档（按顺序）
1. `releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/spec.md`
2. `releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/acceptance.md` — 关注每个 AC 末尾的"测试 layer 分配"
3. `releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/test-plan.md` — integration / e2e 段
4. `releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/interfaces.md` — 15 IF-XXX 接口
5. `releases/0.14.0/.louke/project/specs/v0.14-002-workflow-reflow-design/architecture.md` — 模块边界

### 4.2 spec-001 实施留下的测试资产
- `tests/runner-manifest.toml` — 当前内容请先读
- `tests/unit/v014/` — 207 条 spec-001 单元测试（您不动）
- `tests/integration/v014_*/` — 如果 spec-001 留下了什么，您在 `v014_002_*` 同名目录下展开

## 5. host-project fixture

集成/e2e 测试要有一个 host project 作为操作对象。**不要修改主仓库**作为 fixture。两种方式：

- **(A) 使用 Louke 自己作为 host**（dogfood）：fixture 通过临时子目录 + git worktree 隔离
- **(B) 在 `tests/integration/v014_002_*/fixtures/host-app/` 下放一个最小 Node/Python 应用**

spec-002 的 NFR-0300 要求"宿主技术栈可移植"，所以**强烈建议您至少准备一个 Node fixture**（`tests/integration/v014_002_heterogeneous/fixtures/node-host/`），证明 release-version schema 接受 Node/SemVer。

参考：`.louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/validation/release-version-node-host.valid.candidate.json` 已有 Node 端示例。

## 6. 提交格式

```
test(v014-002): cover FR-0100 interface IF-DES-01 (#250)
test(v014-002): cover FR-0800 integration contract (#256)
test(v014-002): e2e revise loop for FR-2500 (#272)
test(v014-002): heterogeneous host fixture for NFR-0300 (#277)
chore(v014-002): add v014_002 suites to runner-manifest
```

每条 commit body 引用 FR/NFR + issue 号。

## 7. 验证（commit 后必须跑）

```bash
cd /Users/openclaw/workspace/louke
git checkout c654041

# 1. 集成测试
python3 -m pytest tests/integration/v014_002 -q
# 期望：全部 PASS（target ≥ 30 条）

# 2. e2e 测试
python3 -m pytest tests/e2e/v014_002 -q
# 期望：全部 PASS（target ≥ 10 条）

# 3. AC 追溯
python3 tools/check_ac_traceability.py \
  --acceptance .louke/project/specs/v0.14-002-workflow-reflow-design/acceptance.md \
  --tests tests/unit/v014_002,tests/integration/v014_002,tests/e2e/v014_002
# 期望：34/34 covered（Devon 的单元 + 您的集成/e2e 合起来覆盖所有 AC）

# 4. 全套回归
python3 -m pytest tests/unit tests/integration tests/e2e -q
# 期望：spec-001 的 657 pass + 2 skip + 您的新测试 仍不变
```

注意：步骤 1/2 在 Devon 实施前会因 import 失败 → 标 `xfail` 或 `@pytest.mark.skip(reason="awaiting Devon impl")` 也是允许的；commit 时**先写测试再标 xfail**，不要在 RED 阶段就让测试直接 pass。

## 8. 您应交付给我

请把交付报告写到 `.louke/handoff/2026-07-21-v0.14-002-impl-external/shield/REPORT.md`（本地、不进 git）：

```markdown
# v0.14-002 Shield (Integration/E2E) Report

## Per-issue commit list
| Issue | FR/NFR | Layer | Commit(s) | Message |
|---|---|---|---|---|

## Host fixture inventory
- Python host: path + size
- Node host: path + size
- Mock boundaries: list of mocked louke.v014.002.* interfaces

## Test run evidence
- integration: pytest exit + counts
- e2e: pytest exit + counts
- AC traceability combined: tool exit + ratio
- full regression: pytest exit + counts

## Coordination with Devon
- Which FRs were blocked by Devon impl
- Which FRs you self-mocked and how
- Which FRs need Devon to re-validate (skip→pass)

## Deviations / Blockers / Follow-ups
```

## 9. 启动命令

```bash
cd /Users/openclaw/workspace/louke
git fetch origin releases/0.14.0
git checkout c654041
git worktree add .worktrees/shield c654041 -b local/shield-v014-002
cd .worktrees/shield
# 实施完成后报告路径：/Users/openclaw/workspace/louke/.louke/handoff/2026-07-21-v0.14-002-impl-external/shield/REPORT.md
```

## 10. 重要提醒

- **不要修改 `.opencode/agents/**`**（active deployment）。
- **不要 push git**。
- **不要修改 `tests/unit/v014_002/`**。
- **不要修改 `.louke/project/specs/v0.14-002-workflow-reflow-design/**`。
- **runner-manifest 只追加，不删不重写**。
- **commit 务必标 issue 引用 + FR 引用**。
- 测试失败时**不要静默 skip**；要么修测试，要么 `@pytest.mark.xfail(reason="awaiting Devon impl of FR-XXXX")` 显式标注。
