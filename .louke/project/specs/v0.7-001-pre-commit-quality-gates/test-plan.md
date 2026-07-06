# v0.7-001 — pre-commit 接管 lint/format/typecheck/test + R-G-R Red 去 commit — Test Plan

- **Spec ID**: v0.7-001-pre-commit-quality-gates
- **创建日期**: 2026-07-05
- **关联 acceptance**: `.louke/project/specs/v0.7-001-pre-commit-quality-gates/acceptance.md`
- **关联 interfaces**: `.louke/project/specs/v0.7-001-pre-commit-quality-gates/interfaces.md`（断言依据——见 §6.5）

## 1. 立场与边界

### 1.1. 黑盒声明

本 spec 的被测对象是 **louke 工作流基础设施**（CLI 命令、模板文件、prompt 文件、CI 配置片段），**不是算法/金融/规则引擎**。外部可观测出口限于：

- **CLI 端点**：`lk scout install-precommit`、`lk scout foundation`、`lk devon commit-rgr`、`lk keeper gate`、`lk init --adopt` 的 stdout/stderr/exit code
- **文件产物**：`.pre-commit-config.yaml`（项目根）、`.git/hooks/pre-commit`（git 仓库内）、`louke/templates/pre-commit/*.yaml`（louke 仓库模板目录）、`project.toml` 的 `[meta].pre_commit` 字段（fix-002 后）、`.github/workflows/ci.yml` 的 step
- **源/prompt 文件内容**：`louke/agents/{Scout,Devon,Keeper,Archer}.md`、`louke/templates/{task-log,bug-fix}.md` 的文本片段（prompt 文件在此 spec 中是被测对象，不是观测出口——验证 prompt 不再含某关键句对应 acceptance 中的"移除/加入"AC）
- **被删代码的不存在性**：通过 grep / import 在 `louke/keeper.py` / `louke/shield.py` 上断言"某函数已不存在"或"某函数仍保留"
- **pre-commit 框架行为**：通过 `git commit` 触发的 pre-commit hook 的 exit code 与 stderr（不直接断言 hook 内部，仅断言"commit 被阻止"与"stderr 含 ruff/mypy/pytest 报告"）

### 1.2. 不可观测对象（测试不直接依赖）

- `louke/scout.py` 内 Step 5 的内部探测函数命名 / 实现结构
- `RGR_PREFIX` 字典的内部数据结构形态（只断言行为：`--phase red` 报错、`--phase green/refactor` 工作）
- pre-commit hook 框架自身的内部状态机
- Python `pre-commit` 包内部缓存目录 `~/.cache/pre-commit/` 的内容（只断言"install 成功"与"hook 文件存在"）

> **可观测契约**: 凡 acceptance 验证需要的内部状态（如"Step 5 在 Step 4b 与 Step 6 之间"、"RGR_PREFIX 删除了两个 tuple 键"），impl 必须以**外部可断言形态**给出：Step 5 在 prompt 文件中以可 grep 的"Step 5"文本存在（AC-FR0100-2）；RGR_PREFIX 删除键通过"`--phase red` 报错"外部断言（AC-FR0400-3 / AC-6）。无需额外 dump 出口。

### 1.3. 作伪模式（CI 强制拦截）

| #   | 作伪模式                  | 典型表现（本 spec 语境）                                                |
| --- | ------------------------- | ---------------------------------------------------------------------- |
| 1   | 改断言迁就实现            | spec 说 `--phase red` 报错，测试改成"返回 non-zero 但不验证 stderr"     |
| 2   | 用 skip 逃避验证          | `test "fr0300 test hook 阻断"` 加 skip，理由"e2e 永远没写"               |
| 3   | 断言退化                  | `assert grep keeper.py run_external_tool` 替代"调 `--lint` 报错且含 v0.7-001" |
| 4   | try/except: pass          | bats 中 `[ -z "$output" ]` 兜底吞掉 stderr                              |
| 5   | mock 过度                 | mock 掉整个 `lk scout install-precommit`，只测 mock 输出                |
| 6   | ground truth 用 impl      | `.pre-commit-config.yaml` 内容断言 = scout.py 当前输出（无独立模板对照）|
| 7   | 硬编码期望值              | `assert rev == "v0.6.9"` 只因当前模板写的 v0.6.9（应参照模板文件本身）  |
| 8   | trivial pass              | `[ "$status" -eq 0 ]` 单独作为完整 AC 的断言                            |

