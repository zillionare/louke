---
spec_id: v0.12-001-programmatic-workflow-runtime
kind: m-lock
status: approved
approved_by: Aaron
approved_at: 2026-07-13
m_dev_status: not_started
contract_digest: sha256:b6c095d551607a204f962c115f5f8137fa24ba22158ad23c4d8376b045f72d9c
---

# v0.12-001 M-LOCK Record

## 人类批准

> **Codex** [RESOLVED]: M-ARCH 已完成并由 Archer/Prism 校验通过。请确认 architecture.md、interfaces.md、test-plan.md 共同构成的设计合同可以进入 M-LOCK；批准后只锁定合同，不会开始业务实现。
>> **Aaron**: 已评审，现在请锁定。但不要开始业务实现

本记录将该明确批准绑定到下列六份合同的精确字节版本。任何一份变化都会使本 M-LOCK 失效，必须重新 review、重新生成 digest 并再次由 human principal 批准。

## 绑定合同

`contract_digest` 是依次以 `filename + space + sha256 + newline` 串接下表六行后计算的 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| `story.md` | `1905dff23dd74f8b4918cdb78475586205bebf7132982b6e14a315c11973afe4` |
| `spec.md` | `515e876fc91935767cb29b7332df057497d7ca0eb3b25431c4ab6fc94d477b47` |
| `acceptance.md` | `09810ca9ebf1799e79884295c2d503245d33fc51af11ed7c0f1f61a1115cd907` |
| `test-plan.md` | `51855b08e4a7fd838219e36b114d2b3576aeb5709afe45e540efea8b03e84842` |
| `architecture.md` | `7cbc869da8bcdd928dd6f9dd2c118665b76fb8e0887e95365445aa8a913b8031` |
| `interfaces.md` | `72a79da03957873f8ed410a3b1a08d3deb2f3ee6c5382663fcfd6411eb4c912a` |

## 已通过的锁定前检查

- Sage inline-discussion gate：6 个 threads 全部 resolved，`quote-check` 通过。
- Lex acceptance closure：30/30 FR/NFR、144/144 AC，L1—L5 全部通过。
- Sage M-TESTPLAN review：通过。
- Archer test-plan 与 architecture contract：通过。
- Prism M-ARCH review：通过，且 review artifact 的 `source_command=review`。

相应的机器审计记录在 `.louke/project/stage-results/v0.12-001-programmatic-workflow-runtime/`。

## 旧锁定工具的边界

旧 `lk agent sage record-lock` 在写入 `spec.md` 前额外要求 GitHub Project 校验。该检查不适用于本合同：D2 已明确 v0.12 不创建 GitHub Project，且当前历史 Project 只读查询返回失败。Feature issue schema 读取校验为通过（当前尚无 v0.12 Feature issues）；实现 task/issue 的映射仍是本合同中 M-DEV 后、由 trace gate 验证的工作，不以旧 Project gate 代替本次 human M-LOCK。

因此本记录是 v0.12 的权威 M-LOCK 证据；它没有调用或启动 Devon、Shield、实现 worktree、业务代码、测试代码或发布动作。

## 锁定结果

- `story.md`、`spec.md`、`acceptance.md`、`test-plan.md`、`architecture.md`、`interfaces.md` 已共同锁定。
- `.louke/project/project.toml` 的当前阶段为 `M-LOCK`，状态为已批准但 M-DEV 尚未开始。
- 用户明确禁止在本次锁定后自动开始业务实现；任何 M-DEV 入口必须等待新的明确授权。
