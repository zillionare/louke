# v0.7-002 Implementation Code Review

- **Reviewer**: QoderWork (Aaron 委托)
- **日期**: 2026-07-05
- **审查范围**: librarian.py (505行) / init.py (272行) / Librarian.md (167行) / spec.md (827行) / acceptance.md (360行)
- **验证方法**: 静态分析 + 端到端 fixture 测试（M0/M1/M2/rewrite/dry-run/M2→M0 转换）

---

## 验证命令结果汇总

| # | 命令 | 预期 | 实际 | 通过 |
|---|---|---|---|---|
| 1 | `grep yesterday/timedelta` | `timedelta(days=1)` 用于上限 | L341 `yesterday = (today - timedelta(days=1)).isoformat()` | PASS |
| 2 | `grep _cleanup_old_bundles` | compact 步骤 0 调用 | L263 def + L333 调用 | PASS |
| 3 | `grep model_flag/--model` | 优先级链 `--model > --model-from-config > frontmatter` | L457-471 三级 `if/elif/默认` | PASS |
| 4 | `grep openai/anthropic` | 无命中 | EXIT 1 (无命中) | PASS |
| 5 | `grep 'librarian compact' init.py` | L167 命中 | `f'cd {project_path} && {lk_path} librarian compact '` | PASS |
| 6 | `grep cmd_from_raw/cmd_daily` | 无命中 | EXIT 1 (无命中) | PASS |
| 7 | `python -m louke agent librarian --help` | 5 子命令含 compact/rewrite | 正确：distill/lint/rebuild-index/compact/rewrite | PASS |

**端到端 fixture 测试**：

| 场景 | 预期 | 实际 | 通过 |
|---|---|---|---|
| M0 compact（1 dated + 1 no-date raw） | no-date 跳过+warning, 1 bundle, cache 更新 | `[compact] WARN: 1 个 raw 条目无 date 字段, 已跳过` + bundle 仅含 dated entry + cache `last_distill=2026-07-04` | PASS |
| rewrite 无 bundle | stderr 报错, exit 1 | `error: .compact-bundle.md 不存在, 请先跑 lk librarian compact` + RC=1 | PASS |
| rewrite dry-run | 打印 cmd 预览, 不调 opencode | `[dry-run] cmd: opencode run --agent librarian -- <prompt>` + RC=0 | PASS |
| rewrite --model dry-run | `--model gemini-1.5-pro` 透传 | `[dry-run] cmd: opencode run --agent librarian --model gemini-1.5-pro -- <prompt>` | PASS |
| rewrite M2 dry-run | 选 merged bundle | `[dry-run] .compact-bundle-merged.md (M2_map_reduce)` | PASS |
| rewrite --full 覆盖 M2 | 选 main bundle | `[dry-run] .compact-bundle.md (M0/M1_full)` | PASS |
| M2 compact（12 月 × 70K chars） | 12 monthly + 1 merged | 13 files, 正确命名 `.compact-bundle-2025-{01..12}.md` + `-merged.md` | PASS |
| M2→M0 转换 | 旧 M2 bundles 清理 | `[compact] 清理 13 个旧 bundle` → M0 后 0 bundles | PASS |

---

## Must-Fix（阻塞合并）

### 1. Librarian.md 未重写 —— spec FR-0120 全部未实施

**严重程度**: P0（agent prompt 引用已删除的命令，cron 执行时 LLM 会尝试调不存在的 CLI）

**现状**：Librarian.md 仍然是旧版（167 行未变），包含：

| 残留内容 | 行号 | 问题 |
|---|---|---|
| `lk librarian daily [--dry-run]` | L41 | 命令已删除（FR-0080） |
| `lk librarian from-raw --since` | L42 | 命令已删除（FR-0080） |
| `cmd_daily` 引用 | L121 | 函数已删除 |
| `cmd_from_raw` 引用 | L123 | 函数已删除 |
| `from-raw` 作为页面写入路径 | L59, L93, L99 | 功能已废弃 |
| `lk librarian daily` cron 触发 | L111, L120 | cron target 已改 compact |
| 无 `compact` / `rewrite` | — | grep 零命中 |
| 无"调用模式识别"段 | — | FR-0120.1 未实施 |
| 无"上下文窗口策略"段 | — | FR-0140 未体现 |

