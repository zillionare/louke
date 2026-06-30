# v0.6-008 — 验收标准 (acceptance.md)

- **Spec ID**: v0.6-008-louke-v030-usability-closure
- **创建日期**: 2026-06-30
- **关联 spec**: `./spec.md`

> **结构契约**（修复 GLM §18 标注 8）：本 acceptance.md 采用 `verify_acceptance.py:155` + `verify_acceptance.py:287` 期望的格式——`## FR-XXXX {title}` + `### AC-N` 连续编号（每个 FR 内从 1 开始）。实施者用 `lk lex verify-acceptance --spec-file spec.md --acceptance-file acceptance.md` 校验本文件结构合法。
>
> **跨 FR 引用**：spec.md prose 中以 `AC-FRXXXX-YY` 形式引用；本文件按 FR 分组，AC-N 是组内编号。两者等价（YY = N）。

---

## FR-0100 `lk init <bare-name>` 新建项目

### AC-1

- 在空目录 `mkdir test && cd test` 跑 `lk init my-proj` → `ls my-proj/.louke/` 含 `agents templates project wiki raw` 五项目录

### AC-2

- `ls my-proj/.louke/agents/*.md | wc -l` = 12（与 `$LOUKE_HOME/agents/*.md` 数量一致；不含 ROSTER.md —— 历史 commit `6cfc63d` 已将 ROSTER 合并到 Maestro.md）

### AC-3

- `ls my-proj/.louke/templates/*.md | wc -l` = 10（与 `$LOUKE_HOME/templates/*.md` 数量一致；当前含 acceptance / bug-fix / issues / prd / project-info / security-checklist / spec / task-log / task-plan / test-plan）

### AC-4

- `cat my-proj/.gitignore` 含 `.louke/agents/` 与 `.louke/templates/` 两行（去重）

### AC-5

- 在已存在 `my-proj/` 的目录二次跑 `lk init my-proj` → exit 1，stderr 含 `already exists`

### AC-6

- init 前在 `my-proj/` 下手工放 `README.md`（含任意内容）→ init 完成后 `my-proj/README.md` 字节级不变

### AC-7

- init 后 `my-proj/.github/ISSUE_TEMPLATE/feature.yml` 存在（FR-0110 触发）

### AC-8

- init 后 `my-proj/.opencode/agents/*.md` 存在 12 个（FR-0200 触发）

### AC-9

- 在既存 git 仓库（含 `.git/`）跑 `lk init ./newpath` 视为新项目名（创建 `newpath/` 子目录），不是 adopt 当前目录

- ---

## FR-0101 `lk init <existing-path>` adopt

### AC-1

- 存量项目（含 `src/`、`tests/`、自定义 `README.md`）跑 `lk init .` → 源码字节级不变 + 新建 `.louke/` 骨架 + 三档报告打印

### AC-2

- `lk init . --dry-run` 后 `git status` 字节级不变 + 报告打印 `[+]/[=]/[!]/[→]` 计划

### AC-3

- 制造 `.louke/agents/Maestro.md`（与 `$LOUKE_HOME/agents/Maestro.md` 字节不同）→ `lk init . --backup` 后该文件有对应 `.bak`（保留用户修改）

### AC-4

- 制造冲突 → `lk init . --force` 后 `.louke/agents/Maestro.md` 与 `$LOUKE_HOME/agents/Maestro.md` 字节同步

### AC-5

- `lk init . --json` 输出合法 JSON 字符串，`json.loads` 后含 `added`/`skipped`/`backed_up`/`migrated` 四键（均为数组）

### AC-6

- 在非 git 目录（含 `.louke/` 子目录但无 `.git/`）跑 `lk init .` → exit 2，stderr 含 `not a git repo`

### AC-7

- 同时存在 `wiki/` 与 `.louke/wiki/` → `lk init .` → exit 1，stderr 同时含 `wiki` 与 `.louke/wiki` 字样

### AC-8

