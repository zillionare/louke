#!/usr/bin/env bash
# review-watcher.sh — 监控 review 文件变化, 输出到日志
#
# 用法:
#   REVIEW_FILE=path/to/file review-watcher.sh
#
# 行为:
#   每 5 秒 poll 一次 REVIEW_FILE 的 mtime + md5
#   若变化, 打印 "[CHANGED @ <ts>] <diff hint>" 到 stdout
#   Ctrl-C 停止
set -uo pipefail

REVIEW_FILE="${REVIEW_FILE:-.louke/qwen-review-v0.6-009.md}"
POLL_INTERVAL="${POLL_INTERVAL:-5}"

if [ ! -f "$REVIEW_FILE" ]; then
  echo "[watcher] ERROR: $REVIEW_FILE not found" >&2
  exit 1
fi

echo "[watcher] monitoring $REVIEW_FILE (poll=${POLL_INTERVAL}s)"

last_md5=""
last_mtime=0
last_size=0

while true; do
  if [ ! -f "$REVIEW_FILE" ]; then
    echo "[watcher] $(date +%H:%M:%S) file disappeared"
    sleep "$POLL_INTERVAL"
    continue
  fi
  cur_md5=$(md5 -q "$REVIEW_FILE" 2>/dev/null || md5sum "$REVIEW_FILE" 2>/dev/null | awk '{print $1}')
  cur_mtime=$(stat -f %m "$REVIEW_FILE" 2>/dev/null || stat -c %Y "$REVIEW_FILE")
  cur_size=$(wc -c < "$REVIEW_FILE" | tr -d ' ')
  if [ -n "$last_md5" ] && [ "$cur_md5" != "$last_md5" ]; then
    delta=$((cur_size - last_size))
    sign=$([ "$delta" -ge 0 ] && echo "+" || echo "")
    echo "[CHANGED $(date +%H:%M:%S)] md5=${cur_md5:0:8} size=${cur_size} (${sign}${delta})"
  fi
  last_md5="$cur_md5"
  last_mtime="$cur_mtime"
  last_size="$cur_size"
  sleep "$POLL_INTERVAL"
done
