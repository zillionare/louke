# v0.7-001 — pre-commit 接管 lint/format/typecheck/test + R-G-R Red 去 commit — Spec

- **Spec ID**: v0.7-001-pre-commit-quality-gates
- **创建日期**: 2026-07-05
- **状态**: 草稿（待 Aaron 拍板）
- **关联**:
  - 取代 `/tmp/louke-design/quality-gates-design.md`（中性 `quality-gates.toml` 提案）—— 整份设计稿不再采用，本 spec §0.2 说明理由
  - 受影响下游：v0.6-009 `agents/Keeper.md`（lint/test 职责描述）、`agents/Devon.md` §5.1 Red 阶段 commit、`louke/keeper.py` `run_external_tool` / `run_project_tests` / `_load_pyproject_tool` / `_load_pyproject_e2e_config`
  - 受影响下游：`louke/devon.py` `commit-rgr --phase` 三阶段 → 两阶段

## 0. 范围与边界

### 0.1 本 spec 收纳

| 主题 | FR 范围 |
|---|---|
| pre-commit 框架引入 + Scout 阶段安装 | FR-0100 |
| `.pre-commit-config.yaml` 模板体系（base + per-language） | FR-0200 |
| hook 内容定义（lint / format / typecheck / test） | FR-0300 |
| Devon R-G-R 改造：Red 不 commit + `commit-rgr` 移除 `--phase red` | FR-0400 |
| Devon 反模式：`--no-verify` 禁止 | FR-0500 |
| Keeper 瘦身：移除 lint/typecheck/test 代码路径 | FR-0600 |
| CI parity：`pre-commit run --all-files` | FR-0700 |
| 向后兼容 + pre-commit 依赖 + 文档同步 | NFR-0010 / NFR-0020 / NFR-0030 |

### 0.2 不采用 `quality-gates.toml` 提案（supersede）

`/tmp/louke-design/quality-gates-design.md` 提出：建中性 `.louke/project/quality-gates.toml` 描述 lint/typecheck/test 命令，`lk keeper gate` 读它执行。本 spec **否决**该方向，理由：

1. lint / format / typecheck 本质是**单文件、单 commit** 范围的检查，pre-commit 框架原生支持，零 token、语言生态维护，无需 louke 重新发明配置 schema + loader。
2. per-language 命令差异（ruff / eslint / golangci-lint）由 pre-commit 社区 hook repo 解决，louke 不必维护 N 套命令表。
3. 该提案存在未解问题（`paths` schema 与 `keeper.py:166` 不一致、漏迁 e2e loader、§6 风险表 `edit: deny` 事实错误），全部因改用 pre-commit 而消失。
4. `lk keeper gate` 仍需做**跨 commit 语义检查**（commit 消息格式、R-G-R 顺序、AC trace、反模式扫描），这些 pre-commit 做不了 —— Keeper 保留这部分，不消亡。

`quality-gates.toml` 不引入；keeper.py 的 `_load_quality_gates` / `run_external_tool` / `run_project_tests` 删除（FR-0600）；shield.py 的 `_load_quality_gates` / `_load_e2e_config` / `cmd_run_e2e` 保留（e2e 是 Shield 职责，不在本 spec 范围）。

> **与 v0.7-002 关系**：v0.7-002（知识蒸馏 Karpathy 化）早期版本曾含 `quality-gates.toml` 内容，现已剔除。本 spec 的否决声明是清理动作，防止未来 reviewer 看到旧设计稿误以为仍生效。

> **Sage:** §0.2 与现有代码不一致，请 Aaron 拍板 `quality-gates.toml` 的处置边界：
>
> 1. `keeper.py:139` 的 `_load_quality_gates()`、`shield.py:47` 的同函数、`Archer.md §6.4` 让 Archer 产出此文件，**v0.6 已 ship 这套机制**——§0.2 说"否决 / 不引入"事实上是砍掉已发布特性。
> 2. 建议方向：**保留文件 + loader，给 shield 的 `[test.e2e]` 段用**；删除 keeper 端对 `[lint] [typecheck] [test]` 段的读取代码路径。换言之 lint/typecheck/test 命令配置职责归 pre-commit，e2e 配置职责仍归 shield + `quality-gates.toml`。
> 3. 若 Aaron 同意方向 → §0.2 第 4 段重写，FR-0600 范围缩小为"删除 lint/typecheck/test 代码路径 + `[lint] [typecheck] [test]` 段读取"，**e2e 相关全部保留**。
> 4. 若 Aaron 仍要完全砍掉 `quality-gates.toml`（包括 shield 端）→ 需补一份 `quality-gates-e2e.toml` 或迁回 `pyproject.toml [tool.louke.test.e2e]`，本 spec 范围会扩大。
>
> 默认建议：方向 2（保留文件，仅砍 lint/typecheck/test 段读取）。OK？ ✓ resolved
>> **Aaron:** agree ✓ resolved

### 0.3 本 spec 不收纳

