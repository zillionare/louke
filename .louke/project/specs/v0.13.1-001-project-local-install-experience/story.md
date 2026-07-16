# v0.13.1 Project-Local Install Experience + Release Identity Sync

## 目标

完成 v0.13.0 之后识别出的两个紧耦合缺口，使用户能在 5 分钟内把 louke 装到新项目、已有全局 louke 的用户能迁移到项目内 louke 而不动全局、release 时 louke 包版本自动与 git tag 同步。三者共享同一个 v0.13.1 release。

## 用户故事

1. 作为新用户，我希望从 Git clone 或空目录开始，在 5 分钟内通过一个明确的命令序列（`python -m venv .venv && pip install -e .` 或等价的封装）把 louke 装进当前项目的 `.venv/`，并得到一个 `lk --version` 能解析的、与项目当前 git commit 对应的 pinned runtime identity，以便后续命令与项目 lifecycle 一致。

2. 作为已有全局 louke 安装（`~/.louke/venv`）的用户，我希望通过一个项目内命令（如 `lk setup --local`）将 louke 安装到当前项目的 `.venv/` 并注册 pinned identity，**而全局 lk 安装不被修改、移除或升级**，以便项目与全局共存、不互相破坏。

3. 作为项目用户，我希望 `lk upgrade` 在不同 venv 下行为不同：项目根目录内执行时升级项目 `.venv/`；全局 shell 中执行时升级全局 venv；任一路径都不会越界写另一处，以便两种使用方式互不串扰。

4. 作为 release engineer，我希望 `git tag v0.13.x` 触发的 release workflow 在 build wheel 之前自动检查 `pyproject.toml` 的 `version` 字段是否等于 tag 名（去 `v` 前缀）；若不等，自动 commit 一个 `chore(release): bump version a → b` 并继续 build；若相等则直接构建，以便 release artifact 永远携带与 git tag 一致的 METADATA，不再出现 v0.13.0 wheel 报 0.12.1 的不一致。

5. 作为用户，我希望 `lk --version` 输出形如 `<package_version> (pinned: <pinned_version> or "unpinned")`，让我能一眼看出当前 lk 是按 pinned identity 跑的还是 unpinned 跑的，以便项目内运行时不会因为 METADATA 漂移而误判身份。

## 当前边界

- 本版本**只**涉及 install / upgrade / version-identity 三个动作；不动 RuntimeSelector、project store、UI 或 workflow engine。
- 本版本**不**改变 `~/.louke/venv` 作为全局默认安装路径的行为；现有 `install.sh` 默认模式不变，只增加 `--local <path>` 模式。
- 本版本**不**删除任何历史 release tag 或 wheel；v0.13.0 错误的 METADATA 作为历史保留。
- 本版本**不**为 Windows 原生平台提供 install 路径；WSL2/Docker 仍由 install.sh 的原有提示覆盖。
- 本版本**不**改 `lk agent` 子命令集合；install-related 命令只新增 `lk setup --local`，不动 `lk init`。
- 项目内 venv 的 Python 版本仍由 `python3 -m venv` 的发现策略决定（系统 python3）；本版本不强制 Python 3.11+ 检测，但若低于 3.11 则 `pip install` 会自然失败并显示明确信息。