- 既存仓库含 `wiki/`（空目录），跑 `lk init . --no-migrate` → 旧 `wiki/` 字节级不变，报告追加"未迁移"提示

### AC-9

- 既存仓库内跑 `lk init ./newpath` → 创建 `newpath/` 子目录（不是 adopt 当前目录）

### AC-10

- 既存仓库含 `.gitignore`（含自定义条目）→ `lk init . --no-gitignore` 后 `.gitignore` 字节级不变

### AC-11

- 已 init 项目二次跑 `lk init .` → 全部 `[=] skipped`，exit 0，幂等

- ---

## FR-0110 `.github/ISSUE_TEMPLATE/feature.yml` 安装（4 位 schema）

### AC-1

- init 后 `cat .github/ISSUE_TEMPLATE/feature.yml | head -30` 含 `fr_id`/`spec_url`/`acceptance_criteria` 三个 input id

### AC-2

- feature.yml 中 `regex: "^FR-\\d{4}$"`（4 位，不是 3 位）

### AC-3

- 用户定制过的 feature.yml（与 pip 包内字节不同）→ 第二次 init 不被默认覆盖（除非 `--force`）

### AC-4

- `lk init . --no-issue-template` → `.github/ISSUE_TEMPLATE/` 不创建

- ---

## FR-0120 `lk scout invite-owner`

### AC-1

- `lk scout invite-owner OWNER/REPO`（缺 `--version`）→ exit 1，stderr 含 `--version`

### AC-2

- `gh` 未认证（`GH_TOKEN` 空）→ exit 1，stderr 含 `gh 未认证`

### AC-3

- agent 名下找不到 title = `{repo}-{version}` 的 project → exit 1，stderr 含 project title 与 `gh project create` 提示

### AC-4

- GraphQL mutation 返回 403 / 错误 → exit 1，stderr 含 GraphQL 错误响应（截断到 200 字符）

### AC-5

- 成功 → stdout 含 `OWNER 已加入 project 'TITLE' 为 READER`

### AC-6

- `--dry-run` → 不实际调 mutation，但打印所有将执行的 gh 命令

- ---

## FR-0130 `lk upgrade`

### AC-1

- `lk upgrade --dry-run` → stdout 含 `pip install --upgrade louke` 字样；v0.3.0 仍为 v0.3.0（不实际执行）

### AC-2

- 非 dry-run（mock pip 缓存旧版 → 新版 wheel）→ 跑完后 `lk --version` 输出新版本号

### AC-3

- 模拟 pip 失败（mock subprocess 返回 exit 1）→ 透传 exit code，stderr 含 pip 错误输出

- ---

## FR-0200 `lk board <opencode|status>`

### AC-1

- init 后 `ls .opencode/agents/*.md | wc -l` = 12，每文件 `head -5` 含 `model:` 字段

### AC-2

- `sha256sum .opencode/agents/scout.md .louke/agents/Scout.md` 两个文件的 body 段（剥离 frontmatter）hash 相同

### AC-3

- `lk board opencode --dry-run` → `.opencode/agents/` 字节级不变 + stdout 打印 `[+] .opencode/agents/{name}.md`

### AC-4

- `lk board status` → exit 0，stdout 含 `opencode    ✓` 行 + `default_agent: maestro (project opencode.json)` 行

### AC-5

- init 后 `cat .gitignore` 含 `.opencode/agents/` 行

### AC-6

- `lk board vscode` → exit 1，stderr 含 `not supported`

### AC-7

- `lk board unknown-ide` → exit 1，stderr 含 `unknown`

### AC-8

- 设置 `~/.config/opencode/opencode.json` 后 init → 自动跑 board opencode

### AC-9

- `lk init . --board=none` → `.opencode/agents/` 不创建

- ---

## FR-0201 `lk models {list,doctor,bind,unbind}`

### AC-1

- `lk models list` → stdout 每行 `抽象名\t解析结果`；覆盖 source 全部 12 个 agent 的 models[0]

### AC-2

