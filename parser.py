from datetime import datetime, timedelta, timezone
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from deep_translator import GoogleTranslator

SOURCES = {
    "Мир": [
        ("BBC World", "http://bbci.co.uk"),
        ("ТАСС", "https://tass.ru"),
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
    "Россия": [("Интерфакс", "https://interfax.ru")],
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


def extract_image(item):
    enclosure = item.find("enclosure")
    if enclosure is not None:
        url = enclosure.attrib.get("url", "")
        if url and (
            "image" in enclosure.attrib.get("type", "")
            or url.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
        ):
            return url

    for elem in item.iter():
        if elem.tag.endswith(("content", "thumbnail")):
            url = elem.attrib.get("url", "")
            if url and not url.endswith(".mp4"):
                return url

    desc_el = item.find("description")
    if desc_el is not None and desc_el.text:
        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc_el.text)
        if match:
            return match.group(1)

    return ""


articles = []

for region, feeds in SOURCES.items():
    for source_name, url in feeds:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                        " AppleWebKit/537.36"
                    )
                },
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)

                for item in root.findall(".//item")[:5]:
                    title_el = item.find("title")
                    link_el = item.find("link")
                    desc_el = item.find("description")
                    date_el = item.find("pubDate")

                    raw_title = (
                        title_el.text.strip()
                        if title_el is not None and title_el.text
                        else ""
                    )
                    if not raw_title:
                        continue

                    link = (
                        link_el.text.strip()
                        if link_el is not None and link_el.text
                        else "#"
                    )
                    raw_desc = clean_html(
                        desc_el.text if desc_el is not None else ""
                    )
                    pub_date = (
                        date_el.text[:16]
                        if date_el is not None and date_el.text
                        else ""
                    )
                    image_url = extract_image(item)

                    title_ru = translate_text(raw_title)
                    desc_ru = translate_text(raw_desc)

                    articles.append({
                        "region": region,
                        "source": source_name,
                        "title": title_ru,
                        "link": link,
                        "date": pub_date,
                        "description": desc_ru,
                        "image": image_url,
                    })
        except Exception as e:
            print(f"Ошибка {source_name} ({url}): {e}")

barnaul_tz = timezone(timedelta(hours=7))
now_str = datetime.now(barnaul_tz).strftime("%d.%m.%Y в %H:%M")

output = {
    "updated": now_str,
    "categories": list(SOURCES.keys()),
    "articles": articles,
}

with open("news.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