### 1.4. 防护机制（CI 校验 + PR 流程）

1. **AC 强制溯源**
   - 每个测试函数的 docstring/comment 第一行必须含 `AC-FRXXXX-YY`（或 `AC-NFRXXXX-YY`，4 位编号 + 2 位 AC 序号）。bats 测试以 `# AC-FRXXXX-YY` 行内注释标在 `@test` 函数体首行。
   - CI 扫描 `tests/`，校验：每个 AC ≥1 测试引用；每个测试 ≥1 AC 引用。校验由 `lk archer ci-scan`（spec v0.5 提供）执行。
   - 任一校验失败阻塞 merge。

2. **断言禁忌**（CI 静态检查，违反阻塞 merge）
   - bats 中禁止 `[ "$status" -eq 0 ]` 单独作为断言，必须配合 `[[ "$output" == ... ]]` 或额外结构断言（见作伪模式 #8）
   - bats 中禁止 `skip "..."` 不附带 GitHub issue 链接
   - bats 中禁止 `[ -z "$output" ]` 包裹被测代码兜底吞错

3. **测试改动归类**（PR description 必填）
   - [ ] 新增 AC（关联 acceptance.md commit）
   - [ ] spec 变更（关联 spec commit）
   - [ ] 修复 flake / 环境问题（关联 issue）
   - **禁止类别**：「impl 行为与 spec 不一致 → 改测试」。Review 直接 reject。本 spec 中典型如：实现把 `--no-verify` 检测放回 git log → 应改 impl 不是改测试。

4. **可测试性回退**（若某 AC 测不了）
   - 本 spec 已在 spec 阶段排除两条不可测 AC：
     - 原文"Maestro 在 git log 检查若发现 commit 缺 pre-commit 标记"——技术上不成立（`git commit --no-verify` 与正常 commit tree object 一致），spec §FR-0500 Sage quote 已整段删除，落 acceptance AC-FR0500-4 显式声明"不依赖 git log"
     - 原文"pre-commit 性能 ≤ 30s 硬指标"——阻塞 agent 工作流，改软目标，AC 不在性能方向给出硬断言
   - 后续若发现新不可测 AC → 不得 mock 内部强行打通；登记可测试性缺口并回退修订 interfaces/acceptance。

### 1.5. 测试分工

- **单元测试 / 集成测试（bats）**: 功能实施者（Devon）与 impl 同步提交
- **E2E 测试**: 本 spec 的 scenario-0400 "CI 复查 --no-verify 绕过"为 E2E 场景，由测试负责人在 nightly 流水线编写；不在本单元 test-plan 范围
- **Ground Truth（§3）**: 本 spec 不涉及算法/规则/计算正确性，Ground Truth 方法 **N/A**——见 §3 说明
- **审查归口**: 所有测试改动由测试负责人 review；模板文件（`louke/templates/pre-commit/*.yaml`）的"被删/被改/被加"边界是审查重点

---

## 2. 测试环境

### 2.1. 目录组织（推荐）

延续 v0.6 既有 bats 平铺布局，新增三份 bats 文件覆盖本 spec：

```
tests/
├── test_scout_install_precommit.bats    # 新建（FR-0100 + FR-0200 + NFR-0010 AC-3 + NFR-0030 AC-4）
├── test_devon_commit_rgr.bats            # 已存在 → 更新（FR-0400 AC-3/4/5/6 + NFR-0010 AC-4）
├── test_keeper_gate.bats                 # 已存在 → 更新（FR-0600 AC-5/6/7/8/9/10/11 + NFR-0010 AC-1/5）
├── templates/
│   └── test_precommit_templates.bats     # 新建（FR-0200 AC-1/2/3 + FR-0300 AC 维度 + FR-0700 AC-3/4）
├── test_anti_pattern_no_verify.bats      # 新建（FR-0500 AC-1/2/3/4 + NFR-0030 AC-2）
├── test_keeper_gate.bats                 # 同上
├── fixtures/                             # 既有 fixtures 续用
└── ci-tools/                             # 既有
```

> 单元测试与 E2E 用不同 fixture repo（git init 临时仓库 / 真实本地路径），防止过拟合。E2E 不允许 mock 框架内部实现。

