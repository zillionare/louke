# v0.7-001 — pre-commit 接管 lint/format/typecheck/test + R-G-R Red 去 commit — Interfaces

- **Spec ID**: v0.7-001-pre-commit-quality-gates
- **创建日期**: 2026-07-05
- **关联**: spec.md / acceptance.md / architecture.md / test-plan.md（断言依据）

> 本文件是 dev 与 test 之间的**外部可观测契约**唯一源。dev 实现层以此为准出口，test 以此为准断言依据。
>
> **不含**: 内部类层次 / 调度状态机 / 中间数据结构 / 私有方法 / 实现层细节（缓存/数据库选型归 architecture.md）。

---

## 1. CLI 端点契约

### 1.1 `lk scout install-precommit [--force]`（新增）

| 项          | 值                                                                                       |
| ----------- | ---------------------------------------------------------------------------------------- |
| 子命令路径  | `scout install-precommit`                                                                |
| Flags       | `--force`（可选，无该 flag 时若 `.pre-commit-config.yaml` 已存在则跳过生成）              |
| 退出码      | 0=成功；非 0=失败（pre-commit 包未装 / git 仓库不存在 / `pre-commit install` 子进程失败） |
| stdout      | 人类可读步骤日志：探测到的语言列表、生成文件路径、`pre-commit install` 成功与否            |
| stderr      | 错误信息（含 v0.7-001 引用）                                                              |
| 副作用      | (1) 写或刷新项目根 `.pre-commit-config.yaml`；(2) 写或刷新 `.git/hooks/pre-commit`；(3) `project-info.md` 追加/更新 `Pre-commit: installed ({language} + base)` 字段 |

**`--force` 语义**：*.yaml 已存在时也覆写（用于存量项目补装或重塑）。无 `--force` 且已存在 → stdout 打印 "skipped: .pre-commit-config.yaml exists (use --force to overwrite)"，退出 0，不报错。

**被 `lk scout foundation` Step 5 + `lk init --adopt` 共用**：两入口都在内部调_cmd_install_precommit（命名实现细节归 Devon；契约只保证两端代码路径覆盖同一逻辑）。

### 1.2 `lk devon commit-rgr --phase {green | refactor}`（修改）

| 项                  | v0.6 行为                                            | v0.7-001 行为                                                                                              |
| ------------------- | ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `--phase` choices    | `red / green / refactor`                              | `green / refactor`（red 移除）                                                                              |
| `--phase red` 传入   | 走 Red 分支生成 `test: red` commit                   | **退出非零**；stderr 含 `--phase red 已废弃 (v0.7-001): Red 阶段不 commit，详见 agents/Devon.md §5.1`      |
| `--phase green` 行为 | 生成 `feat: green ...` 或 `fix: green ...` + `Closes #{issue}` 末尾 | **不变**                                                                                                  |
| `--phase refactor` 行为 | 生成 `refactor: ...`，不追加 `Closes`       | **不变**                                                                                                   |
| 退出码（成功）       | 0                                                    | 0                                                                                                          |
| 退出码（`--phase red`） | —                                                    | 非 0（argparse choices 拒绝 → exit 2；或 dev 内显式报错 → 非 0 二选一，实现层决定，但 stderr 必含上述 message）|

**label 维度**：`--label feature / fix` 仍支持，与 `--phase green/refactor` 组合四种合法 tuple：`(feature, green)` / `(fix, green)` / `(feature, refactor)` / `(fix, refactor)`；RGR_PREFIX 字典只含此 4 键（v0.6 的 6 键删 2）。

### 1.3 `lk keeper gate`（修改）

| 项                                | v0.6 行为                                          | v0.7-001 行为                                                                                                    |
| --------------------------------- | -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `--lint` flag                      | 跑 lint 子进程                                      | **退出非零**；stderr 含 `--lint 已移除 (v0.7-001): 测试/lint/typecheck 归 pre-commit + CI`                          |
| `--typecheck` flag                 | 跑 typecheck 子进程                                  | **退出非零**；stderr 含 `--typecheck 已移除 (v0.7-001): 测试/lint/typecheck 归 pre-commit + CI`                    |
| `--tests` flag                     | 跑 test 子进程                                       | **退出非零**；stderr 含 `--tests 已移除 (v0.7-001): 测试/lint/typecheck 归 pre-commit + CI`                        |
| `lk keeper gate`（无 flag）       | 校验 commit 消息格式 + R-G-R 顺序 + AC trace + 反模式 + lint + typecheck + test | 校验 commit 消息格式 + R-G-R 顺序 + AC trace + 反模式（**不再调** lint/typecheck/test）                       |
| commit 消息格式校验                | ∈ {`feat: green`, `fix: green`, `refactor`, `test: red`（legacy）} | ∈ {`feat: green`, `fix: green`, `refactor`}；legacy `test: red` 视为历史 commit 静默接受，不参与顺序校验             |
| R-G-R 顺序校验                     | refactor 不得先于 green，同 issue 内                  | **不变**；`fix: green` 与 `feat: green` 等价检查；跨 issue 不参与顺序校验                                          |
| AC trace 校验                      | docstring 中 `AC-FRXXXX-YY` 锚点存在性 + acceptance.md 对应节存在 | **不变**                                                                                                          |
| 反模式扫描                         | `assert True` / `try: pass` / `# noqa` 滥用         | **不变**                                                                                                          |
| 退出码                             | 0=通过；非 0=失败                                  | **不变**                                                                                                          |

