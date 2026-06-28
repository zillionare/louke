# holdpoint v0.1 — Acceptance (fixture for verify_issue_schema tests)

<a id="ac-fr-001"></a>
## FR-001

### AC-1
- agents/Maestro.md 等 14 个 prompt 文件存在
- 每个 agent 暴露 `register(subparsers)` + `run(args)`

### AC-2
- 12 个核心 agent 角色（Scout/Sage/Lex/Archer/Maestro/Devon/Prism/Keeper/Shield/Judge/Warden/Librarian）

<a id="ac-fr-002"></a>
## FR-002

### AC-1
- 10 个阶段代码（M-FOUND ~ M-MILESTONE）

### AC-2
- 阶段表在 agents/Maestro.md 中显式定义

<a id="ac-fr-003"></a>
## FR-003

### AC-1
- 任意阶段的实施者与评审者不重复

<a id="ac-fr-004"></a>
## FR-004

### AC-1
- `pip install holdpoint` 后 `hp --help` 可用

### AC-2
- `hp <agent> <command>` 子命令分发正确

<a id="ac-fr-005"></a>
## FR-005

### AC-1
- quote_parser --check-ready 在所有 quote resolved 时返回 0