### 2.2. 命名约定

- 文件：`test_<被测 CLI 或主题>.bats`，例 `test_scout_install_precommit.bats`、`test_precommit_templates.bats`
- 测试：`@test "AC-FRXXXX-YY: <scenario 描述>"`，例 `@test "AC-FR0100-1: pre-commit dep 在 pyproject.toml"`

### 2.3. 执行

- **离线运行**：测试不应联网拉 hook repo；模板内容断言只校验 `repos:` 结构与 `rev:` 是固定 tag（非 main），不实际下载
- **执行顺序**：unit bats（快）→ e2e（慢，nightly）
- **CI**：每次 push 跑 bats 全套；`pre-commit run --all-files` 步在 CI workflow 中作为另一独立 step
- **隔离**：E2E 用独立 marker / 独立 bats 文件 (`test_anti_pattern_no_verify.bats` 的 E2E case 单独标注 `@test "E2E-AC-FR0500-3: ..."`)

### 2.4. 测试数据

> 本 spec **数据依赖极轻**：只有 git 仓库 fixture（`BATS_TEST_TMPDIR` 下 `git init`）+ 模板文件（louke 仓库内文本）。无历史数据、无第三方 API、无硬件输入。本节作项目可选 → 跳过。

---

## 3. Ground Truth 方法

> **何时需要**: 项目有"算法正确性 / 规则正确性 / 计算结果正确性"需要验证时必填；纯 CRUD / UI 渲染可省略。

**本 spec N/A**。本 spec 被测对象是基础设施（CLI 命令的 exit code / stderr、文件产物的存在性与文本结构、prompt 文件的 grep 命中），不涉及算法/规则/计算的正确性验证。Ground Truth 方法 §3.1 不适用。

### 3.2. Ground Truth 隔离（强制规则）—— 仍部分适用

即便 §3.1 N/A，"禁止 ground truth = impl 输出"原则在本 spec 仍生效，特别是 **模板合并**（FR-0200 AC-3 / FR-0700 AC-4）：

- 断言 `.pre-commit-config.yaml` 内容时，**期望值来源**必须是 `louke/templates/pre-commit/*.yaml` 模板文件本身（用 `yq` 或 Python `yaml.safe_load` 解析模板 → 期望），**不得**直接 hardcode `astral-sh/ruff-pre-commit` 字符串断言。即"模板文件 = ground truth；scout.py 合并产物 = 被测输出；测试比较两者"。
- 测试脚本可 import Python `yaml`/`tomllib` 第三方库读取模板与产物；**不** import `louke.*`（避免循环）。
- 模板文件由 Archer 在 M-ARCH 阶段可编辑（FR-0200 AC-4），测试相应更新——但测试断言的"形态"（rev 是固定 tag、repos 列表 base 在前）不变，故属"形态断言"非"内容硬断言"。

CI 静态检查：测试脚本中若出现 `import louke` → 阻塞 merge（适用于本 spec 的模板合并测试）。

---

## 4. 测试范围

本测试计划覆盖 `.louke/project/specs/v0.7-001-pre-commit-quality-gates/spec.md` 全部 7 个 FR + 3 个 NFR（有效需求/可测性/已决定 均为 ✅）。

| 编号       | 主题                                                        | AC 数 |
| ---------- | ----------------------------------------------------------- | ----- |
| FR-0100    | pre-commit 框架引入 + Scout 阶段安装                         | 7     |
| FR-0200    | `.pre-commit-config.yaml` 模板体系                          | 4     |
| FR-0300    | pre-commit hook 内容（lint/format/typecheck/test）          | 6     |
| FR-0400    | Devon R-G-R：Red 不 commit + commit-rgr 移除 `--phase red`  | 8     |
| FR-0500    | Devon 反模式：`--no-verify` 禁止                            | 4     |
| FR-0600    | Keeper 瘦身：移除 lint/typecheck/test 代码路径               | 11    |
| FR-0700    | CI parity：`pre-commit run --all-files`                     | 4     |
| NFR-0010   | 向后兼容                                                    | 7     |
| NFR-0020   | pre-commit 框架依赖                                         | 2     |
| NFR-0030   | 文档同步                                                    | 5     |
| **合计**   |                                                             | **58** |

---

