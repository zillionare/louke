# External Prism Handoff — v0.14-002 Post-Implementation Review + v0.14-003 Design Review

- **recipient**: 外部 AI / 工程师，承担"Prism"角色（独立技术评审）
- **scope (本批)**:
  - **A**: spec `v0.14-002-workflow-reflow-design` **实施后回看验证**（等 Devon + Shield 交付后做）
  - **B**: spec `v0.14-003-workflow-reflow-impl` **独立设计评审**（首次）
- **commit pin**: `c654041654a7cdd258f5abb983a8b4386f3804b1` on `releases/0.14.0`（spec-002 当前基线）
- **不要写代码**：只产出评审文件

## 0. 您不是实施者

- ❌ 不要修改 `louke/`、`tests/`、`tools/`、`design-artifacts/`、`.opencode/agents/`、`.github/workflows/`
- ❌ 不要 push git
- ✅ 只写评审文件到 `releases/0.14.0/.louke/project/specs/{spec-id}/` 下的 `*-review.md` 或 `design-review.md`
- ✅ 输出 verdict + blockers + evidence

## 1. 您的工作分两阶段

### 阶段 A — spec-002 实施后回看验证（依赖 Devon + Shield 先完成）

**触发条件**：当 Devon 在 `.louke/handoff/2026-07-21-v0.14-002-impl-external/devon/REPORT.md` 和 Shield 在 `.louke/handoff/2026-07-21-v0.14-002-impl-external/shield/REPORT.md` 都标记"完成"时，您启动阶段 A。

**任务**：
1. 读 `devon/REPORT.md` 和 `shield/REPORT.md`（两份都要看）
2. 在新 commit `devon-impl` + `shield-impl` 上跑：
   ```bash
   python3 -m pytest tests/unit tests/integration tests/e2e -q
   python3 tools/check_ac_traceability.py \
     --acceptance .louke/project/specs/v0.14-002-workflow-reflow-design/acceptance.md \
     --tests tests/unit/v014_002,tests/integration/v014_002,tests/e2e/v014_002
   ```
3. 独立 spot-check 5–10 个 FR 的 acceptance：
   - 对每个抽样的 FR：找到实现 commit → 找到单元测试 → 跑测试 → 找到 integration/e2e 测试 → 跑测试
   - 评估四向闭环：AC ↔ IF ↔ ARC ↔ contract
4. 检查 B-2 fix 是否在实施中被尊重（Runtime 签 instance 时 spec.id 是变量）
5. 写 spec-002 **post-impl 评审**到：
   ```
   .louke/project/specs/v0.14-002-workflow-reflow-design/impl-review.md
   ```
   frontmatter: `reviewer: <your-name>, stage: M-IMPL, spec_id, reviewed_at, verdict, summary`

verdict 候选：
- `PASS`：所有 34 FR/NFR 的 acceptance 都通过 4 向闭环 + 测试
- `REJECT`：至少 1 个 substantive gap
- `CONCERNS`：边界情况，不阻塞 baseline 但应记录

### 阶段 B — spec-003 独立设计评审

**触发条件**：可立即开始（不依赖任何实施完成）。

**任务**：
1. 读 spec-003 全部 8 份文档：
   - `releases/0.14.0/.louke/project/specs/v0.14-003-workflow-reflow-impl/story.md`
   - `releases/0.14.0/.louke/project/specs/v0.14-003-workflow-reflow-impl/spec.md`
   - `releases/0.14.0/.louke/project/specs/v0.14-003-workflow-reflow-impl/acceptance.md`
   - `releases/0.14.0/.louke/project/specs/v0.14-003-workflow-reflow-impl/test-plan.md`
   - `releases/0.14.0/.louke/project/specs/v0.14-003-workflow-reflow-impl/architecture.md`
   - `releases/0.14.0/.louke/project/specs/v0.14-003-workflow-reflow-impl/interfaces.md`
   - `releases/0.14.0/.louke/project/specs/v0.14-003-workflow-reflow-impl/flow.md`
   - `releases/0.14.0/.louke/project/specs/v0.14-003-workflow-reflow-impl/story-review.md`
   - `releases/0.14.0/.louke/project/specs/v0.14-003-workflow-reflow-impl/spec-review.md`