### 1.4 `lk shield run-e2e`（不变）

| 项                | 值                                                                       |
| ----------------- | ------------------------------------------------------------------------ |
| 子命令路径         | `shield run-e2e`                                                          |
| 内部实现依赖       | `_load_quality_gates()` + `_load_e2e_config()` + `cmd_run_e2e` **保留**   |
| 行为              | 读 `[test.e2e]` 配置 + 跑 e2e（不在本 spec 范围；不改 shield.py）          |

### 1.5 `lk init --adopt`（修改：内部走 Step 5）

`lk init --adopt` 在已有 git 仓库上调用 `cmd_install_precommit`（同 §1.1 逻辑）。CLI 行为：跑完后 `.pre-commit-config.yaml` 与 `.git/hooks/pre-commit` 存在；stdout 同 §1.1。

---

## 2. 文件 schema 契约

### 2.1 `louke/templates/pre-commit/base.yaml`（新建）

| 字段      | 类型     | 约束                                                                                      |
| --------- | -------- | ----------------------------------------------------------------------------------------- |
| `repos`   | list     | 至少 1 个 repo 条目；`repos[0]` 必须来自 `pre-commit/pre-commit-hooks`                     |
| repo.repo  | string   | `"https://github.com/pre-commit/pre-commit-hooks"`                                         |
| repo.rev   | string   | 固定 tag（非 `main` / `master`），spec 指明 `v4.6.x`                                       |
| repo.hooks | list[dict] | 含 id 为 `trailing-whitespace` / `end-of-file-fixer` / `check-yaml` / `check-toml` / `check-merge-conflict` / `large-files` 六者 |

### 2.2 `louke/templates/pre-commit/{python,node,go,rust,java}.yaml`（新建）

| 模板文件        | 必含 repo 条目（repo URL）                                                | 必含 hook id                          |
| --------------- | ----------------------------------------------------------------------- | ------------------------------------- |
| `python.yaml`   | `https://github.com/astral-sh/ruff-pre-commit`；`https://github.com/pre-commit/mirrors-mypy` | `ruff` (check) / `ruff-format` / `mypy` |
| `node.yaml`     | `https://github.com/pre-commit/mirrors-eslint`；`https://github.com/pre-commit/mirrors-prettier` | `eslint` / `prettier` + 本地 `tsc --noEmit` hook |
| `go.yaml`       | `https://github.com/dominikh/pre-commit-golang`                          | `golangci-lint` / `gofmt` / `go-test`（跑 `go test ./...`） |
| `rust.yaml`     | 本地 repo（`repo: local`），含三个 hook                                   | `cargo-fmt` (跑 `cargo fmt --check`) / `cargo-clippy` / `cargo-test` |
| `java.yaml`     | `https://github.com/pre-commit/mirrors-spotless` 或 checkstyle 等         | 任意 spotless / checkstyle hook id     |

每个模板的 `rev` 字段（除本地 repo）固定 tag（非分支名）。spec FR-0200 已锁定具体 tag 版本（ruff `v0.6.x`、mypy `v1.10.x`、eslint `v9.x`、prettier `v3.3.x`、golangci-lint `v1.59.x`）。

### 2.3 `louke/templates/pre-commit/ci-snippet.yml`（新建）

独立 YAML 文件，结构为单一 GitHub workflow 的 step 片段，含：

```yaml
- name: Run pre-commit on all files
  run: pre-commit run --all-files
```

可直接 `cat` 复制到用户项目 `.github/workflows/<name>.yml` 的 steps 序列中。Archer 在 M-ARCH 阶段可引用本片段到用户项目 CI 配置。

### 2.4 `louke/templates/pre-commit/README.md`（新建）

