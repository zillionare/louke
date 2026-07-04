"""lk - louke CLI.

工具统一入口。每个 agent 一个入口文件 (louke/{agent}.py)，agent prompt 通过
`lk <agent> {command} [--args]` 调用，避免在 agents/*.md 中出现裸 bash 多步命令。

设计原则:
1. 每 agent 一个入口文件 (louke/{agent}.py)
2. agent 不直接调底层脚本，而是通过 `lk <agent>` 调用
3. 多步命令封装成单个 `lk` 命令，减少出错可能
4. 子命令内部可用 subprocess 调底层工具 (louke/_tools/*.py)，或实现新逻辑
5. 退出码遵循 Unix 惯例: 0 = 成功, 非 0 = 失败
"""
__version__ = "0.6.12"

# v0.6-009 NFR-0040: 最低 OpenCode 版本 (Qwen A-8.4 校准)
# permission 对象格式 (替代 deprecated tools 字段) 引入于 OpenCode v1.1.1
MIN_OPENCODE_VERSION = "1.1.1"
