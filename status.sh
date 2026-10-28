#!/usr/bin/env bash

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

PID_FILE="$DIR/monitor.pid"
LOG_FILE="$DIR/monitor.log"

echo "================ 監控狀態 ================"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "狀態: 🟢 運行中 (PID: $PID)"
    else
        echo "狀態: 🔴 已停止 (PID 檔案存在但行程已不在)"
    fi
else
    RUNNING_PIDS=$(pgrep -f "python3.*monitor.py" || true)
    if [ -n "$RUNNING_PIDS" ]; then
        echo "狀態: 🟡 運行中 (未透過 start.sh 啟動，PID: $RUNNING_PIDS)"
    else
        echo "狀態: ⚪ 未在運行"
    fi
fi
echo "=========================================="

if [ -f "$LOG_FILE" ]; then
    echo -e "\n📋 最近 15 行日誌內容:"
    echo "------------------------------------------"
    tail -n 15 "$LOG_FILE"
    echo "------------------------------------------"
fi
