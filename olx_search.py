# -*- coding: utf-8 -*-
import os
import time
import random
import re
import threading
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from flask import Flask

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- НАСТРОЙКИ УВЕДОМЛЕНИЙ ---
TELEGRAM_TOKEN = "8815485101:AAGeoPgoecN44D7thqfwpHmcpBya5I7otoo"
TELEGRAM_CHAT_ID = "5197638520"

# --- НАСТРОЙКИ ПОИСКА ---
URL_CPU = "https://www.olx.ua/uk/elektronika/kompyutery-i-komplektuyuschie/komplektuyuschie-i-aksesuary/q-ryzen-5-9600x/?currency=UAH&search%5Bfilter_float_price%3Ato%5D=7000&search%5Bfilter_enum_subcategory%5D%5B0%5D=protsessory"
MAX_PRICE_CPU = 6800 

URL_RAM = "https://www.olx.ua/uk/elektronika/kompyutery-i-komplektuyuschie/komplektuyuschie-i-aksesuary/q-ddr5-32gb/?currency=UAH&search%5Bfilter_float_price:to%5D=10000&search%5Bfilter_enum_subcategory%5D%5B0%5D=moduli-pamyati"
MAX_PRICE_RAM = 11000 

DB_PATH = "sent_links.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
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
        f"🚨 **Найдено выгодное предложение ({item_type})!**\n\n"
        f"{emoji} **Товар:** {title}\n"
        f"💰 **Цена:** {price}\n"
        f"🔗 **Ссылка:** {link}"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Уведомление [{item_type}] успешно отправлено!")
        else:
            print(f"Ошибка отправки в Telegram: {response.text}")
    except Exception as e:
        print(f"Ошибка соединения с Telegram: {e}")


def clean_price(price_str):
    """Надежное извлечение цифр из любой строки цены"""
    try:
        digits_only = re.sub(r"\D", "", price_str)
        return int(digits_only) if digits_only else None
    except Exception:
        return None


def scan_url(url, max_price, item_type, already_sent_links):
    session = requests.Session()
    try:
        response = session.get(url, headers=HEADERS, timeout=(5, 12))
        
        if response.status_code != 200:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Ошибка {response.status_code} при сканировании {item_type}")
            return

        soup = BeautifulSoup(response.text, "html.parser")
        
        # Поиск карточек по всем возможным селекторам OLX
        cards = soup.find_all(attrs={"data-testid": "l-card"})
        if not cards:
            cards = soup.find_all(attrs={"data-cy": "l-card"})

        print(f"[{datetime.now().strftime('%H:%M:%S')}] {item_type}: Найдено карточек на странице — {len(cards)}")

        for card in cards:
            try:
                # 1. Ссылка
                link_element = card.find("a", href=True)
                if not link_element:
                    continue
                link = link_element["href"]
                if link.startswith("/"):
                    link = "https://www.olx.ua" + link
                clean_link = link.split("?")[0]

                if clean_link in already_sent_links:
                    continue

                # 2. Название
                title_element = card.find("h6") or card.find("h3") or card.find("h4")
                if not title_element:
                    continue
                title = title_element.text.strip()
                title_lower = title.lower()

                # Гибкий фильтр по названиям
                if item_type == "CPU":
                    if "9600" not in title_lower:  # Ловит и 9600x, и 9600 x
                        continue
                elif item_type == "RAM":
                    if "ddr5" not in title_lower and "ддр5" not in title_lower:
                        continue

                # 3. Цена
                price_element = (
                    card.find(attrs={"data-testid": "ad-price"}) 
                    or card.find(attrs={"data-cy": "ad-price"})
                    or card.find("p", string=re.compile(r"грн", re.I))
                )
                
                if not price_element:
                    continue

                price_text = price_element.text.strip()
                numeric_price = clean_price(price_text)

                # Вывод в логи для отладки
                print(f"  Проверка: {title} | Цена: {numeric_price} грн (Лимит: {max_price})")

                if numeric_price and numeric_price <= max_price:
                    print(f"🎯 ПОДХОДИТ [{item_type}]: {title} за {price_text}!")
                    send_telegram_message(title, price_text, clean_link, item_type)
                    already_sent_links.add(clean_link)
                    save_sent_link(clean_link)

            except Exception as e:
                continue

    except Exception as e:
        print(f"Ошибка сканирования {item_type}: {e}")


if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    
    print("Бот-мониторинг запущен на сервере.")
    sent_notifications = load_sent_links()
    
    while True:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] --- Старт проверки ---")
        scan_url(URL_CPU, MAX_PRICE_CPU, "CPU", sent_notifications)
        time.sleep(random.randint(3, 6))
        scan_url(URL_RAM, MAX_PRICE_RAM, "RAM", sent_notifications)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] --- Конец проверки. Пауза 30 мин ---")
        time.sleep(1800)
