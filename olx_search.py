# -*- coding: utf-8 -*-
import os
import time
import random
import threading
from datetime import datetime
import requests
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

TELEGRAM_TOKEN = "8815485101:AAGeoPgoecN44D7thqfwpHmcpBya5I7otoo"
TELEGRAM_CHAT_ID = "5197638520"

# Прямые запросы к API OLX
API_CPU = "https://www.olx.ua/api/v1/offers/?query=ryzen%205%209600x&currency=UAH&filter_float_price:to=7000"
MAX_PRICE_CPU = 6800 

API_RAM = "https://www.olx.ua/api/v1/offers/?query=ddr5%2032gb&currency=UAH&filter_float_price:to=10000"
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
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Ошибка API OLX: статус {response.status_code}")
            return

        data = response.json()
        offers = data.get("data", [])
        print(f"[{datetime.now().strftime('%H:%M:%S')}] API {item_type}: найдено объявлений — {len(offers)}")

        for item in offers:
            link = item.get("url")
            if not link or link in already_sent_links:
                continue

            title = item.get("title", "")
            title_lower = title.lower()

            # Фильтрация по названию
            if item_type == "CPU" and "9600" not in title_lower:
                continue
            if item_type == "RAM" and ("ddr5" not in title_lower and "ддр5" not in title_lower):
                continue

            # Получаем точную цену из JSON
            params = item.get("params", [])
            price = None
            for p in params:
                if p.get("key") == "price":
                    price = p.get("value", {}).get("value")
                    break

            if price is None:
                continue

            print(f"  Чек: {title} | Цена: {price} грн")

            if price <= max_price:
                print(f"🎯 Находка [{item_type}]: {title} за {price} грн!")
                send_telegram_message(title, price, link, item_type)
                already_sent_links.add(link)
                save_sent_link(link)

    except Exception as e:
        print(f"Ошибка при запросе к API {item_type}: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    
    print("Бот запущен через API OLX.")
    sent_notifications = load_sent_links()
    
    while True:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] --- Старт проверки API ---")
        scan_api(API_CPU, MAX_PRICE_CPU, "CPU", sent_notifications)
        time.sleep(random.randint(3, 5))
        scan_api(API_RAM, MAX_PRICE_RAM, "RAM", sent_notifications)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] --- Конец проверки. Пауза 30 мин ---")
        time.sleep(1800)
