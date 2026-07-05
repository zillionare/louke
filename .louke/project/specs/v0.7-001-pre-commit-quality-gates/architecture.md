# v0.7-001 — pre-commit 接管 lint/format/typecheck/test + R-G-R Red 去 commit — Architecture

- **Spec ID**: v0.7-001-pre-commit-quality-gates
- **创建日期**: 2026-07-05
- **关联 spec**: `.louke/project/specs/v0.7-001-pre-commit-quality-gates/spec.md`

## 1. 模块边界

本 spec 是 **louke 工作流基础设施** 改造，不引入新的算法/运行时子系统；模块边界落在现有 louke 源文件 + 模板目录 + prompt 文件 + CI 配置四类产物上。

| 模块 / 产物                | 现状                                                        | 本 spec 改动                                                                                                                     |
| --------------------------- | ----------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `louke/scout.py`            | 含 `cmd_foundation` / `cmd_commit_foundation`，无 Step 5     | 新增 `cmd_install_precommit` 子命令；`cmd_foundation` 在 Step 4b 与 Step 6 之间调用 Step 5；`cmd_init --adopt` 同样调用          |
| `louke/devon.py`            | `commit-rgr` `--phase` ∈ `{red, green, refactor}`；`RGR_PREFIX` 含 6 键（feature/fix × red/green/refactor） | `--phase` choices 改 `[green, refactor]`；`RGR_PREFIX` 删 `('feature','red')` `('fix','red')` → 4 键                               |
| `louke/keeper.py`           | 含 `_load_quality_gates` / `run_external_tool` / `run_project_tests`；`cmd_gate` 含 `--lint/--typecheck/--tests` 三个 flag | 删三函数；`cmd_gate` 删 lint/typecheck/test 三分支；删三 flag；`pyproject.toml [tool.louke.*]` fallback 读取路径一并删         |
| `louke/shield.py`           | 含 `_load_quality_gates` / `_load_e2e_config` / `cmd_run_e2e` | **不动**——e2e 是 Shield 职责，不在本 spec 范围（spec §0.2 + FR-0600 AC-4 明示保留）                                               |
| `louke/templates/pre-commit/` | 目录不存在                                                  | **新建**：`base.yaml` + `python.yaml` + `node.yaml` + `go.yaml` + `rust.yaml` + `java.yaml` + `ci-snippet.yml` + `README.md`     |
| `louke/agents/Scout.md`     | Steps 1-8，无 Step 5                                        | 在 Step 4b 与 Step 6 之间插入 "Step 5: 安装 pre-commit hook" 子流程                                                                |
| `louke/agents/Devon.md`     | §5.1 Phase 1 含 commit-rgr --phase red；§6.2、§8 无 --no-verify 条目 | §5.1 Red 不 commit（删 commit-rgr 调用 + 移除 "测试文件已提交" 退出条件）；§6.2 加禁令；§8 加反模式条目；删除"git log 检查 pre-commit 标记"不可测句 |
| `louke/agents/Keeper.md`    | description 含 "lint / 测试"；§2.1、§3 调度 lint/test        | description 改为 "R-G-R 顺序 / commit 消息格式 / AC trace / 反模式扫描"；§3 / §2.1 移除 lint/test 表述                          |
| `louke/agents/Archer.md`    | §6 可编辑产物清单                                            | 加入 `.pre-commit-config.yaml` 为 Archer 可编辑产物之一                                                                          |
| `louke/templates/task-log.md` / `louke/templates/bug-fix.md` | Commit 字段模板为 `test: red – ...`                          | 改为 `feat: green – ... 或 refactor` / `fix: green – BUG-{编号} ... 或 refactor`                                                  |
| `README.md` / `README.zh.md` | 工作流章节，无 pre-commit 子节                               | 加 "pre-commit 质量门禁" 子节，说明 lint/format/typecheck/test commit 时自动跑 + `--no-verify` 反模式                            |
| `.github/workflows/ci.yml`  | louke 自身 CI，无 pre-commit step                            | 加 `pre-commit run --all-files` step（位于 checkout + 依赖安装之后）                                                              |
| `pyproject.toml`            | `dependencies` 无 pre-commit；无 `[tool.louke.*]`           | 加 `pre-commit >= 3.0, < 5.0`；v0.6 若有 `[tool.louke.lint]` 等段一并删                                                                 |
| `.pre-commit-config.yaml`（louke 仓库根） | 不存在                                                      | **新建**（dogfood）：由 `louke/templates/pre-commit/base.yaml` + `python.yaml` 合并                                                |
| `.louke/project/quality-gates.toml`     | 不存在                                                      | **不引入**。spec §0.2 否决中性 TOML 提案；keeper 端 `[lint] [typecheck] [test]` 段读取一并删；shield 端 `[test.e2e]` 段读取由 shield 独立维护（保留 `_load_quality_gates` + `_load_e2e_config`）|

