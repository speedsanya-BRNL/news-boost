from datetime import datetime, timedelta, timezone
import json
import re
import ssl
import time
import subprocess
from deep_translator import GoogleTranslator
import feedparser
from io import BytesIO

def fetch_feed(url, timeout=8):
    """Скачивает RSS через curl с жёстким таймаутом."""
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout), "--connect-timeout", "5",
             "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
             "-k", url],
            capture_output=True, timeout=timeout + 2
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
        return b""
    except Exception:
        return b""


def parse_feed_xml(xml_bytes):
    return feedparser.parse(BytesIO(xml_bytes))


SOURCES = {
    "Мир": [
        ("RT English", "https://rt-english.com/rss/"),
        ("Life.ru Мир", "https://life.ru/rss"),
    ],
    "Европа": [
        ("RT English", "https://rt-english.com/rss/"),
    ],
    "США": [
        ("Life.ru Мир", "https://life.ru/rss"),
    ],
    "Азия": [
        ("RT English", "https://rt-english.com/rss/"),
    ],
    "Китай": [
        ("RT English", "https://rt-english.com/rss/"),
    ],
    "Таиланд": [
        ("Life.ru Мир", "https://life.ru/rss"),
    ],
    "Паттайя": [
        ("Зе Паттайя Ньюс", "https://thepattayanewsru.com/feed/"),
        ("Google Новости — Паттайя", "https://news.google.com/rss/search?q=%D0%9F%D0%B0%D1%82%D1%82%D0%B0%D1%8F%D1%8F&hl=ru&gl=RU&ceid=RU:ru"),
    ],
    "Россия": [
        ("Лента.ру", "https://lenta.ru/rss/"),
        ("Известия", "https://iz.ru/xml/rss/all.xml"),
        ("Life.ru", "https://life.ru/rss"),
        ("RT English", "https://rt-english.com/rss/"),
    ],
    "Барнаул": [
        ("Толк", "https://tolknews.ru/rss/"),
        ("Амител", "https://amic.ru/rss/"),
    ],
}

translator = GoogleTranslator(source="auto", target="ru")


def is_russian(text):
    return bool(re.search("[а-яА-ЯёЁ]", text))


def translate_text(text):
    if not text or is_russian(text):
        return text
    for attempt in range(3):
        try:
            result = translator.translate(text)
            if result and not is_russian(result):
                return result
            return text
        except Exception:
            if attempt < 2:
                time.sleep(1)
            else:
                return text


def clean_html(raw_html):
    if not raw_html:
        return ""
    clean = re.sub(r"<[^<]+?>", "", raw_html)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:180] + "..." if len(clean) > 180 else clean


def extract_image(entry):
    if "media_content" in entry and entry.media_content:
        for m in entry.media_content:
            if "url" in m and not m["url"].endswith(".mp4"):
                return m["url"]
    if "media_thumbnail" in entry and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url", "")
    if "enclosures" in entry and entry.enclosures:
        for enc in entry.enclosures:
            if "image" in enc.get("type", "") or enc.get("href", "").lower().endswith(
                (".jpg", ".jpeg", ".png", ".webp")
            ):
                return enc.get("href", "")
    summary = entry.get("summary", "") or entry.get("description", "")
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', summary)
    if match:
        return match.group(1)
    return ""


articles = []

for region, feeds in SOURCES.items():
    for source_name, url in feeds:
        try:
            xml_data = fetch_feed(url)
            if not xml_data:
                print(f"[{region}] {source_name}: 0 (нет данных)")
                continue
            feed = parse_feed_xml(xml_data)
            print(f"[{region}] {source_name}: найдено {len(feed.entries)}")

            for entry in feed.entries[:5]:
                raw_title = entry.get("title", "").strip()
                if not raw_title:
                    continue

                link = entry.get("link", "#").strip()
                raw_desc = clean_html(
                    entry.get("summary", "") or entry.get("description", "")
                )
                pub_date = entry.get("published", "")[:16]
                image_url = extract_image(entry)

                articles.append({
                    "region": region,
                    "source": source_name,
                    "title": translate_text(raw_title),
                    "link": link,
                    "date": pub_date,
                    "description": translate_text(raw_desc),
                    "image": image_url,
                })
        except Exception as e:
            print(f"Ошибка {source_name}: {e}")

        time.sleep(0.3)

barnaul_tz = timezone(timedelta(hours=7))
now_str = datetime.now(barnaul_tz).strftime("%d.%m.%Y в %H:%M")

output = {
    "updated": now_str,
    "categories": list(SOURCES.keys()),
    "articles": articles,
}

with open("news.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\nГотово: {len(articles)} новостей сохранено в news.json")
