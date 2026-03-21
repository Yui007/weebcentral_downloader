"""
Conversion Worker.
Background thread for converting chapters to PDF/EPUB/CBZ with progress tracking.
"""

from typing import List, Dict
from pathlib import Path
import os

from PyQt6.QtCore import QThread, pyqtSignal


class ConversionWorker(QThread):
    """
    Worker thread for converting chapters.
    Emits progress signals for UI updates.
    """
    
    # Signals
    started_signal = pyqtSignal()
    chapter_started = pyqtSignal(str)  # Chapter name
    chapter_progress = pyqtSignal(str, int)  # Chapter name, progress 0-100
    chapter_finished = pyqtSignal(str, bool)  # Chapter name, success
    error = pyqtSignal(str, str)  # Chapter name, error message
    finished_signal = pyqtSignal(bool)  # Overall success
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._manga_path = ""
        self._manga_title = ""
        self._conversion_type = ""  # 'pdf', 'epub', or 'cbz'
        self._is_running = False
    
    def set_conversion_params(
        self, 
        manga_path: str,
        manga_title: str,
        conversion_type: str
    ):
        """Set the conversion parameters."""
        self._manga_path = manga_path
        self._manga_title = manga_title
        self._conversion_type = conversion_type.lower()
    
    def run(self):
        """Execute the conversion operation."""
        self._is_running = True
        self.started_signal.emit()
        
        manga_path_obj = Path(self._manga_path)
        
        # Get all chapter directories
        chapter_dirs = sorted([
            d for d in manga_path_obj.iterdir() 
            if d.is_dir() and not d.name.startswith('.')
        ])
        
        if not chapter_dirs:
            self.finished_signal.emit(False)
            return
        
        # Import scraper for conversion methods
        from weebcentral_scraper import WeebCentralScraper
        
        try:
            scraper = WeebCentralScraper(
                manga_url="",
                output_dir=str(manga_path_obj)
            )
            
            successful = 0
            
            for chapter_dir in chapter_dirs:
                if not self._is_running:
                    break
                
                chapter_name = chapter_dir.name
                
                # Emit started signal
                self.chapter_started.emit(chapter_name)
                self.chapter_progress.emit(chapter_name, 0)
                
                # Determine output file
                if self._conversion_type == 'pdf':
                    output_file = manga_path_obj / f"{chapter_name}.pdf"
                elif self._conversion_type == 'epub':
                    output_file = manga_path_obj / f"{chapter_name}.epub"
                elif self._conversion_type == 'cbz':
                    output_file = manga_path_obj / f"{chapter_name}.cbz"
                else:
                    self.error.emit(chapter_name, f"Unknown conversion type: {self._conversion_type}")
                    continue
                
                # Skip if already exists
                if output_file.exists():
                    self.chapter_progress.emit(chapter_name, 100)
                    self.chapter_finished.emit(chapter_name, True)
                    successful += 1
                    continue
                
                # Convert
                try:
                    self.chapter_progress.emit(chapter_name, 50)
                    
                    if self._conversion_type == 'pdf':
                        scraper.create_pdf_from_chapter(str(chapter_dir), chapter_name)
                    elif self._conversion_type == 'epub':
                        scraper.create_epub_from_chapter(str(chapter_dir), chapter_name, self._manga_title)
                    elif self._conversion_type == 'cbz':
                        scraper.create_cbz_from_chapter(str(chapter_dir), chapter_name)
                    
                    self.chapter_progress.emit(chapter_name, 100)
                    self.chapter_finished.emit(chapter_name, True)
                    successful += 1
                    
                except Exception as e:
                    self.error.emit(chapter_name, str(e))
                    self.chapter_finished.emit(chapter_name, False)
            
            self.finished_signal.emit(successful > 0)
            
        except Exception as e:
            self.error.emit("", f"Conversion failed: {str(e)}")
            self.finished_signal.emit(False)
        finally:
            self._is_running = False
    
    def stop(self):
        """Request the worker to stop."""
        self._is_running = False
    
    @property
    def is_running(self) -> bool:
        return self._is_running
