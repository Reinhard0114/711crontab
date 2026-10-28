#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
7-11 賣貨便商品庫存監控腳本
支援常駐循環監控與單次執行（配合 crontab）
"""

import os
import sys
import time
import json
import html
import re
import argparse
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
LOCAL_CONFIG_FILE = BASE_DIR / "config.local.json"
STATE_FILE = BASE_DIR / "stock_state.json"
LOG_FILE = BASE_DIR / "monitor.log"

DEFAULT_CONFIG = {
    "target_url": "https://myship.7-11.com.tw/general/detail/GM2610178124354",
    "interval_seconds": 60,
    "notify_mac": True,
    "discord_webhook_url": "",
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "watch_keywords": []  # 若為空代表監控該頁面所有商品；可填入關鍵字如 ["洋流閃銀流沙版", "TAIWAN"]
}

def load_config():
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        cfg = DEFAULT_CONFIG.copy()
    else:
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = DEFAULT_CONFIG.copy()
                cfg.update(json.load(f))
        except Exception as e:
            log(f"讀取 config.json 失敗: {e}，使用預設設定")
            cfg = DEFAULT_CONFIG.copy()

    # 載入 config.local.json (本機私有設定，不進 git)
    if LOCAL_CONFIG_FILE.exists():
        try:
            with open(LOCAL_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception as e:
            log(f"讀取 config.local.json 失敗: {e}")

    # 支援透過環境變數覆寫 Webhook（適用於 GitHub Actions Secret）
    webhook_env = os.environ.get("DISCORD_WEBHOOK_URL")
    if webhook_env:
        cfg["discord_webhook_url"] = webhook_env

    return cfg

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass


def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"儲存狀態檔案失敗: {e}")

def notify_mac(title, message):
    if sys.platform != "darwin":
        return
    try:
        # 替換雙引號避免 AppleScript 語法錯誤
        safe_title = title.replace('"', '\\"')
        safe_msg = message.replace('"', '\\"')
        cmd = f'display notification "{safe_msg}" with title "{safe_title}" sound name "Glass"'
        subprocess.run(["osascript", "-e", cmd], capture_output=True)
    except Exception as e:
        log(f"Mac 系統通知發送失敗: {e}")

def send_discord_notify(webhook_url, content):
    if not webhook_url:
        return
    payload = json.dumps({"content": content}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "711StockBot/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            pass
    except Exception as e:
        log(f"Discord 通知發送失敗: {e}")

def send_telegram_notify(bot_token, chat_id, content):
    if not bot_token or not chat_id:
        return
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": content}).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "711StockBot/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            pass
    except Exception as e:
        log(f"Telegram 通知發送失敗: {e}")

def send_alerts(config, title, message, url):
    full_text = f"🎉【{title}】\n{message}\n👉 賣場連結: {url}"
    if config.get("notify_mac", True):
        notify_mac(title, message)
    if config.get("discord_webhook_url"):
        send_discord_notify(config["discord_webhook_url"], full_text)
    if config.get("telegram_bot_token") and config.get("telegram_chat_id"):
        send_telegram_notify(config["telegram_bot_token"], config["telegram_chat_id"], full_text)

def fetch_products(target_url):
    req = urllib.request.Request(
        target_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        html_text = resp.read().decode("utf-8", errors="replace")

    raw_products = re.findall(r'data-product="([^"]+)"', html_text)
    products = {}
    seen_ids = set()

    for item_str in raw_products:
        try:
            data = json.loads(html.unescape(item_str))
            prod_id = data.get("Cgdd_Id")
            if not prod_id or prod_id in seen_ids:
                continue
            seen_ids.add(prod_id)

            prod_name = data.get("Cgdd_Product_Name", "未命名商品").strip()
            specs = data.get("Spec", [])
            for spec in specs:
                spec_id = spec.get("Cgds_Id", prod_id)
                spec_title = spec.get("Cgds_Spec", "").strip()
                inventory = int(spec.get("Inventory", 0))
                price = spec.get("Cgds_Price", 0)

                key = f"{prod_id}_{spec_id}"
                display_name = f"{prod_name}" + (f" ({spec_title})" if spec_title else "") + f" - NT${price}"

                products[key] = {
                    "id": prod_id,
                    "spec_id": spec_id,
                    "name": prod_name,
                    "spec": spec_title,
                    "price": price,
                    "display_name": display_name,
                    "inventory": inventory
                }
        except Exception:
            continue

    return products

def run_check(config, is_first_run=False):
    target_url = config.get("target_url")
    watch_keywords = config.get("watch_keywords", [])

    products = fetch_products(target_url)
    if not products:
        log("警告: 未能在頁面解析出商品資料，請確認網址或賣場狀態。")
        return

    saved_state = load_state()
    current_state = {}
    restocked_items = []

    for key, p in products.items():
        name = p["display_name"]
        inv = p["inventory"]
        current_state[key] = inv

        # 關鍵字過濾
        if watch_keywords:
            matched = any(kw in name for kw in watch_keywords)
            if not matched:
                continue

        # 檢查是否補貨 (前一次為 0 且這次 > 0，或是初次有庫存且非第一次紀錄)
        old_inv = saved_state.get(key)
        if old_inv is not None:
            if old_inv == 0 and inv > 0:
                restocked_items.append((p, old_inv, inv))
            elif inv > old_inv and old_inv > 0:
                restocked_items.append((p, old_inv, inv))

    # 初次執行或有商品時列印
    if is_first_run or not saved_state:
        log("=== 當前各規格庫存狀態 ===")
        for key, p in products.items():
            log(f"  [{p['inventory']:>3} 件] {p['display_name']}")
        log("===========================")

    # 發出補貨通知
    if restocked_items:
        for p, old_inv, new_inv in restocked_items:
            alert_title = "7-11 賣貨便補貨通知！"
            alert_msg = f"{p['display_name']} 已補貨！庫存: {new_inv} 件 (原 {old_inv})"
            log(f"🚨 {alert_msg}")
            send_alerts(config, alert_title, alert_msg, target_url)
    elif not is_first_run:
        # 心跳日誌：讓使用者安心知道排程持續正常運作中
        log(f"檢查完成：庫存無變更 (共檢查 {len(products)} 項規格)")

    # 儲存最新狀態
    save_state(current_state)

def main():
    parser = argparse.ArgumentParser(description="7-11 賣貨便庫存監控")
    parser.add_argument("--once", action="store_true", help="僅執行一次檢查後退出 (適用於 crontab)")
    parser.add_argument("--test-notify", action="store_true", help="發送一則測試通知 (確認 Mac / Discord 通知管道是否正常)")
    args = parser.parse_args()

    config = load_config()

    if args.test_notify:
        log("發送測試通知中...")
        send_alerts(
            config,
            "7-11 賣貨便監控 - 測試通知",
            "這是一則測試通知，若看到此訊息代表通知設定成功！",
            config.get("target_url")
        )
        log("✅ 測試通知已送出。")
        return

    if args.once:
        run_check(config, is_first_run=False)
        return

    interval = int(config.get("interval_seconds", 60))
    log(f"🚀 啟動監控程式 (間隔 {interval} 秒)")
    log(f"目標賣場: {config.get('target_url')}")

    is_first = True
    while True:
        try:
            config = load_config()
            interval = int(config.get("interval_seconds", 60))
            run_check(config, is_first_run=is_first)
            is_first = False
        except Exception as e:
            log(f"檢查過程中發生錯誤: {e}")
        time.sleep(interval)

if __name__ == "__main__":
    main()
