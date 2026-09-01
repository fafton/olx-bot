# -*- coding: utf-8 -*-
import os
import re
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = "8815485101:AAGeoPgoecN44D7thqfwpHmcpBya5I7otoo"
TELEGRAM_CHAT_ID = "5197638520"

# Публичные ссылки поиска OLX
URL_CPU = "https://www.olx.ua/uk/elektronika/kompyutery-i-komplektuyuschie/komplektuyuschie-i-aksesuary/q-ryzen-5-9600x/?currency=UAH&search%5Bfilter_float_price%3Ato%5D=6800"
MAX_PRICE_CPU = 6800 

URL_RAM = "https://www.olx.ua/uk/elektronika/kompyutery-i-komplektuyuschie/komplektuyuschie-i-aksesuary/q-ddr5-32gb/?currency=UAH&search%5Bfilter_float_price%3Ato%5D=11000"
MAX_PRICE_RAM = 11000 

DB_PATH = "sent_links.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
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
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Сообщение отправлено в Telegram!")
        else:
            print(f"Ошибка Telegram: {res.text}")
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def clean_price(price_str):
    digits = re.sub(r"\D", "", price_str)
    return int(digits) if digits else None

def scan_olx(url, max_price, item_type, already_sent_links):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Статус ответа {item_type}: {response.status_code}")
        
        if response.status_code != 200:
            return

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.find_all("div", attrs={"data-aria-label": "Оголошення"}) or soup.find_all("div", attrs={"data-testid": "l-card"})

        print(f"[{datetime.now().strftime('%H:%M:%S')}] {item_type}: найдено карточек — {len(cards)}")

        for card in cards:
            link_elem = card.find("a", href=True)
            if not link_elem:
                continue

            link = link_elem["href"]
            if link.startswith("/"):
                link = "https://www.olx.ua" + link
            clean_link = link.split("?")[0]

            if clean_link in already_sent_links:
                continue

            # Название
            title_elem = card.find("h4") or card.find("h6") or card.find("h3")
            if not title_elem:
                continue
            title = title_elem.text.strip()
            title_lower = title.lower()

            if item_type == "CPU" and "9600" not in title_lower:
                continue
            if item_type == "RAM" and ("ddr5" not in title_lower and "ддр5" not in title_lower):
                continue

            # Цена
            price_elem = card.find("p", attrs={"data-testid": "ad-price"}) or card.find("p", string=re.compile(r"грн", re.I))
            if not price_elem:
                continue

            price_num = clean_price(price_elem.text)
            print(f"  Найдено: {title} | {price_num} грн")

            if price_num and price_num <= max_price:
                print(f"🎯 Находка [{item_type}]: {title} за {price_num} грн!")
                send_telegram_message(title, price_num, clean_link, item_type)
                already_sent_links.add(clean_link)
                save_sent_link(clean_link)

    except Exception as e:
        print(f"Ошибка при сканировании {item_type}: {e}")

if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Запуск проверки...")
    sent_links = load_sent_links()
    scan_olx(URL_CPU, MAX_PRICE_CPU, "CPU", sent_links)
    time.sleep(3)
    scan_olx(URL_RAM, MAX_PRICE_RAM, "RAM", sent_links)
    print("Проверка завершена.")