- pre-commit hook 本身的版本升级策略（社区 hook repo 的 `rev` 字段管理）—— 留待 v0.7+ 跟进
- 多语言项目的语言探测冲突解决（如同时有 `pyproject.toml` + `package.json`）—— v0.7-001 默认两者都装，冲突由 Archer 在 M-ARCH 编辑
- `pre-commit autoupdate` 命令的集成（定期刷新 hook repo `rev`）—— 留待 v0.7+
- 非 Python 项目的 pre-commit 安装路径差异（纯 Node/Java 项目仍需 Python 装 `pre-commit` 包，NFR-0020 接受此约束）

---

## 1. 用户故事

### US-0100 lint / format / typecheck 不花 LLM token
- US-0100: 作为 Maestro 调度者，我希望 lint / format / typecheck 检查在 `git commit` 时由 pre-commit hook 自动执行，零 LLM token、零 Keeper agent 调用，以便 Keeper 专注语义级检查、token 消耗下降
- US-0110: 作为 louke 维护者，我希望 per-language 规则由社区 hook repo 维护（ruff / eslint / golangci-lint），louke 只模板化 `.pre-commit-config.yaml`，避免在 louke 代码里维护 N 套 linter 命令表

### US-0200 R-G-R Red 去 commit 让测试可进 pre-commit
- US-0200: 作为 Devon 工作流执行者，我希望 Red 阶段只在工作区写测试 + 跑测试观察失败、不创建 commit，以便 Green / Refactor commit 触发 pre-commit 时所有测试**应当**通过（pre-commit 可放心包含测试 hook）
- US-0210: 作为 Keeper 维护者，Red 不 commit 意味着 git 历史里只有 `feat: green` 和 `refactor` 两类 commit，R-G-R 顺序检查简化为"refactor 不得先于 green（同 issue 内）"

### US-0300 `--no-verify` 显式反模式
- US-0300: 作为 Maestro 协调者，我希望 Devon prompt 显式禁止 `git commit --no-verify`，违反即反模式；CI 跑 `pre-commit run --all-files` 复查，以便 `--no-verify` 绕过在 CI 阶段被捕获

### US-0400 Keeper 瘦身
- US-0400: 作为 louke 维护者，我希望 `lk keeper gate` 不再跑 lint / typecheck / test，这些归 pre-commit；Keeper 保留：commit 消息格式（R-G-R 前缀）+ R-G-R 顺序 + AC trace + 反模式扫描
- US-0410: 作为 Keeper 用户，我希望 `lk keeper gate --tests` flag 移除（测试在 pre-commit + CI），避免 Keeper 重复跑测试

### US-0500 安装时机
- US-0500: 作为新项目发起者，我希望 `lk scout foundation` 在创建 repo / branch 后、`commit-foundation` 前自动探测语言、生成 `.pre-commit-config.yaml`、跑 `pre-commit install`，以便 foundation commit 本身就经过 pre-commit 校验
- US-0510: 作为存量项目采用者，我希望 `lk init --adopt` 对已有 repo 也能补装 pre-commit hook

---

## 2. 关键场景

### scenario-0100 新项目 Scout 阶段装 pre-commit
```
1. Scout Step 1 收集项目信息: 用户选 Python 项目 (intended stack)
2. Scout Step 2-4: 创建 repo / Project / releases 分支
3. Scout Step 5 (新增): 探测 manifest → 无 (greenfield) → 用用户声明的 stack
   - 从 louke/templates/pre-commit/ 合并 base.yaml + python.yaml → 写 .pre-commit-config.yaml
   - 跑 `pre-commit install` → .git/hooks/pre-commit 创建
4. Scout Step 6-8: 写 status / story / commit-foundation
   - commit-foundation 触发 pre-commit: check-yaml / check-toml / trailing-whitespace 通过
5. Devon M-DEV 接手: Red 写测试 (不 commit) → Green commit (pre-commit 跑 ruff + mypy + pytest) → Refactor commit
```

### scenario-0200 Devon R-G-R 不再 commit Red
```
1. Devon 接收 issue #42 (FR-0001)
2. Phase 1 (Red):
   - 写 tests/test_foo.py
   - 跑 pytest → 失败 (期望)
   - **不 commit**, 不调 commit-rgr --phase red
   - 报告 Maestro: "Red 就绪, 测试失败信息指向 FR-0001"
3. Phase 2 (Green):
   - 写 src/foo.py
   - 跑 pytest → 全部通过
   - 调 `lk devon commit-rgr --issue 42 --phase green --message "..."`
   - 工具生成 commit message: "feat: green: ... Closes #42"
   - git commit 触发 pre-commit:
     ✓ ruff check (lint)
     ✓ ruff format --check (format)
     ✓ mypy (typecheck)
     ✓ pytest (test)  ← 安全: Green 阶段测试必过
   - commit 成功, push
4. Phase 3 (Refactor):
   - 重构 src/foo.py
   - 跑 pytest → 仍通过
   - 调 `lk devon commit-rgr --issue 42 --phase refactor --message "..."`
   - commit message: "refactor: ..."
   - pre-commit 再跑一次 (同上)
   - commit 成功, push
```