- mock `opencode models` 输出 `ark/kimi-k2.6\n` → `lk models doctor` 对 `kimi-k2.6` 打印 `✓ kimi-k2.6 -> ark/kimi-k2.6`

### AC-3

- mock 输出含 `ark/foo\n` 与 `opencode/foo\n` 两条同尾段 strong match → doctor 选 `ark/foo`（user provider 优先）

### AC-4

- `lk models bind foo bar/foo` → `cat ~/.louke/models.json` 含 `"foo": "bar/foo"`

### AC-5

- `lk models bind foo bar/foo --project` → `cat .louke/models.json` 含；项目级 alias 在用户级之前读

### AC-6

- `lk models unbind foo` → `~/.louke/models.json` 的 `foo` 键删除；项目级不动

### AC-7

- PATH 移除 `opencode` + alias map 未配 → `lk models doctor` exit 1，stderr 含 `opencode models`

### AC-8

- 弱匹配（抽象名是 model-id 子串）→ tty 下进编号选择；非 tty（CI）下 exit 1，stderr 含 `lk models bind`

### AC-9

- `lk models doctor --fix-auto` 把 strong match 写 `~/.louke/models.json`

### AC-10

- `~/.louke/models.json` 的 `$schema` = `louke://models-config`（不再是 `specforge://`）

- ---

## FR-0210 source agent frontmatter 校验

### AC-1

- 当前 12 个 agent 全部通过 `lk archer lint-frontmatter` exit 0

### AC-2

- 把 Maestro 的 `mode` 改成 `xxx`（非法值）→ lint exit 1，stderr 含 `mode`

### AC-3

- 删除任意 agent 的 `models` 字段 → lint exit 1，stderr 含 `models`

### AC-4

- `models: []`（空数组）→ lint exit 1，stderr 含 `non-empty`

### AC-5

- 把任意 agent 的 primary 改成 `gpt-5`（闭源，不在白名单）→ lint exit 1，stderr 含 `whitelist` 与 `gpt-5`

### AC-6

- 把任意 agent 的 primary 改成 `kimi-2.6`（在白名单）→ lint exit 0

### AC-7

- lint 报告展示每个 agent 的当前 primary（如 `Maestro: glm-5.2`），档位标注可作 hint 不阻断（**白名单是硬约束，档位仅展示**）

### AC-8

- lint 报告展示每个 agent 的 tier 标注（S/A/B），作为 hint 不阻断

- ---

## FR-0300 default_agent: maestro

### AC-1

- init 后 `cat <root>/opencode.json` = `{"default_agent": "maestro"}`

### AC-2

- `<root>/opencode.json` 已存在且 `default_agent = "build"` → 默认模式 exit 1，stderr 含 `default_agent` 与 `not overwrite`

### AC-3

- tty 下回答 Y 后 `cat ~/.config/opencode/opencode.json` 含 `default_agent: maestro`

### AC-4

- `lk init . --no-default-agent` → `<root>/opencode.json` 与 `~/.config/opencode/opencode.json` 字节级不变

### AC-5

- `lk board status` stdout 含 `default_agent: maestro (project opencode.json)` 或 `(set in global)` 或 `(not set)`

### AC-6

- `lk init . --force-default-agent` → 直接覆盖 `default_agent`，非交互

- ---

## FR-0400 `lk scout foundation` MVP

### AC-1

- 缺 `--repo` / `--version` / `--spec-id` 任一 → argparse 错误 exit 2

### AC-2

- 跑完后 `cat .louke/project/project-info.md` 含 FR-0800 全部 12 字段（Version / Repo / Project / Project ID / Spec ID / Release Branch / Smoke Test Issue / Smoke Test PR / DoD / Security Audit / Current Stage / Created）

### AC-3

- 跑完后 `.louke/project/specs/{spec-id}/story.md` 存在且非空

### AC-4

- mock `lk scout identity-check` 返回 exit 1 → 整体 exit 1，stderr 含 `identity`

