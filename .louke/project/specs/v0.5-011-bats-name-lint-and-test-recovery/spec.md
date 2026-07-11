# v0.5-011 — bats name lint + 25 个 test 失败的根因修复 — Spec

- **Spec ID**: v0.5-011-bats-name-lint-and-test-recovery
- **创建日期**: 2026-06-25
- **状态**: 草稿
- **关联**: v0.5-009-test-cleanup, v0.5-010-ASCII-test-names

## 背景

[v0.5-010](v0.5-010-ASCII-test-names/spec.md) ASCII 化 73 个 silent-skip 测试后，跑出真实基线：**291 个测试 / 266 通过 / 25 失败**。v0.5-009 之前这 25 个 silent skip，无人察觉，现在需要分门别类处理。

经深入分析（每条失败查测试断言、工具源码、agent prompt），25 个失败可归 6 类：

| 类别 | 数量 | 性质 | 修复方向 |
|---|---|---|---|
| BRANCH-* | 6 | 测过期约定（v0.4-004 退休的 `spec/{spec-id}`） | 删测试 |
| PROBE-FORM-001/002/004 | 3 | 测过期 Probe prompt 关键词（v0.5-008 重写后未同步） | 改测试 |
| PROBE-FORM-005/006/007 | 3 | 测过期 Probe 反模式声明 | 删测试 |
| SCOUT-ID-001/002/003 | 3 | **真实 bug**（Scout.md 漏身份检查步骤） | 改 Scout.md |
| QP_T04/T05/T17/IT-003 | 4 | **真实 bug**（quote_parser `is_ready` 算法错） | 改 quote_parser.py |
| QP_T19/T20 | 2 | **真实 bug**（JSON schema 缺 `owner_close_role` 字段） | 改 quote_parser.py |
| VA-T02/T07 | 2 | **真实 bug**（verify_acceptance L2 regex 匹配错标题级别） | 改 verify_acceptance.py |
| T05_sage/T06_lex | 2 | **真实 bug**（Sage.md/Lex.md 未引用 quote_parser） | 改 Sage.md/Lex.md |

**核心危害**：
- quote_parser `is_ready` 错算 → spec 004 quote gate 失效，6 open quote 仍报 ready
- verify_acceptance L2 regex 错配 → acceptance.md 漏 FR 不会被检出，Lex 拿到不完整 acceptance 仍进入 stage-2
- SCOUT 漏身份检查步骤 → Scout 在 git config 不一致时也能进 Stage 1，污染后续
- Sage/Lex 不引用 quote_parser → spec 004 工作流在 agent 端是"瞎子"，agent 看不到 quote 状态

## 目标

1. 防 silent skip 复发：写 `tools/lint_bats_names.sh`，CI 强制检查新 test 名 ASCII
2. 修 13 个真实 bug（agent prompt + Python 工具）
3. 删 9 个过期测试（BRANCH 6 + PROBE 3）
4. 改 3 个过期测试断言（PROBE-FORM-001/002/004）
5. 跑全量 bats 0 失败（除 known-failing 如有），bump VERSION 0.5.5 → 0.5.6

## 非目标

- 不实现 `bin/specforge lint-bats` 子命令（用 shell script 足够）
- 不引入 pre-commit hook（v0.6 再说）
- 不重写整个 quote_parser / verify_acceptance（只修对应 bug）
- 不动其它 16 个 bats 文件

## 用户故事

### US-010
story: 作为 specforge 维护者，我希望 CI 拒绝任何新的中文 bats test 名入库，以便 silent skip bug 模式不再发生。
priority: P0

### US-020
story: 作为 specforge 用户，我希望 Scout 在初始化项目时真跑身份检查（而不是文档写"必跑"但实际漏掉），以便 git config 不一致时不会污染项目。
priority: P0

