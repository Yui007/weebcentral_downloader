"""
colab_scraper.py — WeebCentral series metadata & chapter list scraping
"""

import re

import httpx
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://weebcentral.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": BASE_URL,
}

IMG_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "HX-Request": "true",
    "Referer": BASE_URL,
}

# Retry config for page-list fetching
SCRAPE_RETRIES = 4
SCRAPE_BACKOFF = [1, 2, 4, 8]   # seconds between retry attempts


# ---------------------------------------------------------------------------
# Series info  (sync — only called once, no need for async)
# ---------------------------------------------------------------------------

def scrape_manga_info(url: str) -> dict:
    """Scrape series metadata from a WeebCentral series page."""
    print(f"🔎 Fetching series page: {url}")
    res = requests.get(url, headers=HEADERS, timeout=30)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "lxml")

    title_tag = soup.find("h1")
    title = title_tag.text.strip() if title_tag else "Unknown Title"

    cover_url = None
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "brand.png" in src or src.startswith("/static"):
            continue
        if src:
            cover_url = BASE_URL + src if src.startswith("/") else src
            break

    authors  = [a.text.strip() for a in soup.select("a[href*='author=']")]
    tags     = [t.text.strip() for t in soup.select("a[href*='included_tag=']")]

    type_tag   = soup.select_one("a[href*='included_type=']")
    manga_type = type_tag.text.strip() if type_tag else "Unknown"

    status_tag = soup.select_one("a[href*='included_status=']")
    status     = status_tag.text.strip() if status_tag else "Unknown"

    released = None
    for li in soup.find_all("li"):
        if "Released:" in li.text:
            span = li.find("span")
            if span:
                released = span.text.strip()

    description = None
    for li in soup.find_all("li"):
        strong = li.find("strong")
        if strong and "Description" in strong.text:
            p = li.find("p")
            if p:
                description = p.text.strip()

    associated = []
    for li in soup.find_all("li"):
        strong = li.find("strong")
        if strong and "Associated Name" in strong.text:
            associated = [x.text.strip() for x in li.select("li")]

    info = {
        "title":            title,
        "cover_url":        cover_url,
        "authors":          authors,
        "tags":             tags,
        "type":             manga_type,
        "status":           status,
        "released":         released,
        "description":      description,
        "associated_names": associated,
        "series_url":       url,
    }

    print(f"\n{'='*55}")
    print(f"📖 Title    : {title}")
    print(f"👤 Authors  : {', '.join(authors) if authors else 'N/A'}")
    print(f"🏷  Tags     : {', '.join(tags[:5]) if tags else 'N/A'}{' ...' if len(tags) > 5 else ''}")
    print(f"📌 Type     : {manga_type}")
    print(f"📊 Status   : {status}")
    print(f"📅 Released : {released or 'N/A'}")
    print(f"🖼  Cover    : {cover_url or 'N/A'}")
    print(f"{'='*55}")
    if description:
        preview = description[:300] + ("..." if len(description) > 300 else "")
        print(f"\n📝 Description:\n{preview}\n")

    return info


# ---------------------------------------------------------------------------
# Chapter list  (sync — only called once)
# ---------------------------------------------------------------------------

def scrape_chapter_list(series_url: str) -> list:
    """
    Fetch the full chapter list for a series.
    Returns chapters in ascending order: index 1 = oldest/first chapter.
    """
    match = re.search(r"/series/([^/]+)/", series_url)
    if not match:
        raise ValueError(f"Could not extract series ID from URL: {series_url}")
    series_id = match.group(1)

    full_ch_url = f"{BASE_URL}/series/{series_id}/full-chapter-list"
    print(f"🔎 Fetching chapter list: {full_ch_url}")

    res = requests.get(full_ch_url, headers=HEADERS, timeout=30)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "lxml")
    chapter_links = soup.select("a[href*='/chapters/']")

    # WeebCentral returns newest-first → reverse so index 1 = Chapter 1 (oldest)
    chapter_links = list(reversed(chapter_links))

    chapters = []
    for index, a in enumerate(chapter_links, start=1):
        href        = a["href"]
        chapter_url = BASE_URL + href if href.startswith("/") else href
        date_tag    = a.find("time")
        ch_text     = a.get_text(separator=" ", strip=True)
        chapters.append({
            "index": index,
            "title": ch_text or f"Chapter {index}",
            "url":   chapter_url,
            "date":  date_tag.text.strip() if date_tag else "Unknown",
        })

    print(f"\n📚 Total chapters: {len(chapters)}")
    if chapters:
        print(f"   Ch 1 (oldest) : {chapters[0]['title']}")
        print(f"   Ch {len(chapters)} (latest) : {chapters[-1]['title']}")

    return chapters


# ---------------------------------------------------------------------------
# Chapter image list  (async — called in parallel for many chapters at once)
# ---------------------------------------------------------------------------

async def async_get_chapter_images(
    chapter_url: str,
    client: httpx.AsyncClient,
) -> list:
    """
    Async version of get_chapter_images.
    Fetches the image-list page for one chapter with retry + exponential backoff.
    Returns an ordered list of image URLs.
    """
    images_url = f"{chapter_url}/images?reading_style=long_strip"

    last_exc = None
    for attempt in range(SCRAPE_RETRIES):
        try:
            r = await client.get(images_url, timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            images = []
            for img in soup.find_all("img"):
                src = img.get("src")
                if not src:
                    continue
                if "/static/" in src or "broken_image" in src:
                    continue
                images.append(src)
            return images
        except Exception as exc:
            last_exc = exc
            if attempt < SCRAPE_RETRIES - 1:
                import asyncio
                wait = SCRAPE_BACKOFF[attempt]
                await asyncio.sleep(wait)

    raise RuntimeError(
        f"Failed to fetch image list for {chapter_url} "
        f"after {SCRAPE_RETRIES} attempts: {last_exc}"
    )
