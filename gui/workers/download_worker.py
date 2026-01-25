"""
Download Worker.
Background thread for downloading manga chapters with proper progress tracking.
"""

from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import re
import time
import threading

from PyQt6.QtCore import QThread, pyqtSignal

# Import the existing scraper
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from weebcentral_scraper import WeebCentralScraper
from gui.config import get_settings


class DownloadWorker(QThread):
    """
    Worker thread for downloading chapters.
    Uses ThreadPoolExecutor for parallel chapter downloads with proper progress tracking.
    """
    
    # Signals
    started_signal = pyqtSignal()
    chapter_started = pyqtSignal(str)  # Chapter name
    chapter_progress = pyqtSignal(str, int)  # Chapter name, progress 0-100
    chapter_finished = pyqtSignal(str, bool)  # Chapter name, success
    overall_progress = pyqtSignal(int, int)  # Current, total
    error = pyqtSignal(str, str)  # Chapter name, error message
    finished_signal = pyqtSignal(bool)  # Overall success
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._manga_url = ""
        self._manga_title = ""  # Store manga title for merge
        self._chapters: List[Dict] = []
        self._is_running = False
        self._output_dir = None
        self._lock = threading.Lock()
        self._completed_count = 0
        self._downloaded_chapter_dirs = []  # Track chapter dirs for merging
        
        # Progress tracking per chapter
        self._chapter_progress: Dict[str, Dict] = {}  # {name: {total: int, downloaded: int}}
    
    def set_download_params(
        self, 
        manga_url: str, 
        chapters: List[Dict],
        output_dir: Optional[str] = None,
        manga_title: str = ""
    ):
        """Set the download parameters."""
        self._manga_url = manga_url
        self._chapters = chapters
        self._output_dir = output_dir
        self._manga_title = manga_title
    
    def _emit_progress(self, chapter_name: str, downloaded: int, total: int):
        """Thread-safe progress emission."""
        if total > 0 and self._is_running:
            progress = int((downloaded / total) * 100)
            self.chapter_progress.emit(chapter_name, progress)
    
    def _download_single_chapter(self, chapter: Dict, settings, scraper_base) -> tuple:
        """Download a single chapter with proper progress tracking.
        Returns: (success: bool, chapter_dir: str or None, chapter_name: str)
        """
        if not self._is_running:
            chapter_name = chapter.get("name", "Unknown")
            return False, None, chapter_name
        
        chapter_name = chapter.get("name", "Unknown")
        chapter_url = chapter.get("url", "")
        
        try:
            # Emit chapter started signal
            self.chapter_started.emit(chapter_name)
            self._emit_progress(chapter_name, 0, 100)
            
            # Create a scraper instance for this chapter
            scraper = WeebCentralScraper(
                manga_url=self._manga_url,
                output_dir=self._output_dir or settings.output_dir,
                delay=settings.delay,
                max_threads=settings.max_image_threads,
                convert_to_pdf=False,
                convert_to_cbz=False,
                delete_images_after_conversion=False
            )
            
            # Clean up chapter name for directory
            chapter_name_clean = re.sub(r'[\\/*?:"<>|]', '_', chapter_name)
            chapter_dir = os.path.join(scraper.output_dir, chapter_name_clean)
            os.makedirs(chapter_dir, exist_ok=True)
            
            # Get image URLs
            image_urls = scraper.get_chapter_images(chapter_url)
            
            if not image_urls:
                self.chapter_finished.emit(chapter_name, False)
                return False, None, chapter_name
            
            total_images = len(image_urls)
            downloaded_count = 0
            
            # Emit 0% progress
            self._emit_progress(chapter_name, 0, total_images)
            
            # Download images with thread pool
            with ThreadPoolExecutor(max_workers=settings.max_image_threads) as executor:
                future_to_url = {}
                
                for index, url in enumerate(image_urls, 1):
                    ext = url.split('.')[-1].lower()
                    if ext not in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
                        ext = 'jpg'
                    
                    filepath = os.path.join(chapter_dir, f"{index:03d}.{ext}")
                    future = executor.submit(scraper.download_image, url, filepath, chapter_url)
                    future_to_url[future] = url
                    
                    time.sleep(0.1)  # Small delay between starting downloads
                
                for future in as_completed(future_to_url):
                    if not self._is_running:
                        break
                    
                    if future.result():
                        downloaded_count += 1
                    
                    # Emit progress after each image
                    self._emit_progress(chapter_name, downloaded_count, total_images)
            
            success = downloaded_count > 0
            
            if success:
                # Handle conversions only if NOT merging
                if not settings.merge_chapters:
                    if settings.convert_to_pdf:
                        scraper.create_pdf_from_chapter(chapter_dir, chapter_name)
                    if settings.convert_to_cbz:
                        scraper.create_cbz_from_chapter(chapter_dir, chapter_name)
                    if settings.convert_to_epub:
                        scraper.create_epub_from_chapter(chapter_dir, chapter_name)
                    if settings.delete_images_after_conversion:
                        if settings.convert_to_pdf or settings.convert_to_cbz or settings.convert_to_epub:
                            scraper.delete_chapter_images(chapter_dir)
                
                self.chapter_finished.emit(chapter_name, True)
                
                # Update completed count
                with self._lock:
                    self._completed_count += 1
                    self.overall_progress.emit(self._completed_count, len(self._chapters))
            else:
                self.chapter_finished.emit(chapter_name, False)
            
            return success, chapter_dir if success else None, chapter_name
                
        except Exception as e:
            self.error.emit(chapter_name, str(e))
            self.chapter_finished.emit(chapter_name, False)
            return False, None, chapter_name
    
    def run(self):
        """Execute the download operation with parallel chapter downloads."""
        self._is_running = True
        self._completed_count = 0
        self._downloaded_chapter_dirs = []  # Reset for this run
        self.started_signal.emit()
        
        settings = get_settings()
        
        total_chapters = len(self._chapters)
        successful = 0
        
        # Create a base scraper for merge functions
        scraper_base = WeebCentralScraper(
            manga_url=self._manga_url,
            output_dir=self._output_dir or settings.output_dir,
            delay=settings.delay,
            max_threads=settings.max_image_threads,
            convert_to_pdf=settings.convert_to_pdf,
            convert_to_cbz=settings.convert_to_cbz,
            convert_to_epub=settings.convert_to_epub,
            merge_chapters=settings.merge_chapters,
            delete_images_after_conversion=settings.delete_images_after_conversion
        )
        
        try:
            # Use ThreadPoolExecutor for parallel chapter downloads
            max_concurrent = settings.max_threads  # Number of concurrent chapters
            
            with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                # Submit all chapter downloads
                future_to_chapter = {
                    executor.submit(self._download_single_chapter, chapter, settings, scraper_base): chapter
                    for chapter in self._chapters
                }
                
                # Process completed downloads
                for future in as_completed(future_to_chapter):
                    if not self._is_running:
                        for f in future_to_chapter:
                            f.cancel()
                        break
                    
                    chapter = future_to_chapter[future]
                    try:
                        result = future.result()
                        success, chapter_dir, chapter_name = result
                        if success:
                            successful += 1
                            if chapter_dir:
                                self._downloaded_chapter_dirs.append((chapter_dir, chapter_name))
                    except Exception as e:
                        chapter_name = chapter.get("name", "Unknown")
                        self.error.emit(chapter_name, str(e))
            
            # After all chapters complete, create merged files if enabled
            if settings.merge_chapters and self._downloaded_chapter_dirs:
                # Use stored manga title, clean it for filename
                manga_title = re.sub(r'[\\/*?:"<>|]', '_', self._manga_title) if self._manga_title else "manga"
                
                # Get proper output dir from first downloaded chapter (parent of chapter dir)
                first_chapter_dir = self._downloaded_chapter_dirs[0][0]
                merge_output_dir = os.path.dirname(first_chapter_dir)
                
                # Update scraper output_dir for merge functions
                scraper_base.output_dir = merge_output_dir
                
                if settings.convert_to_pdf:
                    scraper_base.create_merged_pdf(self._downloaded_chapter_dirs, manga_title)
                if settings.convert_to_cbz:
                    scraper_base.create_merged_cbz(self._downloaded_chapter_dirs, manga_title)
                if settings.convert_to_epub:
                    scraper_base.create_merged_epub(self._downloaded_chapter_dirs, manga_title)
                
                # Delete chapter images after merge if enabled
                if settings.delete_images_after_conversion:
                    for chapter_dir, _ in self._downloaded_chapter_dirs:
                        if os.path.exists(chapter_dir):
                            scraper_base.delete_chapter_images(chapter_dir)
            
            self.overall_progress.emit(total_chapters, total_chapters)
            self.finished_signal.emit(successful > 0)
            
        except Exception as e:
            self.error.emit("", f"Download failed: {str(e)}")
            self.finished_signal.emit(False)
        finally:
            self._is_running = False
    
    def stop(self):
        """Request the worker to stop."""
        self._is_running = False
    
    @property
    def is_running(self) -> bool:
        return self._is_running