**Spec 要求**（FR-0120）：
- §1 Identity 改英文（已符合 —— 旧版 §1 已是英文）
- §2.1 CLI 表更新为 compact/rewrite/distill/lint/rebuild-index —— **未做**
- §2.3 permissions 加 bundle 写入权属澄清 —— **未做**
- §5 workflow 改写为 compact→rewrite 流程 —— **未做**
- 新增"调用模式识别"段（TUI subagent vs CLI 批处理）—— **未做**

**影响**：LLM 作为 Librarian 执行时，会按 §5.2.A 调用 `lk librarian daily`，命令不存在 → cron 日志报错 → 蒸馏静默失败。

**建议**：这是阻塞项。Librarian.md 必须重写后才能合并。需要更新的内容清单：

1. §2.1 CLI 表：删除 daily/from-raw，加 compact/rewrite（含新 flag）
2. §2.3 permissions：加 bundle 写入权属段（python 写 bundle，不经 LLM edit）
3. §4 三层架构：更新页面写入路径描述（from-raw → compact+rewrite）
4. §5.1 触发条件：`lk librarian daily` → `lk librarian compact`
5. §5.2 步骤 A：改为 compact→rewrite 流程
6. 新增"调用模式识别"段（FR-0120.1）
7. 新增"上下文窗口策略"段（FR-0140）
8. §7 反模式：更新"全量重写 index"措辞（index 由 rebuild-index 生成，不是 LLM 重写）

---

### 2. `cmd_distill` 未按 spec 重定义为 wrapper

**严重程度**: P0（spec §0.2 / NFR-0010 AC-3 明确要求语义变更）

**Spec 要求**（§0.2 第 2 条）：
> 既有 `lk librarian distill`（仅 print 待蒸馏列表）—— **保留 + 重定义**：语义改为"列出待 compact 的 raw"，由 `cmd_distill` 改为 wrapper 调 `cmd_compact --dry-run`

**Acceptance 要求**（NFR-0010 AC-3）：
> `lk librarian distill --source X --target Y` 仍可用；语义改为 wrapper 调 `compact --dry-run`

**实际代码**（librarian.py:110-143）：`cmd_distill` 仍是旧的独立实现（扫描 raw + 打印清单），没有调用 `cmd_compact`。末尾仍打印 `下一步: LLM 阅读这些条目, 蒸馏后用 lk librarian write <wiki-page> 写入` —— `lk librarian write` 命令不存在。

**建议**：将 `cmd_distill` 改为：

```python
def cmd_distill(args):
    """列出待 compact 的 raw 条目. Wrapper 调 cmd_compact --dry-run."""
    compact_args = argparse.Namespace(
        dry_run=True,
        threshold_tokens=50_000,
        m2_threshold=200_000,
    )
    return cmd_compact(compact_args)
```

或保留 `--source`/`--target` 参数但标记 deprecated。

---

## Should-Fix（建议修复）

### 3. `.gitignore` 缺 `.compact-bundle*.md` 条目

**严重程度**: P1

**Spec §6** 关联文件表声称 `.gitignore` 加 `.louke/wiki/.compact-bundle*.md`（bundle 是临时中间产物）。实际 `.gitignore` grep `compact` 零命中。只有 `.louke/raw/` 存在。

Bundle 文件以 `.` 开头（hidden），通常不会被 git 主动追踪，但如果有人 `git add -f .louke/wiki/` 会意外提交。

**建议**：在 `.gitignore` 加一行 `.louke/wiki/.compact-bundle*.md`。

### 4. M2 rewrite 不做 Map-Reduce —— spec scenario-0300 与代码/AC 不一致

**严重程度**: P1（spec 内部不一致）

| 维度 | Map-Reduce (12+1 调用) | Merged-only (1 调用) |
|---|---|---|
| spec scenario-0300 | 12 次 map + 1 次 reduce | — |
| spec FR-0140.3 伪代码 | `for b in bundles[:-1]: opencode_run(...)` + reduce | — |
| spec FR-0140.1 表 | "块数 + 1" LLM 调用 | — |
| 代码 cmd_rewrite | — | 选 merged → 1 次 opencode run |
| acceptance AC-2 | — | "调用 1 次 reduce LLM" |

代码 + acceptance 是一致的（merged-only，1 次调用），但与 spec scenario-0300 + FR-0140.3 伪代码矛盾。

