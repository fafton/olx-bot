# -*- coding: utf-8 -*-
import os
import random
import re
import time
from datetime import datetime
import requests

TELEGRAM_TOKEN = "8815485101:AAGeoPgoecN44D7thqfwpHmcpBya5I7otoo"
TELEGRAM_CHAT_ID = "5197638520"

# Обновленные ссылки API с новыми лимитами
API_CPU = "https://www.olx.ua/api/v1/offers/?query=ryzen%205%209600x&currency=UAH&filter_float_price:to=11000"
MAX_PRICE_CPU = 11000 

API_RAM = "https://www.olx.ua/api/v1/offers/?query=ddr5%2032gb&currency=UAH&filter_float_price:to=11000"
MAX_PRICE_RAM = 11000 

DB_PATH = "sent_links.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
    "Accept": "application/json",
    "Version": "v2"
}

def load_sent_links():
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_sent_link(link):
    with open(DB_PATH, "a", encoding="utf-8") as f:
        f.write(link + "\n")

def send_telegram_message(title, price, link, item_type):
    emoji = "💻" if item_type == "CPU" else "📟"
    text = (
        f"🚨 **Найдено предложение ({item_type})!**\n\n"
        f"{emoji} **Товар:** {title}\n"
        f"💰 **Цена:** {price} грн\n"
        f"🔗 **Ссылка:** {link}"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
    }
    try:
        requests.post(url, json=payload, timeout=10)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Сообщение отправлено в Telegram!")
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def scan_api(api_url, max_price, item_type, already_sent_links):
    try:
        response = requests.get(api_url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Статус API OLX: {response.status_code}")
            return

        data = response.json()
        offers = data.get("data", [])
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {item_type}: найдено {len(offers)} объявлений.")

        for item in offers:
            link = item.get("url")
            if not link or link in already_sent_links:
                continue

            title = item.get("title", "")
            title_lower = title.lower()

            if item_type == "CPU" and "9600" not in title_lower:
                continue
            if item_type == "RAM" and ("ddr5" not in title_lower and "ддр5" not in title_lower):
                continue

            params = item.get("params", [])
            price = None
            for p in params:
                if p.get("key") == "price":
                    price = p.get("value", {}).get("value")
                    break

            if price and price <= max_price:
                print(f"🎯 Находка [{item_type}]: {title} за {price} грн!")
                send_telegram_message(title, price, link, item_type)
                already_sent_links.add(link)
                save_sent_link(link)

    except Exception as e:
        print(f"Ошибка сканирования {item_type}: {e}")

if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Запуск проверки...")
    sent_links = load_sent_links()
    scan_api(API_CPU, MAX_PRICE_CPU, "CPU", sent_links)
    time.sleep(3)
    scan_api(API_RAM, MAX_PRICE_RAM, "RAM", sent_links)
    print("Проверка завершена.")