> **职责裁剪结果**：
> - `lk keeper gate` 仍做 **跨 commit 语义检查**（commit 消息格式 / R-G-R 顺序 / AC trace / 反模式扫描），pre-commit 做不了。
> - `lk shield run-e2e` 仍做 **e2e 配置读取 + 调度**，pre-commit 与 keeper 都不替代。

## 2. 依赖关系

### 2.1 内 louke 模块依赖（调用方向）

```
lk scout foundation
  ├── (现) cmd_foundation → cmd_commit_foundation
  └── (新) cmd_foundation ──Step5──> cmd_install_precommit
                                          ├── 读 louke/templates/pre-commit/base.yaml + {language}.yaml
                                          ├── 写项目根 .pre-commit-config.yaml
                                          ├── 子进程: pre-commit install
                                          └── 写 project-info.md Pre-commit 字段

lk devon commit-rgr --phase {green | refactor}      # red 被拒
  └── 读 RGR_PREFIX[(label, phase)] → 生成 commit message → git commit (触发 pre-commit hook)

lk keeper gate (--lint | --typecheck | --tests)     # 三 flag 均报错 v0.7-001
  └── 校验: commit 消息格式 / R-G-R 顺序 / AC trace / 反模式扫描（不再调 lint/typecheck/test）

lk shield run-e2e                                    # 不变
  └── _load_quality_gates() + _load_e2e_config() + cmd_run_e2e 全保留

pre-commit hook 触发链 (用户项目内)
  git commit
    └── .git/hooks/pre-commit (由 pre-commit install 创建)
          └── 按 .pre-commit-config.yaml 的 repos[*] 跑:
                ├── trailing-whitespace / end-of-file-fixer / check-yaml / check-toml / check-merge-conflict / large-files  (base)
                ├── ruff check / ruff format --check / mypy                                                                 (python)
                ├── eslint / prettier --check / tsc --noEmit                                                                (node)
                ├── golangci-lint / gofmt / go test                                                                         (go)
                ├── cargo fmt --check / cargo clippy / cargo test                                                            (rust)
                └── spotless / checkstyle                                                                                   (java)
```

### 2.2 外部依赖

| 依赖                                  | 类型          | 用途                                              | 引入位置                                 |
| ------------------------------------- | ------------- | ------------------------------------------------- | ---------------------------------------- |
| `pre-commit`（Python 包）              | runtime dep   | 安装 hook + 触发时跑 lint/format/typecheck/test    | `pyproject.toml [project.dependencies]`  |
| `git`                                  | 运行时调用    | `git commit` 触发 hook；`git log` 给 keeper R-G-R  | 系统级（用户已装）                        |
| python `yaml` / `tomllib`              | stdlib/三方   | 在 scout.py 里读/合并模板                          | tomllib stdlib(Python 3.11+); yaml 三方  |
| 各社区 hook repo（remote git）          | pre-commit 资源 | 提供 ruff/mypy/eslint/golangci-lint 等 hook 实现   | 用户首次 `pre-commit install` 拉 ~/.cache |

### 2.3 本 spec 不改的依赖

- louke 自身运行时无新依赖（除 `pre-commit`）。louke 不直接调 ruff / mypy / eslint；这些由 pre-commit 在 install 时拉为隔离环境。

## 3. 技术选型

