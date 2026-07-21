# 三人并行协调 — spec-002 实施 + 三方 review

> 三位外部 AI / 工程师分工：
> - **Devon**：实施者，写 `louke/v014/002/` + `tests/unit/v014_002/`
> - **Shield**：测试者，写 `tests/integration/v014_002/` + `tests/e2e/v014_002/`
> - **Prism**：评审者，产出 `impl-review.md` (spec-002) 与 `design-review.md` (spec-003)

> 三人各自拥有独立 handoff，参阅各自 `HANDOFF.md`。
> 本文档是协调点：合并顺序、依赖关系、冲突面。

## 1. 时序与依赖

```
              ┌─→  Devon 实施 (louke/v014/002 + unit tests)  ─┐
spec-002  ────┤                                              ├──→  Prism 阶段 A (impl-review.md)
              └─→  Shield 集成 / e2e 测试  ─────────────────┘

                                                              同时 ↓
spec-002  ─→  spec-003 design review (Prism 阶段 B，可并行)
```

- **Devon 与 Shield 互不阻塞**（A + 阶段 A 的 mock / B 模式可立刻开跑）
- **Prism 阶段 A** 必须在 Devon + Shield 都完成后做
- **Prism 阶段 B** 可立即做（与 Devon/Shield 完全独立）

## 2. worktree 隔离（推荐）

```bash
git worktree add .worktrees/devon c654041 -b local/devon-v014-002
git worktree add .worktrees/shield c654041 -b local/shield-v014-002
git worktree add .worktrees/prism c654041 -b local/prism-review
```

三人各自 worktree，不冲突。完成时各自把分支 push 到本地 remote（如需要），然后 Maestro 合并。

## 3. 合并顺序（不要乱）

```bash
# 1. 先合 Devon (实施是基础)
git checkout c654041
git merge --no-ff local/devon-v014-002 -m "merge: spec-002 implementation by external Devon"
# → tag 这一时刻：impl-prep-2026-07-21Txxxx

# 2. 再合 Shield (测试叠加)
git merge --no-ff local/shield-v014-002 -m "merge: spec-002 host-project tests by external Shield"
# → Shield 的测试现在可对 Devon 的真实模块跑

# 3. 再合 Prism 阶段 A (impl-review)
git merge --no-ff local/prism-review -- .louke/project/specs/v0.14-002-workflow-reflow-design/impl-review.md -m "review: spec-002 post-impl by external Prism"
# → impl-review.md 现在落到主线

# 4. 合 Prism 阶段 B (design-review for spec-003)
git merge --no-ff local/prism-review -- .louke/project/specs/v0.14-003-workflow-reflow-impl/design-review.md -m "review: spec-003 design by external Prism"
```

## 4. 冲突面清单

| 冲突点 | 由谁控制 | 谁避免 | 协调 |
|---|---|---|---|
| `tests/runner-manifest.toml` | Shield（追加 suite） | Devon / Prism 不修改 | Shield 用 git add -p |
| `louke/v014/002/` | Devon | Shield / Prism 不写 | Devon 独占 |
| `tests/unit/v014_002/` | Devon | Shield / Prism 不写 | Devon 独占 |
| `tests/integration/v014_002/` | Shield | Devon / Prism 不写 | Shield 独占 |
| `tests/e2e/v014_002/` | Shield | Devon / Prism 不写 | Shield 独占 |
| `.louke/project/specs/v0.14-002-*/impl-review.md` | Prism 阶段 A | Devon / Shield 不写 | Prism 独占 |
| `.louke/project/specs/v0.14-003-*/design-review.md` | Prism 阶段 B | Devon / Shield 不写 | Prism 独占 |
| `.louke/handoff/...` | 不进 git | 全部避免 | N/A |
| `tests/conftest.py` (如新增全局 fixture) | Devon 决定 + 通知 Shield | Shield / Prism 不擅自加 | Shield 在 REPORT 里说"需要 conftest 支持 X" |

## 5. REPORT 期望格式（三人各自）

每人的 REPORT 必须写到：