### scenario-0300 Devon 试图 --no-verify 被反模式挡
```
1. Devon Green 阶段, pytest 在 pre-commit 里失败 (某个边界 case)
2. Devon 试图 `git commit --no-verify` 绕过
3. Devon.md §8 反模式已列 `--no-verify` → Devon 不执行
4. Devon 修复测试 / 实现后重跑 pytest → 通过 → 正常 commit
5. (若 Devon 仍执行 --no-verify) Maestro 在 git log 中看不到 pre-commit 标记, 视为反模式触发, 退回 Devon
```

### scenario-0400 CI 复查 --no-verify 绕过
```
1. Devon (假设) 用 --no-verify 提交了 Green commit
2. 本地 pre-commit 没跑, lint 失败未暴露
3. push → CI 触发
4. CI workflow 加一步 `pre-commit run --all-files`
5. CI 失败 (ruff 报错) → Maestro 收到 CI 红灯 → 退回 Devon 修复
```

### scenario-0500 存量项目补装 pre-commit
```
1. 用户已有 Python repo, 无 .pre-commit-config.yaml
2. 跑 `lk init --adopt` (或 `lk scout install-precommit --force`)
3. louke 探测 pyproject.toml → 识别 Python
4. 生成 .pre-commit-config.yaml (base + python)
5. 跑 `pre-commit install`
6. 后续 commit 走 pre-commit
7. (可选) `pre-commit run --all-files` 一次性扫全仓, 看历史代码是否有 lint 问题
```

---

## 3. 功能需求

<a id="fr-0100"></a>

### FR-0100 pre-commit 框架引入 + Scout 阶段安装

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

`pre-commit` 作为 louke 的**运行时依赖**加入 `pyproject.toml` 的 `dependencies`。用户 `pip install louke` 后即有 `pre-commit` 命令可用。

**安装时机**：`lk scout foundation` 在 Step 4b（权限冒烟）之后、Step 6（写状态文件）之前**新增 Step 5: 安装 pre-commit hook**。Step 5 流程：

1. **探测项目语言**（全部匹配项，非短路 —— 多语言项目同时装多个模板，见 §0.3）：
   - `pyproject.toml` / `setup.py` / `pytest.ini` → Python
   - `package.json` → Node / TypeScript（`typescript` 字段在 devDependencies 则含 typecheck）
   - `go.mod` → Go
   - `Cargo.toml` → Rust
   - `pom.xml` / `build.gradle` → Java
   - 上述都没有 → 仅装 base（FR-0200）
2. **生成 `.pre-commit-config.yaml`**：从 `louke/templates/pre-commit/base.yaml` + 探测到的 `{language}.yaml` 合并写入项目根目录。若已存在 `.pre-commit-config.yaml`，跳过生成（除非 `--force`）。
3. **跑 `pre-commit install`**：幂等，重复执行只更新 `.git/hooks/pre-commit`。
4. **记录到 `project.toml`**（fix-002 后）：`[meta].pre_commit = "installed ({language} + base)"`，下游 agent 可读。

**`lk init --adopt`** 走同样流程（已有 repo 补装 hook）。

**新增 CLI 子命令** `lk scout install-precommit [--force]`：单独触发 Step 5，供存量项目补装或重装。

---

<a id="fr-0200"></a>

### FR-0200 `.pre-commit-config.yaml` 模板体系

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

louke 自带模板目录 `louke/templates/pre-commit/`：

| 文件 | 内容 | 适用 |
|---|---|---|
| `base.yaml` | trailing-whitespace / end-of-file-fixer / check-yaml / check-toml / check-merge-conflict / large-files | 所有项目 |
| `python.yaml` | `astral-sh/ruff-pre-commit`（check + format）/ `pre-commit/mirrors-mypy` | Python |
| `node.yaml` | `pre-commit/mirrors-eslint` / `pre-commit/mirrors-prettier` / 本地 `tsc --noEmit` | Node / TypeScript |
| `go.yaml` | `dominikh/pre-commit-golang`（golangci-lint + gofmt）+ 显式 `go-test` hook（`pre-commit.com/go-test`）跑 `go test ./...` | Go |
| `rust.yaml` | 本地 `cargo fmt --check` / `cargo clippy` / `cargo test` | Rust |
| `java.yaml` | `pre-commit/mirrors-spotless` 或 checkstyle | Java |

**合并规则**：
- `base.yaml` 始终包含
- 探测到多语言 → 多个 `{language}.yaml` 的 `repos:` 列表拼接
- 每个模板的 `rev` 字段在 louke 发版时由 `lk upgrade --precommit`（v0.7+ 提供）刷新；v0.7-001 锁定具体 tag（2026-07-05 时已知稳定）：
  - ruff: `v0.6.x`（`astral-sh/ruff-pre-commit`）
  - mypy: `v1.10.x`（`pre-commit/mirrors-mypy`）
  - eslint: `v9.x`（`pre-commit/mirrors-eslint`）
  - prettier: `v3.3.x`（`pre-commit/mirrors-prettier`）
  - golangci-lint: `v1.59.x`（`dominikh/pre-commit-golang`）
  - base hooks（trailing-whitespace 等）: `pre-commit/pre-commit-hooks v4.6.x`

