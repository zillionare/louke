# qf — quanti-forge CLI

工具统一入口。每个 agent 一个子命令空间（`qf {agent} {command}`），
避免在 `agents/*.md` 中出现裸 bash 多步命令。

## 用法

```bash
qf <agent> <command> [options]

# Examples
qf scout identity-check --repo owner/repo
qf sage quote-check --spec v0.1-001-init
qf warden foundation-check --repo owner/repo --version v0.1 --spec-id v0.1-001-init
qf lex verify-acceptance --spec v0.1-001-init
qf archer ci-scan --spec v0.1-001-init
qf judge security-audit --release releases/v0.1 --baseline main
qf prism review --diff HEAD~1..HEAD
qf keeper gate --commit-range HEAD~1..HEAD --tests
qf devon run-tests --scope unit
qf shield run-e2e --spec v0.1-001-init
qf librarian lint --wiki .specforge/wiki
qf maestro status
```

## 设计原则

1. **每 agent 一个入口文件** (`qf/{agent}.py`)
2. **agent 不直接调底层脚本**——通过 `qf {agent}` 调用
3. **多步命令封装成单个 qf 命令**——减少出错可能

## Agent 命令一览

| Agent | 命令 | 用途 |
|---|---|---|
| scout | identity-check | 验证 gh/git 账号一致 (Step 4a) |
| scout | foundation | 完整奠基流程 (Steps 1-8, 交互式) |
| scout | commit-foundation | 提交奠基产物 (Step 8: 多步 git 操作) |
| sage | quote-check | 检查 spec.md 所有 quote 是否 ✓ resolved |
| sage | commit-spec | 提交 spec + acceptance (多步 git 操作) |
| sage | create-issues | 从 spec 创建 GitHub issues |
| sage | lock-spec | 锁定 spec.md |
| warden | foundation-check | F1-F11 自动化检查 |
| lex | verify-acceptance | L1-L5 结构化校验 (Stage 1) |
| lex | verify-issue | L1-L8 schema 验证 (Stage 3) |
| lex | quote-check | 同 sage quote-check (复用) |
| archer | ci-scan | CI 扫描（AC 引用 + 反模式） |
| archer | check-acs | AC 引用闭合检查 |
| archer | commit-design | 提交 test-plan + architecture + interfaces |
| keeper | gate | per-commit gate (commit 格式 + 可选 tests) |
| keeper | regression | 回归判断 (per-bug-fix, 对比范围) |
| judge | security-audit | per-milestone 深度安全审计 (S 级) |
| judge | quick-scan | 浅层安全 pattern 扫描 (per-PR) |
| prism | review | 完整 review (生产 + 测试 + 安全) |
| prism | test-patterns | 测试反模式扫描 (8 类 + AC 引用) |
| prism | security-quick-scan | 浅层安全 pattern |
| prism | code-quality | 代码质量 (函数长度 / 嵌套深度) |
| devon | run-tests | 运行测试 (按 scope: unit/integration/e2e/all) |
| devon | commit-rgr | R-G-R commit (强制 phase 前缀) |
| devon | branch-create | 创建任务分支 feat/{spec-id}/{task-id} |
| shield | run-e2e | 运行 e2e 测试 |
| shield | commit-e2e | 提交 e2e 测试 (多步 git 操作) |
| shield | scaffold | 生成 e2e 骨架 (Playwright/testclient/DB 三种模板) |
| librarian | distill | raw → wiki 蒸馏 (LLM 蒸馏的 qf 包装) |
| librarian | lint | wiki 健康检查 (broken links + orphans) |
| librarian | rebuild-index | 重建 wiki index.md |
| librarian | from-raw | 从 raw 自动归档 resolved 条目到 wiki 草稿 |
| maestro | status | 查看当前 spec/milestone 阶段进度 |
| maestro | advance | 推进到下一阶段 (检查退出条件) |
| maestro | regress | 退回当前阶段 (记录原因到 raw) |
| maestro | escalate | 上报用户 (生成告警消息) |

## 安装

```bash
# 方式 1: pip install -e . (开发模式)
pip install -e .

# 方式 2: 直接调用 (无需安装)
python3 -m qf --help
```

## 退出码

- `0` = 通过 / 命令成功
- 非零 = 失败（critical/high 发现 / 命令失败）

## 相关文档

- `agents/` — 各 agent 的 prompt（含 qf 命令使用说明）
- `agents/REVIEW-PAIRINGS.md` — 评审配对关系
- `agents/ROSTER.md` — 阶段表与角色清单
- `templates/security-checklist.md` — 安全审计基线