含：
- 自定义指南（如何往 `.pre-commit-config.yaml` 加 project-local 规则）
- 指向 `ci-snippet.yml` 的相对链接
- 从 v0.6 `[tool.louke.lint]` 迁移到 `.pre-commit-config.yaml` 的最小迁移指南（NFR-0010）

### 2.5 项目根 `.pre-commit-config.yaml`（Scout 生成产物 + louke 仓库 dogfood）

| 字段          | 类型       | 约束                                                                                           |
| ------------- | ---------- | ---------------------------------------------------------------------------------------------- |
| `repos`       | list       | 第一项恒为 `base.yaml` 内容；其后按探测到的 language 顺序追加 `{language}.yaml` 的 `repos` 列表 |
| repo.rev       | string     | 固定 tag（继承自模板；非 main/master）                                                         |
| repo.hooks[*].id | string    | 与模板对应                                                                                      |
| repo.hooks[*].args / stages | 任意 | 默认 args（不自动加 --apply）；默认 stages 含 `commit`（不跑全仓扫描——全仓扫描由 CI `--all-files` 负责） |

**louke dogfood（FR-0700 AC-4）**：louke 仓库根目录的 `.pre-commit-config.yaml` = base + python 两段拼接，由 Archer 在 M-ARCH 阶段维护（手工生成或 `lk scout install-precommit --force` 在 louke 仓库自跑一次后提交）。

### 2.6 `.git/hooks/pre-commit`（生成产物）

`lk scout install-precommit` 调 `pre-commit install` 子进程创建。该文件存在即可观测；测试断言此文件存在 + mtime 在重跑 install 时刷新。文件内容本身是 pre-commit 框架生成的 shim，不属本契约内容。

### 2.7 `project-info.md` 新增字段

| 字段            | 类型   | 值                                                         |
| --------------- | ------ | ---------------------------------------------------------- |
| `Pre-commit:`    | string | 形如 `installed (python + base)` / `installed (node + base)` / `installed (base)` |

由 Scout Step 5 写入；下游 agent 可 grep 此字段确认 pre-commit 已装。

---

## 3. 源文件 grep 出口契约（删除性 AC 的可观测出口）

> 这些 AC 校验"某函数已不存在"，可观测出口就是**源文件 grep 命中数为 0**。dev 实现须保证 grep 在合并后无命中；test 用 `rg` 在 bats 中断言。

| 编号         | grep 目标                                                                   | 期望                                   |
| ------------ | --------------------------------------------------------------------------- | -------------------------------------- |
| AC-FR0600-1 | `rg "_load_quality_gates" louke/keeper.py`                                  | 无命中                                 |
| AC-FR0600-1 | `rg "_load_quality_gates" louke/shield.py`                                  | **有**命中（对照确认 shield 留下来）  |
| AC-FR0600-2 | `rg "run_external_tool" louke/keeper.py`                                   | 无命中                                 |
| AC-FR0600-3 | `rg "run_project_tests" louke/keeper.py`                                   | 无命中                                 |
| AC-FR0600-4 | `rg "cmd_run_e2e\|_load_e2e_config\|_load_pyproject_e2e" louke/keeper.py`    | 无命中                                 |
| AC-FR0600-4 | `rg "cmd_run_e2e\|_load_e2e_config" louke/shield.py`                         | **有**命中                            |
| AC-FR0400-6 | `rg "\('feature', 'red'\)\|\('fix', 'red'\)" louke/devon.py`                  | 无命中（RGR_PREFIX 已删两键）          |
| NFR-0010-2  | `lk keeper gate` 在 fixture `pyproject.toml` 含 `[tool.louke.lint]` 时**忽略该段**（不再因 lint 命令未配置而报错） | keeper 不读 → exit code 与无该段一致  |

---

## 4. prompt 文件文本出口契约

> 这些 AC 校验 prompt 文件含/不含某关键句，可观测出口是文件 grep。