| 选择                  | 决定                                                            | 版本约束                 | 理由                                                                          |
| --------------------- | --------------------------------------------------------------- | ------------------------ | ----------------------------------------------------------------------------- |
| pre-commit 框架        | **采用** `pre-commit` Python 包                                 | `>= 3.0, < 5.0`          | 允许 3.x / 4.x，留主版本缓冲；hook repo 在主版本切换时可能破坏向后兼容（NFR-0020 spec 引用）|
| Linter / Formatter / Typecheck / Test | 全部走社区 hook repo（不 louke 自实现）                         | 锁定 tag（见 FR-0200）   | 零 token、语言生态原生、louke 不维护 N 套命令表（spec §0.2 否决 quality-gates.toml 理由 1）|
| base hooks            | `pre-commit/pre-commit-hooks`                                   | `v4.6.x`                 | 社区稳定基线 hook 集                                                          |
| Python hook repo       | `astral-sh/ruff-pre-commit` + `pre-commit/mirrors-mypy`         | ruff `v0.6.x` / mypy `v1.10.x` | 2026-07-05 时已知稳定 tag（spec FR-0200）                                     |
| Node hook repo         | `pre-commit/mirrors-eslint` + `pre-commit/mirrors-prettier`     | eslint `v9.x` / prettier `v3.3.x` | 同上                                                                          |
| Go hook repo           | `dominikh/pre-commit-golang` + 显式 `go-test` hook              | golangci-lint `v1.59.x`  | 同上                                                                          |
| Rust hooks（本地）     | 本地 `cargo fmt --check` / `cargo clippy` / `cargo test` hook   | —                        | Rust 生态普遍用本地命令而非远程 hook repo                                     |
| Java hook repo         | `pre-commit/mirrors-spotless` 或 checkstyle                     | —                        | spotless 在 Java 生态事实标准，checkstyle 可替代                              |
| {} language 探测策略   | 全量匹配非短路                                                  | —                        | 多语言项目同时装多个模板（spec §0.3）                                         |
| Slack 兼容性           | `qauality-gates.toml` loader 删除（keeper 端）                  | —                        | e2e 段读取归 shield 端 `_load_e2e_config()`，不重复造轮子                     |

## 4. 关键 trade-off

### 4.1 pre-commit 框架 vs 自实现 lint runner（`quality-gates.toml` 方案）

| 维度         | pre-commit（采用）                                                | quality-gates.toml + keeper loader（否决）                  |
| ------------ | ---------------------------------------------------------------- | --------------------------------------------------------- |
| Token 成本    | **0**（pre-commit 在 commit 进程内跑，无 LLM 调用）              | 0（同）                                                    |
| 语言命令维护  | 由社区 hook repo 维护，louke 只模板化                            | louke 维护 N 套 linter 命令表 + schema + loader            |
| 用户自定义   | 标准 `.pre-commit-config.yaml` 生态，社区文档成熟                | 用户需学 louke 私有 TOML schema                            |
| Schema 风险   | 无（pre-commit 框架标准 schema）                                 | 原 `/tmp/louke-design/quality-gates-design.md` 有未解问题（`paths` schema 与 keeper.py:166 不一致、漏迁 e2e loader、§6 风险表 `edit: deny` 事实错误） |
| 与 louke 集成 | louke 模板 + Scout Step 5 一键装                                  | keeper 实时读 TOML → 进程内执行子进程                      |
| 决策          | **采用** —— 零 token 优势相同，但生态/可维护性显著更好          | —                                                          |

### 4.2 R-G-R Red 阶段去 commit

| 维度            | Red 不 commit（采用）                                              | Red 仍 commit（保留）                                   |
| --------------- | ---------------------------------------------------------------- | ----------------------------------------------------- |
| Pre-commit test hook 可放进 pre-commit？ | **可以**——Green/Refactor 是含测试改动的仅有两类 commit，且测试必过 | **不可以**——Red commit 含失败测试，test hook 会拦死 Red commit |
| Git 历史整洁度    | 只有 `feat: green` / `fix: green` / `refactor` 三类 commit          | 含 `test: red` 噪音 commit                              |
| R-G-R 顺序检查简化 | refactor 不得先于 green（同 issue 内），legacy `test: red` 静默接受 | 需额外校验 `test: red` 前缀存在性                        |
| Breaking change  | `--phase red` 报错，老脚本需更新（spec NFR-0010 #1 已披露）         | 无 break                                               |
| 决策             | **采用** ——test hook 进 pre-commit 是 US-0200 的核心动机          | —                                                      |

### 4.3 `--no-verify` 检测机制

| 维度           | 三层兜底（采用）                                                  | git log 标记检查（否决）                              |
| -------------- | ---------------------------------------------------------------- | -------------------------------------------------- |
| 技术可行性      | (a) Devon prompt §8 反模式；(b) §6.2 禁令；(c) CI `pre-commit run --all-files` | **不成立** —— `git commit --no-verify` 与正常 commit 产生相同的 tree object，`git log` 区分不出 |
| 兜底完整度     | 三层覆盖：prompt 约束 → push 流程 → CI 全仓复查                    | 一层假想检测，技术上无法实现                          |
| 决策            | **采用** ——spec §FR-0500 Sage quote + Aaron resolved Aaron 同意  | 整段删除（spec FR-0500 已删）                          |