**实际含义**：merged bundle 包含所有 raw 全文（`_write_bundle(merged, matched, ...)`），所以 1 次 LLM 调用 = 全量喂入，本质上不是"reduce"而是"全量处理"。如果 token 超模型窗口（这正是 M2 的存在理由），单次调用也会失败。

**建议**：二选一 ——
- (A) 修正 spec scenario-0300 + FR-0140.3 为 "merged-only"（承认 M2 只是分块存储但 LLM 仍一次处理 merged），但需解决"merged 包含所有 raw 所以 token 量没减少"的问题
- (B) 修正代码实现真正的 Map-Reduce（每月 1 次 opencode run 产 mini-distillation → 最后 1 次 reduce 合并）

(A) 更简单但语义不诚实；(B) 符合 spec 但需多写 `build_map_prompt` / `build_reduce_prompt` + 循环。

### 5. spec 内部残留矛盾：FR-0090 + 附录 A 仍引用 v0.7-001 管 cron

**严重程度**: P1

spec 新增 FR-0150 将 cron 安装归属 v0.7-002，但以下位置仍残留旧的 v0.7-001 引用：

| 位置 | 内容 | 问题 |
|---|---|---|
| FR-0090 L325 | "cron 入口（在 `v0.7-001` 安装）" | FR-0150 已将 cron 安装移入 v0.7-002 |
| 附录 A L823 | "在 v0.7-001 实施（cron 框架）" | 同上 |

**建议**：FR-0090 改为"cron 入口（由 FR-0150 安装）"；附录 A 的 `lk init --install-cron` 行改为"v0.7-002 FR-0150 实施"。

### 6. acceptance.md 行号引用错误

**严重程度**: P1

| 位置 | 引用 | 实际 |
|---|---|---|
| FR-0110 AC-4 | `librarian.py:131-151` | 新代码 `cmd_rebuild_index` 在 L199-218；`131-151` 是旧代码坐标 |

实现者如果按 acceptance 行号去定位 `cmd_rebuild_index` 会找错位置。

**建议**：改为 `librarian.py:199-218`（或干脆去掉行号引用，用函数名 `cmd_rebuild_index` 更稳定）。

---

## Nice-to-Have（改善建议）

### 7. M2 merged bundle 的 `_write_bundle` 调用语义混淆

**位置**: librarian.py:414

```python
_write_bundle(merged, matched, f'M2:merge', existing_pages, args.dry_run)
```

merged bundle 的 body 包含所有 raw 全文（与 scenario-0300 描述的"引用所有 12 bundle"不同）。header 说 `Bundles: ['2025-01', ...]`（暗示引用），body 却内联了全部数据。

如果保留 merged-only 模式（不做真 Map-Reduce），建议把 merged bundle 的 body 改为仅列出 sub-bundle 文件名 + 各自摘要（不含 raw 全文），让 LLM 在 rewrite 时自行读取各 sub-bundle。

### 8. `cmd_compact` 零输出路径重复读 cache

**位置**: librarian.py:358-364

```python
if not matched:
    print('[compact] 无新 raw 待蒸馏, 零输出')
    if not args.dry_run:
        cache = _read_cache()         # 重复读: L338 已经读过一次
        cache['last_distill'] = yesterday
        _write_cache(cache)
    return 0
```

L338 已经 `_read_cache()` 并存入 `cache` 变量。L362 再次 `_read_cache()` 是冗余的。虽然不会出错（compact 步骤 1 到步骤 7 之间没有其他进程改 cache），但不优雅。

### 9. `subprocess.run(cmd)` 无 `check=False` 显式声明

**位置**: librarian.py:505

```python
rc = subprocess.run(cmd).returncode
```

`subprocess.run` 默认 `check=False`（不抛异常），所以这里行为正确。但 `init.py` 的 subprocess 调用都显式写了 `check=False`（L150, L177）。建议 `cmd_rewrite` 也加上以保持一致性，同时防止将来有人加 `check=True` 破坏 exit code 透传逻辑。

### 10. M1 warning 输出在 compact 而非 rewrite

**位置**: librarian.py:386

M1 warning `建议 --model gemini-1.5-pro` 在 `cmd_compact` 输出。但 `--model` 是 `cmd_rewrite` 的 flag，用户跑 compact 时还没到想 rewrite 的阶段。Spec FR-0140.4 的 warning 描述也在 rewrite 上下文。

