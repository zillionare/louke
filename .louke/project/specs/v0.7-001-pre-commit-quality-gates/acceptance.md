# v0.7-001 — pre-commit 接管 lint/format/typecheck/test + R-G-R Red 去 commit — Acceptance Criteria

- **Spec ID**: v0.7-001-pre-commit-quality-gates
- **创建日期**: 2026-07-05

> 验收标准集中处。spec.md 只保留 FR/NFR 的需求描述与元数据；可观察、可断言的通过条件在本表里。
>
> 编号约定: AC-FRXXXX-YY（4 位 FR + 2 位 AC 序号）。Lex 阶段一/二校验本表存在性、spec↔acceptance 节对应、每条 AC 可断言。

---

<a id="ac-fr-0100"></a>

## FR-0100 pre-commit 框架引入 + Scout 阶段安装

### AC-1
- `pyproject.toml` 的 `[project.dependencies]` 含 `pre-commit >= 3.0`
- `pip install louke` 后 `pre-commit --version` 可执行

### AC-2
- `agents/Scout.md` 工作流程在 Step 4b 与 Step 6 之间存在 "Step 5: 安装 pre-commit hook"
- `louke/scout.py` 实现 `cmd_install_precommit`（<拟>，v0.7-001 落地时新增），被 `lk scout foundation` 调用链覆盖

### AC-3
- 探测逻辑全部匹配项（非短路）：`pyproject.toml`/`setup.py` → Python；`package.json` → Node；`go.mod` → Go；`Cargo.toml` → Rust；`pom.xml`/`build.gradle` → Java；无 manifest → 仅 base
- 多语言项目（同时有 `pyproject.toml` + `package.json`）→ 同时装 python.yaml + node.yaml

### AC-4
- Scout Step 5 在 repo 根目录写 `.pre-commit-config.yaml`
- 文件内容由 `louke/templates/pre-commit/base.yaml` + 探测到的 `{language}.yaml` 合并
- 若 `.pre-commit-config.yaml` 已存在 → 跳过生成（除非 `--force`）

### AC-5
- Scout Step 5 跑 `pre-commit install` → `.git/hooks/pre-commit` 文件存在
- 重跑 `lk scout install-precommit` → hook 文件被刷新（幂等），不报错

### AC-6
- Scout Step 6 写 `project.toml` 含字段 `[meta].pre_commit = "installed ({language} + base)"`（fix-002 后）
- 下游 agent 可读此字段确认 pre-commit 已装

### AC-7
- `lk scout install-precommit --force` 在已有 repo（无 `.pre-commit-config.yaml`）上独立执行 → 生成配置 + install hook
- `lk init --adopt` 走同样流程

---

<a id="ac-fr-0200"></a>

## FR-0200 `.pre-commit-config.yaml` 模板体系

### AC-1
- `louke/templates/pre-commit/base.yaml` 存在
- 含 hook: trailing-whitespace / end-of-file-fixer / check-yaml / check-toml / check-merge-conflict / large-files
- 所有 hook 的 `rev` 字段是固定 tag（非 `main`/`master`）

### AC-2
- `python.yaml` 含 `astral-sh/ruff-pre-commit`（check + format）+ `pre-commit/mirrors-mypy`
- `node.yaml` 含 `pre-commit/mirrors-eslint` + `pre-commit/mirrors-prettier` + 本地 `tsc --noEmit` hook
- `go.yaml` 含 `dominikh/pre-commit-golang`（golangci-lint + gofmt）+ `go-test` hook（`go test ./...`）
- `rust.yaml` 含本地 `cargo fmt --check` / `cargo clippy` / `cargo test` hook
- `java.yaml` 含 `pre-commit/mirrors-spotless` 或 checkstyle
- 每个模板的 `rev` 字段是固定 tag

### AC-3
- 探测到 Python + Node → `.pre-commit-config.yaml` 的 `repos:` 列表包含 python.yaml 和 node.yaml 两套 repo 条目
- base.yaml 的 repo 始终在最前

### AC-4
- `agents/Archer.md` §6 显式列出 `.pre-commit-config.yaml` 为 Archer 可编辑的架构产物
- Archer 在 M-ARCH 阶段修改 `.pre-commit-config.yaml`（如换 linter）→ 下次 commit 生效

---

<a id="ac-fr-0300"></a>

## FR-0300 pre-commit hook 内容（lint / format / typecheck / test）

