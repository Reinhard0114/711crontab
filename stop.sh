#!/usr/bin/env bash

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

PID_FILE="$DIR/monitor.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "ℹ️ 找不到 monitor.pid，程式可能未在運行。"
    # 額外檢查是否有 monitor.py 在跑
    RUNNING_PIDS=$(pgrep -f "python3.*monitor.py" || true)
    if [ -n "$RUNNING_PIDS" ]; then
        echo "發現殘留的 monitor.py 行程: $RUNNING_PIDS，正在強制關閉..."
        kill -9 $RUNNING_PIDS 2>/dev/null || true
        echo "✅ 已關閉。"
    fi
    exit 0
fi

PID=$(cat "$PID_FILE")

if ps -p "$PID" > /dev/null 2>&1; then
    kill "$PID"
    sleep 1
    if ps -p "$PID" > /dev/null 2>&1; then
        kill -9 "$PID"
    fi
    echo "🛑 監控程式已停止 (PID: $PID)"
else
    echo "ℹ️ 行程 (PID: $PID) 已經不在運行中。"
fi

rm -f "$PID_FILE"
