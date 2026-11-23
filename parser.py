from datetime import datetime, timedelta, timezone
import json
import re
import subprocess
from deep_translator import GoogleTranslator
import feedparser

SOURCES = {
    "Мир": [
        ("ТАСС", "https://tass.ru"),
        ("BBC World", "https://bbci.co.uk"),
    ],
    "Европа": [("Euronews", "https://euronews.com")],
    "США": [("NPR News", "https://npr.org")],
    "Азия": [
        (
            "Channel NewsAsia",
            "https://channelnewsasia.com",
        )
    ],
    "Китай": [
        ("South China Morning Post", "https://scmp.com")
    ],
    "Таиланд": [
        ("Bangkok Post", "https://bangkokpost.com"),
        ("The Pattaya News", "https://thepattayanews.com"),
    ],
    "Россия": [("Лента.ру", "https://lenta.ru")],
    "Барнаул": [
        ("Толк", "https://tolknews.ru"),
        ("Амител", "https://amic.ru"),
    ],
}

translator = GoogleTranslator(source="auto", target="ru")


def is_russian(text):
    return bool(re.search("[а-яА-ЯёЁ]", text))


def translate_text(text):
    if not text or is_russian(text):
        return text
    try:
        return translator.translate(text)
    except Exception:
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
            # Используем системный curl с имитацией обычного браузера
            cmd = [
                "curl",
                "-sL",
                "-A",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "--max-time",
                "15",
                url,
            ]
            xml_bytes = subprocess.check_output(cmd)
            feed = feedparser.parse(xml_bytes)
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

barnaul_tz = timezone(timedelta(hours=7))
now_str = datetime.now(barnaul_tz).strftime("%d.%m.%Y в %H:%M")

output = {
    "updated": now_str,
    "categories": list(SOURCES.keys()),
    "articles": articles,
}

with open("news.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