**Archer 编辑权**：M-ARCH 阶段 Archer 可编辑 `.pre-commit-config.yaml`（如换 linter、加 project-local 规则）。Archer 的 `edit: allow` 配合 prompt 路径白名单已覆盖此文件（属于 architecture 决策范畴）。

---

<a id="fr-0300"></a>

### FR-0300 pre-commit hook 内容（lint / format / typecheck / test）

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

每次 `git commit` 触发 pre-commit，依次跑：

| 阶段 | 检查项 | 失败行为 |
|---|---|---|
| lint | ruff check / eslint / golangci-lint / clippy | 阻止 commit |
| format | ruff format --check / prettier --check / gofmt | 阻止 commit（部分 hook 支持 `--apply` 自动修复后重跑） |
| typecheck | mypy / tsc --noEmit / cargo check | 阻止 commit |
| test | pytest / npm test / go test ./... | 阻止 commit |

**test hook 能进 pre-commit 的关键前提**：FR-0400 Red 阶段不 commit。Green / Refactor 是项目历史中**仅有的**包含测试相关改动的 commit 类型，且两者都要求测试全过。因此 pre-commit 的 test hook 在每次 commit 时都**应当**通过 —— 不会出现 Red commit 被测试 hook 拦死的情况。

**hook 作用域**：pre-commit 默认只跑 staged 文件相关的检查（快）。全仓扫描由 CI `pre-commit run --all-files` 负责（FR-0700）。

**性能预算**（per hook，staged 文件）：
- lint ≤ 5s（ruff / eslint / golangci-lint / clippy）
- format ≤ 3s（ruff format --check / prettier --check / gofmt）
- typecheck ≤ 10s（mypy / tsc --noEmit / cargo check）
- test ≤ 30s（pytest quick 模式 / npm test / go test）

全套 hook 在中等项目（< 1000 staged 文件）应在 60 秒内完成。**超时判定**：若 test hook 单独 > 60s，Archer 可在 `.pre-commit-config.yaml` 里把 test hook 拆到 CI-only（pre-commit 跑 lint/format/typecheck，CI 跑 test）—— 这是 project-level 决策，不属本 spec 强制。

> **Sage:** "30 秒内"是软目标还是硬指标，请 Aaron 拍板：
>
> - **软目标**（推荐）：超出不报错，Archer 可优化；CI 中 CI-only test hook 拆分作为兜底手段。
> - **硬指标**：pre-commit 启动超时 → commit 失败——会阻塞 agent 工作流，不建议。
>
> 默认建议：软目标。OK？ ✓ resolved
>> **Aaron:** agree ✓ resolved

---

<a id="fr-0400"></a>

### FR-0400 Devon R-G-R 改造：Red 不 commit + commit-rgr 移除 `--phase red`

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

#### FR-0400.1 Red 阶段不 commit

`agents/Devon.md` §5.1 Phase 1 (Red) 重写为：

1. 确认在 `releases/{version}` 分支
2. 阅读 issue 关联的 FR/NFR + acceptance
3. 识别测试框架
4. 编写单元测试代码
5. 跑测试确认失败（Red）
6. **不 commit，不调 `commit-rgr --phase red`**
7. 报告 Maestro："Red 就绪，测试失败信息指向 {FR-ID}，待 Green"

退出条件改为：
- [ ] 测试文件已在工作区
- [ ] 测试套件报告 Red
- [ ] 失败信息指向待实现功能
- （移除 "测试文件已提交" 项）

#### FR-0400.2 `commit-rgr` 移除 `--phase red`

`louke/devon.py` `commit-rgr` 子命令：

- `--phase` 选项枚举值从 `{red, green, refactor}` 改为 `{green, refactor}`
- 调用 `--phase red` 直接报错：`error: --phase red 已废弃 (v0.7-001): Red 阶段不 commit，详见 agents/Devon.md §5.1`
- `RGR_PREFIX` 是嵌套 dict（key 为 `(label, phase)` tuple，`devon.py:16`），删除两个 tuple 键：`('feature', 'red')` 和 `('fix', 'red')`；保留 `('feature','green')` `('fix','green')` `('feature','refactor')` `('fix','refactor')`
- Green 仍自动追加 `Closes #{issue}`，Refactor 不追加

> [!NOTE]
> 现状提示：当前 `louke/devon.py:16-23` 的 `RGR_PREFIX` 仍含 `('feature', 'red')` 和 `('fix', 'red')` 键；`louke/agents/Devon.md` §5.1 仍含 `--phase red` 调用和 `test: red` 退出条件。本 FR 落地时同步修改，详见 §6 关联文件表。

#### FR-0400.3 R-G-R 顺序检查简化

