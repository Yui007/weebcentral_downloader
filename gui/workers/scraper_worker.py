"""
Scraper Worker.
Background thread for fetching manga information.
"""

from typing import Optional, Dict, List, Any
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from flaresolverr_client import FlareSolverrSession

from PyQt6.QtCore import QThread, pyqtSignal


class ScraperWorker(QThread):
    """
    Worker thread for fetching manga information from WeebCentral.
    Runs scraping operations in background to keep UI responsive.
    """
    
    # Signals
    started_signal = pyqtSignal()
    progress = pyqtSignal(str)  # Status message
    manga_info_ready = pyqtSignal(dict)  # Manga metadata
    chapters_ready = pyqtSignal(list)  # List of chapters
    cover_ready = pyqtSignal(bytes)  # Cover image data
    error = pyqtSignal(str)  # Error message
    finished_signal = pyqtSignal(bool)  # Success status
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._manga_url = ""
        self._is_running = False
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        # HTML Session (FlareSolverr)
        self.session = FlareSolverrSession()
        
        # Image Session (Direct)
        self.image_session = requests.Session()
        self.image_session.headers.update(self.headers)
    
    def set_url(self, url: str):
        """Set the manga URL to fetch."""
        self._manga_url = url
    
    def run(self):
        """Execute the scraping operation."""
        self._is_running = True
        self.started_signal.emit()
        
        try:
            self.progress.emit("Fetching manga page...")
            
            # Fetch main manga page
            response = self.session.get(self._manga_url)
            if response.status_code != 200:
                self.error.emit(f"Failed to fetch manga page (HTTP {response.status_code})")
                self.finished_signal.emit(False)
                return
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract manga info
            self.progress.emit("Extracting manga information...")
            manga_info = self._extract_manga_info(soup)
            self.manga_info_ready.emit(manga_info)
            
            # Fetch cover image
            if manga_info.get("cover_url"):
                self.progress.emit("Downloading cover image...")
                cover_data = self._fetch_cover(manga_info["cover_url"])
                if cover_data:
                    self.cover_ready.emit(cover_data)
            
            # Fetch chapters
            self.progress.emit("Fetching chapter list...")
            chapters = self._fetch_chapters()
            self.chapters_ready.emit(chapters)
            
            self.progress.emit("Done!")
            self.finished_signal.emit(True)
            
        except requests.exceptions.Timeout:
            self.error.emit("Request timed out. Please try again.")
            self.finished_signal.emit(False)
        except requests.exceptions.ConnectionError:
            self.error.emit("Connection error. Please check your internet.")
            self.finished_signal.emit(False)
        except Exception as e:
            self.error.emit(f"Error: {str(e)}")
            self.finished_signal.emit(False)
        finally:
            self._is_running = False
    
    def _extract_manga_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract manga metadata from the page."""
        info = {
            "title": "",
            "cover_url": "",
            "description": "",
            "metadata": {},
            "tags": []
        }
        
        # Title - look for the main title element
        title_elem = soup.select_one("h1") or soup.select_one("h2.font")
        if title_elem:
            info["title"] = title_elem.get_text(strip=True)
        
        # Cover image
        cover_elem = soup.select_one("img[src*='cover']") or soup.select_one("section img")
        if cover_elem:
            src = cover_elem.get("src", "")
            if src:
                if not src.startswith("http"):
                    src = urljoin("https://weebcentral.com", src)
                info["cover_url"] = src
        
        # Description
        desc_elem = soup.select_one("section p") or soup.select_one("[class*='description']")
        if desc_elem:
            info["description"] = desc_elem.get_text(strip=True)
        
        # Extract metadata from info rows
        info_rows = soup.select("section ul li")
        for row in info_rows:
            text = row.get_text(strip=True)
            if ":" in text:
                key, value = text.split(":", 1)
                info["metadata"][key.strip()] = value.strip()
        
        # Tags/genres
        tag_elems = soup.select("a[href*='genre']") or soup.select("[class*='tag']")
        info["tags"] = [tag.get_text(strip=True) for tag in tag_elems[:10]]
        
        return info
    
    def _fetch_cover(self, url: str) -> Optional[bytes]:
        """Fetch cover image data."""
        try:
            response = self.image_session.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                return response.content
        except Exception:
            pass
        return None
    
    def _fetch_chapters(self) -> List[Dict]:
        """Fetch chapter list from the full chapters page."""
        chapters = []
        
        try:
            # Construct chapters URL using same logic as WeebCentralScraper
            from urllib.parse import urlparse
            parsed_url = urlparse(self._manga_url)
            path_parts = parsed_url.path.split('/')
            # Build path like /series/ID/full-chapter-list
            chapter_list_path = f"{'/'.join(path_parts[:3])}/full-chapter-list"
            chapters_url = f"https://weebcentral.com{chapter_list_path}"
            
            response = self.session.get(chapters_url)
            if response.status_code != 200:
                return chapters
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all chapter links - using exact selector from working scraper
            chapter_elements = soup.select("div[x-data] > a")
            
            # Process chapters in reverse order (oldest first)
            for element in reversed(chapter_elements):
                chapter_url = element.get('href')
                chapter_name_elem = element.select_one("span.flex > span")
                chapter_name = chapter_name_elem.text.strip() if chapter_name_elem else "Unknown Chapter"
                
                if chapter_url:
                    # Handle case where href might be a list
                    if isinstance(chapter_url, list):
                        chapter_url = chapter_url[0]
                    if not chapter_url.startswith(('http://', 'https://')):
                        chapter_url = urljoin("https://weebcentral.com", chapter_url)
                    
                    chapters.append({
                        "name": chapter_name,
                        "url": chapter_url
                    })
        
        except Exception as e:
            print(f"Error fetching chapters: {e}")
        
        return chapters
    
    def stop(self):
        """Request the worker to stop."""
        self._is_running = False