建议在 `cmd_rewrite` 也加 M1/M2 warning（检测 bundle token 量 + 当前模型是否匹配），这样用户跑 rewrite 时也能看到。

---

## acceptance.md 质量评估

**覆盖度**：FR-0070/0080/0090/0100/0110/0120/0130/0140/0150 + NFR-0010/0020/0050 + §0.4 wiki 命名空间 = 全覆盖。无遗漏 FR。

**可测试性**：大部分 AC 可断言（grep 命中/不命中、exit code、stdout 内容匹配）。少数 AC 描述性较强（如 FR-0120 AC-4 "§调用模式识别段说明 TUI subagent vs CLI 批处理"）但可人工审查。

**结构**：按 FR 编号分组 + AC 编号。末尾有关联文件覆盖度矩阵（与 spec §6 对齐）。

**发现的问题**：

| 问题 | 严重程度 |
|---|---|
| L136 `librarian.py:131-151` 行号引用是旧代码坐标 | should-fix |
| FR-0090 AC-1 引用 `FR-0150 已实施` 但 acceptance 本身定义了 FR-0150 节，交叉引用稍显循环 | nice-to-have |
| FR-0110 AC-2/AC-3 的 frontmatter/重复主题检查标注"首次实现"但代码尚未实施 —— AC 描述的是目标态不是现状，应在文档中标注 status=pending | nice-to-have |
| 无 bats 测试文件（`test_librarian_compact.bats` / `test_librarian_rewrite.bats`）存在 —— acceptance 末尾关联文件矩阵引用但不存在 | should-fix（spec §6 也声称新建） |

**总评**：acceptance.md 质量中偏高。覆盖完整、可断言性好、结构清晰。主要问题是行号引用过时 + 测试文件尚未创建。

---

## 总评

| 维度 | librarian.py | init.py | Librarian.md | spec.md | acceptance.md |
|---|---|---|---|---|---|
| **代码正确性** | PASS — 窗口/bundle/模型优先级/dry-run 全部验证通过 | PASS — 1 行改动正确 | **FAIL — 未重写** | PASS（修订后） | PASS |
| **与 spec 一致性** | 高（除 cmd_distill 未改） | 完全一致 | **严重偏离** | 内部残留 2 处旧引用 | 高（行号过时） |
| **异常处理** | 中 — subprocess 无显式 check=False；磁盘满/权限错靠 OSError catch | OK | N/A | N/A | N/A |

**合并判定**：阻塞。修复 2 个 must-fix（Librarian.md 重写 + cmd_distill wrapper）后可合并。should-fix 项（.gitignore、M2 不一致、spec 残留引用、acceptance 行号）建议本轮一并处理。

---

## 前次审查追踪

上轮审查（spec review 2026-07-05）14 个发现中：

| 发现 | 上轮状态 | 本轮状态 |
|---|---|---|
| P0-1 scenario-0200 日期错 | 待修 | **已修**（Day N 相对日期） |
| P0-2 cron 入口虚假引用 | 待修 | **已修**（FR-0150 + init.py:167） |
| P0-3 M2 旧 bundle | 待修 | **已修**（`_cleanup_old_bundles`） |
| P1-4 bundle 不清理 | 待修 | **已修**（compact 步骤 1） |
| P1-5 decisions/entries/consolidated | 待修 | **已修**（§0.4） |
| P1-6 edit 白名单漏 bundle | 待修 | **已修**（spec §2.3 权属段）—— 但 Librarian.md 未同步 |
| P1-7 model flag 优先级 | 待修 | **已修**（FR-0140.4 + 代码 L457-471） |
| P1-8 无 date raw 处理 | 待修 | **已修**（`_scan_resolved_raw` + skip/warning） |
| P2-9 措辞 | 待修 | **已修**（FR-0070 第 3 条） |
| P2-10 quote-dialogue 引用 | 待修 | **已修** |
| P2-11 幂等性 | 待修 | **已修** |
| P2-12 frontmatter 首次实现 | 待修 | **已修** |
| P2-13 rebuild-index 扁平 | 标注 | 标注为 v0.7-003 |
| P2-14 prompt 基线/扩展 | 待修 | **已修**（FR-0080 rewrite 段标注） |