### US-030
story: 作为 specforge 用户，我希望 `quote_parser --check-ready` 在还有 open quote 时返回非 0，以便 IDE/agent 真正被 gate 挡住。
priority: P0

### US-040
story: 作为 specforge 维护者，我希望 `verify_acceptance.py` 的 L2 检查真能检出"acceptance.md 缺 FR 节"，以便 Lex 拿到不完整 acceptance 时能 reject。
priority: P0

### US-050
story: 作为 specforge 用户，我希望 Sage / Lex 在 spec 004 quote 工作流时引用 `tools/quote_parser.py`，以便 agent 能查 quote 状态做决策。
priority: P1

## 功能需求

### FR-010 tools/lint_bats_names.sh

**触发**: `bin/specforge ci-lint-bats` 或 `make lint-bats` 或 CI step

**逻辑**: 扫描 `tests/*.bats`，找 `@test "<NAME>"` 行，断言 `<NAME>` 全部字节为 ASCII (`[\x00-\x7F]`)。失败退出码 1，输出每条违规的 file:line + 原名。

AC: `tools/lint_bats_names.sh tests/*.bats` exit 0（已 ASCII 化）；人为改回 1 个中文名后 exit 1 + 报错。

### FR-020 quote_parser.py is_ready 算法修

**Bug**: `tools/quote_parser.py:443` `result.is_ready = len(result.ready_blockers) == 0`，只看 `ready_blockers` 是否为空。但 spec 004 设计意图是"无 open quote 时 ready"。

**Fix**: 改为 `result.is_ready = len(result.open_quotes) == 0 and len(result.ready_blockers) == 0`。

AC: `bats tests/test_quote_parser.bats` QP_T04/T05/T17 通过。

### FR-030 quote_parser.py JSON 加 owner_close_role 字段

**Bug**: 工具 dataclass 已有 `owner_close_role` 字段（`tools/quote_parser.py:101, 241`），`--check-violations` 也用它（line 491），但 `--format json` 输出 schema 没暴露它（line 511-528）。

**Fix**: 在 JSON 输出加 `owner_close_role`（per quote 或 per result，由 schema 决定；这里选择 per quote，归到 `open_quotes[]` / `resolved_quotes[]` 每条记录里）。

AC: `bats tests/test_quote_parser.bats` QP_T19/T20 通过。

### FR-040 verify_acceptance.py L2 regex 改二级标题

**Bug**: `tools/verify_acceptance.py:35` `RE_FR_SECTION = re.compile(r"^###\s+(FR|NFR)-...")` 匹配三级标题，但 acceptance.md 中 FR/NFR 节是二级 `## FR-`（line 38 已正确）。spec.md 用三级 `### FR-`（line 33）正确。所以工具只看 spec.md 的 FR 列表，但 acceptance.md 的 FR 节用同一 regex 找不到。

**Fix**: 拆成两个 regex：`RE_SPEC_FR` (三级，匹配 spec.md) 和 `RE_ACC_FR` (二级，匹配 acceptance.md)。`RE_ACC_FR` 已经存在 (line 38)。

AC: `bats tests/test_verify_acceptance.bats` VA-T02/T07 通过。

### FR-050 Scout.md 补身份检查

**Bug**: `agents/Scout.md` 未在 Step 4 引用 `tools/check_identity.py`、未把身份检查放在 issue 冒烟之前、退出条件不含"身份一致"。

**Fix**: 在 `Scout.md` 加 Step 4a 身份一致性检查段、Step 4b 才是 issue/PR 权限冒烟、退出条件加"身份一致 (Scout-ID-001/002/003 覆盖)"。

AC: `bats tests/test_scout_project_board.bats` SCOUT-ID-001/002/003 通过。

### FR-060 Sage.md / Lex.md 引用 quote_parser

**Bug**: `agents/Sage.md` / `agents/Lex.md` 未引用 `tools/quote_parser.py`。