### AC-5

- mock `lk warden foundation-check` 返回 exit 1 → 整体 exit 1，stderr 含 `foundation-check`

### AC-6

- `--no-commit` → 不调 commit-foundation，stdout 含 `commit skipped`

### AC-7

- `--dry-run` → 不写任何文件、不调任何子命令，stdout 打印计划

### AC-8

- 已 init 项目重跑 → 幂等（project-info.md / story.md 字节不变除非 `--force`）

- ---

## FR-0401 `lk scout foundation` 完整 P0

### AC-1

- mock `gh repo view` 显示 repo 已存在 → 跳过创建，stderr 含 `already exists`

### AC-2

- mock `gh project list` 显示 Project 已存在 → 跳过创建，复用

### AC-3

- mock invite-owner 失败 → 整体 exit 1，stderr 含 `invite-owner`

### AC-4

- mock 完整流程后，`project-info.md` 含 `Smoke Test Issue` 与 `Smoke Test PR` 两个字段

- ---

## FR-0402 `lk scout foundation` 创建/确保 per-repo backlog project

### AC-1

- 首次 `lk scout foundation` → 实际调 `gh project create` 创建 `my-proj-backlog`，project-info.md 含 `Backlog Project:` 字段（如 `Backlog Project: my-proj-backlog (#5)`）

### AC-2

- 二次 `lk scout foundation`（mock `gh project list` 返回已存在的 `my-proj-backlog`）→ 跳过创建，stdout 含 `reused my-proj-backlog`

### AC-3

- title 匹配严格（`my-proj-backlog-extra` 不算重复）

### AC-4

- backlog 创建失败（如 owner 无权限）→ warning 不阻断 foundation，stderr 含 `my-proj-backlog` 与 retry 提示

### AC-5

- owner 选择与 `my-proj-v0.6` Project 一致（同一字段 `Project ID` 解析得到）

### AC-6

- `--dry-run` 不实际调 `gh project create`，stdout 打印将创建的 title

- ---

## FR-0410 `lk sage create-issues`

### AC-1

- 构造 spec.md 含 0 个 FR 锚点 → exit 0，stdout `0 created, 0 skipped`

### AC-2

- 构造 spec.md 含 3 个 FR；mock `gh issue list` 返回 2 个已存在 → stdout `1 created, 2 skipped`

### AC-3

- mock gh 未认证 → exit 1，stderr 含 `gh 未认证`

### AC-4

- project-info.md 缺 Project URL + 默认模式 → exit 1，stderr 含 `Project URL`

### AC-5

- project-info.md 缺 Project URL + `--skip-project` → warning + 继续创建

### AC-6

- `--dry-run` → 不调 gh，stdout 打印会创建的 issue

### AC-7

- project-info.md 缺 Release Branch → exit 1，stderr 含 `Release Branch` + `scout foundation`

### AC-8

- body 模板 Spec 链接 branch = project-info.md 的 `Release Branch`（如 `releases/v0.6`）

- ---

## FR-0420 `lk sage record-lock`

### AC-1

- 三信号全过 + `--confirm` → spec.md 含 `locked: true`

### AC-2

- mock quote-check 失败 → spec.md 字节不变，exit 1 提示 `Sage signal`

### AC-3

- mock verify-acceptance 失败 → exit 1 列出 `Lex signal: verify-acceptance`

### AC-4

- 缺 `--confirm` → exit 1 提示 `User signal`

### AC-5

- 已 `locked: true` 的 spec 再 record-lock → exit 0，幂等

### AC-6

- 缺 `--spec` → argparse 错误

- ---

## FR-0430 `lk librarian from-raw`

### AC-1

- 无 raw entries → exit 0，stdout `Distilled 0 entries`

### AC-2

- 构造 1 resolved + 1 open raw → exit 0，stdout `Distilled 1 entries`，wiki 页生成

### AC-3

- 生成的 wiki 页 frontmatter 含 `date`/`title`/`type: experience`/`session`/`raw_ref`