### AC-1
- Python 项目中 staged `.py` 文件有 ruff check 失败 → `git commit` 退出非零，commit 不创建
- 错误信息含 ruff 报告

### AC-2
- ruff format --check / prettier --check 失败 → commit 阻止
- hook 默认不自动修复（除非模板配置 `--apply` args）

### AC-3
- mypy / tsc --noEmit / cargo check 失败 → commit 阻止

### AC-4
- pytest / npm test / go test 失败 → commit 阻止
- Green 阶段 commit（测试通过）→ pre-commit test hook 通过，commit 成功

### AC-5
- pre-commit 只对 staged 文件跑检查（非全仓扫描）
- 全仓扫描由 CI `pre-commit run --all-files` 负责（FR-0700）

### AC-6
- Devon Red 阶段（FR-0400.1）不创建 commit → pre-commit 不触发 → test hook 不会因 Red 失败而拦死
- Green/Refactor commit 时测试必过 → test hook 通过

---

<a id="ac-fr-0400"></a>

## FR-0400 Devon R-G-R 改造：Red 不 commit + commit-rgr 移除 --phase red

### AC-1
- FR-0400.1 Red 不 commit: `agents/Devon.md` §5.1 Phase 1 (Red) 的步骤列表中**不含** `commit-rgr --phase red` 调用
- 退出条件**不含** "测试文件已提交" 或 "commit 消息以 `test: red` 开头"
- 退出条件**含** "测试文件已在工作区" + "测试套件报告 Red" + "失败信息指向待实现功能"

### AC-2
- FR-0400.1 Red 不进 git 历史: Devon 完成 Red 阶段后 `git status` 显示测试文件为 untracked / unstaged
- `git log` 中无 `test: red` 前缀的新 commit

### AC-3
- FR-0400.2 `--phase red` 报错: `lk devon commit-rgr --phase red --issue 42 --message "..."` 退出非零
- stderr 含 `--phase red 已废弃 (v0.7-001): Red 阶段不 commit，详见 agents/Devon.md §5.1`

### AC-4
- FR-0400.2 `--phase green` 行为: `lk devon commit-rgr --phase green --issue 42 --message "foo"` 成功
- 生成的 commit message 以 `feat: green` 或 `fix: green` 开头（依 issue labels）
- commit message 末尾含 `Closes #42`

### AC-5
- FR-0400.2 `--phase refactor` 行为: `lk devon commit-rgr --phase refactor --issue 42 --message "cleanup"` 成功
- 生成的 commit message 以 `refactor:` 开头
- commit message **不含** `Closes #42`（仅 Green 追加）

### AC-6
- FR-0400.2 RGR_PREFIX 字典: `louke/devon.py` 的 `RGR_PREFIX` 嵌套 dict 删除 `('feature', 'red')` 和 `('fix', 'red')` 两个 tuple key
- 保留 `('feature','green')` `('fix','green')` `('feature','refactor')` `('fix','refactor')` 共 4 个键

### AC-7
- FR-0400.3 R-G-R 顺序检查: 同 issue 内 commit 序列 `[green]` → `lk keeper gate` 通过
- 同 issue 内 `[green, refactor, refactor]` → 通过
- 同 issue 内 `[refactor, green]` → 报错 "refactor 先于 green (issue #{N})"
- fix cycle 同理：`[fix: green, refactor]` → 通过，`[refactor, fix: green]` → 报错
- 跨 issue 不参与顺序校验（不同 issue 的 commit 不强制 green-before-refactor）

### AC-8
- FR-0400.3 legacy 静默接受: git 历史含 v0.7 前的 `test: red` commit → `lk keeper gate` 不报错
- Keeper 把 `test: red` 视为 legacy，不参与顺序校验

---

<a id="ac-fr-0500"></a>

## FR-0500 Devon 反模式：`--no-verify` 禁止

### AC-1
- `agents/Devon.md` §8 反模式列表含条目 "使用 `git commit --no-verify` 绕过 pre-commit hook"
- 条目含修复指引："pre-commit 失败 → 修复根因后重新 commit；不允许 --no-verify 跳过"

### AC-2
- `agents/Devon.md` §6.2 Push 规则段落含明确禁令："**禁止** `git commit --no-verify`"
- 禁令位于 commit/push 流程描述中