`lk keeper gate` 的 R-G-R 顺序检查（FR-0600 保留）改为：
- 同 issue 内 commit 序列只允许 `[green]` 或 `[green, refactor...]` 或 `[refactor...]`（跨 issue 时不强制）
- **禁止** `refactor` 先于 `green`（同 issue 内）
- **不再检查** `test: red` 是否存在（Red 不 commit，git 历史无此 commit）
- `test: red` 前缀若出现在历史 commit（v0.7 前存量），视为 legacy，不报错

> **Sage:** FR-0400.3 写得很简略，但有两个边界场景请 Aaron 明确，确认后落到 acceptance.md AC-7：
>
> 1. **fix cycle**：`commit-rgr` 支持 `--label fix` 产出 `fix: green` 前缀（`devon.py:21`），fix cycle 内"refactor 不得先于 green"的语义跟 feature cycle 一致。请确认 `lk keeper gate` 把 `fix: green` / `feat: green` 都视为"green 前缀"同等检查。
> 2. **跨 issue 时不强制**：spec 文字"跨 issue 时不强制"——具体是 (a) 不同 issue 的 commit 序列不参与顺序校验、(b) 同 issue 内仍校验，(c) git log 输出按 issue 分组后再校验？建议 (a)——按 issue 分组过于精细，对 agent 增加不必要负担。
>
> 默认建议：fix cycle 等同 feature cycle + 跨 issue 不参与校验（即实现最简）。OK？ ✓ resolved
>> **Aaron:** agree ✓ resolved

---

<a id="fr-0500"></a>

### FR-0500 Devon 反模式：`--no-verify` 禁止

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

`agents/Devon.md` §8 反模式追加一条：

```
❌ 使用 `git commit --no-verify` 绕过 pre-commit hook
   pre-commit 失败 → 修复根因（lint/格式/类型/测试）后重新 commit；不允许 --no-verify 跳过
   若修复超出 Devon 能力 → 报告 Maestro, 由 Archer 介入或人工修复
```

**配套约束**：
- Devon prompt §6.2 Push 规则追加一句："commit 前若 pre-commit hook 失败，必须修复后重新 commit，**禁止** `--no-verify`"
- 假设 Devon 仍执行 `--no-verify` 提交 → push → CI 跑 `pre-commit run --all-files` 失败 → CI 红灯 → Maestro 收到信号退回 Devon 修复

> **Sage:** 原 spec 写"Maestro 在 git log 检查若发现 commit 缺 pre-commit 标记视为反模式触发"，这一句在技术上不成立：`git commit --no-verify` 与正常 `git commit` 产出的 tree / commit object 一致，`git log` 区分不出。建议**整段删除该句**，`--no-verify` 兜底机制只剩：
>
> 1. Devon prompt §8 反模式列表（约束 agent 行为）
> 2. Devon prompt §6.2 `--no-verify` 禁令（commit 前最后一道提示）
> 3. CI `pre-commit run --all-files`（FR-0700，全量复查，捕获漏网）
>
> 这三层已足够。OK？ ✓ resolved
>> **Aaron:** agree ✓ resolved

---

<a id="fr-0600"></a>

### FR-0600 Keeper 瘦身：移除 lint / typecheck / test 代码路径

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

#### FR-0600.1 `louke/keeper.py` 删除的代码路径

| 函数 | 当前行号 | 删除理由 |
|---|---|---|
| `_load_quality_gates()` | keeper.py:139 | 不再从 `pyproject.toml [tool.louke.*]` 或 `quality-gates.toml` 读 lint/typecheck/test 命令（e2e 段读取由 shield 接管，见 FR-0600 关联说明） |
| `run_external_tool()` | keeper.py:178 | lint / typecheck 归 pre-commit |
| `run_project_tests()` | keeper.py:193 | test 归 pre-commit |
| `cmd_gate` 中 lint/typecheck/test 分支 | keeper.py:250-266 | 对应 `--lint` / `--typecheck` / `--tests` flag 一并移除（NFR-0010） |

> **Sage:** FR-0600.1 现状（v0.6 实测）有两处与原 spec 描述不符，请 Aaron 确认修订方向：
>
> 1. **函数名错**：spec 原写 `_load_pyproject_tool()` / `_load_pyproject_e2e_config()` / `cmd_run_e2e`，但 keeper.py 中实际是 `_load_quality_gates()` / `run_external_tool()` / `run_project_tests()`；`cmd_run_e2e` 在 shield.py:108，keeper.py 里**没有** e2e 相关函数（keeper 跑 e2e 是历史叙述）。
> 2. **e2e 处置**：建议 keeper.py 只删 lint/typecheck/test 代码路径，**`shield.py` 的 `_load_quality_gates()` + `_load_e2e_config()` + `cmd_run_e2e` 全部保留**（e2e 是 Shield 职责，不在本 spec 范围内）。需要 Aaron 显式同意"keeper 端瘦到只剩 R-G-R 顺序 / commit 消息格式 / AC trace / 反模式扫描，e2e 不动"。
> 3. **CLI flag 同步删**：keeper.py 当前 `--lint` / `--typecheck` / `--tests` 三个 flag — `--tests` spec 写了要删，`--lint` `--typecheck` 没明说。建议**三个一并删**（FR-0300 把测试归 pre-commit，lint/typecheck 也归 pre-commit，keeper 不重复跑）。
>
> 默认建议：上面表格的内容 + Q1 方向 2 一起锁定。OK？ ✓ resolved
>> **Aaron:** agree ✓ resolved

