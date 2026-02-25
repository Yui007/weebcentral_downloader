"""
colab_downloader.py — Fully parallel async chapter + image downloader

Architecture
------------
  asyncio.gather fires ALL selected chapters at once.
  A semaphore (MAX_CHAPTER_WORKERS) caps how many chapters are ACTIVE simultaneously.
  Inside each active chapter another semaphore (MAX_IMAGE_WORKERS) caps page fetches.
  This means chapters don't wait in a queue — they all start, then race through
  the semaphore as slots free up, so you get maximum throughput without hammering
  the server.

  Chapter A: [img1 img2 img3 ... img10]  ← 10 in-flight at once
  Chapter B: [img1 img2 img3 ... img10]  ← running at same time as A
  Chapter C: [img1 img2 img3 ... img10]  ← running at same time as A & B
  Chapter D: waiting for a slot...
  Chapter E: waiting for a slot...

  httpx with HTTP/2 multiplexing means multiple requests share one TCP
  connection → low overhead, fast throughput.
"""

import asyncio
import re
import time
from pathlib import Path

import httpx
from tqdm.notebook import tqdm

from colab_scraper import BASE_URL, async_get_chapter_images
from colab_converter import images_to_pdf, images_to_cbz, images_to_folder

# ── Tunable concurrency knobs ────────────────────────────────────────────────
MAX_CHAPTER_WORKERS  = 3     # chapters active simultaneously
MAX_IMAGE_WORKERS    = 10    # pages in-flight per chapter
# ── Retry settings ───────────────────────────────────────────────────────────
IMAGE_RETRIES        = 4     # max attempts per image
IMAGE_BACKOFF        = [0.5, 1.0, 2.0, 4.0]   # wait between retries (seconds)
CHAPTER_RETRIES      = 3     # max attempts to fetch a chapter's image list
# ── HTTP ─────────────────────────────────────────────────────────────────────
REQUEST_TIMEOUT      = 30    # seconds per request
# ─────────────────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": BASE_URL,
}

# Valid output formats
VALID_FORMATS = ("pdf", "cbz", "images", "all")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sanitize(name: str) -> str:
    """Strip characters that are illegal in filenames."""
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip()


def _fmt_duration(seconds: float) -> str:
    mins, secs = divmod(int(seconds), 60)
    return f"{mins}m {secs}s" if mins else f"{secs}s"


# ---------------------------------------------------------------------------
# Chapter selection parser
# ---------------------------------------------------------------------------

def parse_chapter_selection(user_input: str, total: int) -> list:
    """
    Convert a user selection string into a list of 0-based chapter indices.

    Formats
    -------
    all          → every chapter
    single N     → one chapter        (e.g. single 5)
    range N-M    → inclusive range    (e.g. range 3-10)
    N,M,P,...    → specific chapters  (e.g. 1,5,9,15)
    N            → treated as single N
    """
    s = user_input.strip().lower()

    if s == "all":
        return list(range(total))

    if s.startswith("single "):
        n = int(s.split()[1])
        return [n - 1]

    if s.startswith("range "):
        parts = s.split()[1].split("-")
        start, end = int(parts[0]), int(parts[1])
        return list(range(start - 1, min(end, total)))

    if re.match(r"^\d+-\d+$", s):
        start, end = map(int, s.split("-"))
        return list(range(start - 1, min(end, total)))

    if "," in s:
        nums = [int(x.strip()) for x in s.split(",")]
        return [n - 1 for n in nums]

    try:
        n = int(s)
        return [n - 1]
    except ValueError:
        raise ValueError(
            f"Unrecognised selection: '{user_input}'\n"
            "Use: all | single N | range N-M | 1,5,9,15"
        )


# ---------------------------------------------------------------------------
# Async image fetcher with retry
# ---------------------------------------------------------------------------

async def _fetch_image(
    client: httpx.AsyncClient,
    url: str,
    semaphore: asyncio.Semaphore,
) -> bytes | None:
    """
    Download one image.
    Bounded by semaphore; retries with exponential backoff on failure.
    """
    async with semaphore:
        for attempt in range(IMAGE_RETRIES):
            try:
                r = await client.get(url, timeout=REQUEST_TIMEOUT)
                if r.status_code == 200:
                    return r.content
                # Treat 429 / 5xx as retriable
                if r.status_code in (429, 500, 502, 503, 504):
                    raise httpx.HTTPStatusError(
                        f"HTTP {r.status_code}", request=r.request, response=r
                    )
            except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError):
                pass

            if attempt < IMAGE_RETRIES - 1:
                await asyncio.sleep(IMAGE_BACKOFF[attempt])

        return None   # all retries exhausted


