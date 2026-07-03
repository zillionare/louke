# louke v0.6.1

**Patch release.** `lk board opencode` and `lk models doctor` now print per-stage progress so users can see what's happening during long-running commands. Also: `--quiet` flag added to suppress progress output.

## Highlights

- **Visible progress for `lk board opencode`**: 5 numbered stages — reading source agents → querying opencode models + parsing model bind → reading auth providers + cost index → resolving model bind + writing files → done. Each stage prints a one-line summary; per-file `[+]` (dry-run) or `[✓]` (written) line is also shown.
- **Visible progress for `lk models doctor`**: 4 numbered stages — scanning source agents → querying opencode models → reading auth.json + costs → 3-layer verification.
- **`--quiet` flag** on both commands for scripts that want a clean output (only final summary is printed).
- **Batched subprocess calls**: `opencode_models()` and `auth_providers()` are now called once per command, not once per agent. For 12 agents, this saves 12 redundant subprocess invocations.

## What's in this release

### `lk board opencode` progress

Old behavior: ~2-3 second silent wait, then `generated 12 OpenCode agents`.

New behavior:
```
[1/5] 读取 source agents: /Users/aaronyang/workspace/louke/agents
      发现 12 个 agent prompt
[2/5] 查询 opencode models + 解析 provider/model bind
      用户级 alias: /Users/aaronyang/.louke/models.json
      项目级 alias: /Users/aaronyang/workspace/louke/.louke/models.json
      调用 opencode models (N=5 abstract names)...
      opencode models 返回 64 个 model
[3/5] 读取 auth providers + cost index
      auth providers: 7 个 (['ark', 'copilot', 'joy']...)
      model costs: 64 个, 其中 free 12 个
[4/5] 解析 model bind + 写入 .opencode/agents/
      [+] archer       subagent   -> ark/glm-5.2
      [+] devon        subagent   -> kimi-2.7-code
      [✓] maestro      primary    -> ark/minimax-m3
      [✓] warden       subagent   -> ark/deepseek-v4-flash
      ... (12 total)
[5/5] 完成: 生成 12 个 OpenCode agent -> /Users/aaronyang/workspace/louke/.opencode/agents
```

Suppress: `lk board opencode --quiet`

### `lk models doctor` progress

```
[1/4] 扫描 source agents: 发现 8 个 abstract model
      样例: deepseek-v4-flash, deepseek-v4-pro, glm-5.2...
[2/4] 查询 opencode models (subprocess)...
      返回 64 个 model
[3/4] 读取 auth.json + model costs
      auth providers (7): ['ark', 'copilot', 'joy', 'local', 'minimax-cn', 'opencode', 'xfei']
      model costs: 64 个, 其中 free 12 个
[4/4] 三层验证 (alias → strong/weak match → auth filter)
✓ deepseek-v4-flash -> ark/deepseek-v4-flash (alias)
...
```

## Install / upgrade

```bash
# 升级
lk upgrade

# 新装
curl -sSL https://raw.githubusercontent.com/zillionare/louke/main/install.sh | bash
```

## Backward compatibility

- Output format change: `lk board opencode` output is more verbose by default. Add `--quiet` to scripts expecting the old terse output.
- No behavior change in the generated `.opencode/agents/*.md` files — same content as v0.6.0.

## License

MIT
