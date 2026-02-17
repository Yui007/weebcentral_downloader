import requests
import os
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from fpdf import FPDF
from flaresolverr_client import FlareSolverrSession
import time
from PIL import Image
import zipfile
import shutil
import base64
from ebooklib import epub

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

class WeebCentralScraper:
    def __init__(self, manga_url, chapter_range=None, output_dir="downloads", delay=1.0, max_threads=4, convert_to_pdf=False, convert_to_cbz=False, convert_to_epub=False, merge_chapters=False, delete_images_after_conversion=False):
        self.base_url = "https://weebcentral.com"
        if not manga_url.startswith(('http://', 'https://')):
            manga_url = 'https://' + manga_url
        self.manga_url = manga_url
        self.chapter_range = chapter_range
        self.output_dir = output_dir
        self.delay = float(delay) # Ensure delay is always float
        self.max_threads = max_threads
        self.convert_to_pdf = convert_to_pdf
        self.convert_to_cbz = convert_to_cbz
        self.convert_to_epub = convert_to_epub
        self.merge_chapters = merge_chapters
        self.delete_images_after_conversion = delete_images_after_conversion
        self.downloaded_chapter_dirs = []  # Track chapter dirs for merging
        
        # Enhanced headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',  # Removed 'br' to fix decoding issues
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        }
        
        # Create a persistent FlareSolverr session for HTML pages
        self.session = FlareSolverrSession()
        
        # Create a standard session for direct image downloads (CDN is not protected)
        self.image_session = requests.Session()
        self.image_session.headers.update(self.headers)
        self.chapters = []  # Store chapters list for reference
        self.progress_callback = None
        self.stop_flag = lambda: False

    def set_progress_callback(self, callback):
        self.progress_callback = callback

    def set_stop_flag(self, stop_flag):
        self.stop_flag = stop_flag

    def get_manga_title(self, soup):
        """Extract the manga title from the page"""
        title_element = soup.select_one("section[x-data] > section:nth-of-type(2) h1")
        if title_element:
            return title_element.text.strip()
        return "unknown_manga"

    def download_cover_image(self, soup, output_dir):
        """Download the manga cover image"""
        try:
            cover_img_element = soup.select_one("img[alt$='cover']")
            if cover_img_element and 'src' in cover_img_element.attrs:
                cover_img_url = cover_img_element['src']
                if not cover_img_url.startswith(('http://', 'https://')):
                    cover_img_url = urljoin(self.base_url, cover_img_url)

                # Get the file extension
                ext = cover_img_url.split('.')[-1].lower()
                if ext not in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
                    ext = 'jpg'
                
                filepath = os.path.join(output_dir, f"cover.{ext}")

                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    logger.info(f"Skipping cover image - already exists")
                    return

                logger.info(f"Downloading cover image from: {cover_img_url}")
                img_response = self.image_session.get(cover_img_url, headers=self.headers, timeout=10)
                img_response.raise_for_status()

                with open(filepath, 'wb') as f:
                    f.write(img_response.content)
                logger.info(f"Successfully downloaded cover image.")
            else:
                logger.warning("Could not find cover image.")
        except Exception as e:
            logger.error(f"Failed to download cover image: {e}")

    def get_chapter_list_url(self):
        """Generate the full chapter list URL from manga URL"""
        parsed_url = urlparse(self.manga_url)
        path_parts = parsed_url.path.split('/')
        chapter_list_path = f"{'/'.join(path_parts[:3])}/full-chapter-list"
        return f"{self.base_url}{chapter_list_path}"

    def get_chapters(self):
        """Get list of all chapter URLs"""
        chapter_list_url = self.get_chapter_list_url()
        logger.info(f"Fetching chapter list from: {chapter_list_url}")
        
        response = self.session.get(chapter_list_url)
        if response.status_code != 200:
            logger.error("Failed to fetch chapter list")
            return []
            
        soup = BeautifulSoup(response.content, 'html.parser')
        chapters = []
        
        # Find all chapter links
        chapter_elements = soup.select("div[x-data] > a")
        
        # Process chapters in reverse order (oldest first)
        for element in reversed(chapter_elements):
            chapter_url = element.get('href')
            chapter_name = element.select_one("span.flex > span")
            chapter_name = chapter_name.text.strip() if chapter_name else "Unknown Chapter"
            
            if chapter_url:
                if isinstance(chapter_url, list):
                    chapter_url = chapter_url[0]
                if not chapter_url.startswith(('http://', 'https://')):
                    chapter_url = urljoin(self.base_url, chapter_url)
                
                chapters.append({
                    'url': chapter_url,
                    'name': chapter_name
                })
        
        return chapters

    def get_chapter_images(self, chapter_url):
        """Get list of image URLs for a chapter using FlareSolverr"""
        # Append /images endpoint with long strip reading style
        images_url = f"{chapter_url}/images?reading_style=long_strip"
        logger.info(f"Fetching images from: {images_url}")
        
        try:
            # Use FlareSolverr session to bypass Cloudflare on the HTML page
            response = self.session.get(images_url)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch chapter images page: {response.status_code}")
                return []
            
            # Parse HTML to find images
            soup = BeautifulSoup(response.content, 'html.parser')
            image_urls = []
            
            for img in soup.find_all("img"):
                src = img.get("src")
                if isinstance(src, list): src = src[0]
                if src and "broken_image" not in src and src.startswith("http"):
                    image_urls.append(src)
            
            logger.info(f"Found {len(image_urls)} images")
            return image_urls
            
        except Exception as e:
            logger.error(f"Failed to get chapter images: {e}")
            return []

    def download_image(self, img_url, filepath, chapter_url):
        """Download a single image"""
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            logger.info(f"Skipping {os.path.basename(filepath)} - already exists")
            return True

        try:
            if not img_url.startswith(('http://', 'https://')):
                img_url = urljoin(chapter_url, img_url)

            # Add referer header for this specific request
            headers = self.headers.copy()
            headers['Referer'] = chapter_url

            # Try multiple times with increasing delays
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    img_response = self.image_session.get(
                        img_url,
                        headers=headers,
                        timeout=10,
                        allow_redirects=True
                    )
                    img_response.raise_for_status()
                    
                    # Verify we got an image
                    content_type = img_response.headers.get('content-type', '')
                    if not content_type.startswith('image/'):
                        raise ValueError(f"Received non-image content-type: {content_type}")

                    with open(filepath, 'wb') as f:
                        f.write(img_response.content)
                    logger.info(f"Successfully downloaded: {os.path.basename(filepath)}")
                    return True

                except requests.exceptions.RequestException as e:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2  # Progressive delay: 2s, 4s, 6s
                        logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                        time.sleep(wait_time)
                    else:
                        raise

        except Exception as e:
            logger.error(f"Failed to download {os.path.basename(filepath)}: {str(e)}")
            return False

    def download_chapter(self, chapter):
        """Download all images for a chapter"""
        if self.stop_flag():
            return 0, None
        
        chapter_name = re.sub(r'[\\/*?:"<>|]', '_', chapter['name'])
        chapter_dir = os.path.join(self.output_dir, chapter_name)
        os.makedirs(chapter_dir, exist_ok=True)
        
        logger.info(f"Downloading chapter: {chapter['name']}")
        image_urls = self.get_chapter_images(chapter['url'])
        
        if not image_urls:
            logger.warning(f"No images found for chapter: {chapter['name']}")
            return 0, None
            
        logger.info(f"Found {len(image_urls)} images")
        
        # Filter out unwanted images
        # image_urls = [url for url in image_urls if not any(
        #     word in url.lower() for word in ['icon', 'logo']
        # )]
        
        # Download images with multiple threads
        downloaded = 0
        if self.progress_callback:
            self.progress_callback(chapter['name'], 0)
        
        with tqdm(total=len(image_urls), desc=f"Chapter {chapter['name']}") as pbar:
            with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
                future_to_url = {}
                
                for index, url in enumerate(image_urls, 1):
                    ext = url.split('.')[-1].lower()
                    if ext not in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
                        ext = 'jpg'
                    
                    filepath = os.path.join(chapter_dir, f"{index:03d}.{ext}")
                    future = executor.submit(self.download_image, url, filepath, chapter['url'])
                    future_to_url[future] = url
                    
                    # Small delay between starting downloads
                    time.sleep(0.2)
                
                for i, future in enumerate(as_completed(future_to_url)):
                    if self.stop_flag():
                        break
                    if future.result():
                        downloaded += 1
                        pbar.update(1)
                        if self.progress_callback:
                            progress = int((i + 1) / len(image_urls) * 100)
                            self.progress_callback(chapter['name'], progress)
        
        logger.info(f"Downloaded {downloaded}/{len(image_urls)} images for chapter: {chapter['name']}")
        return downloaded, chapter_dir

    def create_pdf_from_chapter(self, chapter_dir, chapter_name):
        """Create a PDF from all images in a chapter directory.
        Each page is sized exactly to its image — no white borders.
        """
        logger.info(f"Creating PDF for chapter: {chapter_name}")

        image_files = sorted([
            os.path.join(chapter_dir, f)
            for f in os.listdir(chapter_dir)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif'))
        ])

        if not image_files:
            logger.warning(f"No images found in {chapter_dir} to create PDF.")
            return

        pdf = FPDF()
        pdf.set_auto_page_break(auto=False)  # Prevent FPDF from adding extra space

        for image_file in image_files:
            try:
                with Image.open(image_file) as img:
                    # Convert to RGB if needed (handles PNG transparency, RGBA, etc.)
                    if img.mode not in ("RGB", "L"):
                        img = img.convert("RGB")
                        rgb_path = image_file + "_rgb.jpg"
                        img.save(rgb_path, "JPEG", quality=95)
                        source_path = rgb_path
                    else:
                        source_path = image_file

                    width_px, height_px = img.size

                # Convert pixels → mm (96 DPI standard for web images)
                DPI = 96
                width_mm  = (width_px  / DPI) * 25.4
                height_mm = (height_px / DPI) * 25.4

                # Set page size exactly to image dimensions — zero margins
                pdf.add_page(format=(width_mm, height_mm))
                pdf.set_margins(0, 0, 0)
                pdf.image(source_path, x=0, y=0, w=width_mm, h=height_mm)

                # Clean up temp RGB file if created
                if source_path != image_file and os.path.exists(source_path):
                    os.remove(source_path)

            except Exception as e:
                logger.error(f"Failed to process image {image_file}: {e}")

        pdf_path = os.path.join(self.output_dir, f"{chapter_name}.pdf")
        pdf.output(pdf_path)
        logger.info(f"Successfully created PDF: {pdf_path}")

    def create_cbz_from_chapter(self, chapter_dir, chapter_name):
        """Create a CBZ archive from all images in a chapter directory"""
        logger.info(f"Creating CBZ for chapter: {chapter_name}")

        image_files = sorted([
            os.path.join(chapter_dir, f)
            for f in os.listdir(chapter_dir)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif'))
        ])

        if not image_files:
            logger.warning(f"No images found in {chapter_dir} to create CBZ.")
            return

        cbz_path = os.path.join(self.output_dir, f"{chapter_name}.cbz")
        with zipfile.ZipFile(cbz_path, 'w') as cbz_file:
            for image_file in image_files:
                cbz_file.write(image_file, os.path.basename(image_file))
        logger.info(f"Successfully created CBZ: {cbz_path}")

    def delete_chapter_images(self, chapter_dir):
        """Delete all images in a chapter directory"""
        logger.info(f"Deleting images in: {chapter_dir}")
        try:
            shutil.rmtree(chapter_dir)
            logger.info(f"Successfully deleted directory: {chapter_dir}")
        except Exception as e:
            logger.error(f"Failed to delete directory {chapter_dir}: {e}")

    def create_epub_from_chapter(self, chapter_dir, chapter_name, manga_title=None):
        """Create an EPUB from all images in a chapter directory"""
        logger.info(f"Creating EPUB for chapter: {chapter_name}")
        
        try:
            image_files = sorted([
                os.path.join(chapter_dir, f)
                for f in os.listdir(chapter_dir)
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))
            ])
            
            if not image_files:
                logger.warning(f"No images found in {chapter_dir} to create EPUB.")
                return
            
            book = epub.EpubBook()
            identifier = f'{manga_title or "manga"}-{chapter_name}'.replace(' ', '-').replace('/', '-')
            book.set_identifier(identifier)
            book.set_title(f'{manga_title or "Manga"} - {chapter_name}')
            book.set_language('en')
            book.add_author('WeebCentral Downloader')
            
            spine = ['nav']
            toc = []
            
            for i, image_file in enumerate(image_files, 1):
                # Read and encode image
                with open(image_file, 'rb') as f:
                    img_data = f.read()
                
                ext = os.path.splitext(image_file)[1].lower()
                media_type = {
                    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                    '.png': 'image/png', '.gif': 'image/gif'
                }.get(ext, 'image/jpeg')
                
                # Add image to epub
                img_item = epub.EpubItem(
                    uid=f'img_{i}',
                    file_name=f'images/page_{i:03d}{ext}',
                    media_type=media_type,
                    content=img_data
                )
                book.add_item(img_item)
                
                # Create HTML page for image
                page = epub.EpubHtml(title=f'Page {i}', file_name=f'page_{i:03d}.xhtml')
                page.content = f'''<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Page {i}</title>
<style>body{{margin:0;padding:0;text-align:center;background:#000;}}
img{{max-width:100%;max-height:100vh;object-fit:contain;}}</style>
</head>
<body><img src="images/page_{i:03d}{ext}" alt="Page {i}"/></body>
</html>'''
                book.add_item(page)
                spine.append(page)
                
                # Add first page to TOC
                if i == 1:
                    toc.append(epub.Link(page.file_name, chapter_name, 'intro'))
            
            book.toc = toc
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            book.spine = spine
            
            # Clean chapter name for file
            chapter_name_clean = re.sub(r'[\\/*?:"<>|]', '_', chapter_name)
            epub_path = os.path.join(self.output_dir, f"{chapter_name_clean}.epub")
            epub.write_epub(epub_path, book, {})
            logger.info(f"Successfully created EPUB: {epub_path}")
        except Exception as e:
            logger.error(f"Failed to create EPUB for {chapter_name}: {e}")

    def create_merged_pdf(self, chapter_dirs, manga_title):
        """Create a single merged PDF from all chapter directories.
        Each page is sized exactly to its image — no white borders.
        """
        logger.info(f"Creating merged PDF for: {manga_title}")

        pdf = FPDF()
        pdf.set_auto_page_break(auto=False)

        for chapter_dir, chapter_name in sorted(chapter_dirs, key=lambda x: self.extract_chapter_number(x[1])):
            if not os.path.exists(chapter_dir):
                continue

            image_files = sorted([
                os.path.join(chapter_dir, f)
                for f in os.listdir(chapter_dir)
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif'))
            ])

            for image_file in image_files:
                try:
                    with Image.open(image_file) as img:
                        # Handle transparency (PNG/RGBA) — FPDF can't handle it
                        if img.mode not in ("RGB", "L"):
                            img = img.convert("RGB")
                            source_path = image_file + "_rgb.jpg"
                            img.save(source_path, "JPEG", quality=95)
                        else:
                            source_path = image_file

                        width_px, height_px = img.size

                    # Pixels → mm at 96 DPI
                    DPI = 96
                    width_mm  = (width_px / DPI) * 25.4
                    height_mm = (height_px / DPI) * 25.4

                    pdf.add_page(format=(width_mm, height_mm))
                    pdf.set_margins(0, 0, 0)
                    pdf.image(source_path, x=0, y=0, w=width_mm, h=height_mm)

                    # Clean up temp file
                    if source_path != image_file and os.path.exists(source_path):
                        os.remove(source_path)

                except Exception as e:
                    logger.error(f"Failed to process image {image_file}: {e}")

        pdf_path = os.path.join(self.output_dir, f"{manga_title}.pdf")
        pdf.output(pdf_path)
        logger.info(f"Successfully created merged PDF: {pdf_path}")

    def create_merged_cbz(self, chapter_dirs, manga_title):
        """Create a single merged CBZ from all chapter directories"""
        logger.info(f"Creating merged CBZ for: {manga_title}")
        
        cbz_path = os.path.join(self.output_dir, f"{manga_title}.cbz")
        with zipfile.ZipFile(cbz_path, 'w') as cbz_file:
            for chapter_dir, chapter_name in sorted(chapter_dirs, key=lambda x: self.extract_chapter_number(x[1])):
                if not os.path.exists(chapter_dir):
                    continue
                    
                image_files = sorted([
                    os.path.join(chapter_dir, f)
                    for f in os.listdir(chapter_dir)
                    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif'))
                ])
                
                # Create chapter folder inside CBZ
                chapter_folder = re.sub(r'[\\/*?:"<>|]', '_', chapter_name)
                for image_file in image_files:
                    cbz_file.write(image_file, f"{chapter_folder}/{os.path.basename(image_file)}")
        
        logger.info(f"Successfully created merged CBZ: {cbz_path}")

    def create_merged_epub(self, chapter_dirs, manga_title):
        """Create a single merged EPUB from all chapter directories"""
        logger.info(f"Creating merged EPUB for: {manga_title}")
        
        book = epub.EpubBook()
        book.set_identifier(manga_title.replace(' ', '-'))
        book.set_title(manga_title)
        book.set_language('en')
        
        spine = ['nav']
        toc = []
        img_counter = 1
        
        for chapter_dir, chapter_name in sorted(chapter_dirs, key=lambda x: self.extract_chapter_number(x[1])):
            if not os.path.exists(chapter_dir):
                continue
                
            image_files = sorted([
                os.path.join(chapter_dir, f)
                for f in os.listdir(chapter_dir)
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif'))
            ])
            
            chapter_pages = []
            for image_file in image_files:
                with open(image_file, 'rb') as f:
                    img_data = f.read()
                
                ext = os.path.splitext(image_file)[1].lower()
                media_type = {
                    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                    '.png': 'image/png', '.webp': 'image/webp', '.gif': 'image/gif'
                }.get(ext, 'image/jpeg')
                
                img_item = epub.EpubItem(
                    uid=f'img_{img_counter}',
                    file_name=f'images/page_{img_counter:04d}{ext}',
                    media_type=media_type,
                    content=img_data
                )
                book.add_item(img_item)
                
                page = epub.EpubHtml(title=f'{chapter_name} - Page {img_counter}', file_name=f'page_{img_counter:04d}.xhtml')
                page.content = f'''<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{chapter_name}</title>
<style>body{{margin:0;padding:0;text-align:center;background:#000;}}
img{{max-width:100%;max-height:100vh;object-fit:contain;}}</style>
</head>
<body><img src="images/page_{img_counter:04d}{ext}" alt="{chapter_name}"/></body>
</html>'''
                book.add_item(page)
                spine.append(page)
                chapter_pages.append(page)
                img_counter += 1
            
            if chapter_pages:
                toc.append(epub.Link(chapter_pages[0].file_name, chapter_name, chapter_name.replace(' ', '-')))
        
        book.toc = toc
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = spine
        
        epub_path = os.path.join(self.output_dir, f"{manga_title}.epub")
        epub.write_epub(epub_path, book, {})
        logger.info(f"Successfully created merged EPUB: {epub_path}")

    def parse_chapter_range(self, total_chapters):
        """Parse chapter range and return list of indices to download"""
        if self.chapter_range is None:
            return list(range(total_chapters))
        
        if isinstance(self.chapter_range, (int, float)):
            # Single chapter
            # Convert chapter number to index by finding closest match
            target = float(self.chapter_range)
            for i, chapter in enumerate(self.chapters):
                chapter_num = self.extract_chapter_number(chapter['name'])
                if chapter_num == target:
                    return [i]
            logger.error(f"Chapter {self.chapter_range} not found")
            return []
        
        if isinstance(self.chapter_range, tuple):
            start, end = map(float, self.chapter_range)
            indices = []
            for i, chapter in enumerate(self.chapters):
                chapter_num = self.extract_chapter_number(chapter['name'])
                if start <= chapter_num <= end:
                    indices.append(i)
            if indices:
                return indices
            else:
                logger.error(f"No chapters found in range {start} to {end}")
                return []
        
        return []

    def extract_chapter_number(self, chapter_name):
        """Extract chapter number from chapter name, handling decimal points"""
        # Try to find a decimal number pattern (e.g., 23.5, 100.2, etc.)
        match = re.search(r'(?:chapter\s*)?(\d+\.?\d*)', chapter_name.lower())
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return 0.0

    def run(self):
        """Run the full scraping process"""
        logger.info(f"Starting to scrape manga from: {self.manga_url}")
        
        # Get manga page
        response = self.session.get(self.manga_url)
        if response.status_code != 200:
            logger.error("Failed to fetch manga page")
            return False
            
        soup = BeautifulSoup(response.content, 'html.parser')
        manga_title = self.get_manga_title(soup)
        logger.info(f"Manga title: {manga_title}")
        
        # Update output directory to include manga title
        manga_title_clean = re.sub(r'[\\/*?:"<>|]', '_', manga_title)
        self.output_dir = os.path.join(self.output_dir, manga_title_clean)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Download cover image
        self.download_cover_image(soup, self.output_dir)
        
        # Get all chapters
        self.chapters = self.get_chapters()  # Store chapters in instance variable
        if not self.chapters:
            logger.error("No chapters found")
            return False
        
        # Get chapters to download based on range
        chapter_indices = self.parse_chapter_range(len(self.chapters))
        chapters_to_download = [self.chapters[i] for i in chapter_indices]
        
        if not chapters_to_download:
            logger.error("No chapters selected for download")
            return False
        
        logger.info(f"Will download {len(chapters_to_download)} chapters")
        
        # Add checkpoint file
        checkpoint_file = os.path.join(self.output_dir, '.checkpoint')
        downloaded_chapters = set()
        
        if os.path.exists(checkpoint_file):
            with open(checkpoint_file, 'r') as f:
                downloaded_chapters = set(f.read().splitlines())
        
        # Download chapters concurrently
        total_downloaded = 0
        self.downloaded_chapter_dirs = []  # Reset for this run
        self.manga_title_clean = manga_title_clean  # Store for merge functions
        
        try:
            with ThreadPoolExecutor(max_workers=3) as executor:  # Limit to 3 concurrent chapter downloads
                future_to_chapter = {
                    executor.submit(self.download_chapter, chapter): chapter 
                    for chapter in chapters_to_download
                }
                
                for future in as_completed(future_to_chapter):
                    if self.stop_flag():
                        logger.info("Download stopped by user")
                        return False
                    
                    chapter = future_to_chapter[future]
                    try:
                        downloaded, chapter_dir = future.result()
                        if downloaded > 0:
                            total_downloaded += downloaded
                            # Track chapter dir for potential merging
                            if chapter_dir:
                                self.downloaded_chapter_dirs.append((chapter_dir, chapter['name']))
                            
                            # Update checkpoint file
                            with open(checkpoint_file, 'a') as f:
                                f.write(f"{chapter['name']}\n")
                            
                            # Only create per-chapter files if NOT merging
                            if not self.merge_chapters:
                                if self.convert_to_pdf and chapter_dir:
                                    self.create_pdf_from_chapter(chapter_dir, chapter['name'])
                                if self.convert_to_cbz and chapter_dir:
                                    self.create_cbz_from_chapter(chapter_dir, chapter['name'])
                                if self.convert_to_epub and chapter_dir:
                                    self.create_epub_from_chapter(chapter_dir, chapter['name'], manga_title)
                                
                                if self.delete_images_after_conversion and chapter_dir:
                                    if self.convert_to_pdf or self.convert_to_cbz or self.convert_to_epub:
                                        self.delete_chapter_images(chapter_dir)
                        
                        time.sleep(self.delay)  # Small delay between chapters
                    except Exception as e:
                        logger.error(f"Error downloading chapter {chapter['name']}: {e}")
            
            # After all chapters downloaded, create merged files if enabled
            if self.merge_chapters and self.downloaded_chapter_dirs:
                logger.info("Creating merged files...")
                if self.convert_to_pdf:
                    self.create_merged_pdf(self.downloaded_chapter_dirs, manga_title_clean)
                if self.convert_to_cbz:
                    self.create_merged_cbz(self.downloaded_chapter_dirs, manga_title_clean)
                if self.convert_to_epub:
                    self.create_merged_epub(self.downloaded_chapter_dirs, manga_title_clean)
                
                # Delete chapter images after merge if enabled
                if self.delete_images_after_conversion:
                    for chapter_dir, _ in self.downloaded_chapter_dirs:
                        if os.path.exists(chapter_dir):
                            self.delete_chapter_images(chapter_dir)
            
            logger.info(f"Completed downloading {manga_title}. Total images: {total_downloaded}")
            return True
        
        except Exception as e:
            logger.error(f"Error during download: {e}")
            return False

