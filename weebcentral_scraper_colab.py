import requests
import os
import re
import shutil  # Add missing import for shutil
import tempfile  # Add import for tempfile
import uuid
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm.notebook import tqdm  # Using notebook version for Colab
from IPython.core.display import display, HTML
import subprocess
import sys
import zipfile
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Check if running in Colab - use multiple detection methods
def is_colab():
    if 'google.colab' in sys.modules:
        return True
    if os.path.exists('/content') and os.path.exists('/usr/local/lib/python3.10/dist-packages'):
        return True
    if 'COLAB_GPU' in os.environ or 'COLAB_RELEASE_TAG' in os.environ:
        return True
    if os.path.exists('/content'):
        return True
    return False

IN_COLAB = is_colab()

# Chrome paths for Colab (these are set when Chrome for Testing is installed manually)
CHROME_BINARY_PATH = '/opt/chrome-linux64/chrome'
CHROMEDRIVER_PATH = '/opt/chromedriver-linux64/chromedriver'

# Colab-specific: Check if Chrome is installed, warn if not
if IN_COLAB:
    if not os.path.exists(CHROME_BINARY_PATH):
        print("⚠️  Chrome for Testing not found!")
        print("Please run the Chrome installation cell first.")
        print("See the notebook instructions for setup commands.")

class WeebCentralScraper:
    def __init__(self, manga_url, chapter_range=None, output_dir="downloads", delay=1.0, max_threads=4, convert_to_cbz=False, delete_images=False):
        self.base_url = "https://weebcentral.com"
        if not manga_url.startswith(('http://', 'https://')):
            manga_url = 'https://' + manga_url
        self.manga_url = manga_url
        self.chapter_range = chapter_range
        self.output_dir = output_dir
        self.delay = float(delay)
        self.max_threads = max_threads
        self.convert_to_cbz = convert_to_cbz
        self.delete_images = delete_images
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
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
        
        # Create output directory in Colab
        if IN_COLAB:
            try:
                from google.colab import drive
                drive.mount('/content/drive')
                self.output_dir = f'/content/drive/MyDrive/{output_dir}'
            except Exception as e:
                logger.warning(f"Could not mount Google Drive: {e}. Using local Colab storage.")
                self.output_dir = f'/content/{output_dir}'
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.chapters = []
        self.progress_callback = None
        self.stop_flag = lambda: False

    def get_chrome_driver(self):
        """Configure and return Chrome WebDriver with appropriate options"""
        chrome_options = webdriver.ChromeOptions()
        
        if IN_COLAB:
            # Use undetected-chromedriver to bypass Cloudflare
            # This library patches Chrome at a deep level to avoid detection
            try:
                import undetected_chromedriver as uc
            except ImportError:
                logger.info("Installing undetected-chromedriver...")
                subprocess.run([sys.executable, '-m', 'pip', 'install', 'undetected-chromedriver', '-q'], check=True)
                import undetected_chromedriver as uc
            
            options = uc.ChromeOptions()
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument("--window-size=1920,1080")
            
            # undetected-chromedriver will automatically download and patch the correct chromedriver
            driver = uc.Chrome(
                options=options,
                browser_executable_path=CHROME_BINARY_PATH,
                driver_executable_path=CHROMEDRIVER_PATH,
                headless=True,
                use_subprocess=True
            )
            logger.info("Undetected Chrome driver initialized successfully.")
        else:
            # Local setup - use new headless mode
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument(f'user-agent={self.headers["User-Agent"]}')
            
            prefs = {
                "profile.default_content_setting_values.notifications": 2,
            }
            chrome_options.add_experimental_option("prefs", prefs)
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            
            try:
                from selenium.webdriver.chrome.service import Service as ChromeService
                from webdriver_manager.chrome import ChromeDriverManager
                service = ChromeService(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
            except (ImportError, Exception):
                logger.warning("WebDriver manager not found or failed. Falling back to default ChromeDriver in PATH.")
                driver = webdriver.Chrome(options=chrome_options)
        
        return driver

    def cleanup_chrome(self, driver):
        """Properly cleanup Chrome instance."""
        if not driver:
            return
        try:
            driver.close()
            driver.quit()
        except Exception as e:
            # This can happen if the browser has already crashed
            logger.warning(f"Ignoring error during Chrome cleanup: {e}")

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
        """Get list of all chapter URLs using Selenium to bypass Cloudflare"""
        chapter_list_url = self.get_chapter_list_url()
        logger.info(f"Fetching chapter list from: {chapter_list_url}")
        
        driver = None
        try:
            driver = self.get_chrome_driver()
            driver.get(chapter_list_url)
            
            # Wait for chapter elements to load
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[x-data] > a")))
            time.sleep(2)  # Extra wait for dynamic content
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
        except Exception as e:
            logger.error(f"Failed to fetch chapter list: {e}")
            return []
        finally:
            self.cleanup_chrome(driver)
            
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

    def get_chapter_images(self, chapter_url, max_retries=3):
        """Get list of image URLs for a chapter with retry functionality."""
        logger.info("Loading page with Selenium...")
        driver = None
        for attempt in range(max_retries):
            try:
                driver = self.get_chrome_driver()
                driver.get(chapter_url)

                # Wait for images to become visible
                wait = WebDriverWait(driver, 20)
                wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "img[src*='/manga/']")))
                
                # Scroll down to trigger lazy loading
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)  # Wait for new images to load

                image_elements = driver.find_elements(By.CSS_SELECTOR, "img[src*='/manga/']")
                image_urls = [img.get_attribute('src') for img in image_elements if img.get_attribute('src')]

                if image_urls:
                    logger.info(f"Found {len(image_urls)} images on attempt {attempt + 1}")
                    return image_urls
                else:
                    logger.warning(f"No images found on attempt {attempt + 1}, retrying...")

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    logger.error("All attempts to get chapter images failed.")
                    return []
            finally:
                self.cleanup_chrome(driver)

            # Wait before retrying
            if attempt < max_retries - 1:
                time.sleep(3 * (attempt + 1))

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
        image_urls = [
            url for url in image_urls if url and not any(
                word in url.lower() for word in ['avatar', 'icon', 'logo', 'banner', 'brand']
            )
        ]
        
        # Download images with multiple threads
        downloaded = 0
        if self.progress_callback:
            self.progress_callback(chapter['name'], 0)
        
        with tqdm(total=len(image_urls), desc=f"Chapter {chapter['name']}") as pbar:
            with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
                future_to_url = {}
                
                for index, url in enumerate(image_urls, 1):
                    if not url:
                        continue
                    ext = url.split('.')[-1].lower() if '.' in url else 'jpg'
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
        
        # Get manga page using Selenium to bypass Cloudflare
        driver = None
        try:
            logger.info("Initializing Chrome Driver in run()...")
            driver = self.get_chrome_driver()
            logger.info("Chrome Driver initialized successfully.")
            
            logger.info(f"Navigating to {self.manga_url}...")
            driver.get(self.manga_url)
            logger.info("Navigation command sent.")
            
            # Wait for main content to load
            logger.info("Waiting for page content (section[x-data])...")
            wait = WebDriverWait(driver, 30) # Increased timeout
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "section[x-data]")))
            logger.info("Page element found.")
            
            time.sleep(5)  # Extra wait for dynamic content/Cloudflare challenge
            logger.info("Finished extra wait.")
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            logger.info("Parsed page source with BeautifulSoup.")
            
        except Exception as e:
            logger.error(f"Failed to fetch manga page: {e}")
            if driver:
                try:
                    logger.info("Attempting to capture screenshot of failure...")
                    driver.save_screenshot("debug_failure.png")
                    logger.info("Screenshot saved to debug_failure.png")
                    logger.info(f"Current URL: {driver.current_url}")
                    logger.info(f"Page Title: {driver.title}")
                except Exception as sc_e:
                    logger.error(f"Failed to capture debug info: {sc_e}")
            return False
        finally:
            self.cleanup_chrome(driver)
            
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

                            if self.convert_to_cbz and chapter_dir:
                                self.create_cbz_from_chapter(chapter_dir, chapter['name'])

                            if self.delete_images and chapter_dir:
                                self.delete_chapter_images(chapter_dir)

                        time.sleep(self.delay)  # Small delay between chapters
                    except Exception as e:
                        logger.error(f"Error downloading chapter {chapter['name']}: {e}")
            
            logger.info(f"Completed downloading {manga_title}. Total images: {total_downloaded}")
            return True
        
        except Exception as e:
            logger.error(f"Error during download: {e}")
            return False

