#!/usr/bin/env bash

# 移動到當前腳本目錄
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

PID_FILE="$DIR/monitor.pid"
LOG_FILE="$DIR/monitor.log"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "⚠️ 監控程式已經在運行中 (PID: $PID)"
        echo "若要查看狀態可執行: ./status.sh"
        echo "若要停止可執行: ./stop.sh"
        exit 0
    else
        # 殘留的 PID 檔案
        rm -f "$PID_FILE"
    fi
fi

# 啟動背景行程 (stdout 交由 monitor.py 自行寫入 log 避免重複，stderr 記錄錯誤)
nohup python3 -u monitor.py > /dev/null 2>> "$LOG_FILE" &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

echo "✅ 監控程式已成功在背景啟動！(PID: $NEW_PID)"
echo "📄 即時日誌檔案: $LOG_FILE"
echo "🔍 查看即時日誌指令: tail -f monitor.log"
echo "🛑 停止指令: ./stop.sh"
