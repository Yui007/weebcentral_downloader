import requests
import os
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from selenium.webdriver.support.ui import WebDriverWait
from fpdf import FPDF
from PIL import Image

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

class WeebCentralScraper:
    def __init__(self, manga_url, chapter_range=None, output_dir="downloads", delay=1, max_threads=4, convert_to_pdf=False):
        self.base_url = "https://weebcentral.com"
        if not manga_url.startswith(('http://', 'https://')):
            manga_url = 'https://' + manga_url
        self.manga_url = manga_url
        self.chapter_range = chapter_range
        self.output_dir = output_dir
        self.delay = delay
        self.max_threads = max_threads
        self.convert_to_pdf = convert_to_pdf
        
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
        
        # Create a session for persistent connections
        self.session = requests.Session()
        self.session.headers.update(self.headers)
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
        
        response = requests.get(chapter_list_url, headers=self.headers)
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
                if not chapter_url.startswith(('http://', 'https://')):
                    chapter_url = urljoin(self.base_url, chapter_url)
                
                chapters.append({
                    'url': chapter_url,
                    'name': chapter_name
                })
        
        return chapters

    def get_chapter_images(self, chapter_url):
        """Get list of image URLs for a chapter"""
        logger.info("Loading page with Selenium...")
        
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'user-agent={self.headers["User-Agent"]}')
        # Add preference to disable brotli compression
        options.add_experimental_option('prefs', {
            'profile.default_content_settings.cookies': 2,
            'profile.managed_default_content_settings.images': 1,
            'profile.default_content_setting_values.notifications': 2
        })
        # Add header to disable brotli
        options.add_argument('--accept-encoding=gzip, deflate')
        
        driver = webdriver.Chrome(options=options)
        
        try:
            driver.get(chapter_url)
            time.sleep(3)  # Wait for JavaScript to load
            
            # Wait for images to load
            WebDriverWait(driver, 10).until(
                lambda x: x.find_elements(By.CSS_SELECTOR, "img[src*='/manga/']")
            )
            
            # Get all image elements
            image_elements = driver.find_elements(By.CSS_SELECTOR, "img[src*='/manga/']")
            image_urls = []
            
            for img in image_elements:
                url = img.get_attribute('src')
                if url and not url.startswith('data:'):
                    image_urls.append(url)
            
            logger.info(f"Found {len(image_urls)} images")
            return image_urls
            
        finally:
            driver.quit()

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
                    img_response = self.session.get(
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
        image_urls = [url for url in image_urls if not any(
            word in url.lower() for word in ['avatar', 'icon', 'logo', 'banner', 'brand']
        )]
        
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
        """Create a PDF from all images in a chapter directory"""
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
        for image_file in image_files:
            try:
                with Image.open(image_file) as img:
                    width, height = img.size
                    # A4 size: 210x297 mm
                    # Keep aspect ratio
                    if width > height:
                        w, h = 297, 210
                    else:
                        w, h = 210, 297
                    
                    # Scale image to fit page
                    w_new = w
                    h_new = h
                    if width / height > w / h:
                        h_new = w * height / width
                    else:
                        w_new = h * width / height
                        
                    pdf.add_page()
                    pdf.image(image_file, x=(w - w_new) / 2, y=(h - h_new) / 2, w=w_new, h=h_new)
            except Exception as e:
                logger.error(f"Failed to process image {image_file}: {e}")

        pdf_path = os.path.join(self.output_dir, f"{chapter_name}.pdf")
        pdf.output(pdf_path, "F")
        logger.info(f"Successfully created PDF: {pdf_path}")

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
        response = requests.get(self.manga_url, headers=self.headers)
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
                            # Update checkpoint file
                            with open(checkpoint_file, 'a') as f:
                                f.write(f"{chapter['name']}\n")
                            
                            if self.convert_to_pdf and chapter_dir:
                                self.create_pdf_from_chapter(chapter_dir, chapter['name'])
                        
                        time.sleep(self.delay)  # Small delay between chapters
                    except Exception as e:
                        logger.error(f"Error downloading chapter {chapter['name']}: {e}")
            
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
    
    scraper = WeebCentralScraper(
        manga_url=manga_url,
        chapter_range=chapter_range,
        output_dir=output_dir,
        delay=delay,
        max_threads=max_threads,
        convert_to_pdf=convert_to_pdf_choice
    )
    
    scraper.run()