#### FR-0600.2 `lk keeper gate` 保留的检查项

| 检查项 | 数据源 | 为什么 pre-commit 做不了 |
|---|---|---|
| commit 消息格式（`feat: green` / `fix: green` / `refactor` 前缀） | `git log` | pre-commit 只看当前 commit 的 staged 文件，不看 commit 消息内容（虽然也有 `commit-msg` hook 但那是另一套） |
| R-G-R 顺序（refactor 不得先于 green、同 issue 内；`fix: green` 与 `feat: green` 等价检查） | `git log` 跨 commit | pre-commit 单 commit 作用域 |
| AC trace（docstring `AC-FRXXXX-YY` 锚点存在性） | 跨文件 AST 扫描 | pre-commit 不做语义分析 |
| 反模式扫描（`assert True` / `try: pass` / `# noqa` 滥用） | AST 扫描 | louke 特定规则，社区 hook 无 |

#### FR-0600.3 `lk keeper gate` CLI flag 移除（`--tests` / `--lint` / `--typecheck`）

`--tests` / `--no-tests` / `--lint` / `--typecheck` 选项全部删除。lint/typecheck/test 归 pre-commit（本地）+ CI（远程），Keeper 不重复跑。`_load_quality_gates` 的 `pyproject.toml [tool.louke.*]` fallback 路径一并删除。

Keeper.md description 字段更新：

```yaml
# 旧
description: 质量门禁 — 调度 lk keeper CLI 验证 R-G-R / 测试 / lint / commit 格式
# 新
description: 质量门禁 — 验证 R-G-R 顺序 / commit 消息格式 / AC trace / 反模式扫描
```

---

<a id="fr-0700"></a>

### FR-0700 CI parity：`pre-commit run --all-files`

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

louke 自身的 CI（`.github/workflows/*.yml`）新增一步：

```yaml
- name: Run pre-commit on all files
  run: pre-commit run --all-files
```

**目的**：捕获 `--no-verify` 绕过。本地 pre-commit 只跑 staged 文件；CI 跑全仓，任何漏网的 lint/格式/类型/测试失败都会暴露。

**用户项目 CI**：`lk scout foundation` 不直接改用户的 `.github/workflows/`（那是 Archer 的 architecture 决策范畴）。但 louke 提供独立 CI snippet 文件供 Archer 引用：
- `louke/templates/pre-commit/ci-snippet.yml` — 可直接 `cat` 复制到用户项目 `.github/workflows/`
- `louke/templates/pre-commit/README.md` — 使用说明 + 指向 ci-snippet.yml 的链接

> **Sage:** FR-0700 未明确 louke 自身是否 dogfood 这套模板，请 Aaron 拍板：
>
> 1. **dogfood**（推荐）：louke 仓库根目录写一份 `.pre-commit-config.yaml`（用 louke 模板的 base + python 组合），`pyproject.toml` 的 `dependencies` 同样依赖 `pre-commit`，CI `.github/workflows/ci.yml` 跑 `pre-commit run --all-files` 把模板自身当 lint 网——模板有问题第一时间在 louke 仓库暴露。
> 2. **不 dogfood**：只在 `louke/templates/pre-commit/` 产模板，自己 CI 用 ruff/mypy/pytest 原生命令。模板与 louke 自身 lint 规则可能漂移。
>
> 默认建议：dogfood。OK？ ✓ resolved
>> **Aaron:** dogfood ✓ resolved

**louke 自身 dogfood**（Aaron 已确认）：louke 仓库根目录写一份 `.pre-commit-config.yaml`（用 louke 模板的 base + python 组合），CI `.github/workflows/ci.yml` 跑 `pre-commit run --all-files`。模板有问题第一时间在 louke 仓库暴露，避免模板与 louke 自身 lint 规则漂移。

---

## 4. 非功能需求

<a id="nfr-0010"></a>

### NFR-0010 向后兼容

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

⚠️ **Breaking changes 显式声明**：

1. **Devon `commit-rgr --phase red` 移除**：脚本 / prompt 仍传 `--phase red` 会报错。存量 Devon.md / 外部脚本需更新。
2. **`lk keeper gate --tests` / `--lint` / `--typecheck` 移除**：`--tests` 写了要删；`--lint` `--typecheck` 同样需删（FR-0300 把 lint/typecheck 归 pre-commit，keeper 不重复跑）。CI 脚本若调用 → 改为 `pre-commit run --all-files`。
3. **`pyproject.toml [tool.louke.*]` 不再读取**：v0.6 的 `_load_quality_gates()` 对 `[tool.louke.lint]` 等段有 fallback 读取；本 spec 后该 fallback 是否一并删（FR-0600 提示需要）——若保留则与"lint/typecheck 归 pre-commit"语义冲突，建议删。
4. **git 历史中的 `test: red` commit**：v0.7 前的存量 commit 不受影响（不重写历史）。Keeper 的 R-G-R 顺序检查对 legacy `test: red` commit 静默接受。
5. **模板同步**：`louke/templates/task-log.md` 和 `louke/templates/bug-fix.md` 中的 `Commit: test: red – {编号} {描述}` 模板需同步改为 `feat: green` / `fix: green` / `refactor` 前缀（FR-0400 后这些模板会让 agent 误产 `test: red` commit）。
6. **`.opencode/agents/` 部署产物**：`.opencode/agents/devon.md` 是 `lk board opencode` 的部署产物（非源文件）。FR-0400/FR-0500 改动只需改 `louke/agents/Devon.md`（单一来源），功能完成后跑 `lk board opencode` 刷新部署。