### AC-4

- 跑两次幂等 → 第二次 raw 已含 `distilled-to` 字段，跳过

### AC-5

- `--since 2026-06-25` 只处理 6-25 之后的 raw

### AC-6

- 蒸馏后 `wiki/index.md` 含新页

- ---

## FR-0440 `lk librarian write`

### AC-1

- 写入后文件存在，frontmatter 含 `type`/`title`/`date`

### AC-2

- 写完后 `index.md` 含新页链接

### AC-3

- `--type xxx` → argparse 错误

### AC-4

- `page-relpath = ../../etc/passwd` → exit 1，stderr 含 `path traversal`

### AC-5

- `page-relpath = agents/Maestro.md`（不在 pages/ 下）→ exit 1

### AC-6

- 缺 `--type` → argparse 错误

- ---

## FR-0450 `resolve_spec_path`

### AC-1

- cwd 在 git root 子目录，`--spec specs/X/spec.md` 实际位于 git root → 找到并成功 check

### AC-2

- 路径 git root 也不存在 → exit ≠ 0，stderr 含原始 path + `git root: <root>`

### AC-3

- 非 git repo → 跳过 git root 回落，直接走原路径

### AC-4

- `lk lex verify-acceptance` 的 `--spec-file` + `--acceptance-file` 同 AC-1/2/3

- ---

## FR-0500 `lk --version` + 版本号单源同步

### AC-1

- `lk --version` 输出形如 `lk 0.3.0`（精确匹配 `^lk \d+\.\d+\.\d+$`）

### AC-2

- `lk -v` 同 AC-1

### AC-3

- `louke/__init__.py:__version__` 与 `pyproject.toml:project.version` 字节同步（运行 `tests/test_version_sync.bats`）

### AC-4

- `tests/test_version_sync.bats` 验证两处一致

- ---

## FR-0510 `pyproject.toml` package-data 扩充

### AC-1

- `pip install louke` 后 `importlib.resources.files('louke').joinpath('resources/.github/ISSUE_TEMPLATE/feature.yml').is_file()` = True

### AC-2

- 同上 `.github/workflows/louke-ci.yml` is_file() = True

### AC-3

- wheel (`dist/*.whl`) 用 `unzip -l` 看含 `louke/resources/.github/ISSUE_TEMPLATE/feature.yml` 路径

### AC-4

- sdist (`dist/*.tar.gz`) 用 `tar tzf` 看含同样路径

- ---

## FR-0520 项目级 `.github/workflows/louke-ci.yml` 自动安装

### AC-1

- init 后 `<root>/.github/workflows/louke-ci.yml` 存在

### AC-2

- `--no-workflows` 不创建该文件

### AC-3

- workflow 含 `workflow_dispatch` 入口 + spec_id input

### AC-4

- workflow 含循环 `for spec in .louke/project/specs/*/`（不依赖 sed 推断）

### AC-5

- `pip install louke` 后 `lk archer ci-scan` 可调用

- ---

## FR-0530 `lk scout commit-foundation` glob 修复

### AC-1

- `lk scout commit-foundation` 后 `git status` 不残留 untracked `*.md`

### AC-2

- `git log --name-only -1` 含 `specs/{id}/*.md` 文件名

### AC-3

- `*.md` glob 无匹配 → warning 但 exit 0

- ---

## FR-0540 `verify_acceptance.py` 默认 release 分支

### AC-1

- project-info.md 含 `Release Branch: releases/v0.6` → `lk lex verify-acceptance` 实际读 `releases/v0.6`（mock gh api 验证 query string 含 `ref=releases/v0.6`）

### AC-2

- project-info.md 缺 release branch → fallback `main` + stderr warning

### AC-3

- mock gh api 返回 200 → verify-acceptance 读到 spec/acceptance 内容

### AC-4

- `--branch releases/v0.5` 显式覆盖默认

- ---

## FR-0550 FR/AC 4 位 schema 全栈升级

