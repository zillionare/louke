# Scope Boundary Cheat Sheet — 评审者参考

> 当您判断一个发现是否构成 blocker 时，先用它过一遍。

## 1. 实质性 vs 程序性 区分

### 实质性 (substantive) — 应作为合法 blocker
- AC ↔ IF ↔ ARC ↔ contract 四向闭环缺失、orphan 或冲突。
- 文档编号格式错（FR/NFR 编号不连贯、AC ID 与 FR ID 不对应）。
- machine contract 缺必需字段、kind 错位、digest 失配。
- schema meta-invalid、instance 不 validate。
- 设计合同写死了 instance 应该承载的值（schema 不可复用）。
- candidate 与 active 边界不清，可能自证或自激活。
- secret / password / token / API key 明文出现在 candidate JSON。
- FR/NFR 与 Acceptance 不一致（orphan FR、缺少 AC、duplicate AC）。
- 三向 traceability 缺失：test-plan AC 没有 test layer / runner / fixture / CI job。

### 程序性 (procedural pseudo-gate) — 不应作为 blocker
- v0.14 Runtime registry/runner/prompt deployment 尚未激活到 `.opencode/agents/**`。
- candidate 必须现在就被部署 / 替换 `.opencode/agents/prism.md`。
- 7 类 machine contract 必须已经安装到 `.louke/project/contracts/`。
- 实际 CI 必须跑过 `real-smoke` / `publish` job。
- `lk agent maestro advance` 退出 0（CLI 反映 v0.13.1 stale 状态属预期）。
- `lk agent devon commit-rgr` 可用（v0.14 中是过渡工具，不作为规范）。
- Host-authenticated 二次 M-LOCK（实施后再次门禁）必须执行。
- story.md / spec.md / acceptance.md 中存在 `PLACEHOLDER` 字样 — 这是合法标识，digest 由 Runtime 计算。
- prompt candidate 的 `digest_source` 字段、bundle digest scope 与 active deployment digest 不一致 — 这恰好是 Prism round 5 B-1/B-3 标的问题，是 substantive；不是程序性。

## 2. 不要给出的建议

- 不要建议"先激活 v0.14 Runtime 再评审"。这是循环论证。
- 不要建议"用 v0.13 的 lk agent 命令验证"。v0.13 工具输出是 stale 的，不作权威。
- 不要建议"删除 candidate 改用 inline"。candidate 是设计 baseline，不应被删除。
- 不要建议"把 spec 002 / 003 拆得更细"。它们已经按功能 release 切分。
- 不要建议"重写 design bundle 让我再评审"。评审者职责是评审，不是改写。

## 3. 不要假设的事情

- 不要假设 `.opencode/agents/prism.md` 是 candidate 的镜像。它是 active trusted reviewer；与 candidate 是两个独立 identity。
- 不要假设 `louke/agents/Archer.md` 是 spec-002 设计 baseline 的一部分 — 它属于 candidate prompt bundle，受 FR-1700 约束，由 spec-002 引入。
- 不要假设 `tests/runner-manifest.toml` 或 `.github/workflows/louke-ci.yml` 已被外部 CI 消费 — 这些都是 candidate / 实施产物。
- 不要假设 spec-001 的 24 个 issue 在 spec-002 / 003 评审中相关 — 它们是独立 spec。

## 4. 项目状态一句话总结

- spec-001: done。v0.14 单元 207/207 + 整套 657/657+2skip + AC 82/82。HEAD `63d0da3`，tag `v0.14.0-001-impl`。
- spec-002: requirements/lifecycle 通过；design candidate bundle 完整但有 3 个 substantive blocker（Prism round 5 REJECT）。
- spec-003: requirements/lifecycle 通过；design baseline 已写但未做独立 review。
- 工具层：v0.13 的 `lk agent *` CLI 仍可用但语义反映 v0.13.1；v0.14 Runtime/registry/runner/prompt 正在 spec 002/003 实施中产生。

## 5. 您可能用得上的链接

- 实施批 commit 列表：`git log 1d88e61..63d0da3 --oneline`
- spec-002 candidate 设计：`.louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/`
- spec-003 设计：`.louke/project/specs/v0.14-003-workflow-reflow-impl/`
- 流程速览：`.louke/project/specs/v0.14-003-workflow-reflow-impl/flow.md`