if __name__ == "__main__":
    manga_url = input("Enter the manga URL: ")
    
    # Chapter selection
    chapter_select = input(
        "Enter chapter selection (default: all):\n"
        "- Single chapter: '5' or '23.5'\n"
        "- Range: '1-10' or '5.5-15.5'\n"
        "- All chapters: press Enter\n"
        "Your choice: "
    ).strip()
    
    chapter_range = None
    if chapter_select:
        if '-' in chapter_select:
            try:
                start, end = map(float, chapter_select.split('-'))
                chapter_range = (start, end)
            except ValueError:
                print("Invalid range format. Using all chapters.")
        else:
            try:
                chapter_range = float(chapter_select)
            except ValueError:
                print("Invalid chapter number. Using all chapters.")
    
    output_dir = input("Enter output directory (default: downloads): ") or "downloads"
    delay = float(input("Enter delay between chapters in seconds (default: 1.0): ") or "1.0")
    max_threads = int(input("Enter maximum number of download threads (default: 4): ") or "4")
    convert_to_pdf_choice = input("Convert chapters to PDF? (y/n, default: n): ").lower() == 'y'
    convert_to_cbz_choice = input("Convert chapters to CBZ? (y/n, default: n): ").lower() == 'y'
    delete_images_choice = input("Delete images after conversion? (y/n, default: n): ").lower() == 'y'
    
    scraper = WeebCentralScraper(
        manga_url=manga_url,
        chapter_range=chapter_range,
        output_dir=output_dir,
        delay=delay,
        max_threads=max_threads,
        convert_to_pdf=convert_to_pdf_choice,
        convert_to_cbz=convert_to_cbz_choice,
        delete_images_after_conversion=delete_images_choice
    )
    
    scraper.run()