async def _download_pages(image_urls: list, desc: str = "") -> list:
    """
    Download all pages for one chapter in parallel.
    Uses asyncio.gather to preserve page order.
    Returns list[bytes | None].
    """
    semaphore = asyncio.Semaphore(MAX_IMAGE_WORKERS)

    async with httpx.AsyncClient(
        headers=HEADERS,
        http2=True,
        limits=httpx.Limits(
            max_connections=MAX_IMAGE_WORKERS + 5,
            max_keepalive_connections=MAX_IMAGE_WORKERS,
        ),
    ) as client:
        pbar = tqdm(total=len(image_urls), desc=desc, leave=False, unit="pg")

        async def fetch_and_tick(url: str) -> bytes | None:
            result = await _fetch_image(client, url, semaphore)
            pbar.update(1)
            return result

        results = await asyncio.gather(*[fetch_and_tick(u) for u in image_urls])
        pbar.close()

    return list(results)


# ---------------------------------------------------------------------------
# Single-chapter pipeline
# ---------------------------------------------------------------------------

async def _process_chapter(
    chapter: dict,
    ch_num: int,
    total_chapters: int,
    manga_info: dict,
    output_format: str,
    series_dir: Path,
    chapter_semaphore: asyncio.Semaphore,
    position: int,
    total_selected: int,
    shared_client: httpx.AsyncClient,
) -> None:
    """
    Full pipeline for one chapter:
      1. Fetch image URL list (async, with retry — via shared_client)
      2. Download all pages in parallel
      3. Convert & save (runs in thread pool to keep event loop free)
    """
    async with chapter_semaphore:
        title_safe    = sanitize(manga_info["title"])
        ch_title_safe = sanitize(chapter["title"])[:80]
        file_stem     = f"{title_safe} - Ch{str(ch_num).zfill(3)} - {ch_title_safe}"
        bar_label     = f"  Ch{str(ch_num).zfill(3)}"
        tag           = f"[{position}/{total_selected}]"

        print(f"{tag} 📖  {chapter['title']}  ({chapter['date']})")

        # ── 1. Fetch image URL list (async, retried inside async_get_chapter_images) ──
        try:
            image_urls = await async_get_chapter_images(chapter["url"], shared_client)
        except Exception as e:
            print(f"{tag} ❌  Could not get image list after {CHAPTER_RETRIES} retries: {e}")
            return

        if not image_urls:
            print(f"{tag} ⚠️   No images found for this chapter, skipping.")
            return

        print(f"       🖼  {len(image_urls)} pages — downloading in parallel...")

        # ── 2. Download pages ────────────────────────────────────────────────────────
        image_bytes_list = await _download_pages(image_urls, desc=bar_label)

        good   = sum(1 for x in image_bytes_list if x)
        failed = len(image_urls) - good
        status = f"✅ {good}/{len(image_urls)} pages"
        if failed:
            status += f"  ⚠️  {failed} failed"
        print(f"       {status}")

        # ── 3. Convert & save (CPU-bound → thread pool) ──────────────────────────────
        loop = asyncio.get_event_loop()

        if output_format in ("pdf", "all"):
            pdf_path = str(series_dir / f"{file_stem}.pdf")
            print(f"       📄 Building PDF...")
            await loop.run_in_executor(None, images_to_pdf, image_bytes_list, pdf_path)
            print(f"          → {Path(pdf_path).name}")

        if output_format in ("cbz", "all"):
            cbz_path = str(series_dir / f"{file_stem}.cbz")
            print(f"       📦 Building CBZ...")
            await loop.run_in_executor(
                None, images_to_cbz,
                image_bytes_list, cbz_path, manga_info, ch_num, total_chapters,
            )
            print(f"          → {Path(cbz_path).name}")

        if output_format in ("images", "all"):
            img_dir = str(series_dir / file_stem)
            print(f"       🗂  Saving raw images...")
            saved = await loop.run_in_executor(
                None, images_to_folder, image_bytes_list, img_dir
            )
            print(f"          → {Path(img_dir).name}/  ({saved} files)")

        print()