## 5. 验收标准

1. **单元测试覆盖率 ≥95%**：本 spec 的"覆盖率"= AC 引用闭合（58/58 AC × 至少 1 测试）。行覆盖率由 v0.7+ 的 `lk archer ci-scan` 配合 Python `coverage` 在 CI 中收集（仅约束 `louke/scout.py` / `louke/devon.py` / `louke/keeper.py` 三处新增/删除行）。
2. spec §1 中 5 个用户故事（US-0100 ~ US-0510）与 §2 中 5 个关键场景（scenario-0100 ~ scenario-0500）全部被 bats 测试或 E2E 场景覆盖且通过。
3. 所有 7 FR + 3 NFR 都有对应测试覆盖，AC 引用闭合（同 §1.4 第 1 条）。
4. §6 外部依赖分层测试：L1 默认 CI 通过；L3（scenario-0400 真实 CI 触发）放 nightly。

---

## 6. 外部依赖分层测试（项目可选 —— 本 spec 启用）

> 本 spec 有明确的外部依赖：**pre-commit Python 包** + **git** + **社区 hook repo 远程（仅在真实 install/run 时）**。L1/L2 在 CI 默认跑；L3 在 nightly。

### 6.1. 三个不可回避的约束

| #   | 约束                                       | 后果                                                                  |
| --- | ------------------------------------------ | --------------------------------------------------------------------- |
| C1  | CI 不能拉社区 hook repo（可能无网络或被墙） | "真实跑 ruff/mypy hook" 不可在所有 CI runner 上以最快代价验证          |
| C2  | pre-commit hook install 后才有 `.git/hooks/pre-commit` | 测试需要临时 git repo fixture                                          |
| C3  | 不能 mock pre-commit 框架内部               | mock 掉 `pre-commit install` 等于测 mock 的行为，违反黑盒立场         |

### 6.2. 立场: 可控化 vs mock

- **可控化**：测试用 `BATS_TEST_TMPDIR` 下 `git init` 临时仓库作为 fixture；用 `pip show pre-commit` 验证包已装；用模板文件本身作为 ground truth（见 §3.2）。
- **不可 mock**：不得 mock `lk scout install-precommit` / `lk devon commit-rgr` / `lk keeper gate` 内部实现；测试通过 `python3 -m louke <cmd>` 子进程出口断言。
- **边界铁律**：任何情况下不为"让测试通过"而 patch `louke/scout.py` 的探测函数 / `louke/keeper.py` 的 gate 函数。若 AC 测不了 → 回退修订 interfaces/acceptance。

### 6.3. 三层测试金字塔

| 层   | 名称             | 速度     | 覆盖 AC 范围                                                    | 默认运行       |
| ---- | ---------------- | -------- | ------------------------------------------------------------- | -------------- |
| L1   | 确定性仿真       | 秒级     | 绝大部分：模板内容断言、CLI exit code/stderr、文件产物存在性   | ✅ CI 默认     |
| L2   | 契约仿真         | 秒级     | `pre-commit install` 在 fixture repo 跑成功（不实际拉 hook repo，验证 `.git/hooks/pre-commit` 文件创建） | ✅ CI 默认（需 pre-commit 已 pip install）|
| L3   | 真实环境冒烟     | 真实     | scenario-0400 真实 CI 触发：故意 `--no-verify` 提交 ruff 失败代码 → 推到测试分支 → CI `pre-commit run --all-files` 失败 → CI 红灯 | ❌ nightly / 手动 |

- **L1 确定性仿真**：模板文件 yaml 解析、`lk devon commit-rgr --phase red` 报错、`lk keeper gate --lint/--typecheck/--tests` 报错、源文件 grep（`rg "_load_quality_gates" louke/keeper.py` 应无命中；`rg "_load_quality_gates" louke/shield.py` 应命中）
- **L2 契约仿真**：`lk scout install-precommit --force` 在 fixture repo 真实跑（pre-commit 包已 pip install），断言 `.pre-commit-config.yaml` 被写、`.git/hooks/pre-commit` 文件被创建
- **L3 真实环境冒烟**：scenario-0400 + FR-0500 AC-3 + FR-0700 AC-2，必须真实 CI 触发；单次往返

