#!/usr/bin/env bash
# review-lock.sh — 文件锁助手, 用于 Kilo/Qwen 协作编辑 review 文件
#
# 用法:
#   review-lock.sh acquire <name>  # 尝试获取锁; 成功返回 0, 失败返回 1
#   review-lock.sh release         # 释放当前 <name> 持有的锁 (要求 name 匹配)
#   review-lock.sh status          # 显示锁状态 (FREE / held by <name>, age)
#   review-lock.sh force <name>    # 强制抢锁 (慎用; 仅用于 stale 锁恢复)
#
# 协议:
#   - 锁 = 一个目录, 路径由 REVIEW_FILE_PATH 环境变量决定 (默认 .louke/qwen-review-v0.6-009.lock/)
#   - 锁目录内含 `owner` 文件, 写持有者名字 + ISO 时间戳
#   - TTL = 600 秒; 超时未续期, 视为 stale, 下个 acquire 会自动抢
#   - 持有者编辑期间每 5 分钟 touch 锁目录 (mtime 续期)
#
# 双方调用顺序:
#   1. acquire <name>      # 拿到锁
#   2. (edit file ...)
#   3. release             # 释放锁
#   4. (对端: 看到 mtime 变化, 轮询 status; 锁 FREE 后 acquire)
set -euo pipefail

LOCK_DIR="${REVIEW_FILE_PATH:-.louke/qwen-review-v0.6-009.lock}"
TTL=600

acquire() {
  local name="$1"
  if [ -d "$LOCK_DIR" ]; then
    if [ -f "$LOCK_DIR/owner" ]; then
      local current_owner
      current_owner="$(cat "$LOCK_DIR/owner" 2>/dev/null || echo 'unknown')"
      local mtime
      mtime=$(stat -f %m "$LOCK_DIR" 2>/dev/null || stat -c %Y "$LOCK_DIR" 2>/dev/null || echo 0)
      local now
      now=$(date +%s)
      local age=$((now - mtime))
      if [ "$age" -gt "$TTL" ] && [ "${current_owner%% *}" != "$name" ]; then
        echo "[lock] stale lock (age=${age}s owner=${current_owner%% *}) — stealing"
        rm -rf "$LOCK_DIR"
      else
        echo "[lock] HELD by ${current_owner%% *} (age=${age}s)" >&2
        return 1
      fi
    else
      echo "[lock] HELD (no owner file)" >&2
      return 1
    fi
  fi
  mkdir -p "$LOCK_DIR"
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "$LOCK_DIR/acquired_at"
  echo "$name" > "$LOCK_DIR/owner"
  touch "$LOCK_DIR"
  echo "[lock] ACQUIRED by $name"
  return 0
}

release() {
  local name="${1:-}"
  if [ ! -d "$LOCK_DIR" ]; then
    echo "[lock] FREE (nothing to release)"
    return 0
  fi
  if [ -n "$name" ] && [ -f "$LOCK_DIR/owner" ]; then
    local current_owner
    current_owner="$(cat "$LOCK_DIR/owner" 2>/dev/null || echo '')"
    if [ "${current_owner%% *}" != "$name" ]; then
      echo "[lock] cannot release: owned by ${current_owner%% *}, not $name" >&2
      return 1
    fi
  fi
  rm -rf "$LOCK_DIR"
  echo "[lock] RELEASED"
  return 0
}

status() {
  if [ ! -d "$LOCK_DIR" ]; then
    echo "FREE"
    return 0
  fi
  local current_owner="unknown"
  if [ -f "$LOCK_DIR/owner" ]; then
    current_owner="$(cat "$LOCK_DIR/owner" 2>/dev/null || echo 'unknown')"
  fi
  local mtime
  mtime=$(stat -f %m "$LOCK_DIR" 2>/dev/null || stat -c %Y "$LOCK_DIR" 2>/dev/null || echo 0)
  local now
  now=$(date +%s)
  local age=$((now - mtime))
  local stale=""
  if [ "$age" -gt "$TTL" ]; then
    stale=" [STALE]"
  fi
  echo "HELD by ${current_owner} (age=${age}s)${stale}"
  return 0
}

force() {
  local name="$1"
  rm -rf "$LOCK_DIR"
  acquire "$name"
}

cmd="${1:-}"
shift || true
case "$cmd" in
  acquire)  acquire "$@" ;;
  release)  release "$@" ;;
  status)   status ;;
  force)    force "$@" ;;
  *)
    echo "usage: $0 {acquire <name>|release [name]|status|force <name>}" >&2
    exit 2
    ;;
esac
