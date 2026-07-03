# louke v0.6.4

**Bugfix release.** `lk board opencode` and `lk board status` now require a git repository (or explicit `--root <path>`) instead of silently falling back to `Path.cwd()`. Previously, running these commands from a non-project directory would write `.opencode/agents/*.md` to a random location (potentially creating garbage files in `/tmp/` or wherever the user happened to be).

## Highlights

- **New `_require_project_root()` helper** in `louke/board.py`. Both `cmd_opencode` and `cmd_status` use it. Resolution priority: `--root` arg → `git_root()` → error with hint.
- **Clear error message** when no git repo and no `--root`:
  ```
  error: lk board opencode 需要 git 仓库 (或显式 --root).
    hint: 在 louke 项目根目录 (有 .git/) 跑, 或 --root <path>
  ```
- **`--root` flag added to `lk board opencode`** (was previously only on `lk board status`).
- **No files created** in non-project directories.

## What's in this release

### Before (v0.6.3, broken)

```python
def cmd_opencode(args):
    root = getattr(args, 'root', None) or git_root() or Path.cwd()
    # If git_root() returns None (not in git repo), silently uses Path.cwd()
    ...
    dest_dir = root / '.opencode/agents'  # Creates files wherever!
```

Reproduction:
```bash
$ cd /tmp/foo
$ lk board opencode
[5/5] 完成: 生成 12 个 OpenCode agent -> /tmp/foo/.opencode/agents
# 12 files in /tmp/foo/.opencode/agents/ — garbage
```

### After (v0.6.4, fixed)

```python
def cmd_opencode(args):
    root = _require_project_root(args, 'lk board opencode')
    if root is None:
        return 1
    ...
```

New behavior:
```bash
$ cd /tmp/foo
$ lk board opencode
error: lk board opencode 需要 git 仓库 (或显式 --root).
  hint: 在 louke 项目根目录 (有 .git/) 跑, 或 --root <path>
$ echo $?
1
$ ls /tmp/foo/.opencode/   # not created
ls: /tmp/foo/.opencode/: No such file or directory
```

Override:
```bash
$ lk board opencode --root /path/to/project   # works
```

### Why this matters

Before v0.6.4:
- Running `lk board opencode` from `/tmp/` or a random directory would create `.opencode/agents/` there.
- This pollutes the filesystem and could overwrite important files.
- No warning, no error — silent failure.

After v0.6.4:
- Same command from a non-project directory → error + hint, exit code 1.
- Explicit `--root` for non-default project locations.
- Project root always derived from git, not cwd.

## Backward compatibility

- Existing workflows that run `lk board opencode` from inside a louke project (i.e., inside a git repo with `.louke/agents/` or `agents/`) — no change in behavior.
- New `--root` flag for `lk board opencode` (was already on `lk board status`).
- No new dependencies, no API breaks.

## Install / upgrade

```bash
lk upgrade
lk --version    # lk 0.6.4
```

## License

MIT