> L3 测试**必须**标注对应 marker：bats `@test "E2E-AC-FR0700-2: ..."`，并以 GitHub issue 链接（#87 FR-0700）附带豁免，不得以无 issue 的 skip 逃避。

### 6.4. 测试基础设施的职责契约

| 组件                | 职责（对外）                                                | 边界（不实现什么）                          |
| ------------------- | --------------------------------------------------------- | ------------------------------------------- |
| 测试 fixture repo   | 在 `BATS_TEST_TMPDIR` 下 `git init` -b main 临时仓库       | 不预填 `.pre-commit-config.yaml`（除非 --force 路径） |
| 模板解析器          | 用 Python `yaml.safe_load` 读取 `louke/templates/pre-commit/*.yaml` 形态断言 | 不调用 `louke.*` 任何模块                    |
| pre-commit 包检查   | `pip show pre-commit` + `pre-commit --version` 出口       | 不 mock install 行为                        |
| CI snippet 校验器   | 比对 `louke/templates/pre-commit/ci-snippet.yml` 含 `pre-commit run --all-files` step | 不实际执行该 step（L3 才执行）              |

### 6.5. 断言依据 — 与 interfaces.md 闭合

测试断言**只能**落在 `interfaces.md` 已定义的外部可观测出口上：

- **CLI 出口**：`lk scout install-precommit` exit code / stderr；`lk devon commit-rgr --phase red` stderr 须含 "v0.7-001" + "agents/Devon.md §5.1"；`lk keeper gate --lint/--typecheck/--tests` stderr 须含对应 v0.7-001 message
- **文件 schema**：`.pre-commit-config.yaml` 的 `repos:` 列表 schema（base + per-language）；`louke/templates/pre-commit/*.yaml` 的 hook id / rev / repo 字段；`project.toml` 的 `[meta].pre_commit = "installed (...)"` 字段（fix-002 后）
- **源文件 grep 出口**：keeper.py 不含 `_load_quality_gates` / `run_external_tool` / `run_project_tests`；shield.py 反之仍含
- **prompt 文件文本出口**：`agents/Devon.md` §8 含"--no-verify"字样；§5.1 不含"commit-rgr --phase red"

> 若某 AC 需要的状态在 `interfaces.md` 中**没有**对应可观测出口，回退修订。本 spec 目前已闭合：例如 AC-FR0100-2（Step 5 在 Step 4b 与 Step 6 之间存在）的可观测出口 = `agents/Scout.md` 文本中"Step 5"标题 + `louke/scout.py` 的 `cmd_install_precommit` 函数被 `cmd_foundation` 调用链覆盖（用 `lk scout foundation` 的 stdout 含 Step 5 文本验证）。

---

## 7. CI 门禁

```bash
lk archer ci-scan \
  --acceptance .louke/project/specs/v0.7-001-pre-commit-quality-gates/acceptance.md \
  --tests tests/
```

校验项：
- AC 引用闭合（58/58 AC ≥1 测试，每个测试 ≥1 AC）
- 反模式静态扫描（§1.3 八条；针对 bats 测试做正则扫描）
- 命中率 ≥95%（针对 `louke/scout.py` / `louke/devon.py` / `louke/keeper.py` 新增/修改行）
- §3.2 ground truth 隔离：测试脚本 `import louke.*` → 阻塞 merge

**外加本 spec 专属 CI step**（FR-0700 AC-1）：
```yaml
- name: Run pre-commit on all files
  run: pre-commit run --all-files
```
此 step 与 `lk archer ci-scan` 并列存在，前者是 dogfood 自检（模板在 louke 仓库自身暴露问题），后者是 AC 引用闭合校验。两者互不替代。

---

## 8. AC 覆盖策略映射（按 FR/NFR 给测试方向，非清单）

> Archer §10 反模式 #1：test-plan 不写测试用例清单/覆盖矩阵。下表只标"哪个测试方向覆盖哪个 AC 的可观测出口"，具体用例由 Devon 在 `tests/` 编写时按 `AC-FRXXXX-YY` 引用。