**Fix**: 在 quote dialogue 阶段相关段落加 `tools/quote_parser.py --check-ready` / `tools/quote_parser.py --check-violations` 引用。

AC: `bats tests/test_spec004_sage_lex.bats` T05/T06 通过。

### FR-070 删/改过期测试

**删** (6+3=9 个):
- `test_branch_naming.bats` BRANCH-001/006/007/008/009/010（测过期分支约定）
- `test_probe.bats` PROBE-FORM-005/006/007（测 v0.5-008 已废的反模式声明）

**改** (3 个):
- `test_probe.bats` PROBE-FORM-001: 改测"Probe 引用 issue form 字段"（与 FORM-002 合并）
- `test_probe.bats` PROBE-FORM-002: 保留
- `test_probe.bats` PROBE-FORM-004: 改测"Probe 命名约定 UT-{issue#}-{AC序}-{测试序}"

AC: 跑全量 bats，0 失败（除 known-failing）。

### FR-080 run bats 0 fail + bump VERSION

- 跑 `bats tests/*.bats` 应达到 0 失败（或只剩 known-failing）
- VERSION 0.5.5 → 0.5.6
- commit + tag

## 验收标准

| ID | 描述 | 验证 |
|---|---|---|
| AC-010 | `tools/lint_bats_names.sh` 存在并能工作 | `bash tools/lint_bats_names.sh tests/*.bats` exit 0 |
| AC-020 | quote_parser `is_ready` 算法修复 | `bats tests/test_quote_parser.bats` 22/22 通过 |
| AC-030 | quote_parser JSON 含 owner_close_role | `bats tests/test_quote_parser.bats` 22/22 通过 |
| AC-040 | verify_acceptance L2 修 | `bats tests/test_verify_acceptance.bats` 7/7 通过 |
| AC-050 | Scout.md 修 | `bats tests/test_scout_project_board.bats` 6/6 通过 |
| AC-060 | Sage.md + Lex.md 修 | `bats tests/test_spec004_sage_lex.bats` 8/8 通过 |
| AC-070 | 过期测试删除/修改 | `bats tests/test_branch_naming.bats` 仅剩 5 个 ASCII-passing 测试 |
| AC-080 | 全量 bats 0 fail | `bats tests/*.bats | grep -c "^not ok"` = 0 |
| AC-090 | VERSION 已 bump | `cat VERSION` = `0.5.6` |
| AC-100 | 已 commit + tag | `git tag | grep v0.5.6` |

## 任务拆解

```
T1. 写 tools/lint_bats_names.sh          (~30 行)
T2. 修 quote_parser.py is_ready           (~5 行改)
T3. 修 quote_parser.py JSON schema        (~10 行加)
T4. 修 verify_acceptance.py L2 regex      (~5 行拆)
T5. 修 agents/Scout.md (3 处)             (~10 行加)
T6. 修 agents/Sage.md + Lex.md (各 1 段)  (~10 行加)
T7. 删 BRANCH-* 6 个 + PROBE-FORM 005/006/007 3 个 + 改 PROBE-FORM-001/002/004 3 个
T8. 跑全量 bats 验证 0 fail
T9. bump VERSION 0.5.5 → 0.5.6 + commit + tag
```

## 风险

- **R-010** 改 quote_parser `is_ready` 算法可能影响下游 spec 004 gate 行为（spec 004 用户原本依赖 `len(ready_blockers)==0`）
  → 加 `result.is_ready_open_quotes_only` 旁路字段保留旧行为；默认改新行为
- **R-020** 删 BRANCH-* 测试可能丢失 v0.4 时期的回归保险
  → 在 `tests/test_branch_naming.bats` 顶部加注释说明这些约定已退役，新约定在 ADR 005
- **R-030** 修 Scout.md / Sage.md / Lex.md 可能引入 prompt 不一致
  → 改完跑 `bats tests/test_*.bats` 中所有引用这些 agent 的测试，确保无新失败
