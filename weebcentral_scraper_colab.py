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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Check if running in Colab
IN_COLAB = 'google.colab' in sys.modules

# Install required packages for Colab
if IN_COLAB:
    def install_chrome():
        commands = [
            'apt-get update',
            'apt-get install -y chromium-chromedriver',
            'cp /usr/lib/chromium-browser/chromedriver /usr/bin',
            'chmod +x /usr/bin/chromedriver'
        ]
        for cmd in commands:
            process = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if process.returncode != 0:
                print(f"Error running {cmd}:")
                print(process.stderr)
                return False
        return True

    # Install Chrome and ChromeDriver
    if not install_chrome():
        raise RuntimeError("Failed to install Chrome/ChromeDriver")
    
    # Import Selenium after installation
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
else:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
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
                os.makedirs(self.output_dir, exist_ok=True)
            except Exception as e:
                logger.error(f"Error setting up Google Drive: {e}")
                raise
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.chapters = []
        self.progress_callback = None
        self.stop_flag = lambda: False

    def get_chrome_driver(self):
        """Configure and return Chrome WebDriver with appropriate options"""
        import tempfile
        import uuid
        import shutil
        from datetime import datetime
        
        chrome_options = webdriver.ChromeOptions()
        
        # Create a unique temporary directory with timestamp and UUID
        temp_dir = os.path.join(
            tempfile.gettempdir(),
            f'chrome_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}_{uuid.uuid4().hex}'
        )
        
        try:
            # Ensure the directory is clean
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)
            
            # Basic options for both environments
            chrome_options.add_argument('--headless=new')  # Use new headless mode
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument(f'--user-data-dir={temp_dir}')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--remote-debugging-port=0')  # Use random port
            # Add header to disable brotli
            chrome_options.add_argument('--accept-encoding=gzip, deflate')
            
            # Add preference to disable brotli compression
            chrome_options.add_experimental_option('prefs', {
                'profile.default_content_settings.cookies': 2,
                'profile.managed_default_content_settings.images': 1,
                'profile.default_content_setting_values.notifications': 2
            })
            
            if IN_COLAB:
                service = Service('/usr/bin/chromedriver')
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                driver = webdriver.Chrome(options=chrome_options)
            
            return driver, temp_dir
        
        except Exception as e:
            # Clean up on failure
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise Exception(f"Failed to create Chrome driver: {str(e)}")

    def cleanup_chrome(self, driver, temp_dir):
        """Properly cleanup Chrome instance and its temporary directory"""
        try:
            if driver:
                driver.quit()
                
                # Clean up the temporary directory
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            logger.error(f"Error during Chrome cleanup: {e}")

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
        """Get list of image URLs for a chapter"""
        logger.info("Loading page with Selenium...")
        
        driver = None
        temp_dir = None
        
        try:
            driver, temp_dir = self.get_chrome_driver()
            driver.get(chapter_url)
            
            # Wait for images to load with explicit wait
            try:
                WebDriverWait(driver, 20).until(
                    lambda x: x.find_elements(By.CSS_SELECTOR, "img[src*='/manga/']")
                )
            except Exception as e:
                logger.warning(f"Timeout waiting for images: {str(e)}")
            
            # Additional wait for dynamic content
            time.sleep(5)
            
            # Get all image elements
            image_elements = driver.find_elements(By.CSS_SELECTOR, "img[src*='/manga/']")
            image_urls = []
            
            for img in image_elements:
                url = img.get_attribute('src')
                if url and not url.startswith('data:'):
                    image_urls.append(url)
            
            logger.info(f"Found {len(image_urls)} images")
            return image_urls
        
        except Exception as e:
            logger.error(f"Error in get_chapter_images: {str(e)}")
            return []
        
        finally:
            try:
                if driver:
                    driver.quit()
                if temp_dir and os.path.exists(temp_dir):
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")

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