> **Sage:** 请 Aaron 把以下 4 个边界纳入 v0.7-001 改动清单（否则 spec 落地后这些会被遗忘）：
>
> 1. **CLI flag**：`lk keeper gate --lint` / `--typecheck` / `--tests` 全删，NFR-0010 已加。
> 2. **pyproject fallback**：`_load_quality_gates()` 的 `pyproject.toml [tool.louke.*]` fallback 路径是否一并删？默认建议：删（FR-0600 配套）。
> 3. **templates 同步**：`louke/templates/task-log.md:12` `louke/templates/bug-fix.md:26` 都是 `Commit: test: red – {编号} {描述}` 模板，FR-0400 后这些模板会让 agent 误产 `test: red` commit。建议同时改：
>    - `task-log.md:12` → 改为 `Commit: feat: green – ... 或 refactor: ...`
>    - `bug-fix.md:26` → `Commit: fix: green – BUG-{编号} {描述}` / `refactor: ...`
> 4. **Dual prompt file**: `.opencode/agents/devon.md:76` 跟 `louke/agents/Devon.md:90` 是两份独立 Dev prompt 源，FR-0400/FR-0500 改动只列了 `agents/Devon.md`。请确认 **两份都要改**，或 `.opencode/` 目录是 shadow / 旧版（如是 shadow 则 `agents/Devon.md` 单一来源）。 ✓ resolved
>> **Aaron:** 本项目下的.opencode/agents 视为部署，功能完成后，要执行 lk upgrade/board ✓ resolved
> **Sage:** 默认建议：以上 4 项全部纳入。OK？ ✓ resolved
>> **Aaron:** agree ✓ resolved

**升级路径**：
- `lk upgrade` 升级到 v0.7+ 后，跑 `lk scout install-precommit --force` 补装 pre-commit hook
- 现有 `pyproject.toml [tool.louke.lint]` 配置：louke 不再读取，用户可手动迁移到 `.pre-commit-config.yaml`（louke 不提供自动迁移工具，因为字段差异大）

**最小迁移指南**（详见 `louke/templates/pre-commit/README.md`）：
1. 识别旧 `[tool.louke.lint]` 的 `command` + `args`
2. 查社区 hook repo 对应（ruff → `astral-sh/ruff-pre-commit`，eslint → `pre-commit/mirrors-eslint`）
3. 写入 `.pre-commit-config.yaml` 的 `repos:` 列表
4. 跑 `pre-commit run --all-files` 验证
- Archer 在 M-ARCH 阶段把 lint 决策从 spec 产物迁移到 `.pre-commit-config.yaml`

<a id="nfr-0020"></a>

### NFR-0020 pre-commit 框架依赖

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- `pre-commit` 加入 `pyproject.toml` 的 `dependencies`（非 dev-dependencies，因为 louke 运行时需要它安装 hook）
- 版本约束：`pre-commit >= 3.0, < 5.0`（允许 3.x / 4.x，留主版本缓冲；hook repo 在主版本切换时可能破坏向后兼容）
- 非 Python 项目（纯 Node / Java / Rust）仍需 Python 环境装 `pre-commit` —— 接受此约束，因 louke 本身依赖 Python，用户装 louke 时已有 Python

> **Sage:** 请 Aaron 决定 `pre-commit` 依赖上限。`pre-commit 4.x` 已发布，hook repo 在主版本切换时可能破坏向后兼容。建议钉 `pre-commit >= 3.0, < 5.0`（允许 3.x / 4.x，留缓冲）。OK？ ✓ resolved
>> **Aaron:** agree ✓ resolved

<a id="nfr-0030"></a>

### NFR-0030 文档同步

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **README.md / README.zh.md**：在"工作流"章节加"pre-commit 质量门禁"小节，说明 lint/format/typecheck/test 在 commit 时自动跑、零 token、`--no-verify` 是反模式
- **`agents/Devon.md`**：§5.1 Red 不 commit、§6.2 加 `--no-verify` 禁令、§8 加反模式条目
- **`agents/Keeper.md`**：description 改、§3 任务描述移除"调度 lint/test"、§2.1 tools 移除 lint/test 相关 CLI 调用
- **`agents/Scout.md`**：新增 Step 5 安装 pre-commit hook 的流程描述
- **`agents/Archer.md`**：§6 加"`.pre-commit-config.yaml` 是 Archer 可编辑的架构产物之一"

