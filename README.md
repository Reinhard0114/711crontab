# 7-11 賣貨便商品庫存與補貨監控工具

輕量級 7-11 賣貨便庫存監控工具，無須安裝肥重的無頭瀏覽器（Puppeteer/Playwright），使用 Python 3 標準庫原生執行。當監控的商品有補貨時（庫存從 0 變成大於 0 或庫存增加），會自動發送通知。

---

## 快速開始

### 1. 前景測試運行（直接在終端機查看）
適合剛下載下來先測試抓取功能：
```bash
python3 monitor.py
```
如需中斷按 `Ctrl + C`。
### 2. 測試通知功能
確認你的 Mac 彈出通知或 Webhook 是否正常：
```bash
python3 monitor.py --test-notify
```

---

## 啟動與停止方式（背景常駐守護行程）

本專案提供好用的小腳本，可直接在背景持續監控：

### 啟動監控
```bash
./start.sh
```
> 會以 `nohup` 背景執行 `monitor.py`，並記錄 PID 至 `monitor.pid`，終端機關閉也不會中斷。

### 查看目前運行狀態與最新日誌
```bash
./status.sh
```

### 查看即時日誌
```bash
tail -f monitor.log
```

### 停止監控
```bash
./stop.sh
```

---

## 使用系統 Crontab 排程方式（可選）

如果你希望使用 macOS / Linux 內建的 `crontab` 定期每幾分鐘檢查一次（而不是 24 小時常駐程式），可以使用 `--once` 參數：

1. 開啟 crontab 編輯器：
   ```bash
   crontab -e
   ```
2. 新增以下排程（例如：每 5 分鐘執行一次檢查）：
   ```cron
   */5 * * * * cd /Users/reinhard.chu/code/711crontab && /usr/bin/python3 monitor.py --once >> monitor.log 2>&1
   ```
3. 儲存退出即可。

---

## 雲端 24 小時排程 (GitHub Actions)

本專案內建 GitHub Actions 排程工作流程（`.github/workflows/monitor.yml`），每 5 分鐘自動執行一次：

1. **設定 Discord Webhook 密鑰**：
   - 到你的 GitHub Repository 頁面 ➜ **Settings** ➜ **Secrets and variables** ➜ **Actions**。
   - 點擊 **New repository secret**。
   - Name 輸入：`DISCORD_WEBHOOK_URL`
   - Secret 輸入你的 Discord Webhook 網址。
2. **享受無限免費額度**：
   - 到 Repository 頁面 ➜ **Settings** ➜ 頁面最下方 **Danger Zone** ➜ **Change repository visibility** ➜ 設為 **Public**。
   - 公開專案在 GitHub Actions 享有**完全免費、無時間上限**的配額！

---

## 設定說明 (`config.json` 與 `config.local.json`)

你可以直接編輯專案目錄下的 `config.json` 來調整參數：

```json
{
  "target_url": "https://myship.7-11.com.tw/general/detail/GM2610178124354",
  "interval_seconds": 60,
  "notify_mac": true,
  "discord_webhook_url": "",
  "telegram_bot_token": "",
  "telegram_chat_id": "",
  "watch_keywords": []
}
```

### 參數解說：
| 欄位 | 預設值 | 說明 |
| :--- | :--- | :--- |
| `target_url` | 賣貨便網址 | 要監控的 7-11 賣貨便商品頁面網址。 |
| `interval_seconds` | `60` | 背景執行時每次檢查的間隔秒數（建議不低於 30 秒）。 |
| `notify_mac` | `true` | 在 Mac 上補貨時是否跳出 macOS 系統橫幅通知與提示音。 |
| `discord_webhook_url` | `""` | 可填入 Discord 頻道的 Webhook URL，補貨時會自動推播到頻道。 |
| `telegram_bot_token` | `""` | Telegram Bot Token（可選）。 |
| `telegram_chat_id` | `""` | 接收通知的 Telegram Chat ID（可選）。 |
| `watch_keywords` | `[]` | **過濾特定商品規格**。若為空 `[]` 會監控該頁面所有規格；若只想搶特定款，例如填入 `["洋流閃銀流沙版", "TAIWAN"]`，則只會在這些款式補貨時通報。 |

---

## 檔案結構說明

- `monitor.py`：主監控程式，包含解析商品庫存、比對變更與發送通知。
- `config.json`：設定檔。
- `stock_state.json`：記錄上一次各規格庫存數量的狀態檔（自動生成，重啟時不會洗版）。
- `monitor.log`：執行日誌。
- `start.sh`：啟動背景常駐行程。
- `stop.sh`：停止背景行程。
- `status.sh`：檢查運行狀態與近期日誌。