2. 不参考 design-artifacts（spec-003 还没有 candidate bundle）
3. 评估 spec-003 的 ARC-## / IF-#### / AC 三向闭环
4. **关注跨 spec 一致性**：spec-002 用 `IF-DES-01` 等语义 anchor；spec-003 用 `IF-####` 编号 anchor。**这是一个 substantive 缺陷**——architecture search 与 validation tool 的统一性会破坏。但是否阻塞由您判断。
5. 验证 AC 数量 36 = 30 FR + 6 NFR
6. 写 spec-003 **设计评审**到：
   ```
   .louke/project/specs/v0.14-003-workflow-reflow-impl/design-review.md
   ```
   frontmatter: `reviewer: <your-name>, stage: M-DESIGN, spec_id, reviewed_at, verdict, full digest chain`

verdict 同上。

## 2. 评审产物格式

每个评审文件必须含 frontmatter（**frontmatter 是程序解析的关键**）：

```markdown
---
reviewer: <your-name-or-handle>
stage: M-DESIGN | M-IMPL
spec_id: <v0.14-XXX-name>
reviewed_at: 2026-07-21
verdict: PASS | REJECT | CONCERNS
story_digest: sha256:...
spec_digest: sha256:...
acceptance_digest: sha256:...
test_plan_digest: sha256:...  # 仅 design review
architecture_digest: sha256:...
interfaces_digest: sha256:...
prior_round_digest: sha256:...  # 如果适用
---

# M-DESIGN Independent Technical Review — Round N (Prism / external)

## Verdict
**PASS / REJECT / CONCERNS**

## Evidence summary
- digest chain recomputed on disk
- spot-checks
- independent validations

## Core blockers
≤ 3 条，每条 file:line 引用 + 不依赖 v0.14 Runtime 激活的 fix 路径

## Non-blocking observations
任意

## Files changed
- <评审文件名>
```

## 3. 实质 vs 程序门禁（您必须知道）

### 实质性 (substantive) — 应作为合法 blocker
- AC ↔ IF ↔ ARC ↔ contract 四向闭环缺失、orphan 或冲突
- 文档编号格式错
- machine contract 缺必需字段、kind 错位、digest 失配
- schema meta-invalid、instance 不 validate
- 设计合同写死了 instance 应该承载的值
- candidate 与 active 边界不清
- secret / password / token / API key 明文
- FR/NFR 与 Acceptance 不一致
- B-2 fix 没有在实施中被尊重（Runtime 签 instance 时仍写死）

### 程序性 (procedural pseudo-gate) — **不要作为 blocker**
- v0.14 Runtime registry/runner/prompt deployment 未激活
- candidate 必须现在部署
- 7 类 machine contract 必须已安装到 `.louke/project/contracts/`
- 实际 CI 跑过 real-smoke / publish job
- `lk agent maestro advance` 退出 0
- `lk agent devon commit-rgr` 可用
- Host-authenticated 二次 M-LOCK
- prompt candidate 的 `digest_source` 字段、bundle digest scope 与 active deployment digest 不一致（**这是 activation-time 关注点**）

## 4. 关键复现命令（您可以跑）

### spec-002 B-2 修复确认
```bash
python3 - <<'PY'
import json, jsonschema
sa = json.load(open('.louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/registry/agent-io/archer-design-task-input-1.0.0.schema.json'))
sp = json.load(open('.louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/registry/agent-io/prism-design-review-task-input-1.0.0.schema.json'))
jsonschema.Draft202012Validator.check_schema(sa)
jsonschema.Draft202012Validator.check_schema(sp)
print('both meta-valid: PASS')

# 跨 spec 测试（spec-003）
task = json.load(open('.louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/inputs/archer-author-task-manifest.candidate.json'))
mut = json.loads(json.dumps(task))
mut['spec']['id'] = 'v0.14-003-workflow-reflow-impl'
mut['allowed_write_set'] = [p.replace('v0.14-002','v0.14-003') for p in mut['allowed_write_set']]
mut['output_contract']['artifact_manifest_path'] = mut['output_contract']['artifact_manifest_path'].replace('v0.14-002','v0.14-003')
jsonschema.Draft202012Validator(sa).validate(mut)
print('archer cross-spec: PASS')
PY
```