### FR-0100 (7 AC) → `test_scout_install_precommit.bats` + `test_scout_foundation.bats`（已存在，更新）
- AC-1: L1 — grep `pyproject.toml` 含 `pre-commit >= 3.0`；`pip show pre-commit` exit 0
- AC-2: L1 — `agents/Scout.md` 文本含 "Step 5: 安装 pre-commit hook"；`lk scout foundation --dry-run` stdout 含 Step 5 行
- AC-3: L1 — fixture repo 放 `pyproject.toml` + `package.json` 双 manifest → `lk scout install-precommit --force` 后 `.pre-commit-config.yaml` 含 python + node 两套 repos
- AC-4: L1 — fixture repo 跑 install-precommit → `.pre-commit-config.yaml` 存在且 yaml 解析后 `repos[0]` repo 来自 base.yaml；再次跑（无 --force）→ 文件不被覆写
- AC-5: L2 — 跑 install-precommit → `.git/hooks/pre-commit` 文件存在；再跑 → 文件 mtime 刷新 + exit 0
- AC-6: L1 — `project.toml` 含 `[meta].pre_commit = "installed (python + base)"` 字段（fix-002 后）
- AC-7: L1/L2 — `lk scout install-precommit --force` 独立运行 + `lk init --adopt` 独立运行（fixture repo 已有 git 历史但无 pre-commit）

### FR-0200 (4 AC) → `templates/test_precommit_templates.bats`
- AC-1: L1 — `base.yaml` 存在；解析后含 trailing-whitespace / end-of-file-fixer / check-yaml / check-toml / check-merge-conflict / large-files 6 个 hook id；所有 `rev` 字段非 main/master
- AC-2: L1 — `python.yaml`/`node.yaml`/`go.yaml`/`rust.yaml`/`java.yaml` 各自存在且含对应社区 repo；`rev` 固定 tag
- AC-3: L1 — fixture repo py+node → 合并产物 `repos` 中 base 在最前 + python 段 + node 段；用 `yq`/python yaml 比对模板拼接
- AC-4: L1 — `agents/Archer.md` §6 含 ".pre-commit-config.yaml" 字样（grep）

### FR-0300 (6 AC) → `test_scout_install_precommit.bats`（fixture 触发 git commit 验证 pre-commit 行为）+ L3 nightly
- AC-1: L2/L3 — fixture repo 写一个 `import os\nimport sys\n` 不用 sys 的 .py → `git commit` 退出非零 + stderr 含 ruff 报告
- AC-2: L2/L3 — fixture 写一段未格式化 .py → commit 阻止；模板默认无 `--apply` args（断言 base/python 模板里无 `--apply`）
- AC-3: L2/L3 — fixture 写类型不匹配的 .py → mypy 报错 + commit 阻止
- AC-4: L2/L3 — fixture 写一个会失败 pytest test staged → commit 退出非零；恢复正常后 commit 成功（验证 Green 阶段测试通过 → test hook 通过）
- AC-5: L1 — `lk scout install-precommit` 生成的 `.pre-commit-config.yaml` 顶层注释或 schema 中默认 stages 不含全仓扫描选项；CI step `pre-commit run --all-files` 在 ci-snippet.yml 中独立存在（不混入 commit hook）
- AC-6: L1 — `agents/Devon.md` §5.1 Red 阶段不含 "commit-rgr --phase red" 字样 → Red 不创建 commit → pre-commit 不触发（间接论证测试 hook 不会被 Red 失败拦死）

### FR-0400 (8 AC) → `test_devon_commit_rgr.bats` + `test_keeper_gate.bats`
- AC-1: L1 — `agents/Devon.md` §5.1 步骤列表 grep 不含 "commit-rgr --phase red"；退出条件 grep 不含 "测试文件已提交" / "test: red"；含 "测试文件已在工作区"
- AC-2: L1 — fixture repo 跑 Devon Red 模拟（直接写 test 文件不调 commit-rgr）→ `git status` 显示 untracked；`git log` 无 `test: red` 新 commit
- AC-3: L1 — `lk devon commit-rgr --phase red --issue 42 --message "x"` 退出非零 + stderr 含 "v0.7-001" + "agents/Devon.md §5.1"
- AC-4: L1 — `lk devon commit-rgr --phase green --issue 42 --message "foo"` exit 0 + commit message 含 `feat: green` 或 `fix: green` + 末尾 `Closes #42`
- AC-5: L1 — `--phase refactor` exit 0 + message 含 `refactor:` + **不含** `Closes #42`
- AC-6: L1 — `louke/devon.py` grep `('feature', 'red')` 与 `('fix', 'red')` 应**无**命中（已删）；`('feature','green')` 等 4 键应有命中（间接验证 RGR_PREFIX 形态——但**主断言**通过行为 AC-3/4/5）
- AC-7: L1 — fixture repo 构造 git log 序列 `[green]` → `lk keeper gate` exit 0；`[green, refactor, refactor]` → exit 0；`[refactor, green]`（同 issue）→ exit 非 0 + stderr 含 "refactor 先于 green"；fix cycle 同样；跨 issue 的 `[refactor, green]` 不报错
- AC-8: L1 — fixture 含 legacy `test: red` commit（v0.7 前格式）→ `lk keeper gate` exit 0