### AC-1

- 12 个 `_tools/*.py` 引用 `louke.schema` 共享正则（grep 无重复 `\d{3}` 字面量）

### AC-2

- feature.yml `regex: "^FR-\\d{4}$"`

### AC-3

- README + README.zh 比较表行 `FR-XXXX / AC-FRXXXX-YY`

### AC-4

- 4 位 FR fixture spec.md 通过 verify-acceptance

- ---

## FR-0560 `lk archer ci-scan` 参数一致性

### AC-1

- `lk archer ci-scan --spec v0.6-008` 仍可用

### AC-2

- `lk archer ci-scan --acceptance .louke/.../acceptance.md --tests tests/` 也能用（template 示例方式）

### AC-3

- 同时给 `--spec` + `--acceptance` → argparse 错误

### AC-4

- `--json` 输出 `{"ac_total": N, "ac_referenced": M, "anti_patterns": [...], "passed": bool}` 是合法 JSON

- ---

## FR-0570 `lk devon run-tests` 项目配置化

### AC-1

- pyproject.toml `[tool.louke.test]` 不存在 → 用硬编码 fallback（pytest tests/unit/ 等）

### AC-2

- 配置 `command = "npm test"` → 跑 npm test 而非 pytest（mock subprocess 验证）

### AC-3

- `--scope unit` 按 paths.unit 配置定位测试目录

### AC-4

- 配置 `command = ""` → exit 1 actionable

- ---

## FR-0580 `lk devon commit-rgr` push + `--issue` + 可配置

### AC-1

- 默认跑完后 `git log -1` 含新 commit，`git status` 含 ahead 状态（未 push）

### AC-2

- `--push` 后 commit push 到 origin，`git status` 干净

### AC-3

- `--issue #42` → commit message 含 `Closes #42`

### AC-4

- 缺 `--phase` 或 `--message` → argparse 错误

- ---

## FR-0590 `lk keeper gate` 完整检查

### AC-1

- commit range 内 `feat: green` 在 `test: red` 之前 → exit 1，stderr 含 `R-G-R order`

### AC-2

- commit message 不符前缀 → exit 1

### AC-3

- ci-scan 失败（AC 未引用） → exit 1，列出未引用 AC

### AC-4

- lint 配置存在 → 跑 lint；失败 exit 1

### AC-5

- 全部通过 → exit 0

### AC-6

- `--tests` 跑项目配置的 test command，失败 exit 1

- ---

## FR-0600 `lk prism review` diff range 支持

### AC-1

- `lk prism review --diff HEAD~1..HEAD` 正确解析 range（mock get_diff_files 收到 `(HEAD~1, HEAD)`）

### AC-2

- `lk prism review --diff HEAD` 仍 work（旧行为）

### AC-3

- 同步到 test-patterns / security-quick-scan / code-quality

- ---

## FR-0610 `lk judge security-audit` 两阶段

### AC-1

- 默认 `lk judge security-audit` 跑阶段一 + 输出报告（JSON 写到 raw/）

### AC-2

- `--use-llm` 跑阶段二（缺模型 → exit 1 actionable）

### AC-3

- 报告含 `verdict` 字段

### AC-4

- blocker 存在 → exit 1

- ---

## FR-0620 `lk shield scaffold` 加 `--spec`

### AC-1

- `lk shield scaffold --type playwright --spec v0.6-008 --scenario login --ac-id AC-FR0100-01` 不崩，生成模板文件

### AC-2

- 缺 `--spec` → argparse 错误 `The following arguments are required: --spec`

- ---

## FR-0630 `lk shield run-e2e` 项目配置化

### AC-1

- 配置 `command = "behave"` → 跑 behave 而非 pytest

### AC-2

- `--browser firefox` 替换 `{browser}` 占位

### AC-3

- e2e 测试不通过 → exit 非零

- ---

## FR-0700 `lk maestro advance` 10 阶段 holdpoint 自动调用

### AC-1