### spec-002 实施验证
```bash
python3 -m pytest tests/unit/v014_002 tests/integration/v014_002 tests/e2e/v014_002 -q
python3 tools/check_ac_traceability.py \
  --acceptance .louke/project/specs/v0.14-002-workflow-reflow-design/acceptance.md \
  --tests tests/unit/v014_002,tests/integration/v014_002,tests/e2e/v014_002
```

### spec-003 一致性
```bash
rg -c '^### ARC-' .louke/project/specs/v0.14-003-workflow-reflow-impl/architecture.md
rg -c '^### IF-[0-9]{4}' .louke/project/specs/v0.14-003-workflow-reflow-impl/interfaces.md
rg -c '^### AC-FR' .louke/project/specs/v0.14-003-workflow-reflow-impl/acceptance.md
# 期望：≥36 ARC、≥16 IF、30 个 FR 各自的 AC
```

## 5. 您的产出

**两份**评审文件，最终 commit 到 `releases/0.14.0`：

1. **`.louke/project/specs/v0.14-002-workflow-reflow-design/impl-review.md`**（阶段 A）
2. **`.louke/project/specs/v0.14-003-workflow-reflow-impl/design-review.md`**（阶段 B，可立即做）

每份文件以一个独立 commit 提交：

```
review(v014-002-impl): post-impl review by external prism
review(v014-003-design): independent design review by external prism
```

不要合并到一个 commit；便于后续 digest 链追溯。

## 6. 启动命令

```bash
cd /Users/openclaw/workspace/louke
git fetch origin releases/0.14.0
git checkout c654041
# 不需要 worktree；评审只写 spec 目录下的 review 文件
# 但为了不与 Devon/Shield 冲突，可以用 worktree：
git worktree add .worktrees/prism c654041 -b local/prism-review
cd .worktrees/prism
# 阶段 A 等 Devon/Shield 完成；阶段 B 可立即做
```

## 7. 不要看的文件

- `.louke/spec_archive/stale-v013/**` — 旧 v0.13 `lk agent *` 输出，已废弃
- `.louke/spec_archive/wip/**` — 早期 WIP，与 v0.14 无关
- 任何 `requirements.txt` / `pyproject.toml` 的版本变更 — 与本评审无关
- `.opencode/agents/**`（active deployment）— 不激活它

## 8. 时间预算

- 阶段 A：≤ 90 分钟（5–10 个 FR spot-check + 4 向闭环 + 报告）
- 阶段 B：≤ 60 分钟（spec-003 通读 + 三向闭环 + anchor 命名一致性 + 报告）

## 9. 关键问题列表（您在评审时应回答）

### 阶段 A（spec-002 实施后）
1. 28 FR + 6 NFR = 34 issue，是否都 `status:done`？
2. 每个 issue 是否都有 commit 引用？commit body 是否引用 FR/NFR 编号？
3. 测试是否都通过？
4. AC 追溯 34/34？
5. B-2 fix 在实施中是否被尊重？（Runtime 签 instance 时 spec.id 是变量）
6. 任何 PR 中是否含 secret 明文？
7. host-project fixtures 是否注册到 runner-manifest？
8. spec-001 实施的 657 + 2 skip 回归是否保持？

### 阶段 B（spec-003 设计）
1. spec-003 的 ARC 数量？IF 数量？AC 数量？三者闭环？
2. 跨 spec anchor 命名分歧（spec-002 用 `IF-DES-01`，spec-003 用 `IF-####`）是否构成 design baseline 冲突？
3. spec-003 flow.md 是否覆盖 M-STORY → M-SPEC → M-ACC → M-LOCK-1 → M-DESIGN → M-DEV → M-E2E → M-SECURITY → M-MILESTONE？
4. spec-003 36 个 GitHub Issue（#284–#319）是否都标了 Feature + v0.14 + FR-1800 + spec:v0.14-003？
5. spec-003 是否声明 inherited `IF-*`（来自 spec-002）？这些 inherited IF 是否真实存在于 spec-002 的 interfaces.md？
6. 任何 PR 中是否含 secret 明文？
7. R-G-R / B/R/G/(Refactor) sibling Git 模型是否清晰？

完成时告诉我：两份评审文件路径 + 一句话总评（PASS / REJECT / CONCERNS）。