### FR-0500 (4 AC) → `test_anti_pattern_no_verify.bats`
- AC-1: L1 — `agents/Devon.md` §8 反模式列表 grep 含 "git commit --no-verify" + "修复根因"
- AC-2: L1 — `agents/Devon.md` §6.2 grep 含 "禁止" + "git commit --no-verify"
- AC-3: L3 — E2E：故意 `--no-verify` 提交 ruff 失败代码 → 推到测试分支 → CI `pre-commit run --all-files` 失败 → CI 红灯（nightly / 手动触发，标 issue #85 链接）
- AC-4: L1 — `agents/Devon.md` §8 与 §6.2 grep **不**含 "git log 检查若发现 commit 缺 pre-commit 标记"（即确认该不可测句已删）

### FR-0600 (11 AC) → `test_keeper_gate.bats` + grep 静态检查
- AC-1: L1 — `rg "_load_quality_gates" louke/keeper.py` 无命中；`rg "_load_quality_gates" louke/shield.py` **有**命中（对照确认 keeper 端删、shield 端留）
- AC-2: `rg "run_external_tool" louke/keeper.py` 无命中；`cmd_gate` grep 无 `run_external_tool`
- AC-3: `rg "run_project_tests" louke/keeper.py` 无命中；`cmd_gate` grep 无 test 调用
- AC-4: `rg "cmd_run_e2e|_load_e2e_config|_load_pyproject_e2e" louke/keeper.py` 无命中；shield.py 中三者**有**命中
- AC-5: L1 — fixture repo 提交前缀非 R-G-R 的 commit → `lk keeper gate` exit 非 0 + stderr 报错
- AC-6: 同 FR-0400 AC-7（同一 fixture 验证 keeper 的 R-G-R 顺序校验）
- AC-7: L1 — fixture 含 docstring `AC-FRXXXX-YY` 锚点缺失的代码文件 → `lk keeper gate` exit 非 0 + 报错
- AC-8: L1 — fixture 含 `assert True` / `try: pass` 反模式文件 → `lk keeper gate` exit 非 0 + 报错
- AC-9: L1 — `lk keeper gate --tests` exit 非 0 + stderr 含 "`--tests 已移除 (v0.7-001)`"；`--lint` / `--typecheck` 同样
- AC-10: L1 — `agents/Keeper.md` frontmatter `description` 字段 grep `测试|lint` 无命中；含 "R-G-R 顺序 / commit 消息格式 / AC trace / 反模式扫描"
- AC-11: L1 — `agents/Keeper.md` §2.1 tools 段 grep 不含 `lk keeper gate --tests|lint|typecheck`

### FR-0700 (4 AC) → `test_precommit_templates.bats` + L3 nightly
- AC-1: L1 — `.github/workflows/ci.yml` grep 含 "Run pre-commit on all files" + "pre-commit run --all-files"；step 位于 checkout/dep 之后
- AC-2: L3 — 故意 `--no-verify` commit ruff 失败代码 → push → CI 失败 → 红灯（同 FR-0500 AC-3，nightly）
- AC-3: L1 — `louke/templates/pre-commit/ci-snippet.yml` 存在且 grep 含 `pre-commit run --all-files`；`README.md` 含指向 ci-snippet.yml 链接
- AC-4: L1 — louke 仓库根 `.pre-commit-config.yaml` 存在；yq 解析后 repos = base.yaml hooks + python.yaml hooks 顺序拼接；CI 跑 `pre-commit run --all-files` 在 dogfood step（同 AC-1）