### AC-3
- 假设 Devon 用 `--no-verify` 提交了 lint 失败的 commit → push 后 CI 跑 `pre-commit run --all-files` → 失败 → CI 红灯
- Maestro 收到 CI 红灯 → 识别为反模式触发 → 退回 Devon

### AC-4
- `--no-verify` 检测不依赖 `git log`：spec 移除"git log 检查若发现 commit 缺 pre-commit 标记"——技术上无法实现（`git commit --no-verify` 不写 pre-commit 输出到 git object）
- `Maestro` 撤退回触发器仅为：(a) Devon prompt 反模式规则记录在 agent 自我审查；(b) CI 红灯（FR-0700）

---

<a id="ac-fr-0600"></a>

## FR-0600 Keeper 瘦身：移除 lint / typecheck / test 代码路径

### AC-1
- FR-0600.1 `_load_quality_gates()` 删除: `louke/keeper.py` 不再定义此函数
- 备注：`louke/shield.py` 仍保留同名函数（e2e 配置读取职责保留给 shield）

### AC-2
- FR-0600.1 `run_external_tool()` 删除: `louke/keeper.py` 不再定义此函数
- `cmd_gate` 不再调用 lint / typecheck 相关函数

### AC-3
- FR-0600.1 `run_project_tests()` 删除: `louke/keeper.py` 不再定义此函数
- `cmd_gate` 不再调用 test 执行函数

### AC-4
- FR-0600.1 e2e 配置职责归 shield: keeper.py 不再含 e2e 相关代码（验证：grep `cmd_run_e2e\|_load_e2e_config\|_load_pyproject_e2e` 在 keeper.py 无命中）
- `louke/shield.py` 中 `_load_quality_gates()` + `_load_e2e_config()` + `cmd_run_e2e` 三者保留

### AC-5
- FR-0600.2 commit 消息格式: `lk keeper gate` 仍校验 commit 消息前缀 ∈ {`feat: green`, `fix: green`, `refactor`}
- 非 R-G-R 前缀的 commit → 报错

### AC-6
- FR-0600.2 R-G-R 顺序: `lk keeper gate` 校验同 issue 内 refactor 不先于 green
- 同 issue 内 commit 序列只允许 `[green]` / `[green, refactor...]`，`[refactor, green]` → 报错
- fix cycle 同理（`fix: green` 与 `feat: green` 等价检查）
- 跨 issue 不参与顺序校验

### AC-7
- FR-0600.2 AC trace: `lk keeper gate` 仍扫描 docstring 中的 `AC-FRXXXX-YY` 锚点
- 锚点缺失 / acceptance.md 中无对应节 → 报错

### AC-8
- FR-0600.2 反模式扫描: `lk keeper gate` 仍扫描 `assert True` / `try: pass` / `# noqa` 滥用等反模式
- 命中反模式 → 报错

### AC-9
- FR-0600.3 CLI flag 报错: `lk keeper gate --tests` 退出非零
- `lk keeper gate --lint` / `--typecheck` 同样退出非零
- stderr 分别含 `--tests 已移除 (v0.7-001)` / `--lint 已移除 (v0.7-001)` / `--typecheck 已移除 (v0.7-001): 测试/lint/typecheck 归 pre-commit + CI`

### AC-10
- FR-0600.3 Keeper.md description: frontmatter `description` = `质量门禁 — 验证 R-G-R 顺序 / commit 消息格式 / AC trace / 反模式扫描`
- 不再含 `测试` / `lint` 字样

### AC-11
- FR-0600.3 Keeper.md §2.1 tools: 不含 lint / typecheck / test 相关 CLI 调用
- 仅保留 `lk keeper gate` + `git log` 相关命令

---

<a id="ac-fr-0700"></a>

## FR-0700 CI parity：`pre-commit run --all-files`

### AC-1
- `.github/workflows/ci.yml` 含 step `- name: Run pre-commit on all files` + `run: pre-commit run --all-files`
- step 位于 checkout + 依赖安装之后

### AC-2
- 故意提交一个 ruff check 失败的 commit（用 `--no-verify` 绕过本地）
- push 后 CI 跑 `pre-commit run --all-files` → 失败 → CI 整体红灯

### AC-3
- `louke/templates/pre-commit/ci-snippet.yml` 存在，含 `pre-commit run --all-files` step（独立 YAML 文件，可直接 `cat` 复制）
- `louke/templates/pre-commit/README.md` 含指向 ci-snippet.yml 的链接 + 使用说明
- Archer 可引用 ci-snippet.yml 到用户项目 `.github/workflows/`