def main():
    """Main function for Colab interface"""
    display(HTML("<h2>WeebCentral Manga Downloader</h2>"))
    
    # Get manga URL
    manga_url = input("Enter manga URL: ")
    
    # Get chapter selection
    print("\nChapter Selection:")
    print("1. All chapters")
    print("2. Single chapter")
    print("3. Chapter range")
    choice = input("Enter your choice (1-3): ")
    
    chapter_range = None
    if choice == "2":
        chapter = float(input("Enter chapter number: "))
        chapter_range = chapter
    elif choice == "3":
        start = float(input("Enter start chapter: "))
        end = float(input("Enter end chapter: "))
        chapter_range = (start, end)
    
    # Get other parameters
    output_dir = input("\nEnter output directory (default: manga_downloads): ") or "manga_downloads"
    delay = float(input("Enter delay between chapters in seconds (default: 1.0): ") or "1.0")
    max_threads = int(input("Enter maximum number of download threads (default: 4): ") or "4")
    convert_to_cbz_choice = input("Convert chapters to CBZ? (y/n, default: n): ").lower() == 'y'
    delete_images_choice = input("Delete images after conversion? (y/n, default: n): ").lower() == 'y'
    
    # Create and run scraper
    scraper = WeebCentralScraper(
        manga_url=manga_url,
        chapter_range=chapter_range,
        output_dir=output_dir,
        delay=delay,
        max_threads=max_threads,
        convert_to_cbz=convert_to_cbz_choice,
        delete_images=delete_images_choice
    )
    
    scraper.run()

if __name__ == "__main__":
    main()