### NFR-0010 (7 AC) → 散落各 bats 文件
- AC-1: 同 FR-0400 AC-8
- AC-2: L1 — fixture `pyproject.toml` 含 `[tool.louke.lint]` fake 段 → `lk keeper gate` 不读它（即 keeper 不报"lint 命令未配置"错，而是忽略）；`rg "_load_quality_gates" louke/keeper.py` 无进一步证实
- AC-3: 同 FR-0100 AC-7
- AC-4: 同 FR-0400 AC-3（stderr 含 v0.7-001 + §5.1 指引）
- AC-5: 同 FR-0600 AC-9
- AC-6: L1 — `louke/templates/task-log.md` Commit 字段 grep 不含 "test: red"；含 "feat: green" 或 "refactor"；`bug-fix.md` 同理含 "fix: green"
- AC-7: L1 — `louke/agents/Devon.md` 是单一源（被 grep）；`.opencode/agents/devon.md` 是部署产物，规定功能完成后 `lk board opencode` 刷新——本测试只验证源文件，不验证部署产物（部署产物由 `lk board opencode` 自身的测试覆盖）

### NFR-0020 (2 AC) → `test_scout_install_precommit.bats`
- AC-1: L1 — `pyproject.toml` grep 含 `pre-commit >= 3.0` 且 `< 5.0` 字样；`pip show pre-commit` exit 0
- AC-2: L2 — fixture repo 仅含 `package.json`（无 Python manifest）→ `lk scout install-precommit --force` exit 0 + `.git/hooks/pre-commit` 文件存在（验证 louke 装上后 Python pre-commit 包可用，NFR-0020 接受"非 Python 项目仍需 Python"约束）

### NFR-0030 (5 AC) → grep 静态检查 + `test_precommit_templates.bats`
- AC-1: L1 — `README.md` 与 `README.zh.md` grep 含 "pre-commit 质量门禁" 子节标题 + "--no-verify 是反模式"
- AC-2: 同 FR-0500 AC-1/AC-2 + FR-0400 AC-1（三处合并验证 Devon.md）
- AC-3: 同 FR-0600 AC-10/AC-11（Keeper.md 三处同步验证一次）
- AC-4: 同 FR-0100 AC-2（Scout.md Step 5 验证）
- AC-5: 同 FR-0200 AC-4（Archer.md §6 .pre-commit-config.yaml 验证）

---

## 9. 测试分工与产物路径

| 产物                          | 编写方 | 路径                                                                 |
| ----------------------------- | ------ | -------------------------------------------------------------------- |
| `test_scout_install_precommit.bats` | Devon  | `tests/test_scout_install_precommit.bats`                            |
| `test_devon_commit_rgr.bats`（更新） | Devon  | `tests/test_devon_commit_rgr.bats`                                  |
| `test_keeper_gate.bats`（更新）     | Devon  | `tests/test_keeper_gate.bats`                                       |
| `test_precommit_templates.bats`     | Devon  | `tests/templates/test_precommit_templates.bats`（按 §2.1 布局）       |
| `test_anti_pattern_no_verify.bats`  | Devon（L1 部分）/ 测试负责人（L3 部分） | `tests/test_anti_pattern_no_verify.bats`         |
| L3 nightly workflow             | 测试负责人 | `.github/workflows/nightly-e2e.yml`（nightly，单次 --no-verify 真实往返）|

---

## 10. Judge 评审清单

- [x] 测试策略覆盖主要风险（CLI exit code、文件产物、grep 静态、真实 CI 冒烟）
- [x] 每个 AC 都能反向追踪到测试代码（§8 表已逐条标 AC → 测试方向）
- [x] test-plan 不维护具体测试用例清单/覆盖矩阵（§8 只给"测试方向"不给断言细节）
- [x] 反模式 CI 门禁已启用（§1.3 + §1.4 + §7）
- [x] 测试数据来源可复现（§2.4 N/A，本 spec 数据依赖极轻）
- [x] tests/ 布局已说明（§2.1 续沿用 v0.6 bats 平铺 + 新增 templates/ 子目录）
- [x] §3 Ground Truth 方法已说明（§3 N/A with reason + §3.2 部分适用）
- [x] §6 外部依赖分层测试已说明（§6 启用，pre-commit + git + hook repo 三层）
- [x] interfaces.md 与 test-plan 闭合（§6.5 列出全部断言出口均与 interfaces.md 对应）