- `lk maestro advance --stage M-FOUND` 调 `lk warden foundation-check` exit 0 → advance exit 0

### AC-2

- `lk maestro advance --stage M-LOCK` 缺 `--confirm`（或 signal 缺）→ exit 1

### AC-3

- 任意阶段失败 → advance exit 1 + 列出失败子命令

### AC-4

- 全部成功 → 调 FR-0710 更新 project-info.md

- ---

## FR-0710 `lk maestro advance` 成功后更新 project-info.md

### AC-1

- advance 成功后 project-info.md 含 `Current Stage: M-FOUND`（或对应阶段）

### AC-2

- raw 路径下生成 session 记录

### AC-3

- 下次 advance 读 `Current Stage` 推断前置阶段

- ---

## FR-0720 M-SECURITY 自动跳过判定

### AC-1

- `Security Audit: disabled` → advance exit 0，跳过 audit

### AC-2

- `Security Audit: enabled` → 调 `lk judge security-audit`

### AC-3

- audit verdict = `pass` → advance exit 0

### AC-4

- audit verdict = `fail` → advance exit 1

- ---

## FR-0730 M-MILESTONE 检查 Librarian + merge/tag

### AC-1

- mock `releases/v0.6` 已合 main + tag `v0.6` 存在 + raw 已 distill → advance exit 0

### AC-2

- 未合 main → exit 1，stderr 含 `merge releases/v0.6`

### AC-3

- 缺 tag → exit 1，stderr 含 `git tag v0.6`

- ---

## FR-0740 `lk lex verify-project` Issue↔Project 关联验证

### AC-1

- mock 全部 issue 已关联 Project → exit 0

### AC-2

- mock 2 个 issue 未关联 → exit 1，列出未关联编号

### AC-3

- project-info.md 缺 Project URL → exit 1 提示先跑 scout foundation

- ---

## FR-0800 `templates/project-info.md` 字段对齐 Scout.md

### AC-1

- `cat louke/templates/project-info.md` 含全部 12 字段

### AC-2

- `lk scout foundation`（FR-0400 MVP）跑完后 `cat .louke/project/project-info.md` 含 12 字段

### AC-3

- `lk warden foundation-check` 缺任一字段 → exit 1 列出缺失字段

- ---

## FR-0810 raw 路径统一

### AC-1

- `grep -RE 'raw/sources' louke/agents/ louke/*.py` 命中 0

### AC-2

- `librarian.py` 用 `raw_path()` 函数（grep `from ._common import raw_path`）

### AC-3

- 旧 `raw/sources/` 残留目录被迁移到 `raw/{date}/` 或删除

- ---

## FR-0820 raw / wiki 入 git 策略

> **状态: open**（Aaron 未拍板）—— 暂不修改 `.gitignore` 与 prompts 入库策略。

### AC-1

- README § "Project memory" 段含明确"raw/wiki 入 git, agents/templates 不入"声明（待 Aaron 拍板后实施）

### AC-2

- 生成的 `.gitignore` 不含 `.louke/raw/` / `.louke/wiki/`（待 Aaron 拍板后实施）

### AC-3

- 文档与 agent prompt 引用一致（待 Aaron 拍板后实施）

- ---

## FR-0830 Librarian 完整功能

### AC-1

- wiki 页缺 `date` 字段 → lint exit 1 列出

### AC-2

- `[[nonexistent]]` wikilink → lint warning

### AC-3

- rebuild-index 后 `index.md` 按 type 分组

### AC-4

- lint 后 `.cache/sha256.json` 含每页 hash

### AC-5

- `overview.md` 含每 type 摘要

### AC-6

- `log.md` 含今日 lint 事件

- ---

## FR-0900 README 文档修复

### AC-1

- `grep -E '"plugin".*louke|louke.*plugin' README*.md` 命中 0

### AC-2

- README § "Use in Your Project" 主体是 `lk init` / `lk init .`，不是 `lk scout foundation`

### AC-3

- README.zh 不含孤立行 `^s$`

