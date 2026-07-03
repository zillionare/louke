# v0.6-008 — louke v0.3.0 可用性收口（usability closure）— Spec

- **Spec ID**: v0.6-008-louke-v030-usability-closure
- **创建日期**: 2026-06-30
- **状态**: 草稿（GLM 仓库审计 + 我的差异对照已收敛；待 GLM 实施）
- **关联**:
  - 释放的 draft 编号：v0.6-006-louke-init-and-board-commands、v0.6-007-stub-implementation（合并到本 spec）
  - 既有 spec：v0.3-003-init-adopt-mode、v0.5-005-namespace-cleanup、v0.5-007-multi-ide-boards、v0.5-008-test-quality-standards
  - 审计来源：`/tmp/louke-missing-spec.md`（GLM 仓库评估，345 行，§0–§18）
  - 关联 issue：#76（Maestro 入口）、#77（S/A/B 模型校准）

## 0. 范围与边界

**本 spec 收纳** 仓库审计出来的全部"v0.3.0 不可用"缺口，按主题分 9 节：

1. §1 项目初始化（init / adopt / issue-template / invite-owner / upgrade）
2. §2 IDE 板生成（board opencode / models alias / source frontmatter 校验）
3. §3 默认 agent（Maestro 为入口）
4. §4 Stub 命令真实实现（scout foundation / sage create-issues / sage lock-spec / librarian from-raw & write / resolve_spec_path）
5. §5 工具链收口（lk --version / package-data / glob 修复 / verify-acceptance 分支 / FR-schema 4 位升级 / ci-scan 参数 / 测试命令可配置 / keeper gate 全检 / shield scaffold --spec / 等）
6. §6 Maestro 流程闭环（10 阶段 holdpoint 自动调用 / state 更新 / M-SECURITY 跳过判定 / M-MILESTONE merge&tag / Lex Project 验证）
7. §7 项目信息模板与 Librarian（project-info.md 字段对齐 / raw 路径统一 / 入 git 策略 / Librarian 完整功能）
8. §8 README 与文档一致性
9. §9 非功能需求与测试矩阵

**本 spec 不收纳**：
- v0.6-005 命名重构（独立 spec 进行中）
- 模型档位 S/A/B/C 校准细节（issue #77 backlog）
- 既有 v0.5-008 测试质量标准的具体 lint 规则（保持独立演进）

## 1. 用户故事（按主题聚类）

### US-0100 项目奠基
- US-0100: 作为 louke 新用户，我希望 `lk init my-proj` 一次铺好项目骨架（agents / templates / wiki / raw / issue template / OpenCode 板 / default_agent），以便开箱即用
- US-0110: 作为存量项目维护者，我希望 `lk init . --dry-run` 预览改动、`--backup` / `--force` 保护/覆盖我的定制、`--json` 给脚本消费，以便非破坏接入
- US-0120: 作为 Scout agent，我希望 `lk scout invite-owner <o/r> --version V` 把 repo owner 加入 Project READER，以便 M-FOUND Step 6 收尾
- US-0130: 作为 louke 用户，我希望 `pip install --upgrade louke` 是默认升级路径（CLI `lk upgrade` 作为便捷包装）

### US-0200 IDE 集成
- US-0200: 作为 OpenCode 用户，我希望装完 louke 后 `/agents` 列表看到全部 12 个 agent（每个带正确 `model:` 字段），以便 IDE 内驱动流水线
- US-0210: 作为 louke 用户，我希望 agent prompt 里写的抽象模型名（`kimi-k2.6` / `glm-5.2`）在 init 时自动绑定到本机 OpenCode 已配置的 `provider/model`，weak match 走交互，no match 给 bind 提示
- US-0220: 作为 louke 维护者，我希望 source agent frontmatter 与档位表一致（mode + models），board 工具可直接解析

### US-0300 入口
- US-0300: 作为 OpenCode 用户，我希望 `lk init` 后新会话的入口 agent 默认是 Maestro，不需要每次手动 `<leader>a` 切换

### US-0400 Stub 命令真实化
- US-0400: 作为 Scout agent，我希望 `lk scout foundation --repo OWNER/REPO --version V --spec-id ID` 走完 8 步奠基（写 project-info / story / 调 identity / warden / commit），不要再被占位挡住
- US-0410: 作为 Sage agent，我希望 `lk sage create-issues --spec ID` 把 spec 里所有 `FR-XXXX` 转成 GitHub issue（去重 + Project 关联），不再手写 12 个 `gh issue create`
- US-0420: 作为 Sage agent，我希望 `lk sage record-lock --spec ID` 在三信号齐后记录 `locked: true`（结果记录器，不可替代三信号判定）
- US-0430: 作为 Librarian agent，我希望 `lk librarian from-raw` 把 `status=resolved` raw 实际蒸馏到 wiki pages（幂等）
- US-0440: 作为 Librarian agent，我希望 `lk librarian write <page>` 写入 wiki 页（防 path traversal，写后 rebuild-index）
- US-0450: 作为 agent，我希望在子目录跑 `lk sage quote-check --spec specs/X/spec.md` 时，若 git root 下能找到，自动用 git root 路径

