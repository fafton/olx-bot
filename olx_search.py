# -*- coding: utf-8 -*-
import os
import time
import random
import threading
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from flask import Flask

# --- ВЕБ-СЕРВЕР ДЛЯ БЕСПЛАТНОГО ТАРИФА RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_web():
    # Render передает порт через переменную окружения PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- НАСТРОЙКИ УВЕДОМЛЕНИЙ ---
TELEGRAM_TOKEN = "8815485101:AAGeoPgoecN44D7thqfwpHmcpBya5I7otoo"
TELEGRAM_CHAT_ID = "5197638520"

# --- НАСТРОЙКИ ДЛЯ ПРОЦЕССОРА ---
URL_CPU = "https://www.olx.ua/uk/elektronika/kompyutery-i-komplektuyuschie/komplektuyuschie-i-aksesuary/q-ryzen-5-9600x/?currency=UAH&search%5Bfilter_float_price%3Ato%5D=7000&search%5Bfilter_enum_subcategory%5D%5B0%5D=protsessory"
MAX_PRICE_CPU = 6500 

# --- НАСТРОЙКИ ДЛЯ ОПЕРАТИВНОЙ ПАМЯТИ ---
URL_RAM = "https://www.olx.ua/uk/elektronika/kompyutery-i-komplektuyuschie/komplektuyuschie-i-aksesuary/q-ddr5-32gb/?currency=UAH&search%5Bfilter_float_price:to%5D=10000&search%5Bfilter_enum_subcategory%5D%5B0%5D=moduli-pamyati"
MAX_PRICE_RAM = 10000 

DB_PATH = "sent_links.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0"
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
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Уведомление [{item_type}] отправлено!")
        else:
            print(f"Ошибка отправки в Telegram: {response.text}")
    except Exception as e:
        print(f"Не удалось связаться с Telegram API: {e}")


def clean_price(price_str):
    try:
        cleaned = (
            price_str.replace("грн.", "")
            .replace("грн", "")
            .replace(" ", "")
            .split("Д")[0]
        )
        return int(cleaned)
    except ValueError:
        return None


def scan_url(url, max_price, item_type, already_sent_links):
    session = requests.Session()
    try:
        response = session.get(url, headers=HEADERS, timeout=(5, 12))
        
        if response.status_code == 403:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Ошибка 403 при сканировании {item_type}.")
            return
        elif response.status_code != 200:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Ошибка {response.status_code} при сканировании {item_type}")
            return

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.find_all(attrs={"data-testid": "l-card"})
        if not cards:
            cards = soup.find_all("div", attrs={"data-cy": "l-card"})

        if not cards:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Карточки {item_type} не найдены.")
            return

        for card in cards:
            try:
                link_element = card.find("a", href=True)
                if not link_element:
                    continue
                link = link_element["href"]
                if link.startswith("/"):
                    link = "https://www.olx.ua" + link

                clean_link = link.split("?")[0]

                if clean_link in already_sent_links:
                    continue

                title = "Без названия"
                title_element = card.find("h6") or card.find("h3") or card.find("h4")
                if title_element:
                    title = title_element.text.strip()

                title_lower = title.lower()
                
                if item_type == "CPU":
                    if "9600x" not in title_lower and "9600 x" not in title_lower:
                        continue
                elif item_type == "RAM":
                    if "ddr5" not in title_lower and "ддр5" not in title_lower:
                        continue

                price_element = card.find(attrs={"data-testid": "ad-price"}) or card.find(attrs={"data-cy": "ad-price"})
                if not price_element:
                    continue
                price_text = price_element.text.strip()
                numeric_price = clean_price(price_text)

                if numeric_price and numeric_price <= max_price:
                    print(f"🎯 Найдено [{item_type}]: {title} за {price_text}!")
                    send_telegram_message(title, price_text, clean_link, item_type)
                    already_sent_links.add(clean_link)
                    save_sent_link(clean_link)
                    
            except Exception:
                continue

    except Exception as e:
        print(f"Ошибка при обработке {item_type}: {e}")


if __name__ == "__main__":
    # Запускаем веб-сервер в фоновом потоке для Render
    threading.Thread(target=run_web, daemon=True).start()
    
    print("Бот-мониторинг запущен на сервере.")
    sent_notifications = load_sent_links()
    print(f"Загружено ранее отправленных ссылок: {len(sent_notifications)}")
    
    while True:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Начало круга сканирования...")
        scan_url(URL_CPU, MAX_PRICE_CPU, "CPU", sent_notifications)
        time.sleep(random.randint(3, 6))
        scan_url(URL_RAM, MAX_PRICE_RAM, "RAM", sent_notifications)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Круг завершен. Засыпаю на 30 минут...")
        time.sleep(1800)