| 编号           | 文件                        | grep 目标                                                       | 期望      |
| -------------- | --------------------------- | --------------------------------------------------------------- | --------- |
| AC-FR0100-2    | `louke/agents/Scout.md`       | 含 "Step 5: 安装 pre-commit hook"                                | **有**命中|
| AC-FR0200-4    | `louke/agents/Archer.md` §6   | 含 ".pre-commit-config.yaml"                                     | **有**命中|
| AC-FR0400-1    | `louke/agents/Devon.md` §5.1  | 含 "commit-rgr --phase red"                                      | **无**命中|
| AC-FR0400-1    | `louke/agents/Devon.md` §5.1  | 含 "测试文件已提交" / "test: red"                                 | **无**命中|
| AC-FR0400-1    | `louke/agents/Devon.md` §5.1  | 含 "测试文件已在工作区"                                          | **有**命中|
| AC-FR0500-1    | `louke/agents/Devon.md` §8    | 含 "git commit --no-verify" + "修复根因"                          | **有**命中|
| AC-FR0500-2    | `louke/agents/Devon.md` §6.2  | 含 "禁止" + "git commit --no-verify"                              | **有**命中|
| AC-FR0500-4    | `louke/agents/Devon.md`        | 含 "git log 检查若发现 commit 缺 pre-commit 标记"                 | **无**命中（不可测句已删）|
| AC-FR0600-10   | `louke/agents/Keeper.md` frontmatter | `description` 含 "R-G-R 顺序 / commit 消息格式 / AC trace / 反模式扫描" | **有**命中|
| AC-FR0600-10   | `louke/agents/Keeper.md` frontmatter | `description` 含 `测试` 或 `lint`                                  | **无**命中|
| AC-FR0600-11   | `louke/agents/Keeper.md` §2.1  | 含 `lk keeper gate --tests` / `--lint` / `--typecheck`            | **无**命中|
| AC-NFR0010-6   | `louke/templates/task-log.md` Commit 字段 | 含 "test: red"                                          | **无**命中|
| AC-NFR0010-6   | `louke/templates/task-log.md` Commit 字段 | 含 "feat: green" 或 "refactor"                          | **有**命中|
| AC-NFR0010-6   | `louke/templates/bug-fix.md` Commit 字段   | 含 "test: red"                                          | **无**命中|
| AC-NFR0010-6   | `louke/templates/bug-fix.md` Commit 字段   | 含 "fix: green"                                         | **有**命中|
| AC-NFR0010-7   | `louke/agents/Devon.md` §5.1  | 是单一源；`.opencode/agents/devon.md` 是 `lk board opencode` 部署产物（不在本契约要求测试） | — |
| AC-NFR0030-1   | `README.md`, `README.zh.md` 工作流章节 | 含 "pre-commit 质量门禁" 子节 + "--no-verify 是反模式"              | **有**命中|

---

## 5. CI 配置出口契约

### 5.1 `.github/workflows/ci.yml`（修改）

新增 step（位于 checkout + 依赖安装之后）：

```yaml
- name: Run pre-commit on all files
  run: pre-commit run --all-files
```

step 名固定为 `Run pre-commit on all files`；run 命令固定 `pre-commit run --all-files`。

### 5.2 L3 nightly workflow（新建，可选）

`tests/test_anti_pattern_no_verify.bats` 中 `E2E-AC-FR0500-3` / `E2E-AC-FR0700-2` 在 nightly workflow `pre-commit run --all-files` 真实 CI 触发场景下运行。具体 workflow 文件路径由测试负责人决定（spec §6 关联文件未列）。

---

## 6. 数据 schema 契约

本 spec 不引入新的 DB schema / 缓存键 / 持久序列化格式。

唯一的"数据存盘"是：
- `.pre-commit-config.yaml`（YAML 文件，§2.5）
- `project-info.md` 的 `Pre-commit:` 字段（§2.7，plain text）
- louke 仓库根 `.pre-commit-config.yaml`（与 §2.5 同；dogfood 产物）

无数据库、无缓存、无结构化日志 schema 引入。

---

## 7. 公开 API / SDK 契约

本 spec 不引入新的对外 SDK 暴露接口。所有可观测出口都是 CLI 子命令（§1）+ 文件产物（§2 / §3 / §4 / §5）。louke 的 Python 模块仍不被外部 import 调用（CLI 是唯一对外接口）。

---

## 8. 闭合自检

| interfaces 出口类别          | 数量 | test-plan 覆盖章节                                   |
| ---------------------------- | ---- | ---------------------------------------------------- |
| CLI 新增/修改端点             | 4    | §8 FR-0100 / FR-0400 / FR-0600 / FR-0700 + NFR-0010 |
| 模板文件（louke/templates/pre-commit/） | 8   | §8 FR-0200 / FR-0700 + NFR-0030-1                    |
| 源文件 grep 出口              | 8    | §8 FR-0600 + NFR-0010-2                              |
| prompt 文件 grep 出口         | 16   | §8 FR-0400 / FR-0500 / FR-0600 / NFR-0010-6/7 + NFR-0030 |
| CI 配置 step                  | 1    | §8 FR-0700-1                                        |
| project-info.md 字段          | 1    | §8 FR-0100-6                                        |
| `.pre-commit-config.yaml`（项目根产物） | schema | §8 FR-0200-3 / FR-0700-4                            |

每个出口在 test-plan.md §8 表中均有对应 AC 编号 + 测试方向。闭合成立。