### US-0500 工具链收口
- US-0500: 作为安装者，我希望 `lk --version` 真实返回版本号（不再 `?`）
- US-0510: 作为维护者，我希望 pyproject 版本号与 louke/__init__.py 单源同步
- US-0520: 作为用户，我希望 `pip install louke` 后 `lk init` 能找到 issue template / workflows（package-data 完整）
- US-0530: 作为用户，我希望 `lk scout commit-foundation` 真的把 specs/{id}/*.md 加进去（glob 正确展开）
- US-0540: 作为 Lex agent，我希望 `lk lex verify-acceptance` 默认读当前 release 分支（不是 main）
- US-0550: 作为 agent，我希望 FR/AC 编号在 spec.md / acceptance.md / issue template / 校验工具里统一为 4 位
- US-0560: 作为多语言项目用户，我希望 `lk archer ci-scan` / `lk devon run-tests` / `lk keeper gate --tests` 不硬编码 pytest，能读项目配置
- US-0570: 作为 Devon agent，我希望 `lk devon commit-rgr --issue #N` 把 `Closes #N` 写进 commit，并能 push
- US-0580: 作为 Keeper agent，我希望 `lk keeper gate` 不只查 commit prefix，还验证 R-G-R 顺序、测试先于实现、lint / typecheck / AC trace / 反模式完整集合
- US-0590: 作为 Prism agent，我希望 `lk prism review --diff HEAD~1..HEAD` 正确解析 range（不把 range 当 ref）
- US-0600: 作为 Judge agent，我希望 `lk judge security-audit` 是两阶段：pattern scan + agent 语义审查，输出机器可读报告供 Maestro 判定
- US-0610: 作为 Shield agent，我希望 `lk shield scaffold --type playwright --spec ID --scenario X` 不崩（--spec 已注册）

### US-0700 Maestro 闭环
- US-0700: 作为 Maestro agent，我希望 `lk maestro advance --stage M-TESTPLAN` / `M-ARCH` 等 10 个阶段各自自动调用对应 holdpoint（不再打印 `[todo]`）
- US-0710: 作为用户，我希望 advance 成功后 `project-info.md` 的 stage 字段被更新（不只打印）
- US-0720: 作为用户，我希望 M-SECURITY 根据 DoD 的 `Security Audit` 字段自动 skip 或调 judge
- US-0730: 作为用户，我希望 M-MILESTONE 检查 Librarian 输出 + release merge + tag
- US-0740: 作为 Lex agent，我希望 `lk lex verify-project`（或 `verify-issue` 阶段二增强）验证 issue 与 Project 的关联

### US-0800 项目信息 / Librarian
- US-0800: 作为用户，我希望 `templates/project-info.md` 字段与 Scout.md Step 6 一致（Version / Repo / Project / Project ID / Spec ID / Release Branch / Smoke Test Issue / DoD / Security Audit / Created）
- US-0810: 作为用户，我希望 raw 路径在所有 agent prompt 里统一为 `.louke/raw/{date}/{session-id}.md`（去掉 Librarian.md 的 `.louke/raw/sources/`）
- US-0820: 作为用户，我希望 raw / wiki 是否进 git 在 README 与 .gitignore 中明确定稿
- US-0830: 作为 Librarian agent，我希望 librarian 命令支持 frontmatter type/title/date 校验、broken link 检测、orphan page 检测、duplicate detect、incremental cache、overview/log 更新

### US-0900 文档
- US-0900: 作为新用户，我希望 README 不再误述 `lk scout foundation`（实际是占位）、不再写 `{"plugin": ["louke"]}`（实际不存在）、不再用 3 位 FR 示例

## 2. 关键场景

### scenario-0100 空目录 init
```
$ mkdir my-proj && cd my-proj
$ lk init .
  mkdir .louke/{agents,templates,project,wiki/pages,wiki/decisions,raw/sources}
  cp 12 agents → .louke/agents/
  cp 7 templates → .louke/templates/
  write .gitignore (.louke/agents/, .louke/templates/；去重)
  detect OpenCode → 跑 board opencode (生成 .opencode/agents/*.md)
  models doctor --fix-auto → 写 ~/.louke/models.json 缓存
  write <root>/opencode.json {"default_agent": "maestro"}
  prompt: "写入全局 ~/.config/opencode/opencode.json? (Y/n)"
  install .github/ISSUE_TEMPLATE/feature.yml (4 位 schema)
  report: opencode ✓, default_agent: maestro (project), 12 agents

$ lk board status
  opencode    ✓  (.opencode/agents/ — 12 agents, default model: ark/kimi-k2.6)
  default_agent: maestro (project opencode.json)
```

### scenario-0110 既存项目 adopt
```
$ cd ~/work/my-existing-repo
$ lk init . --dry-run
  [+] .louke/agents/{12}.md
  [+] .louke/templates/{7}.md
  [→] (none; 无旧 wiki/raw)
  [+] .opencode/agents/{12}.md
  [+] opencode.json (default_agent)
  [+] .github/ISSUE_TEMPLATE/feature.yml
$ lk init .       # 实际执行
  12 added, 0 skipped, 0 backed, 0 migrated
$ git status      # 看到一批 [+] 文件
```

### scenario-0200 抽象模型自动绑定
```
$ lk init .
  ...
  source model: kimi-k2.6
  Found candidates from `opencode models`:
    [1] ark/kimi-k2.6        (strong, user provider)
    [2] opencode/kimi-k2.6   (strong, opencode subscription)
  Choose [1]:
  Wrote ~/.louke/models.json: kimi-k2.6 → ark/kimi-k2.6
  ✓ 全部 agent 已绑定
```

### scenario-0400 Scout foundation MVP
```
$ lk scout foundation \
    --repo zillionare/my-proj --version v0.6 --spec-id v0.6-008-closure \
    --story '...' --dod 'unit ≥95% + e2e pass'
  → 写 .louke/project/project-info.md（12 字段）
  → 写 .louke/project/specs/v0.6-008-closure/story.md
  → 调 lk scout identity-check --repo zillionare/my-proj
  → 调 lk warden foundation-check --repo ... --version v0.6 --spec-id ...
  → 调 lk scout commit-foundation --spec-id ... --message 'story/prd: ...' --version v0.6
  → 输出 [项目奠基完成] 块
```

### scenario-0420 lock-spec 三信号
```
# Sage: 1) quote-check 通过; 2) 用户在 IDE 内确认; 3) Lex 三阶段通过
$ lk sage record-lock --spec v0.6-008-closure
  → 校验 3 信号: quote_check_ok=True, lex_3stage_ok=True, user_confirmed=True
  → 全部 True → 写 frontmatter locked: true, commit+push
  → 任一 False → exit 1，列出缺失信号
```

### scenario-0700 Maestro advance
```
$ lk maestro advance --stage M-TESTPLAN
  → check lk archer validate-test-plan --spec ...
  → check lk sage review --spec ...   (rule-based 默认, --use-llm 可选)
  → 全部 exit 0 → 更新 project-info.md current_stage: M-TESTPLAN
  → 输出 "[阶段: M-TESTPLAN] Archer + Sage 完成 → 通过"
```

---

## 3. 功能需求 — §1 项目初始化

> **元数据列**: 有效需求 ✅/❌ | 可测性 ✅/⚠️ {原因} | 是否已决定 ✅/⚠️/❌

---

<a id="fr-0100"></a>
### FR-0100 `lk init <bare-name>` 新建项目

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**实现要点**（继承 v0.3-003 FR-015 向后兼容 + v0.5-005 路径收归到 `.louke/`）：

1. 判定 `argv[0]` 是否既存路径：`.`、`./`、`../`、`/abs` 或 `~/...` 且 target 是已存在目录 → 走 FR-0101 adopt；**否则视为新项目名**。**例外**：`./newpath` 在既存仓库下仍视为新项目名（AC-FR0100-09）
2. `<name>/` 已存在且非空 → exit 1，stderr 含 `Directory '<name>' already exists`
3. `mkdir -p <name>/.louke/{agents,templates,project,wiki/pages,wiki/decisions,raw/sources}`
4. 从 `$LOUKE_HOME/agents/`（即 `importlib.util.find_spec('louke').origin` 的父目录）拷贝所有 `*.md` 到 `<name>/.louke/agents/`（当前含 12 个 agent prompt；不含 ROSTER.md —— 历史 commit `6cfc63d` 已将 ROSTER 合并到 Maestro.md）
5. 从 `$LOUKE_HOME/templates/` 拷贝所有 `*.md` 到 `<name>/.louke/templates/`
6. 写 `<name>/.gitignore`：文件不存在 → 新建含 `.louke/agents/\n.louke/templates/\n`；存在 → `grep -qxF` 去重，append（前补空行）
7. 调 FR-0110 (issue template 安装)
8. 调 FR-0200 / FR-0201 / FR-0300 (board / models / default_agent)
9. 打印 onboarding：路径、agents/templates 计数、wiki/raw 路径、IDE 板状态、default_agent 状态、下一步

**AC**

- AC-FR0100-01: `lk init my-proj` 后 `ls my-proj/.louke/` 含 `agents templates project wiki raw` 五项
- AC-FR0100-02: `ls my-proj/.louke/agents/*.md | wc -l` = 12（与 `$LOUKE_HOME/agents/*.md` 数量一致；不含 ROSTER.md —— 历史 commit `6cfc63d` 已将 ROSTER 合并到 Maestro.md）
- AC-FR0100-03: `ls my-proj/.louke/templates/*.md | wc -l` = 10（与 `$LOUKE_HOME/templates/*.md` 数量一致；当前含 acceptance / bug-fix / issues / prd / project-info / security-checklist / spec / task-log / task-plan / test-plan）
- AC-FR0100-04: `cat my-proj/.gitignore` 含 `.louke/agents/` 与 `.louke/templates/`
- AC-FR0100-05: 第二次跑 `lk init my-proj` → exit 1，stderr 含 `already exists`
- AC-FR0100-06: init 前在 `<name>/` 下手工放的 `README.md` 字节级不变
- AC-FR0100-07: init 后 `<name>/.github/ISSUE_TEMPLATE/feature.yml` 存在
- AC-FR0100-08: init 后 `<name>/.opencode/agents/*.md` 存在 12 个
- AC-FR0100-09: 在既存仓库跑 `lk init ./newpath` 视为新项目名（不走 adopt）

---

<a id="fr-0101"></a>
### FR-0101 `lk init <existing-path>` 既存项目 adopt

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**实现要点**：

1. 解析 target 为绝对路径；**要求是 git repo** → 否则 exit 2（区分于一般错误的 exit 1）
2. `cd $TARGET`
3. **旧路径迁移**（继承 v0.5-005 FR-030，路径改为 `.louke/`）：若存在 `wiki/` 且无 `.louke/wiki/` → `git mv`（若跟踪）/ `mv`（若未跟踪）；`raw/` 同理。**冲突**（新旧并存）→ exit 1，stderr 同时含新旧路径名
4. **create-if-missing**：对 `.louke/{agents,templates,project,wiki/pages,wiki/decisions,raw/sources}/` 七项，只 `mkdir -p` 缺失的
5. **文件冲突处理**（继承 v0.3-003 FR-011）：
   - target 不存在 → cp 计入 `[+]` added
   - 字节相同 → 静默 skip 计入 `[=]` skipped
   - 不同 + `--force` → cp 计入 `[=]` overwritten
   - 不同 + `--backup` → `cp $dest $dest.bak` 计入 `[!]` backed
   - 不同 + 默认 → warn + skip 计入 `[=]` skipped
6. 调 FR-0200 / FR-0201 / FR-0300
7. 调 FR-0110
8. **`.gitignore` 追加**：`.louke/agents/` 与 `.louke/templates/` 两条，去重；`--no-gitignore` 跳过
9. **报告**：默认四档 `[+]/[=]/[!]/[→]`；`--json` 输出 `{added:[], skipped:[], backed_up:[], migrated:[]}`

**flags**: `--dry-run` / `--backup` / `--force` / `--no-gitignore` / `--no-migrate` / `--board=<opencode|none>` / `--with-issue-template` / `--no-issue-template` / `--no-default-agent` / `--json`

**exit code**: 0=成功（含 dry-run），1=一般错误，2=非 git repo

**AC**

- AC-FR0101-01: 存量项目（含 src/、tests/）跑 `lk init .` → 源码字节级不变 + 新建 `.louke/` 骨架 + 报告
- AC-FR0101-02: `lk init . --dry-run` 后 working tree 字节级不变 + 报告打印计划
- AC-FR0101-03: `lk init . --backup` 后每个被 skip 的 `*.md` 都有对应 `.bak`
- AC-FR0101-04: `lk init . --force` 后 `.louke/agents/*.md` 与 `$LOUKE_HOME/agents/*.md` 字节同步
- AC-FR0101-05: `lk init . --json` 输出合法 JSON，含 `added`/`skipped`/`backed_up`/`migrated` 四键
- AC-FR0101-06: 非 git repo → exit 2，stderr 含 `not a git repo`
- AC-FR0101-07: 旧路径 `wiki/` + 新路径 `.louke/wiki/` 都存在 → exit 1，stderr 同时含两者
- AC-FR0101-08: `lk init . --no-migrate` 不动旧路径，报告追加"未迁移"提示
- AC-FR0101-09: 既存仓库内 `lk init ./newpath` 视为新项目名（不走 adopt）
- AC-FR0101-10: `lk init . --no-gitignore` 后 `.gitignore` 字节级不变
- AC-FR0101-11: `lk init .` 二次跑（项目已 init 过）→ 全部 skipped，idempotent

---

<a id="fr-0110"></a>
### FR-0110 `.github/ISSUE_TEMPLATE/feature.yml` 安装（4 位 schema）

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**实现要点**：

1. `lk init` 默认从 `$LOUKE_HOME/.github/ISSUE_TEMPLATE/feature.yml` 拷贝到 `<target>/.github/ISSUE_TEMPLATE/feature.yml`
2. **feature.yml 升级为 4 位 FR schema**（修复 GLM B1.6）：regex `^FR-\d{4}$`，placeholder `FR-0001`，spec_url fragment 同样改为 `fr-0001`
3. 冲突策略同 FR-0101 step 5
4. `--no-issue-template` flag 关闭；默认 on

**AC**

- AC-FR0110-01: init 后 `.github/ISSUE_TEMPLATE/feature.yml` 含 `fr_id`/`spec_url`/`acceptance_criteria` 三 id
- AC-FR0110-02: feature.yml 内 `regex: "^FR-\\d{4}$"`（不是 3 位）
- AC-FR0110-03: 用户定制过的 feature.yml 在第二次 init 不被默认覆盖
- AC-FR0110-04: `lk init . --no-issue-template` 后 `.github/ISSUE_TEMPLATE/` 不创建

---

<a id="fr-0120"></a>
### FR-0120 `lk scout invite-owner <owner/repo> --version V`

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**命名空间归属**：本命令归 Scout（**不是**顶层 `lk invite-owner`），与 Scout.md Step 6 "确保人类 owner 拥有 project 访问权" 直接对齐。

**实现要点**：

1. 校验 `--version V` 必填
2. 拿 `gh api user -q .login` 得 agent 身份
3. `gh project list --owner $GH_USER --format json` 找 title = `{repo-basename}-{version}` 的 project id
4. `gh api graphql` 查 repo owner userId（query: `user(login:"OWNER"){id}`）
5. GraphQL `updateProjectV2Collaborators` mutation 把 owner 加入为 READER
6. 任一失败（gh 未认证 / project 不存在 / GraphQL 403 / owner 已是 collaborator）→ exit 1，**actionable stderr**

**flag**: `--dry-run` 打印会做什么不实际调 mutation

**`lk init` 行为**：**不**自动调 invite-owner（避免 init 阶段强制 gh auth）

**AC**

- AC-FR0120-01: 缺 `--version` → exit 1，stderr 含 `--version`
- AC-FR0120-02: `gh` 未认证 → exit 1，stderr 含 `gh 未认证`
- AC-FR0120-03: project 未在 agent 名下找到 → exit 1，stderr 含 project title + 创建命令提示
- AC-FR0120-04: GraphQL mutation 失败 → exit 1，stderr 含 GraphQL 错误响应
- AC-FR0120-05: 成功 → stdout 含 `${OWNER} 已加入 project '${TITLE}' 为 READER`
- AC-FR0120-06: `--dry-run` 不实际调 mutation 但打印所有将执行的命令

---

<a id="fr-0130"></a>
### FR-0130 `lk upgrade` — pip 包装（P1）

| 有效需求 | 可测性 | 是否已决定                  |
| -------- | ------ | --------------------------- |
| ✅        | ✅      | ⚠️ GLM 提议 P1，本 spec 接受 |

**优先级**：P1（在 §1 完成 + §5 B1.1/B1.2 落地后再实现）。PyPI 包模型下，`pip install --upgrade louke` 是 native 路径，CLI 仅作便捷。

**实现要点**：

1. 解析 louke 安装位置：从 `sys.argv[0]` 软链追溯到 venv 内 `lk` → `dirname` 得 venv 路径
2. 在该 venv 内 `subprocess` 调 `pip install --upgrade louke`
3. 退出码透传
4. flag：`--dry-run`（只打印将执行的 pip 命令）、`--pre`（允许预发布）、`--reinstall`（等价 `--upgrade --force-reinstall`）

**AC**

- AC-FR0130-01: `lk upgrade --dry-run` stdout 含 `pip install --upgrade louke` 字样，不实际执行
- AC-FR0130-02: 非 dry-run 跑完后 `lk --version` 输出新版本号
- AC-FR0130-03: pip 失败（无网络 / PyPI 403）→ 透传 exit code，stderr 含 pip 错误

---

## 4. 功能需求 — §2 IDE 集成

---

<a id="fr-0200"></a>
### FR-0200 `lk board <opencode|status>` OpenCode 板生成

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

> ⚠️ **SUPERSEDED by v0.6-009 FR-0060.2** (2026-07-03): 本 FR 隐含的"`/agents` 列表看到全部 12 个 agent"行为在 v0.6-009 之后被修订 —— TUI 顶层 `<Leader>a` 列表**只**显示 Maestro (mode: primary), 其余 11 个 agent 改 `mode: subagent`, 只能通过 Maestro 的 `task` 工具调用。详见 v0.6-009 spec §0.2 受影响下游段落。

**立场**：README 已声明 "OpenCode only (currently)"；**不再实现** `lk board vscode`（与 v0.5-007 NFR-010 历史兼容放 P1，未来按需开新 FR）。`lk board vscode` 调用应 exit 1。

**实现要点**：

1. **frontmatter 解析器**：复用 `tools/specforge_board.py:90-110` 已实现的 YAML-like 解析（不支持完整 YAML，但 `key: value` 与 `key:\n  - item` 形式够用）
2. **`lk board opencode`**：
   - 源目录优先 `.louke/agents/`，fallback `agents/`（specforge 自身仓 dev 模式）
   - 跳过 `README.md`、`ROSTER.md`
   - 对每个 agent：解析 frontmatter 取 `name`/`description`/`mode`/`models`
   - 在 `.opencode/agents/{lowercase-name}.md` 生成：
     ```yaml
     ---
     description: <copied>
     mode: <copied or 'all'>
     model: <models[0] 经 FR-0201 解析得到的 full name>
     ---
     <body copied>
     ```
   - **不**生成 `models:` 数组（OpenCode 原生不识别）
   - `.gitignore` 追加 `.opencode/agents/`（去重）
3. **`lk board status`** 输出：
   ```
   opencode    ✓  (.opencode/agents/ — 12 agents, default model: ark/kimi-k2.6)
   default_agent: maestro (project opencode.json)
   ```
   - 判定：目录存在 + ≥1 文件 + frontmatter 含 `model:`
   - `default_agent:` 三态：(project opencode.json) / (global opencode.json) / (not set)
4. **`lk init` 自动探测**：`.opencode/` 或 `~/.config/opencode/opencode.json` 存在 → 跑 board opencode；都没有 → 不装
5. `--board=opencode` 强制装；`--board=none` 不装
6. **幂等**：重跑无副作用（覆盖源名单内的；用户手写的其它 `.opencode/agents/*.md` 不动）

**AC**

- AC-FR0200-01: init 后 `.opencode/agents/{12}.md` 存在，每文件 frontmatter 含 `model:`
- AC-FR0200-02: `.opencode/agents/scout.md` body sha256 = `.louke/agents/Scout.md` sha256
- AC-FR0200-03: `lk board opencode --dry-run` 后 working tree 不变
- AC-FR0200-04: `lk board status` exit 0，stdout 含 `✓/-` 与 `default_agent:` 行
- AC-FR0200-05: init 后 `.gitignore` 含 `.opencode/agents/`（如装了 opencode 板）
- AC-FR0200-06: `lk board vscode` → exit 1，stderr 含 `not supported`
- AC-FR0200-07: `lk board unknown-ide` → exit 1
- AC-FR0200-08: init 自动探测 `~/.config/opencode/opencode.json` → 装 opencode 板
- AC-FR0200-09: init `--board=none` 跳过自动探测

---

<a id="fr-0201"></a>
### FR-0201 `lk models {list,doctor,bind,unbind}` 抽象模型解析

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**实现要点**：

1. **配置 schema URL 修正**（修复 GLM B1.7 + 我的 A2）：从历史 `specforge://models-alias` 改为 `louke://models-config`（统一 louke 命名）
2. **schema 形态**：
   ```json
   {
     "$schema": "louke://models-config",
     "version": 1,
     "aliases": { "kimi-k2.6": "ark/kimi-k2.6" }
   }
   ```
3. **三层优先级**（继承 v0.5-007 FR-080）：
   1. 项目级 `<root>/.louke/models.json`
   2. 用户级 `~/.louke/models.json`
   3. `opencode models 2>/dev/null` 自动发现
4. **强匹配算法**：`normalize = re.sub(r'[^a-z0-9]+', '', value.lower())`；抽象名与 model-id 末段完全相等 → strong match
5. **多 strong match 优先级**：非 `opencode/` 前缀 provider 优先；`opencode/` 次之；并列取字典序最小 + warning
6. **弱匹配**（包含关系）：tty 走编号选择；非 tty fail
7. **子命令**：
   - `lk models list` — 列出 source 全部抽象名 + 解析结果（`{alias}\t{resolved}`）
   - `lk models doctor [--fix-auto] [--ide=<ide>]` — 跑自动发现；`--fix-auto` 把 strong match 写 `~/.louke/models.json`
   - `lk models bind <abstract> <full> [--project]` — 写用户级 / 项目级 alias
   - `lk models unbind <abstract> [--project]` — 删对应键
8. **`opencode models` 缺失**：退化只查 1+2；无命中 → exit 1 提示 `opencode models` 不可用
9. **环境变量 override**：`LOUKE_MODELS_CONFIG` / `LOUKE_PROJECT_MODELS_CONFIG`（与 v0.5-007 一致）
10. **`lk init` 集成**：board 生成前自动 `lk models doctor --ide=opencode --fix-auto`；仅 weak/no match 时进交互

**AC**

- AC-FR0201-01: `lk models list` 输出含 source 全部抽象名，第二列是解析后全名或 `-`
- AC-FR0201-02: `opencode models` 输出含 `ark/kimi-k2.6` → doctor 打印 ✓ `ark/kimi-k2.6`
- AC-FR0201-03: 多个 strong match 时，非 `opencode/` provider 优先
- AC-FR0201-04: `lk models bind foo bar/foo` → `~/.louke/models.json` 含 `"foo": "bar/foo"`
- AC-FR0201-05: `lk models bind foo bar/foo --project` → `<root>/.louke/models.json` 含；项目级优先于用户级
- AC-FR0201-06: `lk models unbind foo` 删用户级键（不动项目级）
- AC-FR0201-07: `opencode models` 不存在 + alias map 未配 → doctor exit 1，stderr 含 `opencode models`
- AC-FR0201-08: 弱匹配 tty 下进交互；非 tty exit 1 提示 `lk models bind`
- AC-FR0201-09: `--fix-auto` 把 strong match 写 `~/.louke/models.json`
- AC-FR0201-10: 配置 schema `$schema` = `louke://models-config`（不再是 `specforge://`）

---

<a id="fr-0210"></a>
### FR-0210 source agent frontmatter 校验（不是新增）

| 有效需求 | 可测性 | 是否已决定 |
| --- | --- | --- |
| ✅ | ✅ | ✅ |

**事实修正**（修复我的 A1）：当前 12 个 `louke/agents/*.md` **已**含 `mode: all` + `models:` frontmatter。本 FR 是**校验 + 规范化**，不是新增。

**开源模型政策**（Aaron 2026-06-30 拍板）：

**只使用 8 个开源模型**，按 3 档分配：

| 档 | 模型 | 说明 |
| --- | --- | --- |
| **S**（强） | `glm-5.2`, `minimax-m3` | 高质量、强推理 |
| **A**（中） | `kimi-2.6`, `kimi-2.7`, `deepseek-v4-pro` | 性价比主力 |
| **B**（轻） | `deepseek-v4-flash`, `glm-5` | 简单任务、低成本 |

**档位 → agent 映射**（v0.6-008 落地，**按任务复杂度分级**）：

| 档 | agent | primary | fallback | 任务复杂度 |
| --- | --- | --- | --- | --- |
| S | Maestro | `minimax-m3` | `glm-5.2` | 长程协调、状态跟踪 |
| S | Sage | `glm-5.2` | `minimax-m3` | Socratic 对话、需求澄清 |
| S | Judge | `minimax-m3` | `glm-5.2` | S 级深度安全审计 |
| S | Archer | `glm-5.2` | `minimax-m3` | 架构设计 |
| A | Devon | `kimi-2.7-code` | `deepseek-v4-pro` | R-G-R 编码 |
| A | Prism | `deepseek-v4-pro` | `kimi-2.6` | 代码评审（反模式 + 安全快扫） |
| A | Shield | `kimi-2.6` | `kimi-2.7-code` | e2e 模板编写 |
| B | Lex | `deepseek-v4-flash` | `glm-5` | 工具调用 + 结构校验 |
| B | Warden | `glm-5` | `minimax-2.7` | gate 检查 |
| B | Keeper | `minimax-2.7` | `deepseek-v4-flash` | commit 门禁 |
| B | Scout | `glm-5` | `minimax-2.7` | 交互式引导 |
| B | Librarian | `minimax-2.7` | `glm-5` | wiki 维护 |

**历史**：v0.5-007 写过 S/A/B/C 四档 tier 表（含 `gpt-5.4-mini` 等闭源模型），Aaron 2026-06-27（commit `655b215`）把 Scout 从 `glm-5.2` 改成 `gpt-5.4-mini` 时**没同步更新 spec**——说明 tier 表从一开始就不是 source of truth。2026-06-30 拍板：**只使用开源模型，移除 `gpt-5.4-mini`**，按 S/A/B 三档重排。

**实现要点**：

1. **lint 工具**（`tools/check_agent_frontmatter.py`，或 `lk archer lint-frontmatter`）：扫描 `louke/agents/*.md` + `.louke/agents/*.md`
2. **必查**（结构性）：
   - `mode` ∈ {`primary`, `subagent`, `all`}
   - `models` 至少 1 个元素（primary 必填）
   - `name` 非空
   - `description` 非空
   - **`models` 元素必须 ∈ 8 模型白名单**（S/A/B 三个列表的并集）—— 闭源模型或未列入的抽象名直接 fail
3. **档位断言**（不强制，留 hint）：
   - lint 报告可**展示**每个 agent 的档位（按"主 primary 落在哪个档"判断），但不阻断
   - rationale 已落到 issue #77，未来调整档位表时改 spec FR-0210 与本表一致
4. **白名单变更流程**：未来加入/移除模型，需同时改：(a) spec FR-0210 表格、(b) 12 个 agent frontmatter（如果用到）、(c) `lk models list` 解析逻辑、(d) 文档

**AC**

- AC-FR0210-01: 当前 12 个 agent 全部通过 `lk archer lint-frontmatter` exit 0
- AC-FR0210-02: 把 Maestro 的 `mode` 改成 `xxx`（非法）→ lint exit 1，stderr 含 `mode`
- AC-FR0210-03: 缺 `models` 字段 → lint exit 1，stderr 含 `models`
- AC-FR0210-04: `models: []`（空数组）→ lint exit 1，stderr 含 `non-empty`
- AC-FR0210-05: 把任意 agent 的 primary 改成 `gpt-5`（闭源，不在白名单）→ lint exit 1，stderr 含 `whitelist` 与 `gpt-5`
- AC-FR0210-06: 把任意 agent 的 primary 改成 `kimi-2.6`（在白名单）→ lint exit 0
- AC-FR0210-07: lint 报告展示每个 agent 的当前 primary（如 `Maestro: glm-5.2`）
3. `lk agent lint`（或 `lk archer lint-frontmatter`）执行校验，exit 0/1
4. **不**自动改 frontmatter（agent prompt 改动需人审）

**AC**

- AC-FR0210-01: 当前 12 个 agent 全部通过 lint（无回归）
- AC-FR0210-02: 把 Maestro 的 `models[0]` 改成 `glm-5.2` → lint exit 1，stderr 列出冲突
- AC-FR0210-03: 缺 `mode` 字段 → lint exit 1
- AC-FR0210-04: `models` 为空数组 → lint exit 1

---

## 5. 功能需求 — §3 默认 agent

---

<a id="fr-0300"></a>
### FR-0300 `lk init` 写 default_agent: maestro

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**实现要点**：

1. **项目级** `<root>/opencode.json`：
   - 不存在 → 新建 `{"default_agent": "maestro"}`
   - 存在 + 无 `default_agent` 键 → 写入
   - 存在 + `default_agent = "maestro"` → skip
   - 存在 + `default_agent` 是其他值 → **默认拒绝并 warning**；`--force-default-agent` 覆盖；`--no-default-agent` 跳过
2. **全局 prompt**：tty 下询问 "是否同时把 default_agent 写入全局 ~/.config/opencode/opencode.json？(Y/n)"；Y 则同样规则写入
3. `--global-default-agent` 跳过 prompt 直接写；`--no-global-default-agent` 不写全局
4. **`lk board status` 集成**：输出 `default_agent: maestro (set in project opencode.json)` 或 `(set in global)` 或 `(not set)`

**AC**

- AC-FR0300-01: init 后 `<root>/opencode.json` 含 `"default_agent": "maestro"`
- AC-FR0300-02: 项目 `opencode.json` 已存在且 `default_agent = "build"` → 默认 exit 1 警告；`--force-default-agent` 覆盖
- AC-FR0300-03: tty 下回答 Y 后 `~/.config/opencode/opencode.json` 也含 `default_agent: maestro`
- AC-FR0300-04: `lk init . --no-default-agent` → 两个 `opencode.json` 都不被改
- AC-FR0300-05: `lk board status` 输出含 `default_agent:` 行
- AC-FR0300-06: `--force-default-agent` 非交互（CI 用），直接覆盖

---

## 6. 功能需求 — §4 Stub 命令真实实现

---

<a id="fr-0400"></a>
### FR-0400 `lk scout foundation` MVP（明确分两阶段）

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**两阶段声明**（修复我的 A6 + 采纳 GLM §18.2 第 6 条）：
- **MVP（本 FR）**：写 `project-info.md` 与 `story.md`，调 `lk scout identity-check` / `lk warden foundation-check` / `lk scout commit-foundation`。**不**创建 GitHub repo / Project / Smoke Issue / Smoke PR / invite-owner。
- **完整 P0**（后续 FR-0401）：M-FOUND Step 2–5 全流程。

**MVP 实现要点**：

1. 校验 `--repo` / `--version` / `--spec-id` 必填
2. `--story <text>` / `--story-file <path>` / stdin 选填；缺则从 spec-id 推断路径
3. `--dod <text>` 选填；缺则用默认 `e2e 全通过 + 单元测试覆盖率 ≥95% + 安全审查 (M-SECURITY)`
4. 写 `<root>/.louke/project/project-info.md`（FR-0800 字段对齐）
5. 写 `<root>/.louke/project/specs/{spec-id}/story.md`
6. `subprocess` 调 `lk scout identity-check --repo {repo}`
7. `subprocess` 调 `lk warden foundation-check --repo {repo} --version {version} --spec-id {spec-id}`
8. step 7 exit 0 → `subprocess` 调 `lk scout commit-foundation --spec-id {spec-id} --message 'story/prd: initial draft for {spec-id}' --version {version}`
9. 输出 Scout.md 标准报告块

**flag**: `--no-commit` 跳过 step 8；`--dry-run` 打印计划不实际写

**AC**

- AC-FR0400-01: 缺任一必填 flag → argparse 错误（exit 2）
- AC-FR0400-02: 跑完后 `<root>/.louke/project/project-info.md` 含 FR-0800 全部 12 字段
- AC-FR0400-03: 跑完后 `<root>/.louke/project/specs/{spec-id}/story.md` 存在且非空
- AC-FR0400-04: `lk scout identity-check` 失败 → exit 1，stderr 含 `identity`
- AC-FR0400-05: `lk warden foundation-check` 失败 → exit 1，stderr 含 `foundation-check`
- AC-FR0400-06: 全部通过 + `--no-commit` → 不调 commit-foundation
- AC-FR0400-07: `--dry-run` 不写任何文件、不调任何子命令
- AC-FR0400-08: 已 init 项目重跑 → 幂等（不覆盖已写文件除非 `--force`）

---

<a id="fr-0401"></a>
### FR-0401 `lk scout foundation` 完整 P0（创建 repo / Project / Smoke）

| 有效需求 | 可测性       | 是否已决定 |
| -------- | ------------ | ---------- |
| ✅        | ⚠️ 需 gh auth | ⚠️          |

**承接 FR-0400 MVP**。完整实现 Scout.md Step 2–5：

1. 创建 GitHub repo（如不存在）：`gh repo create {repo} --{public|private} --description ...`
2. 创建 `releases/{version}` 分支（基于 main）
3. 创建 GitHub Project `{repo}-{version}`：`gh project create --owner {GH_USER} --title ...`
4. 写 Project README
5. 调 FR-0120 `lk scout invite-owner`
6. Smoke Issue 创建 + 立即 close
7. Smoke PR 创建 + 立即 close
8. 调 FR-0400 MVP 后续步骤

**测试策略**：用 `gh` mock 跑测试（GLM §15 推荐）；真实 gh 调用只在 manual smoke test。

**AC**

- AC-FR0401-01: repo 已存在 → 跳过创建，stderr 含 `already exists`
- AC-FR0401-02: Project 已存在 → 跳过创建，复用
- AC-FR0401-03: invite-owner 失败 → 整体 exit 1，提示用户手动添加
- AC-FR0401-04: Smoke PR 创建后 `gh pr close` 立即关闭，PR 编号记入 project-info.md

---

<a id="fr-0402"></a>
### FR-0402 `lk scout foundation` 创建/确保 per-repo backlog project

| 有效需求 | 可测性 | 是否已决定 |
| --- | --- | --- |
| ✅ | ⚠️ 需 gh | ✅ |

**目标**：每次 `lk scout foundation`（FR-0401 完整 P0 Step 3 创建 `{repo}-{version}` Project 后）追加一步：确保 `{repo}-backlog` Project 存在（per-repo，**永久**，区别于 per-release 的 `{repo}-{version}`）。

**用途**：放"想到但未排期"的用户故事 / feature idea / 内部待办。`gh issue create --no-milestone` 创建的 issue 自然归入 backlog；planning 时把 backlog issue 拉进 `{repo}-{version}`。

> **注意**：本节是 louke 框架实现细节，仅在 spec 内部区分。**面向终端用户的 README 只描述 `{repo}-backlog` 一个概念**，不提及 louke 维护者自己的内部 backlog。

**实现要点**：

1. **dedup 规则**（你强调的"不要重复创建"）：
   - 查询 `gh project list --owner {owner} --format json`
   - 过滤 title 严格等于 `{repo}-backlog`（大小写敏感）
   - 找到 → 跳过，stdout `{repo}-backlog reused (id: {PROJECT_ID})`
   - 没找到 → 调 `gh project create --owner {owner} --title {repo}-backlog --description 'Backlog for {repo}: unscheduled user stories and feature ideas'`，记录 id 到 project-info.md
2. **owner 选择**：与 `{repo}-{version}` Project 一致（FR-0401 Step 3 用的 owner；若 agent 是 collaborator 模式仍可能失败，由 FR-0120 invite-owner 兜底）
3. **写入 project-info.md**：模板（FR-0800）增加字段 `Backlog Project: {repo}-backlog (#{PROJECT_ID})`
4. **fail 软策略**（采纳 NFR-0200 actionable）：backlog 创建失败不阻断 foundation（避免 1 个 gh API 失败让整个 init 卡住），warning to stderr 含 retry 命令

**AC**

- AC-FR0402-01: 首次 `lk scout foundation` → 实际调 `gh project create` 创建 `{repo}-backlog`，project-info.md 含 `Backlog Project:` 字段
- AC-FR0402-02: 二次 `lk scout foundation`（mock `gh project list` 返回已存在的 `{repo}-backlog`）→ 跳过创建，stdout 含 `reused`
- AC-FR0402-03: title 匹配严格（`{repo}-backlog-extra` 不算重复）
- AC-FR0402-04: backlog 创建失败（如 owner 无权限）→ warning 不阻断 foundation，stderr 含 `{repo}-backlog` 与 retry 提示
- AC-FR0402-05: owner 选择与 `{repo}-{version}` Project 一致（同一字段 `Project ID` 解析得到）
- AC-FR0402-06: `--dry-run` 不实际调 `gh project create`，stdout 打印将创建的 title

---

<a id="fr-0410"></a>
### FR-0410 `lk sage create-issues` 真实实现

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**实现要点**：

1. 校验 `--spec` 必填（或 `--spec-file` 走 FR-0240 路径回落）
2. 读 `spec.md`，用 `re.findall(r'<a\s+id="fr-(\d{4})"></a>', text)` 提取所有 FR 编号
3. 对每个 FR：
   - 提取标题（FR 标题行第一个非空）
   - 决定 AC value（FR-0700 三选一：`acceptance.md#ac-fr-XXXX` 优先 / spec.md 锚 `无` / `无`）
4. body 模板：
   ```
   ### 需求 ID
   FR-XXXX

   ### Spec 链接
   {REPO_URL}/blob/{BRANCH}/.louke/project/specs/{spec-id}/spec.md#fr-XXXX

   ### 验收标准
   {AC_VALUE}
   ```
   - **`{BRANCH}` 解析**（修复我的 A5）：取自 `<root>/.louke/project/project-info.md` 的 `Release Branch` 字段（如 `releases/v0.6`）；缺失则 fail 提示用户先跑 `lk scout foundation`
5. 去重：`gh issue list --repo {REPO} --search 'in:title [FR-XXXX]' --json number,title` 查到 → skip（计入 `[=]`）
6. `gh issue create --repo {REPO} --title '[FR-XXXX] {title}' --label Feature --body-file /tmp/issue-body.md`
7. **Project 关联**（采纳 GLM §18.2 第 8 条）：
   - 默认行为：若 `project-info.md` 缺 Project URL → **exit 非零**（默认 mode 应阻塞，符合 Lex 阶段二必验要求）
   - `--skip-project` flag：warning + 继续创建 issue（不关联 Project）
   - 有 Project URL：`gh project item-add {PROJECT_URL} --url {ISSUE_URL}`
8. 输出：`Created: [FR-0001] #N ... / Skipped: [FR-0002] #M (exists) / Project: linked / Skipped-project: --skip-project`

**AC**

- AC-FR0410-01: spec.md 含 0 个 FR 锚点 → exit 0，stdout `0 created, 0 skipped`
- AC-FR0410-02: spec.md 含 3 个 FR；2 个已存在 → 1 created, 2 skipped
- AC-FR0410-03: `gh` 未认证 → exit 1，stderr 含 `gh 未认证`
- AC-FR0410-04: project-info.md 缺 Project URL + 默认模式 → exit 1
- AC-FR0410-05: project-info.md 缺 Project URL + `--skip-project` → warning + 继续创建
- AC-FR0410-06: `--dry-run` 不实际调 `gh`
- AC-FR0410-07: 缺 `Release Branch` 字段 → exit 1 提示跑 scout foundation
- AC-FR0410-08: body 模板 Spec 链接的 branch = project-info.md 的 `Release Branch`

---

<a id="fr-0420"></a>
### FR-0420 `lk sage record-lock` 结果记录器（三信号判定）

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**重要语义澄清**（修复我的 A4 + 采纳 GLM §18.2 第 7 条）：
- `lk sage record-lock` **不是**锁定信号本身，而是**三信号齐之后的结果记录器**
- 三信号：
  1. **Sage 信号**: `lk sage quote-check --spec {id} --check-ready` exit 0
  2. **Lex 信号**: `lk lex verify-acceptance` + `lk lex verify-issue` + `lk lex verify-project` 三阶段全通过
  3. **用户信号**: 人类在 IDE 内显式确认（Maestro 流程记录）
- `locked: true` 是**结果**，不可替代信号

**实现要点**：

1. 校验 `--spec` 必填；可选 `--confirm` flag 表示用户已显式确认
2. **三信号校验**：
   - step 1: 跑 `lk sage quote-check --spec {id} --check-ready`；非零 → exit 1，stderr `Sage signal: 未通过 (quote 块未 resolved)`
   - step 2: 跑 `lk lex verify-acceptance --spec {id}` + `lk lex verify-issue --spec {id}` + `lk lex verify-project --spec {id}`；任一非零 → exit 1，stderr 列出失败
   - step 3: 缺 `--confirm` → exit 1，stderr `User signal: 缺 --confirm flag 或 IDE 内显式确认`
3. 三信号齐 → spec.md frontmatter 合并 `locked: true` + `locked-at: {ISO timestamp}` + `locked-by: lk sage record-lock`
4. `lk sage commit-spec --spec {id} --message 'spec: lock {spec-id}'`

**AC**

- AC-FR0420-01: 跑完三信号齐 → spec.md 含 `locked: true`
- AC-FR0420-02: quote-check 失败 → spec.md 不被修改，exit 1 提示 `Sage signal`
- AC-FR0420-03: 任一 Lex 阶段失败 → exit 1 列出失败阶段
- AC-FR0420-04: 缺 `--confirm` → exit 1 提示 `User signal`
- AC-FR0420-05: 已 lock 的 spec 再 record-lock → idempotent，exit 0 不报错
- AC-FR0420-06: 缺 `--spec` → argparse 错误

---

<a id="fr-0430"></a>
### FR-0430 `lk librarian from-raw` 真实蒸馏

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**实现要点**：

1. 扫描 `<root>/.louke/raw/{yy-mm-dd}/{session-id}.md`（FR-0810 统一路径）
2. 过滤 `status: resolved` 且 `superseded-by` 为空（或指向更新条目）
3. 对每条：生成 wiki 页 `<root>/.louke/wiki/pages/{yy-mm-dd}-{slug}.md`
4. frontmatter：
   ```yaml
   ---
   date: 2026-06-30
   title: <frontmatter title 或 "Session: {session-id}">
   type: experience   # 默认；decision / entity 由 raw frontmatter 显式标注
   session: {session-id}
   raw_ref: ../raw/{yy-mm-dd}/{session-id}.md
   agents: [...]
   tags: [...]
   ---
   ```
5. body 拷贝 raw 中 `## 议题 / ## 决定 / ## 试过但放弃 / ## 开放问题` 四段
6. 写完后更新 raw frontmatter 加 `distilled-to: pages/{path}`
7. 同步刷新 `<root>/.louke/wiki/index.md`（FR-0830 lint）

**AC**

- AC-FR0430-01: 无 raw entries → exit 0，stdout `Distilled 0 entries`
- AC-FR0430-02: 1 resolved + 1 open → `Distilled 1 entries`，wiki 页生成
- AC-FR0430-03: wiki 页 frontmatter 含 `date`/`title`/`type: experience`/`session`/`raw_ref`
- AC-FR0430-04: 跑两次幂等：raw 含 `distilled-to` → 跳过
- AC-FR0430-05: `--since 2026-06-25` 只处理 6-25 之后（含）的 raw
- AC-FR0430-06: 蒸馏完成后 `wiki/index.md` 含新页

---

<a id="fr-0440"></a>
### FR-0440 `lk librarian write <page-relpath>` 含 path traversal 防护

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**实现要点**（采纳 GLM §17.2 第 6 条 path traversal 防护）：

1. 校验 `<page-relpath>` 必须以 `pages/` 起；不含 `..` 段；解析后路径必须在 `<root>/.louke/wiki/` 内 → 否则 exit 1 提示 `path traversal rejected`
2. flag: `--type experience|decision|entity`（必填）；`--title T`；`--date YYYY-MM-DD`（默认今天）；body 来自 stdin 或 `--content-file <path>`
3. 写 `<root>/.louke/wiki/{page-relpath}.md`，自动生成 frontmatter（`date`/`title`/`type`/`slug`）
4. 写完调 `lk librarian rebuild-index --wiki .louke/wiki`（FR-0830）

**AC**

- AC-FR0440-01: 写入后文件存在，frontmatter 含 `type`/`title`/`date`
- AC-FR0440-02: `index.md` 含新页链接
- AC-FR0440-03: `--type xxx` 非法值 → argparse 错误
- AC-FR0440-04: `page-relpath = ../../etc/passwd` → exit 1，stderr 含 `path traversal`
- AC-FR0440-05: `page-relpath = agents/Maestro.md`（不在 pages/ 下）→ exit 1
- AC-FR0440-06: 写入失败（缺 type）→ exit 1

---

<a id="fr-0450"></a>
### FR-0450 `lk sage/lex quote-check` + `lk lex verify-acceptance` 加 resolve_spec_path

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**实现要点**（修复 GLM §17.2 第 5 条 + 我的 v0.6-007 FR-0240/0250）：

1. 路径解析顺序：
   - 绝对路径且存在 → 用
   - 相对路径在 cwd 存在 → 用
   - 否则 `git rev-parse --show-toplevel` 找 git root，拼 `<root>/<arg>` → 存在则用
   - 都不存在 → 透传给下层工具，让其报错（stderr 包含原始 path + git root 作调试信息）
2. **应用到**：
   - `lk sage quote-check --spec <path>` — `--spec` 参数走 resolve
   - `lk lex quote-check --spec <path>` — 同样
   - `lk lex verify-acceptance --spec-file <p> --acceptance-file <p>` — 两个路径都走 resolve

**AC**

- AC-FR0450-01: cwd 在 git root 子目录，`--spec specs/X/spec.md` 实际位于 git root → 找到并成功 check
- AC-FR0450-02: 路径 git root 也不存在 → exit ≠ 0，stderr 含原始 path + `git root: <root>`
- AC-FR0450-03: 不是 git repo → 跳过 git root 回落，直接走原路径
- AC-FR0450-04: `lk lex verify-acceptance` 的 `--spec-file` + `--acceptance-file` 同 AC-FR0450-01/02/03

---

## 7. 功能需求 — §5 工具链收口

---

<a id="fr-0500"></a>
### FR-0500 `lk --version` + 版本号单源同步

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**修复 GLM B1.1 / B1.2**：
- 当前 `lk --version` → argparse 错误（`<agent>` 必填）；`install.sh:121` 拿到 `?`
- `pyproject.toml` = `0.3.0`，但 `louke/__init__.py:__version__ = "0.1.0"`（不一致）

**实现要点**（采纳 GLM §18 标注，**不分两步**；当前 release 手动对齐即可）：

1. `__main__.py` 顶层加：
   ```python
   if len(sys.argv) == 2 and sys.argv[1] in ("--version", "-v", "version"):
       from . import __version__
       print(f"lk {__version__}")
       return 0
   ```
2. **手动对齐**：版本号写在 `pyproject.toml`（source of truth）；`louke/__init__.py:__version__` 由 release 流程手动同步
3. CI 加一个 `tests/test_version_sync.bats`：跑 `tomllib.load(open('pyproject.toml','rb'))['project']['version']` 与 `louke/__init__.__version__` 比较，**不一致 exit 1**（防止发版后忘了同步）
4. 删除 `install.sh:121` 的 `lk --version` workaround

**未来优化（不在本 FR 范围）**：构建时自动 sync（如 hatch hook / setuptools custom command）需要单独 spec；当前 setuptools + Makefile 体系下不强加，避免引入构建系统变化。

**AC**

- AC-FR0500-01: `lk --version` 输出形如 `lk 0.3.0`
- AC-FR0500-02: `lk -v` 同上
- AC-FR0500-03: `louke/__init__.py:__version__` 与 `pyproject.toml:version` 同步（CI 测试守门）
- AC-FR0500-04: `tests/test_version_sync.bats` 验证两处一致

---

<a id="fr-0510"></a>
### FR-0510 `pyproject.toml` package-data 扩充

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**修复 GLM B1.3**：当前 package-data 只有 `["py.typed", "agents/*.md", "templates/*.md"]`，缺 `.github/ISSUE_TEMPLATE/` 与 `.github/workflows/`。

**实现要点**（采纳 GLM §18 标注——setuptools package-data 只能可靠包含**包目录内**文件；当前 `.github/` 在仓库根，不在 `louke/` 包目录）：

1. **把资源移到包内**（新建 `louke/resources/`）：
   ```
   louke/resources/
     .github/ISSUE_TEMPLATE/feature.yml
     .github/workflows/louke-ci.yml
     .github/workflows/louke-release.yml
   ```
2. `pyproject.toml` 更新：
   ```toml
   [tool.setuptools.package-data]
   louke = [
     "py.typed",
     "agents/*.md",
     "templates/*.md",
     "resources/.github/ISSUE_TEMPLATE/*.yml",
     "resources/.github/workflows/*.yml",
   ]
   ```
3. **运行时访问**：用 `importlib.resources.files('louke').joinpath('resources/.github/ISSUE_TEMPLATE/feature.yml')`（Python 3.9+ 标准库；不引入 `pkg_resources`）
4. **sdist**：补 `MANIFEST.in` 含 `recursive-include louke/resources *`

**AC**

- AC-FR0510-01: `pip install louke` 后 `importlib.resources.files('louke').joinpath('resources/.github/ISSUE_TEMPLATE/feature.yml').is_file()` = True
- AC-FR0510-02: 同上 `.github/workflows/louke-ci.yml` is_file() = True
- AC-FR0510-03: wheel (`dist/*.whl`) 用 `unzip -l` 看含 `louke/resources/.github/ISSUE_TEMPLATE/feature.yml` 路径
- AC-FR0510-04: sdist (`dist/*.tar.gz`) 用 `tar tzf` 看含同样路径

---

<a id="fr-0520"></a>
### FR-0520 项目级 `.github/workflows/louke-ci.yml` 自动安装

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**修复 GLM §3 + §15**：仓库没有 `.github/workflows/louke-ci.yml`，`lk init` 也不装。

**实现要点**（采纳 GLM §18 标注——`SPEC_ID` 通过 sed 推断不稳定）：

1. 资源位置：`louke/resources/.github/workflows/louke-ci.yml`（随 FR-0510 package-data）
2. **CI workflow 模板**：
   ```yaml
   name: louke-ci
   on:
     push:
       branches: [main, "releases/**"]
     pull_request:
       branches: [main, "releases/**"]
     workflow_dispatch:
       inputs:
         spec_id:
           description: "spec-id to scan (e.g. v0.6-008). Leave blank to scan all."
           required: false
           default: ""
   jobs:
     gate:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
         - run: pip install louke
         - name: AC traceability scan
           run: |
             if [ -n "${{ inputs.spec_id }}" ]; then
               lk archer ci-scan --spec "${{ inputs.spec_id }}"
             else
               for spec in .louke/project/specs/*/; do
                 spec_id=$(basename "$spec")
                 lk archer ci-scan --spec "$spec_id" || exit 1
               done
             fi
   ```
3. `lk init` 默认安装到 `<root>/.github/workflows/louke-ci.yml`（`--with-workflows` / `--no-workflows` flag）
4. **SPEC_ID 解析规则**：优先读 `workflow_dispatch` 输入；其次 CI 默认从 `.github/CODEOWNERS` 或 `.louke/project/project-info.md:Current Stage` 推断；都不存在则扫所有 spec（每个单独调用）

**AC**

- AC-FR0520-01: init 后 `<root>/.github/workflows/louke-ci.yml` 存在
- AC-FR0520-02: `--no-workflows` 不创建该文件
- AC-FR0520-03: workflow 含 `workflow_dispatch` 入口 + spec_id input
- AC-FR0520-04: workflow 含循环 `for spec in .louke/project/specs/*/`（不依赖 sed 推断）
- AC-FR0520-05: `pip install louke` 后 `lk archer ci-scan` 可调用

---

<a id="fr-0530"></a>
### FR-0530 `lk scout commit-foundation` glob 修复

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**修复 GLM §6 + B1.4**：当前 `louke/scout.py:71-73` 用 `subprocess.run(['git', 'add', f"{spec_path}/*.md", ...])`，但 subprocess list 模式不走 shell，glob 不展开。

**实现要点**：

1. 改为先 `glob.glob(f"{spec_path}/*.md")` 得具体路径列表，再传给 `git add`
2. 若 `glob` 返回空 → warning + 继续（不阻断 commit）
3. 同步加 `.louke/project/project-info.md`（无 glob）

**AC**

- AC-FR0530-01: `lk scout commit-foundation` 后 `git status` 不再残留 untracked `*.md`
- AC-FR0530-02: 跑完后 `git log --name-only -1` 含 `specs/{id}/*.md` 文件名
- AC-FR0530-03: `*.md` glob 无匹配时 warning 但不 exit 非零

---

<a id="fr-0540"></a>
### FR-0540 `verify_acceptance.py` 默认 release 分支 + gh api 路径修正

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**修复 GLM §8 + B1.5**：当前 `verify_acceptance.py:86, 99, 104` 硬读 `?ref=main`；`--branch` 默认 `main`；gh api path 不完整。

**实现要点**：

1. `--branch` 默认从 `<root>/.louke/project/project-info.md` 的 `Release Branch` 字段读取（如 `releases/v0.6`）；缺失 fallback 到 `main` 并 warning
2. gh api path 补全：`/repos/{owner}/{repo}/contents/{path}?ref={branch}`
3. 增加 `--repo` 自动从 project-info.md 的 `Repo` 字段读（FR-0240 类回落）
4. `gh repo view` 仅在缺 project-info.md 时用

**AC**

- AC-FR0540-01: project-info.md 含 `Release Branch: releases/v0.6` → `verify-acceptance` 读 `releases/v0.6`（不是 main）
- AC-FR0540-02: project-info.md 缺 release branch → fallback main + warning
- AC-FR0540-03: gh api 调通读出 `releases/v0.6/.louke/project/specs/{id}/spec.md`
- AC-FR0540-04: `--branch releases/v0.5` 显式覆盖默认

---

<a id="fr-0550"></a>
### FR-0550 FR/AC 4 位 schema 全栈升级

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**修复 GLM B1.6 / B1.7 / §14 + 我的 A2**：
- `.github/ISSUE_TEMPLATE/feature.yml` regex `^FR-\\d{3}$` (3 位)
- `louke/_tools/check_acs.py:13-14` regex `\d{3}`
- `louke/_tools/check_assertions.py` regex 待查
- `louke/_tools/verify_acceptance.py` regex 待查
- `louke/_tools/verify_issue_schema.py` regex 待查
- `louke/_tools/quote_parser.py` regex 待查
- `README.md:216` 比较表 `FR-XXX / AC-XXX-N`
- `README.zh.md:212` 比较表 `FR-XXX / AC-XXX-N`

**实现要点**：

1. 所有 FR/AC 正则改为 4 位：`re.compile(r'<a\s+id="(?:fr|nfr)-(\d{4})"', re.I)` 等
2. issue template 改为 `regex: "^FR-\\d{4}$"`，placeholder `FR-0001`，URL fragment `#fr-0001`
3. `louke/schema.py` 新增共享正则常量，所有 `_tools/*.py` 引用（避免各处重复定义）
4. README § "How louke compares" 表格行改：`FR-XXXX / AC-FRXXXX-YY + lk archer ci-scan`
5. README 比较表同步更新（GLM §14 第 3 条）

**AC**

- AC-FR0550-01: 12 个 `louke/_tools/*.py` 引用统一 4 位正则（来自 `louke/schema.py`）
- AC-FR0550-02: feature.yml `regex: "^FR-\\d{4}$"`（不是 3 位）
- AC-FR0550-03: README + README.zh 表格行 `FR-XXXX / AC-FRXXXX-YY`
- AC-FR0550-04: 用 4 位 FR 的 fixture spec.md 通过 verify-acceptance

---

<a id="fr-0560"></a>
### FR-0560 `lk archer ci-scan` 参数一致性 + 4 位 AC

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**修复 GLM §9 + B2.1**：当前 `archer.py:ci-scan` 只接 `--spec`；`cmd_ci_scan` 内部用 `--acceptance` + `--tests`，但 argparse 不暴露 → 用户按 `templates/test-plan.md` 示例调必崩。

**实现要点**：

1. `lk archer ci-scan` argparse 改：
   - `--spec` 与 `--acceptance` 互斥（spec-id 解析到 acceptance.md 路径）
   - `--tests DIR` 可选（默认 `tests/`）
   - `--json` 输出结构化结果
2. 与 `templates/test-plan.md` 示例调用方式对齐
3. 4 位 AC 引用（FR-0550 已覆盖）

**AC**

- AC-FR0560-01: `lk archer ci-scan --spec v0.6-008-closure` 仍可用
- AC-FR0560-02: `lk archer ci-scan --acceptance .louke/.../acceptance.md --tests tests/` 也能用（template 示例方式）
- AC-FR0560-03: 互斥：同时给 `--spec` + `--acceptance` → argparse 错误
- AC-FR0560-04: `--json` 输出 `{"ac_total": N, "ac_referenced": M, "anti_patterns": [...], "passed": bool}`

---

<a id="fr-0570"></a>
### FR-0570 `lk devon run-tests` 项目配置化

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**修复 GLM §10 + B2.2**：当前硬编码 `pytest` + `tests/`。

**实现要点**：

1. 读 `<root>/pyproject.toml` 的 `[tool.louke.test]` 段（如不存在 → fallback 当前硬编码）：
   ```toml
   [tool.louke.test]
   command = "pytest"
   args = ["-q", "--tb=short"]
   paths = { unit = "tests/unit/", integration = "tests/", e2e = "tests/e2e/", all = "tests/" }
   ```
2. 非 Python 项目可在 `[tool.louke.test]` 配 `command = "npm test"` 等
3. `--scope` 仍按 unit/integration/e2e/all
4. `--fast` 保留 → 加 `-x` 到 args 末尾

**AC**

- AC-FR0570-01: pyproject.toml `[tool.louke.test]` 不存在 → 用硬编码 fallback
- AC-FR0570-02: 配置 `command = "npm test"` → 跑 `npm test` 而不是 pytest
- AC-FR0570-03: `--scope unit` 按 paths.unit 配置定位测试目录
- AC-FR0570-04: 配置错误（如 `command = ""`）→ exit 1 actionable

---

<a id="fr-0580"></a>
### FR-0580 `lk devon commit-rgr` 加 push + `--issue` + 可配置

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**修复 GLM §10 + B2.3 / B2.4**：当前只 commit，不 push；缺 `--issue` flag 写 `Closes #N`。

**实现要点**（采纳 GLM §18 标注——开发者指令要求不默认 push，避免 agent 误 push）：

1. **默认 no-push**：只 commit，不 push
2. `--push` flag 显式 push（agent prompt 中由 Maestro/用户显式传）
3. `--issue #N` 把 `Closes #N` 加到 commit message 末尾
4. 保留 `--task-id TASK-XX` 兼容 Devon.md 现有协议
5. message 格式：`test: red TASK-01 {message} {Closes #N}`

**AC**

- AC-FR0580-01: 默认跑完后 `git log -1` 含新 commit，`git status` 含 ahead 状态（未 push）
- AC-FR0580-02: `--push` 后 commit push 到 origin，`git status` 干净
- AC-FR0580-03: `--issue #42` 后 commit message 含 `Closes #42`
- AC-FR0580-04: 缺 `--phase` 或 `--message` → argparse 错误

---

<a id="fr-0590"></a>
### FR-0590 `lk keeper gate` 完整检查

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**修复 GLM §10 + B2.5 / B2.6**：当前 `keeper.py:check_commit_messages` 只查 commit prefix。

**实现要点**：

1. **commit format**: R-G-R 前缀（已有）
2. **R-G-R 顺序**: 对 commit-range 内每个 commit，验证 phase 顺序（如 `test: red` → `feat: green` → `refactor:`），单 cycle 内不允许跳
3. **测试先于实现**: cycle 内 `test: red` 必须先于 `feat: green` 提交
4. **lint**（可选）: `[tool.louke.lint]` 配 `command = "ruff check"` 等；缺则跳过
5. **typecheck**（可选）: `[tool.louke.typecheck]` 配 `command = "mypy src"` 等；缺则跳过
6. **AC trace**: 调 `lk archer ci-scan --commit-range <range>` 验证 AC 引用闭合
7. **反模式**: 调 `lk archer check-acs` + `lk archer check-anti-patterns`（如实现）
8. **--tests**: 走 FR-0570 的项目配置
9. **退出**: 任一失败 → exit 1，stderr 列出失败项 + actionable 提示

**AC**

- AC-FR0590-01: commit range 内 `feat: green` 在 `test: red` 之前 → exit 1，stderr 含 `R-G-R order`
- AC-FR0590-02: commit message 不符前缀 → exit 1
- AC-FR0590-03: ci-scan 失败（AC 未引用） → exit 1，列出未引用 AC
- AC-FR0590-04: lint 配置存在 → 跑 lint；失败 exit 1
- AC-FR0590-05: 全部通过 → exit 0
- AC-FR0590-06: `--tests` 跑项目配置的 test command，失败 exit 1

---

<a id="fr-0600"></a>
### FR-0600 `lk prism review` diff range 支持

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**修复 GLM §10 + B2.7**：当前 `prism.py:50, 109, 126` 用 `get_diff_files('HEAD~1', args.diff)`，当 `args.diff='HEAD~1..HEAD'` 时把 range 当 ref。

**实现要点**：

1. 检测 `args.diff` 是否含 `..`：
   - 含 → 拆为 `(left, right)`，直接传给 `git diff --name-only {left} {right}`
   - 不含 → 维持 `get_diff_files('HEAD~1', args.diff)`（向后兼容）
2. 同步 `lk prism test-patterns` / `lk prism security-quick-scan` / `lk prism code-quality`

**AC**

- AC-FR0600-01: `lk prism review --diff HEAD~1..HEAD` 正确解析 range
- AC-FR0600-02: `lk prism review --diff HEAD` 仍 work（旧行为）
- AC-FR0600-03: 同步到 test-patterns / security-quick-scan / code-quality

---

<a id="fr-0610"></a>
### FR-0610 `lk judge security-audit` 两阶段

| 有效需求 | 可测性           | 是否已决定 |
| -------- | ---------------- | ---------- |
| ✅        | ⚠️ 阶段二需 agent | ✅          |

**修复 GLM §10 + B2.8**：当前只有 pattern scan 框架；缺 S 级语义审查 + 机器可读报告。

**实现要点**（采纳 GLM §18.2 第 3 条）：

1. **阶段一（rule-based）**：`lk judge security-audit` 跑现有 pattern scan + 输出初判
2. **阶段二（agent semantic，可选）**：`--use-llm` flag 触发，调用本机模型（`~/.louke/models.json` 中 `kimi-k2.6` 映射，或 `$LOUKE_OPENCODE_REVIEW_MODEL`）生成 S 级审查报告
3. **机器可读报告 schema**（写 `<root>/.louke/raw/security-audit-{date}.json`）：
   ```json
   {
     "audit_id": "...",
     "stage1_findings": [...],
     "stage2_findings": [...] | null,
     "blockers": [...],
     "warnings": [...],
     "verdict": "pass" | "fail" | "needs-human-review"
   }
   ```
4. 退出码：0=pass, 1=fail (blocker), 2=needs-human-review
5. **未配置 LLM**：缺 `--use-llm` 默认 run 阶段一即可，不阻塞

**AC**

- AC-FR0610-01: 默认 `lk judge security-audit` 跑阶段一 + 输出报告
- AC-FR0610-02: `--use-llm` 跑阶段二（缺模型 → exit 1 actionable）
- AC-FR0610-03: 报告含 `verdict` 字段，Maestro 可直接读
- AC-FR0610-04: blocker 存在 → exit 1

---

<a id="fr-0620"></a>
### FR-0620 `lk shield scaffold` 加 `--spec`

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**修复 GLM §10 + B2.9**：当前 `shield.py:51-55` 注册的 `scaffold` argparse 没 `--spec`，但 `cmd_scaffold:96` 用了 `args.spec` → 必崩。

**实现要点**：

1. `scaffold` argparse 加 `--spec`（必填）
2. 默认放路径 `.louke/project/specs/{spec}/tests/e2e/`（与 `commit-e2e` 对齐）
3. 错误信息：`The following arguments are required: --spec`

**AC**

- AC-FR0620-01: `lk shield scaffold --type playwright --spec v0.6-008 --scenario login --ac-id AC-FR0100-01` 不崩，生成模板文件
- AC-FR0620-02: 缺 `--spec` → argparse 错误

---

<a id="fr-0630"></a>
### FR-0630 `lk shield run-e2e` 项目配置化

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**修复 GLM §10 + B2.10**：当前硬编码 `pytest` + playwright 参数。

**实现要点**：

1. 读 `[tool.louke.test]` 段（同 FR-0570），`paths.e2e` 走配置
2. `[tool.louke.test.e2e]` 子段（可选）：
   ```toml
   [tool.louke.test.e2e]
   command = "pytest"
   args = ["-q", "--tb=short", "--browser={browser}"]
   ```
3. `--browser` 默认 `chromium`；非 Playwright 项目可忽略

**AC**

- AC-FR0630-01: 配置 `command = "behave"` → 跑 behave 而不是 pytest
- AC-FR0630-02: `--browser firefox` 替换 `{browser}` 占位
- AC-FR0630-03: e2e 测试不通过 → exit 非零

---

## 8. 功能需求 — §6 Maestro 流程闭环

---

<a id="fr-0700"></a>
### FR-0700 `lk maestro advance` 10 阶段 holdpoint 自动调用

| 有效需求 | 可测性           | 是否已决定 |
| -------- | ---------------- | ---------- |
| ✅        | ⚠️ 部分需 gh mock | ✅          |

**修复 GLM §11 + B3.1**：当前 `maestro.py:advance` 多阶段打印 `[todo]` 后阻塞。

**实现要点**（按 Maestro.md 阶段表）：

| `--stage`     | 自动调用的 holdpoint                                                  | 说明   |
| ------------- | --------------------------------------------------------------------- | ------ |
| `M-FOUND`     | `lk warden foundation-check --repo X --version V --spec-id ID`        | 已存在 |
| `M-SPEC`      | `lk lex verify-acceptance` + `lk lex verify-issue`                    | 已存在 |
| `M-TESTPLAN`  | `lk archer validate-test-plan`（FR-0720）                             | 待实现 |
| `M-ARCH`      | `lk archer validate-arch`（FR-0720）                                  | 待实现 |
| `M-LOCK`      | `lk sage record-lock --spec ID --confirm`（FR-0420）                  | 待实现 |
| `M-DEV`       | `lk keeper gate --commit-range <range>`（FR-0590）                    | 待实现 |
| `M-E2E`       | `lk keeper gate --commit-range <range> --tests` + `lk shield run-e2e` | 待实现 |
| `M-BUGFIX`    | `lk keeper regression --baseline X --current Y`                       | 已存在 |
| `M-SECURITY`  | 走 FR-0720 跳过判定 → 调 `lk judge security-audit` 或 skip            | 待实现 |
| `M-MILESTONE` | 走 FR-0730 合并/tag 检查 + `lk librarian from-raw`                    | 待实现 |

**AC**

- AC-FR0700-01: `lk maestro advance --stage M-FOUND` 调 foundation-check（exit 0 → advance 成功）
- AC-FR0700-02: `lk maestro advance --stage M-LOCK` 缺 `--confirm` → 调 record-lock 失败 → advance exit 1
- AC-FR0700-03: 任意阶段失败 → advance exit 1 + 列出失败子命令
- AC-FR0700-04: 全部成功 → 调 FR-0710 更新 project-info.md

---

<a id="fr-0710"></a>
### FR-0710 `lk maestro advance` 成功后更新 project-info.md

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**修复 GLM §11 + B3.2**：当前 advance 只打印，不更新 state。

**实现要点**：

1. advance 成功后写 `<root>/.louke/project/project-info.md` 的 `Current Stage` 字段（新增）
2. 写 `<root>/.louke/raw/{date}/maestro-{spec-id}-stage-{stage}.md`（按 FR-0810 路径）记录推进事件
3. 若 M-MILESTONE → 追加 `Last Milestone: {ISO date}`

**AC**

- AC-FR0710-01: advance 成功后 project-info.md 含 `Current Stage: M-FOUND`
- AC-FR0710-02: raw 路径下生成 session 记录
- AC-FR0710-03: 下次 advance 读 `Current Stage` 推断前置阶段

---

<a id="fr-0720"></a>
### FR-0720 M-SECURITY 自动跳过判定

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**修复 GLM §11 + B3.3**：当前 M-SECURITY 需手工触发。

**实现要点**：

1. `lk maestro advance --stage M-SECURITY`：
   - 读 project-info.md 的 `Security Audit: enabled/disabled` 字段
   - `disabled` → skip，stdout `[阶段: M-SECURITY] DoD 关闭，跳过`
   - `enabled` → 调 `lk judge security-audit --release releases/{version}`（FR-0610）

**AC**

- AC-FR0720-01: `Security Audit: disabled` → advance exit 0，跳过 audit
- AC-FR0720-02: `Security Audit: enabled` → 调 `lk judge security-audit`
- AC-FR0720-03: audit verdict = `pass` → advance exit 0
- AC-FR0720-04: audit verdict = `fail` → advance exit 1

---

<a id="fr-0730"></a>
### FR-0730 M-MILESTONE 检查 Librarian + merge/tag

| 有效需求 | 可测性  | 是否已决定 |
| -------- | ------- | ---------- |
| ✅        | ⚠️ 需 gh | ✅          |

**修复 GLM §11 + B3.4**：当前 M-MILESTONE 不验证 Librarian / merge / tag。

**实现要点**：

1. `lk maestro advance --stage M-MILESTONE`：
   - 检查 `git status` clean
   - 检查 `releases/{version}` 分支已合回 main（如 `gh pr view --base main --head releases/{version} --json state`）
   - 检查 tag `v{version}` 存在
   - 检查 `lk librarian from-raw` 已 distill 完（看 `.louke/raw/` 是否有未处理 resolved 条目）
   - 全部通过 → exit 0
2. **未合回 main** → exit 1，提示跑 merge
3. **缺 tag** → exit 1，提示打 tag

**AC**

- AC-FR0730-01: `releases/v0.6` 已合 main + tag `v0.6` 存在 + raw 已 distill → advance exit 0
- AC-FR0730-02: 未合 main → exit 1，stderr 含 `merge releases/v0.6`
- AC-FR0730-03: 缺 tag → exit 1，stderr 含 `git tag v0.6`

---

<a id="fr-0740"></a>
### FR-0740 `lk lex verify-project` Issue↔Project 关联验证

| 有效需求 | 可测性  | 是否已决定 |
| -------- | ------- | ---------- |
| ✅        | ⚠️ 需 gh | ✅          |

**修复 GLM §8 + B3.6**：Lex 阶段二要求验证 Project 关联；当前 `verify_issue_schema` 不实现。

**实现要点**：

1. 新增 `lk lex verify-project --spec ID`：
   - 读 project-info.md 的 Project URL
   - 对 spec.md 每个 FR 对应的 issue，验证 `gh project item-list {PROJECT_URL} --format json` 包含该 issue URL
   - 缺关联 → 报告未关联列表
2. `lk lex verify-issue --spec ID` 阶段三增强：自动调 verify-project 作为子检查

**AC**

- AC-FR0740-01: 全部 issue 已关联 Project → exit 0
- AC-FR0740-02: 2 个 issue 未关联 → exit 1，列出未关联编号
- AC-FR0740-03: project-info.md 缺 Project URL → exit 1 提示先跑 scout foundation

---

## 9. 功能需求 — §7 项目信息模板与 Librarian

---

<a id="fr-0800"></a>
### FR-0800 `templates/project-info.md` 字段对齐 Scout.md

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**修复 GLM §6 + B3.5**：当前模板 8 字段，Scout.md Step 6 模板 12 字段。

**实现要点**：

1. `louke/templates/project-info.md` 改为：
   ```markdown
   # Project Info

   - **Version**: {版本号}
   - **Repo**: github.com/{owner}/{repo}
   - **Project**: {repo}-{version}
   - **Project ID**: https://github.com/users/{owner}/projects/{id}
   - **Spec ID**: v{version}-{NNN}-{keyword}
   - **Release Branch**: `releases/{version}`
   - **Smoke Test Issue**: #{编号}（closed）
   - **Smoke Test PR**: #{编号}（closed）
   - **DoD**: {Step 1 收集的完成定义}
   - **Security Audit**: {enabled / disabled}
   - **Current Stage**: {M-FOUND | M-SPEC | ...}
   - **Created**: {YYYY-MM-DD}
   ```
2. `check_foundation.py` F6 校验全部 12 字段（含 current_stage）

**AC**

- AC-FR0800-01: 模板含全部 12 字段
- AC-FR0800-02: `lk scout foundation`（FR-0400 MVP）跑完后 project-info.md 含全部 12 字段
- AC-FR0800-03: `lk warden foundation-check` 缺任一字段 → exit 1 列出缺失

---

<a id="fr-0810"></a>
### FR-0810 raw 路径统一

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**修复 GLM §12 + B4.1**：11 个 agent 用 `.louke/raw/{date}/{session-id}.md`，Librarian.md 用 `.louke/raw/sources/`。

**实现要点**：

1. `Librarian.md:25` 改为 `.louke/raw/{yy-mm-dd}/`（删除 `sources/` 引用）
2. 路径生成工具函数 `louke/_common.py:raw_path(date, session_id)` 统一接口
3. 现有 `wiki/.louke/raw/sources/` 残留条目（如果有）一次性迁移到 `.louke/raw/{date}/`（按 frontmatter `date` 字段）

**AC**

- AC-FR0810-01: 12 个 agent prompt 路径引用全部为 `.louke/raw/{date}/{session-id}.md`
- AC-FR0810-02: `librarian.py` 用 `raw_path()` 函数
- AC-FR0810-03: 旧 `raw/sources/` 残留目录被迁移或删除

---

<a id="fr-0820"></a>
### FR-0820 raw / wiki 入 git 策略

| 有效需求 | 可测性 | 是否已决定 |
| --- | --- | --- |
| ✅ | ✅ | ✅ |

**v0.6-008 决定**（采纳 Aaron 2026-06-30 两条评论 + 关联 backlog issue）：

**默认**：`raw/` / `wiki/` **入 git**（与产品代码同仓）——多人协作 + agents IDE 内 git push 时一并提交 + 简单。

**未来增强**（**不在 v0.6-008 范围**，已建 backlog issue）：

- **Backlog issue [#78](https://github.com/zillionare/louke/issues/78)**：`.louke/project` 作为独立私有 GitHub repo（`private`，通过 git submodule 引入），分离 spec/wiki 与公开代码。**GLM review 标注：submodule 设计涉及多个 FR 改造（FR-0100/0101/0400/0401/0530/0730/0800 都要加 submodule 支持），单次 PR 风险高，独立 spec 实施**。
- **Backlog issue [#79](https://github.com/zillionare/louke/issues/79)**：louke web 服务（`louke serve`），渲染 + 可选在线编辑 wiki / spec / acceptance / test-plan。**GLM review 标注：web 服务是独立大件（部署/认证/编辑 API/PR 流程），独立 spec 实施**。

**实施要点**（v0.6-008 范围内）：

1. README § "Project memory" 段明确："`.louke/raw/` 与 `.louke/wiki/` **入 git**（多人共享协作记忆）；`.louke/agents/` 与 `.louke/templates/` 与 `.opencode/agents/` **不入 git**（本地缓存，由 `lk init` 重建）"
2. `.gitignore` 模板（FR-0100 step 6）只 ignore `agents/` / `templates/` / `.opencode/agents/`，**不**ignore `raw/` / `wiki/`
3. README 加段"Backlog project"（FR-0402 触发，per-repo backlog Project 用法），并链接 issue #78 / #79 提示未来增强路径
4. v0.6-005 epic #74 的"framework vs project split"对 raw/wiki 的处理与此保持一致

**AC**

- AC-FR0820-01: README § "Project memory" 段含明确"raw/wiki 入 git, agents/templates 不入"声明
- AC-FR0820-02: 生成的 `.gitignore` 不含 `.louke/raw/` / `.louke/wiki/`
- AC-FR0820-03: 文档与 `agents/*.md` 路径引用一致
- AC-FR0820-04: README 含"Backlog project"段（FR-0402 触发），并链接 issue #78 / #79 作为未来增强路径

---

<a id="fr-0830"></a>
### FR-0830 Librarian 完整功能（frontmatter 校验 / lint / cache / overview / log）

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**修复 GLM §12 + B4.3 / B4.4**：当前 `librarian.py` 简单实现。

**实现要点**：

1. **`lk librarian lint --wiki <dir>`** 增强：
   - frontmatter 必填 `date`/`title`/`type`
   - broken wikilinks `[[xxx]]` 检测（xxx 不存在 → warning）
   - orphan pages（无任何 wikilink 引用）→ warning
   - duplicate pages（title 重复）→ error
2. **`lk librarian rebuild-index --wiki <dir>`** 增强：
   - 按 `type` 分组（decision / experience / entity）
   - 按 `date` 倒序
   - 每项包含 title + 日期 + frontmatter tags
3. **incremental cache** `<wiki>/.cache/sha256.json`：每页 sha256，lint 时只重算变更页
4. **`<wiki>/overview.md`**：自动生成（按 type 分组的高层摘要，每 type 最多 5 条最近）
5. **`<wiki>/log.md`**：自动追加每次 lint / rebuild-index / from-raw 的事件（ISO timestamp + 动作 + 操作者）
6. **`lk librarian frontmatter-lint`** 新子命令：只校验 frontmatter 不过 wikilink

**AC**

- AC-FR0830-01: wiki 页缺 `date` 字段 → lint exit 1 列出
- AC-FR0830-02: `[[nonexistent]]` wikilink → lint warning
- AC-FR0830-03: rebuild-index 后 `index.md` 按 type 分组
- AC-FR0830-04: lint 后 `.cache/sha256.json` 含每页 hash
- AC-FR0830-05: overview.md 含每 type 摘要
- AC-FR0830-06: log.md 含今日 lint 事件

---

## 10. 功能需求 — §8 文档一致性

---

<a id="fr-0900"></a>
### FR-0900 README / README.zh 文档修复（合并所有散点）

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**修复 GLM §4 / §13 / §14 + 我的 A5**（合并为一个 FR，AC 覆盖所有散点）：

1. **删除** `{"plugin": ["louke"]}` 误导配置（双 README）
2. **替换** § "Use in Your Project": `lk scout foundation` 示例 → `lk init <name>` + `lk init .`（FR-0100/0101）
3. **修正** § "Use with Your AI Assistant → OpenCode": 改为 `lk init` 自动生成 `.opencode/agents/*.md` + `default_agent: maestro`
4. **删除** README.zh:162 孤立 `s`（GLM §14 + 实测确认）
5. **比较表** `FR-XXX / AC-XXX-N` 改为 `FR-XXXX / AC-FRXXXX-YY`（双 README）
6. **加段** "How louke compares" 表底：标注 FR 编号已统一 4 位
7. **加段** README § Architecture 块底部：从"supported environments"补一句"版本查询：`lk --version`"
8. **替换** "32 commands" 描述（README § "You now have"）：自动从 `lk --help` 取实际命令数（template 脚本渲染）
9. **加段** § Install 末尾："升级: `pip install --upgrade louke`"（呼应 FR-0130 P1）
10. **加段** § Use with Your AI Assistant 后："用户心智入口仍是 `lk <agent> <cmd>`，顶层无 alias；Maestro 在 OpenCode 内调度"

**AC**

- AC-FR0900-01: `grep -E '"plugin".*louke|louke.*plugin' README*.md` 命中 0
- AC-FR0900-02: README § "Use in Your Project" 主体是 `lk init <name>` + `lk init .`，不是 `lk scout foundation`
- AC-FR0900-03: README.zh 不含孤立行 `^s$`
- AC-FR0900-04: README.md:216 比较表行 `FR-XXXX / AC-FRXXXX-YY`
- AC-FR0900-05: README.zh:212 同样
- AC-FR0900-06: README 含 `lk --version` 用法说明
- AC-FR0900-07: README 含 `pip install --upgrade louke` 升级指引
- AC-FR0900-08: README 顶部 "Supported environments" 段保留（已加）
- AC-FR0900-09: "32 commands" 改为自动从 `lk --help` 取
- AC-FR0900-10: **新增段** "Backlog project"（中英文 README 都加，面向终端用户），含：
  - 何时创建：`lk scout foundation` 自动确保 `{repo}-backlog` Project 存在（dedup by title，重复跑不重建）
  - 与 `{repo}-{version}` Project 区别：per-repo 永久 vs per-release 临时
  - 用法示例：`gh issue create --no-milestone` 落到 backlog；planning 时把 backlog issue 拉进 `{repo}-{version}`
  - **不**提及任何 louke 内部项目（如 `specforge-backlog`）；本段只面向终端用户
- AC-FR0900-11: backlog 段位置：§ Architecture 之后、§ Use with Your AI Assistant 之前，作为独立 `###` 段
- AC-FR0900-12: README + README.zh 含 "Agent capabilities & model tiers" 5 列表（Agent / Tier / Open-source example / Closed-source reference / 备注），覆盖全部 12 个 agent，档位标注 S/A/B

---

## 11. 非功能需求

---

<a id="nfr-0100"></a>
### NFR-0100 测试矩阵（GLM §15 端到端可用性测试）

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

**新增 bats 文件**（每个 FR 一组）：

- `tests/test_init.bats` — FR-0100/0101/0110
- `tests/test_board.bats` — FR-0200
- `tests/test_models.bats` — FR-0201
- `tests/test_default_agent.bats` — FR-0300
- `tests/test_scout_foundation.bats` — FR-0400/0401/0402/0530
- `tests/test_sage_create_issues.bats` — FR-0410
- `tests/test_sage_record_lock.bats` — FR-0420
- `tests/test_librarian.bats` — FR-0430/0440/0830
- `tests/test_resolve_spec_path.bats` — FR-0450
- `tests/test_version.bats` — FR-0500
- `tests/test_package_data.bats` — FR-0510/0520
- `tests/test_verify_acceptance.bats` — FR-0540
- `tests/test_fr_schema.bats` — FR-0550
- `tests/test_archer_ci_scan.bats` — FR-0560
- `tests/test_devon_config.bats` — FR-0570/0580
- `tests/test_keeper_gate.bats` — FR-0590
- `tests/test_prism_diff.bats` — FR-0600
- `tests/test_judge_security.bats` — FR-0610
- `tests/test_shield_scaffold.bats` — FR-0620/0630
- `tests/test_maestro_advance.bats` — FR-0700/0710/0720/0730
- `tests/test_lex_verify_project.bats` — FR-0740
- `tests/test_project_info_template.bats` — FR-0800
- `tests/test_raw_path.bats` — FR-0810

**GLM §15 10 项端到端测试**必须包含：

1. `lk --version` / `lk --help` 成功
2. `lk init --dry-run` 在空目录输出完整计划
3. `lk init/adopt` 在临时 git repo 生成 `.louke` / issue template / workflow / `.opencode/agents/`
4. `lk models doctor` 用 mock `opencode models` 自动绑定 `glm-5.2` → `provider/glm-5.2`
5. `lk board opencode` 生成 12 个 agent，`model:` 是 provider/model
6. `lk scout foundation` 用 gh mock 跑通（不触碰真实 GitHub）
7. `lk sage create-issues` gh mock 按 FR-XXXX 创建 issue 关联 Project
8. `lk lex verify-acceptance/verify-issue` 对 4 位 schema 通过
9. `lk archer ci-scan` 对 4 位 AC 引用通过
10. `lk maestro advance` 在 fixture 项目按阶段推进或给出明确阻塞原因

---

<a id="nfr-0200"></a>
### NFR-0200 错误信息 actionable

所有失败路径 stderr **必须**含：
- (a) 失败的具体子命令或检查
- (b) 用户下一步可以做什么（"运行 `lk X --help`" / "检查 ~/.louke/models.json" 等）

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

<a id="nfr-0300"></a>
### NFR-0300 现有 bats 测试不回归

`tests/test_*.bats` 现有所有 case 在本 spec 实施后必须继续通过；新功能只增不改现有路径。

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

<a id="nfr-0400"></a>
### NFR-0400 ADR 留痕

新增 `.louke/wiki/decisions/009-louke-v030-usability-closure.md`（或合并到 008），含：

- 背景：v0.3.0 PyPI 发布但端到端不可用
- 决策：§1-§8 共 ~30 FR 一次性收口
- 备选 A：分多个小 spec 跨数月（拒绝，慢）
- 备选 B：维持现状等用户报告（拒绝，损害品牌）
- 后果：~60 个文件修改（CLI/agents/templates/CI/docs/tests）

并在 README § Architecture / Decision 表格追加 `[009]` 一行。

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

## 12. 澄清记录

| #   | 问题                                                                                                                                                     | 待回答              |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- |
| 1   | FR-0400 MVP 与 FR-0401 完整 P0 实施时，是先 MVP 还是并行？倾向先 MVP（验收写 project-info + 调子命令），FR-0401 单独 PR                                  | Aaron: 需要全部实现 |
| 2   | FR-0610 `--use-llm` 阶段二，未配模型时是否要 hard fail 还是 warning + 仅阶段一？倾向 warning（不阻塞 CI）                                                | 仅阶段一            |
| 3   | FR-0820 raw/wiki 入 git——Aaron 2026-06-30 拍板：v0.6-008 默认入 git；submodule + web 服务进 backlog (#78 / #79)                                                  | resolved by minimax  |
| 4   | FR-0130 `lk upgrade` P1 还是 P0？GLM 倾向 P1，本 spec 已采纳                                                                                             | 已采纳 GLM          |
| 5   | FR-0830 wiki frontmatter `type` 取值约束：是 `experience / decision / entity` 三选一，还是允许 free-form + lint 校验？倾向三选一（与 Librarian.md 一致） | 三选一，以后可扩展  |
| 6   | FR-0700 M-LOCK 阶段 `lk sage record-lock` 的 `--confirm` 是必须 flag 还是默认 prompt？倾向 flag（CI 友好），人类 IDE 内由 Maestro 调度时显式传           | flag                |

> **GLM:** 暂不实现 FR-0100/FR-0101 中“agents=13（12 agent + ROSTER）”相关验收。当前仓库根目录与包内 `louke/agents/` 均没有 `ROSTER.md`，历史 `ROSTER.md` 已在迁移中删除；若要恢复，需先决定是恢复 ROSTER 作为包资源，还是把 AC-FR0100-02 改为 12 个 agent。直接实现会导致 init 测试按不存在资源失败。
> 状态: [resolved by minimax 2026-06-30] — AC-FR0100-02 改为 12（spec.md:196 / acceptance.md:63）；FR-0100 step 4 删除 ROSTER 引用；scenario-0100 删除 ROSTER 引用。无需恢复 ROSTER 资源。
>> Aaron:没有 roster 这个 Agent， 请改AC-FR0100-02 → 已采纳

> **GLM:** 暂不实现 FR-0100/FR-0101 中“templates=7”相关验收的精确数量。当前仓库 `templates/` 实际有 10 个 markdown 模板（acceptance、bug-fix、issues、prd、project-info、security-checklist、spec、task-log、task-plan、test-plan），spec.md 与 acceptance.md 均写 7，但又列出超过 7 个名称。需要先把模板数量定稿为 10，或明确只复制核心 7 个。
> 状态: [resolved by minimax 2026-06-30] — AC-FR0100-03 改为 10（spec.md:197 / acceptance.md:64），列出全部 10 个名称与 `$LOUKE_HOME` 数量一致。

> **GLM:** 暂不实现 FR-0500 的“构建时自动从 pyproject 同步 `louke/__init__.py`”完整方案。当前项目使用 setuptools + Makefile，没有 hatch hook；可以先实现 `lk --version` 与手动版本对齐，但 build-time version-sync 需要单独设计，避免引入构建系统变化。
> 状态: [resolved by minimax 2026-06-30] — FR-0500 step 2-4 改为手动同步 + `tests/test_version_sync.bats` 守门（spec.md:1448 段）。

> **GLM:** 暂不实现 FR-0510 中将 `.github/ISSUE_TEMPLATE/*.yml` 与 `.github/workflows/*.yml` 作为 `louke` 包内路径的方案。setuptools package-data 只能可靠包含包目录内文件；当前 `.github/` 在仓库根，不在 `louke/` 包目录。需要先决定是移动/复制资源到 `louke/resources/`，还是调整构建 MANIFEST + importlib.resources 访问方式。
> 状态: [resolved by minimax 2026-06-30] — FR-0510 step 1 改用 `louke/resources/` 装 + `importlib.resources` 访问（spec.md:1486 段）。

> **GLM:** 暂不实现 FR-0520 中给出的 GitHub Actions 示例原样逻辑。`SPEC_ID` 未定义时用 `ls .louke/project/specs/ | head -1 | sed 's:/.*::'` 不稳定，且多 spec 项目会误扫第一个 spec。需要先定义 CI 如何发现 active spec 或由 workflow input/env 明确传入。
> 状态: [resolved by minimax 2026-06-30] — FR-0520 step 2 改用 `workflow_dispatch` 输入 + 循环扫所有 spec（spec.md:1518 段）。

> **GLM:** 暂不实现 FR-0580 的默认 `git push` 行为。开发者指令要求不要在未明确请求时 push；把 `lk devon commit-rgr` 默认改为 push 会让本工具执行实现/测试时存在误 push 风险。建议命令支持 `--push` 显式推送，或保持默认不 push，并在 agent prompt 中要求 agent 显式传 `--push`。
> 状态: [resolved by minimax 2026-06-30] — FR-0580 step 1 改默认 no-push，加 `--push` flag（spec.md:1037 段）。

> **GLM:** 暂不实现 FR-0820 的"raw/wiki 入 git"默认策略。该条在 spec 自身仍标注"待 Aaron 拍板"；在拍板前不能修改 `.gitignore` 与 prompts 的入库策略，否则会改变项目记忆的版本化边界。
> 状态: [resolved by minimax 2026-06-30] — Aaron 拍板：v0.6-008 默认入 git；submodule + web 服务进 backlog issue #78 / #79；FR-0820 文本已改，澄清记录第 3 条已更新，AC-4 新增"README 含 Backlog project 段 + 链接 #78/#79"。

> **GLM:** 暂不依赖本 spec 的 `acceptance.md` 作为 `lk lex verify-acceptance` 门禁输入。当前 acceptance.md 使用 `### FR-0100` + `- **AC-FR...**` 索引式结构，而现有/目标 verify-acceptance 工具要求 `## FR-XXXX` 小节下 `### AC-N` 连续编号结构；实测 `lk lex verify-acceptance --spec-file ... --acceptance-file ...` 报缺少全部 FR/NFR 节。需要 Sage/minimax 先把 acceptance.md 改为工具契约结构，或另行修改工具契约。
> 状态: [resolved by minimax 2026-06-30] — acceptance.md 全文重写为 `## FR-XXXX {title}` + `### AC-N` 工具契约结构（与 verify_acceptance.py:155, 287 一致）。

## 13. Lex 审核结果

- [ ] 所有需求可追踪到用户故事
- [ ] 所有需求可断言（有明确的测试方法）
- [ ] 没有模糊词汇
- [ ] 所有 FR 都有显式锚点 `<a id="fr-XXXX"></a>`
- [ ] 所有 FR 编号 4 位
- [ ] 与既有 spec（v0.5-007 / v0.5-008 / v0.6-005）的引用无冲突
- [ ] `agents/*.md` 路径引用与 FR-0810 一致