### AC-4

- README.md:216 比较表行 `FR-XXXX / AC-FRXXXX-YY`

### AC-5

- README.zh:212 同样

### AC-6

- README 含 `lk --version` 用法说明

### AC-7

- README 含 `pip install --upgrade louke` 升级指引

### AC-8

- README 顶部 "Supported environments" 段保留

### AC-9

- "32 commands" 改为自动从 `lk --help` 取（脚本渲染或注释掉）

### AC-10

- README + README.zh 含新段 "Backlog project"（**仅面向终端用户**）：

- 何时创建（`lk scout foundation` 自动确保 `my-proj-backlog` Project 存在，dedup by title）
- 与 `{repo}-{version}` Project 区别（per-repo 永久 vs per-release 临时）
- 用法示例：`gh issue create --no-milestone` 落到 backlog；planning 时拉进 `{repo}-{version}`
- **不**提及任何 louke 内部项目（`specforge-backlog` 等）；本段只面向终端用户

### AC-11

- backlog 段位置：§ Architecture 之后、§ Use with Your AI Assistant 之前，作为独立 `###` 段

### AC-12

- README + README.zh 含 "Agent capabilities & model tiers" 表，5 列（Agent / Tier / Open-source example / Closed-source reference / 备注），覆盖全部 12 个 agent，档位标注 S/A/B

- ---

## NFR-0100 测试矩阵（GLM §15 端到端可用性测试）

### AC-1

- 10 项端到端测试全部存在（详见 spec.md NFR-0100 段；每个 AC 对应 bats 文件存在并通过）

### AC-2

- 新增 bats 文件覆盖所有 FR（详见 spec.md NFR-0100 表格；不回归既有 case）

- ---

## NFR-0200 错误信息 actionable

### AC-1

- 所有失败路径 stderr 含失败子命令/检查

### AC-2

- 所有失败路径 stderr 含用户下一步动作（grep stderr 含 `运行 ` / `检查 ` 等引导短语）

- ---

## NFR-0300 现有 bats 测试不回归

### AC-1

- `tests/test_*.bats` 现有所有 case 在本 spec 实施后继续通过

- ---

## NFR-0400 ADR 留痕

### AC-1

- `.louke/wiki/decisions/009-louke-v030-usability-closure.md` 存在，含背景/决策/备选/后果四段

### AC-2

- README § Architecture / Decision 表格追加 `[009]` 一行

- ---

## 实施顺序建议

P0-A：让 install→init→board→models 闭环
1. FR-0500 / FR-0510 / FR-0520（版本、package-data、CI 安装）
2. FR-0100 / FR-0101 / FR-0110（init/adopt/issue-template）
3. FR-0200 / FR-0201 / FR-0300（board/models/default_agent）
4. FR-0210（frontmatter 校验）

P0-B：让 M-FOUND/M-SPEC 跑
5. FR-0400 / FR-0530 / FR-0800（scout foundation MVP + glob + project-info 字段）
6. FR-0120（invite-owner）
7. FR-0410 / FR-0420（sage create-issues + record-lock）
8. FR-0540 / FR-0550 / FR-0740（verify-acceptance + 4 位 + verify-project）
9. FR-0450（resolve_spec_path）

P0-C：让开发 gate 可用
10. FR-0560 / FR-0570 / FR-0580（ci-scan 参数 / devon 配置 / push）
11. FR-0590 / FR-0620 / FR-0630（keeper / shield 修补）
12. FR-0600 / FR-0610（prism range / judge 两阶段）
13. FR-0700 / FR-0710 / FR-0720 / FR-0730（maestro 闭环）

P1：长期体验
14. FR-0130（upgrade P1）
15. FR-0401（scout foundation 完整 P0）
16. FR-0430 / FR-0440 / FR-0830（librarian 完整）
17. FR-0810 / FR-0820（raw 路径 + 入 git）

跨切：FR-0900 README 修复跟随每个 PR 顺手做。