### 4.4 louke 自身 dogfood `.pre-commit-config.yaml`

| 维度            | dogfood（采用）                                                    | 不 dogfood                                                |
| --------------- | ---------------------------------------------------------------- | --------------------------------------------------------- |
| 模板漂移风险    | **低**——louke CI 跑 `pre-commit run --all-files`，模板有问题立即在 louke 仓库自身暴露 | **高**——模板与 louke 自身 lint 规则可能漂移                |
| 维护成本        | louke 仓库根多一份 `.pre-commit-config.yaml`                       | 仅模板目录                                                |
| 决策            | **采用** ——Aaron 已在 FR-0700 Sage quote 明确 dogfood                | —                                                          |

### 4.5 `quality-gates.toml` 处置边界

| 维度                | 方向 2（采用）                                                    | 方向 1 保留全部 / 方向 4 全删                            |
| ------------------- | ---------------------------------------------------------------- | ------------------------------------------------------- |
| keeper.py loader     | 删 `_load_quality_gates()` + `run_external_tool()` + `run_project_tests()`, 不再读 lint/typecheck/test 命令 | 全保留 = 与 spec §0.2 直接冲突；全删 = 需补 `quality-gates-e2e.toml` 或迁回 `pyproject.toml [tool.louke.test.e2e]`，扩大 spec 范围 |
| shield.py loader     | **保留** `_load_quality_gates()` + `_load_e2e_config()` + `cmd_run_e2e` (e2e 是 Shield 职责) | —                                                          |
| `quality-gates.toml` 文件本身 | 不引入 lint/typecheck/test 段；shield 的 [test.e2e] 由 shield 自己负责读写（文件若存在则 shield 读 e2e 段；不存在则用 shield 内默认）| — |
| 决策                 | **采用** ——Aaron Q1 resolved，spec §0.2 已据此重写                | —                                                          |

### 4.6 pre-commit performance soft vs hard cutoff

| 维度        | 软目标（采用）                                              | 硬指标（否决）                                          |
| ----------- | --------------------------------------------------------- | ---------------------------------------------------- |
| test hook ≤60s 触发超时 | 否——超出仅记录，Archer 可在 M-ARCH 把 test hook 拆到 CI-only | 是——超时 → commit 失败 → 阻塞 agent 工作流         |
| 兜底机制     | CI-only test hook 拆分作为 project-level 决策（不属 spec 强制） | 无                                                    |
| 决策         | **采用** ——Aaron FR-0300 Sage quote resolved               | —                                                     |

## 5. 风险与缓解

| 风险                                              | 缓解                                                                                                                  |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| 社区 hook repo 的 `rev` 在 louke 发版期间失效      | FR-0200 v0.7-001 锁定具体稳定 tag；v0.7+ 提供 `lk upgrade --precommit` 刷新（不在本 spec 范围）                          |
| 多语言项目语言探测冲突（pyproject + package 同时有）| §0.3：默认两者都装；冲突由 Archer 在 M-ARCH 编辑 `.pre-commit-config.yaml`                                              |
| pre-commit 4.x 主版本变更 hook schema 兼容性       | NFR-0020 约束 `< 5.0`；hook repo 主版本切换时由社区维持向后兼容（如破坏 → bump major 在 v0.7+ 跟进）                    |
| 存量项目 `[tool.louke.lint]` 配置不自动迁移         | NFR-0010 升级路径：手动迁移，louke 不提供自动迁移工具（字段差异大）；`louke/templates/pre-commit/README.md` 给最小迁移指南 |
| `.opencode/agents/devon.md` 部署产物漂移            | NFR-0010 #6：`agents/Devon.md` 是单一源；功能完成后跑 `lk board opencode` 刷新部署（本 spec 不直接改部署产物）         |

## 6. 与 interfaces.md 的对应

- 本 architecture.md 定义模块边界 + 依赖 + trade-off。
- `interfaces.md` 定义上述四类产物的**外部可观测契约**：CLI 签名 / 文件 schema / grep 出口 / prompt 文本出口。
- 两者闭合原则（Archer §8.3）：interfaces.md 定义的每个出口在 test-plan.md §6.5 与 §8 中都有测试断言。