### AC-4
- louke 仓库自身 dogfood：根目录 `.pre-commit-config.yaml` 由 `louke/templates/pre-commit/base.yaml` + `python.yaml` 合并生成
- louke CI `.github/workflows/ci.yml` 跑 `pre-commit run --all-files`，模板问题在 louke 仓库自身暴露

---

<a id="ac-nfr-0010"></a>

## NFR-0010 向后兼容

### AC-1
- git 历史含 v0.7 前的 `test: red` commit → `lk keeper gate` 不报错（静默接受为 legacy）

### AC-2
- `pyproject.toml` 含 `[tool.louke.*]` 段 → louke 不再读（keeper `_load_quality_gates` 删除，pyproject fallback 同步移除）
- 用户需手动迁移到 `.pre-commit-config.yaml`（louke 不提供自动迁移工具）
- 原 v0.6 的 `pyproject.toml [tool.louke.test.e2e]` 段读取归 shield 端 `_load_e2e_config()`，不受本 spec 影响（仅去掉 keeper 端 fallback）

### AC-3
- 已有 repo（无 `.pre-commit-config.yaml`）跑 `lk scout install-precommit --force` → 成功安装
- 后续 commit 走 pre-commit

### AC-4
- 老脚本调 `lk devon commit-rgr --phase red` → 报错信息含 v0.7-001 引用 + `agents/Devon.md §5.1` 指引
- 用户能从报错信息知道如何迁移

### AC-5
- 老脚本调 `lk keeper gate --lint` / `--typecheck` / `--tests` → 三个 flag 都退出非零
- stderr 含 v0.7-001 引用 + "归 pre-commit + CI" 指引

### AC-6
- `louke/templates/task-log.md` Commit 字段模板从 `test: red – ...` 改为 `feat: green – ... 或 refactor: ...`
- `louke/templates/bug-fix.md` Commit 字段模板从 `test: red – BUG-{编号} ...` 改为 `fix: green – BUG-{编号} ... 或 refactor: ...`

### AC-7
- `louke/agents/Devon.md` 是单一源文件，§5.1 Red 阶段不含 commit-rgr 调用
- `.opencode/agents/devon.md` 是 `lk board opencode` 的部署产物（非源文件），功能完成后跑 `lk board opencode` 刷新部署即可同步

---

<a id="ac-nfr-0020"></a>

## NFR-0020 pre-commit 框架依赖

### AC-1
- `pyproject.toml` `[project.dependencies]` 含 `pre-commit >= 3.0, < 5.0`（允许 3.x / 4.x，留主版本缓冲）
- `pip show pre-commit` 在 louke 装好后可执行

### AC-2
- 纯 Node 项目（无 Python manifest）装 louke → `pre-commit` 命令可用（Python 随 louke 依赖装入）
- `pre-commit install` 在 Node 项目 repo 成功执行

---

<a id="ac-nfr-0030"></a>

## NFR-0030 文档同步

### AC-1
- `README.md` "工作流"章节含 "pre-commit 质量门禁" 子节
- `README.zh.md` 含对应中文子节
- 子节说明: lint/format/typecheck/test 在 commit 时自动跑 + `--no-verify` 是反模式

### AC-2
- `agents/Devon.md` §5.1 Red 阶段不含 commit-rgr 调用（FR-0400.1 AC-1）
- §6.2 Push 规则含 `--no-verify` 禁令（FR-0500 AC-2）
- §8 反模式含 `--no-verify` 条目（FR-0500 AC-1）

### AC-3
- `agents/Keeper.md` frontmatter `description` 不含 `测试` / `lint` 字样（FR-0600.3 AC-10）
- §3 任务描述移除 "调度 lint/test" 类表述
- §2.1 tools 段移除 lint/test 相关 CLI 调用

### AC-4
- `agents/Scout.md` 工作流程含 "Step 5: 安装 pre-commit hook"
- Step 5 描述: 探测语言 → 生成 `.pre-commit-config.yaml` → `pre-commit install` → 记录 `project.toml`

### AC-5
- `agents/Archer.md` §6 显式列出 `.pre-commit-config.yaml` 为 Archer 可编辑产物
- Archer 在 M-ARCH 阶段可调整 linter / formatter / typecheck 工具选型