| 角色 | 路径 |
|---|---|
| Devon | `.louke/handoff/2026-07-21-v0.14-002-impl-external/devon/REPORT.md` |
| Shield | `.louke/handoff/2026-07-21-v0.14-002-impl-external/shield/REPORT.md` |
| Prism | `.louke/handoff/2026-07-21-v0.14-002-impl-external/prism/REPORT.md` |

REPORT 不进 git，仅供 Maestro 阅。

## 6. 合并触发点（Master 等待条件）

Maestro 仅在以下全部满足时启动合并：

- [ ] Devon REPORT 标"完成"
- [ ] Shield REPORT 标"完成"
- [ ] Devon 的 `python3 -m pytest tests/unit/v014_002 -q` 全部 PASS
- [ ] Shield 的 `python3 -m pytest tests/integration/v014_002 tests/e2e/v014_002 -q` 全部 PASS（或显式标注 xfail 的 FR）
- [ ] AC 追溯 34/34
- [ ] 全套回归 `python3 -m pytest tests/unit -q` 不破 spec-001 的 657+2skip

## 7. 后续（合并后）

- 我（Maestro）打 batch tag `v0.14.0-002-impl`（参考 spec-001 的命名）
- 等 spec-003 设计 PASS 后，由 Devon + Shield 再做一次 spec-003 实施
- 最后打 `v0.14.0-003-impl` tag
- 三批完成后整体 `v0.14.0` 发布

## 8. 紧急协调

如果 Devon 和 Shield 之间出现真冲突（例如：Devon 的实现接口命名 ≠ interfaces.md 的契约），按以下优先级处理：

1. interfaces.md 是契约（不变）
2. Devon 必改实现以匹配契约
3. Shield 测试不动
4. 在 Devon REPORT 标 "residual: FR-XXXX 接口调整"

如果三人对 substantive gate / procedural gate 的判断不一致，写到自己的 REPORT，Maestro 仲裁。

## 9. 时序参考

```
T+0       : 三人同时开 worktree
T+0~T+90  : Prism 阶段 B (spec-003 设计评审)
T+0~T+360 : Devon 实施 34 个 FR/NFR
T+0~T+360 : Shield 实施集成/e2e（可与 Devon 并行，必要时 mock）
T+360     : Devon + Shield 同步完成
T+360~T+450 : Prism 阶段 A (spec-002 impl-review)
T+450~T+480 : Maestro 合并 + tag
```

## 10. 不要做的

- 不要让三人改 `.opencode/agents/**`。
- 不要让三人 push git（Maestro 决定 push 时机）。
- 不要让三人写 `pyproject.toml` / `requirements.txt` 改版本。
- 不要让 Prism 修改 `tests/`、`louke/`、`design-artifacts/`。
- 不要让 Devon/Shield 写 review 文件。

---

## 11. 给"找三人"的协调模板

发出去时附上各自 handoff：

```
[Devon 一句话]
请阅读 .louke/handoff/2026-07-21-v0.14-002-impl-external/devon/HANDOFF.md，
基于 commit c654041 实施 spec-002 的 louke/v014/002/ + tests/unit/v014_002/，
完成后把 REPORT 写到 .louke/handoff/2026-07-21-v0.14-002-impl-external/devon/REPORT.md。

[Shield 一句话]
请阅读 .louke/handoff/2026-07-21-v0.14-002-impl-external/shield/HANDOFF.md，
基于 commit c654041 写 spec-002 的 host-project 集成 + e2e 测试，
完成后把 REPORT 写到 .louke/handoff/2026-07-21-v0.14-002-impl-external/shield/REPORT.md。

[Prism 一句话]
请阅读 .louke/handoff/2026-07-21-v0.14-002-impl-external/prism/HANDOFF.md，
基于 commit c654041 做两件事：(A) spec-002 实施后回看（等 Devon/Shield 完成）；
(B) spec-003 独立设计评审（可立即做）。产出落到 spec-002/impl-review.md 和 spec-003/design-review.md。
```

如果对协调时序不清楚，参考本 README。