---

## 5. 澄清记录

| Q | 议题 | 决定 |
|---|---|---|
| Q1 | lint / format / typecheck 放 Keeper agent 还是 pre-commit | pre-commit —— 零 token、单文件级、语言生态原生 |
| Q2 | test 能否进 pre-commit | 能 —— 前提是 Red 阶段不 commit（FR-0400），Green/Refactor commit 时测试必过 |
| Q3 | Red 不 commit 是否影响 R-G-R 工作流 | 不影响 —— Red 仍是工作区写测试 + 跑测试观察失败；只是不进 git 历史。Green/Refactor commit 仍是 R-G-R 的 Green/Refactor |
| Q4 | `quality-gates.toml` 提案是否采纳 | 否决（§0.2）—— per-language 命令问题 pre-commit 生态已解决 |
| Q5 | `--no-verify` 如何防范 | Devon prompt 反模式 + CI `pre-commit run --all-files` 复查 |
| Q6 | 存量项目如何升级 | `lk scout install-precommit --force` 补装；存量 `[tool.louke.lint]` 配置不自动迁移 |
| Q7 | 多语言项目如何处理 | 探测到多语言 → 多个 `{language}.yaml` 拼接；冲突由 Archer 编辑 |
| Q8 | pre-commit hook 的 `rev` 如何升级 | v0.7-001 固定稳定 rev；v0.7+ 提供 `lk upgrade --precommit` 刷新 |
| Q9 | e2e 测试归谁 | Shield agent + CI —— Keeper 不调度 e2e（`cmd_run_e2e` 在 `louke/shield.py:108`，不在 keeper.py；本 spec 不改 shield 的 e2e 调度） |

---

## 6. 关联文件

| 文件 | 改动 |
|---|---|
| `pyproject.toml` | 加 `pre-commit >= 3.0` 到 `dependencies`；移除 `[tool.louke.lint]` / `[tool.louke.test]` 相关配置（若存在） |
| `louke/templates/pre-commit/base.yaml` | **新建**：通用 hook（whitespace / yaml / toml / large-files） |
| `louke/templates/pre-commit/python.yaml` | **新建**：ruff check + ruff format + mypy |
| `louke/templates/pre-commit/node.yaml` | **新建**：eslint + prettier + tsc |
| `louke/templates/pre-commit/go.yaml` | **新建**：golangci-lint + gofmt + go-test |
| `louke/templates/pre-commit/rust.yaml` | **新建**：cargo fmt + clippy + test |
| `louke/templates/pre-commit/java.yaml` | **新建**：spotless / checkstyle |
| `louke/templates/pre-commit/README.md` | **新建**：自定义指南 + 指向 ci-snippet.yml 的链接 |
| `louke/templates/pre-commit/ci-snippet.yml` | **新建**：CI 配置片段（YAML），供 Archer 引用到用户项目 |
| `louke/scout.py` | 加 `cmd_install_precommit` 实现 + Step 5 流程 |
| `louke/devon.py` | `commit-rgr` `--phase` 枚举移除 `red`；`RGR_PREFIX` 移除 `('feature','red')` / `('fix','red')` 两个 tuple 键 |
| `louke/keeper.py` | 删 `_load_quality_gates` / `run_external_tool` / `run_project_tests`；`cmd_gate` 移除 lint/typecheck/test 调用；`--tests` / `--lint` / `--typecheck` flag 移除 |
| `louke/shield.py` | 保留 `_load_quality_gates` / `_load_e2e_config` / `cmd_run_e2e`（e2e 是 Shield 职责，不在本 spec 范围） |
| `louke/agents/Devon.md` | §5.1 Red 不 commit；§6.2 加 `--no-verify` 禁令；§8 加反模式 |
| `louke/agents/Keeper.md` | description 改；§3 移除 lint/test；§2.1 tools 移除 lint/test CLI |
| `louke/agents/Scout.md` | 新增 Step 5: 安装 pre-commit hook |
| `louke/agents/Archer.md` | §6 加 `.pre-commit-config.yaml` 是 Archer 可编辑产物 |
| `louke/templates/task-log.md` | `Commit: test: red` 模板改为 `feat: green` / `refactor` 前缀 |
| `louke/templates/bug-fix.md` | `Commit: test: red` 模板改为 `fix: green` / `refactor` 前缀 |
| `README.md` / `README.zh.md` | 加"pre-commit 质量门禁"小节 |
| `.github/workflows/ci.yml` | 加 `pre-commit run --all-files` 步骤 |
| `tests/test_devon_commit_rgr.bats` | 更新：`--phase red` 报错；`--phase green` / `refactor` 通过 |
| `tests/test_keeper_gate.bats` | 更新：移除 lint/test 相关断言；保留 R-G-R 顺序 + commit 格式 + AC trace + 反模式 |
| `tests/test_scout_install_precommit.bats` | **新建**：Step 5 探测 + 生成 + install 流程 |