# ---------------------------------------------------------------------------
# Async orchestrator
# ---------------------------------------------------------------------------

async def _run_all_chapters(
    manga_info: dict,
    chapters: list,
    selected_indices: list,
    output_format: str,
    series_dir: Path,
) -> None:
    """
    Fire all chapter tasks at once. The semaphore enforces MAX_CHAPTER_WORKERS.
    A single shared httpx.AsyncClient is reused across all chapter image-list
    fetches for connection pooling efficiency.
    """
    total_chapters = len(chapters)
    chapter_sem    = asyncio.Semaphore(MAX_CHAPTER_WORKERS)

    # Shared client for image-list fetching (not for page downloads — those
    # each create their own client to isolate connection pools per chapter)
    async with httpx.AsyncClient(
        headers=HEADERS,
        http2=True,
        limits=httpx.Limits(
            max_connections=MAX_CHAPTER_WORKERS * 2,
            max_keepalive_connections=MAX_CHAPTER_WORKERS,
        ),
    ) as shared_client:

        tasks = []
        for pos, idx in enumerate(selected_indices, 1):
            if idx < 0 or idx >= total_chapters:
                print(f"⚠️  Chapter {idx + 1} out of range (total: {total_chapters}), skipping.")
                continue
            tasks.append(
                _process_chapter(
                    chapter           = chapters[idx],
                    ch_num            = idx + 1,
                    total_chapters    = total_chapters,
                    manga_info        = manga_info,
                    output_format     = output_format,
                    series_dir        = series_dir,
                    chapter_semaphore = chapter_sem,
                    position          = pos,
                    total_selected    = len(selected_indices),
                    shared_client     = shared_client,
                )
            )

        # All tasks fire immediately; semaphore gates actual work
        await asyncio.gather(*tasks)


# ---------------------------------------------------------------------------
# Public sync entry point
# ---------------------------------------------------------------------------

def download_chapters(
    manga_info: dict,
    chapters: list,
    selected_indices: list,
    output_format: str,
    output_dir: str = "/content/manga",
) -> str:
    """
    Download selected chapters fully in parallel and save to disk.

    Parameters
    ----------
    manga_info       : dict from colab_scraper.scrape_manga_info()
    chapters         : list from colab_scraper.scrape_chapter_list()
    selected_indices : 0-based chapter indices to download
    output_format    : 'pdf' | 'cbz' | 'images' | 'all'
    output_dir       : root output folder (default /content/manga)

    Returns
    -------
    Absolute path to the series output directory as a string.
    """
    if output_format not in VALID_FORMATS:
        raise ValueError(f"output_format must be one of {VALID_FORMATS}, got '{output_format}'")

    title_safe = sanitize(manga_info["title"])
    series_dir = Path(output_dir) / title_safe
    series_dir.mkdir(parents=True, exist_ok=True)

    fmt_label = {
        "pdf":    "PDF",
        "cbz":    "CBZ (with ComicInfo.xml)",
        "images": "Raw Images folder",
        "all":    "PDF + CBZ + Raw Images",
    }[output_format]

    print(f"\n{'─'*55}")
    print(f"💾 Output   : {series_dir}")
    print(f"📥 Format   : {fmt_label}")
    print(f"⚡ Parallel : {MAX_CHAPTER_WORKERS} chapters  ×  {MAX_IMAGE_WORKERS} images/chapter")
    print(f"🔁 Retries  : {CHAPTER_RETRIES} chapter / {IMAGE_RETRIES} image")
    print(f"📦 Queued   : {len(selected_indices)} chapter(s)")
    print(f"{'─'*55}\n")

    t0 = time.perf_counter()

    # nest_asyncio lets asyncio.run() work inside Jupyter/Colab's running event loop
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass

    asyncio.run(
        _run_all_chapters(
            manga_info       = manga_info,
            chapters         = chapters,
            selected_indices = selected_indices,
            output_format    = output_format,
            series_dir       = series_dir,
        )
    )

    elapsed = time.perf_counter() - t0
    print(f"{'─'*55}")
    print(f"🎉 Finished in {_fmt_duration(elapsed)}  —  saved to:")
    print(f"   {series_dir}")
    return str(series_dir)
