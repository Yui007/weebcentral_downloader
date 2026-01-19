"""
Downloads Tab.
Shows active and completed downloads with progress tracking.
"""

from typing import Optional, Dict
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QScrollArea, QPushButton, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QCursor, QDesktopServices
from PyQt6.QtCore import QUrl

from gui.theme import Colors, Spacing, Fonts
from gui.components.animated_button import AnimatedButton
from gui.components.download_card import DownloadCard, DownloadStatus
from gui.config import get_settings


class DownloadsTab(QWidget):
    """
    Downloads tab showing active, queued, and completed downloads.
    """
    
    cancelDownload = pyqtSignal(str)  # Emits chapter name to cancel
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: Dict[str, DownloadCard] = {}
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.LG)
        
        # Header with overall progress
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_MEDIUM};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_LG}px;
                padding: {Spacing.LG}px;
            }}
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setSpacing(Spacing.MD)
        
        # Title row
        title_row = QHBoxLayout()
        
        title = QLabel("⬇️ Downloads")
        title.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.FAMILY_DISPLAY};
                font-size: {Fonts.SIZE_H2}px;
                font-weight: bold;
            }}
        """)
        title_row.addWidget(title)
        
        title_row.addStretch()
        
        # Status label
        self._status_label = QLabel("No active downloads")
        self._status_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: {Fonts.SIZE_BODY}px;
            }}
        """)
        title_row.addWidget(self._status_label)
        
        header_layout.addLayout(title_row)
        
        # Overall progress bar
        self._overall_progress = QProgressBar()
        self._overall_progress.setMinimum(0)
        self._overall_progress.setMaximum(100)
        self._overall_progress.setValue(0)
        self._overall_progress.setTextVisible(True)
        self._overall_progress.setFormat("Overall: %p%")
        self._overall_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {Colors.BG_LIGHT};
                border: none;
                border-radius: {Spacing.RADIUS_SM}px;
                text-align: center;
                color: {Colors.TEXT_PRIMARY};
                font-weight: bold;
                min-height: 24px;
            }}
            QProgressBar::chunk {{
                background: {Colors.GRADIENT_SUCCESS};
                border-radius: {Spacing.RADIUS_SM}px;
            }}
        """)
        header_layout.addWidget(self._overall_progress)
        
        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(Spacing.SM)
        
        self._clear_btn = AnimatedButton("🗑️ Clear Completed")
        self._clear_btn.clicked.connect(self._clear_completed)
        btn_row.addWidget(self._clear_btn)
        
        self._open_folder_btn = AnimatedButton("📁 Open Folder")
        self._open_folder_btn.clicked.connect(self._open_download_folder)
        btn_row.addWidget(self._open_folder_btn)
        
        btn_row.addStretch()
        header_layout.addLayout(btn_row)
        
        layout.addWidget(header)
        
        # Downloads scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
        """)
        
        self._scroll_content = QWidget()
        self._scroll_layout = QVBoxLayout(self._scroll_content)
        self._scroll_layout.setContentsMargins(0, 0, 0, 0)
        self._scroll_layout.setSpacing(Spacing.MD)
        self._scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Empty state
        self._empty_widget = QWidget()
        empty_layout = QVBoxLayout(self._empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        empty_icon = QLabel("📥")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon.setStyleSheet("font-size: 48px;")
        empty_layout.addWidget(empty_icon)
        
        empty_text = QLabel("No downloads yet")
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_text.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_MUTED};
                font-size: {Fonts.SIZE_BODY}px;
            }}
        """)
        empty_layout.addWidget(empty_text)
        
        self._scroll_layout.addWidget(self._empty_widget)
        
        scroll.setWidget(self._scroll_content)
        layout.addWidget(scroll, 1)
    
    def add_download(self, chapter_name: str) -> DownloadCard:
        """Add a new download card."""
        if chapter_name in self._cards:
            return self._cards[chapter_name]
        
        # Hide empty state
        self._empty_widget.hide()
        
        # Create card
        card = DownloadCard(chapter_name)
        card.cancelRequested.connect(self._on_cancel_requested)
        
        # Insert at top
        self._scroll_layout.insertWidget(0, card)
        self._cards[chapter_name] = card
        
        # Animate in
        QTimer.singleShot(50, card.fade_in)
        
        self._update_status()
        return card
    
    def update_progress(self, chapter_name: str, progress: int):
        """Update download progress for a chapter."""
        if chapter_name in self._cards:
            card = self._cards[chapter_name]
            card.set_progress(progress)
            self._update_overall_progress()
    
    def set_status(self, chapter_name: str, status: DownloadStatus):
        """Set download status for a chapter."""
        if chapter_name in self._cards:
            self._cards[chapter_name].set_status(status)
            self._update_status()
            self._update_overall_progress()
    
    def mark_completed(self, chapter_name: str):
        """Mark a chapter download as completed."""
        self.set_status(chapter_name, DownloadStatus.COMPLETED)
    
    def mark_error(self, chapter_name: str):
        """Mark a chapter download as failed."""
        self.set_status(chapter_name, DownloadStatus.ERROR)
    
    def _on_cancel_requested(self, chapter_name: str):
        """Handle cancel request from a card."""
        self.cancelDownload.emit(chapter_name)
    
    def _clear_completed(self):
        """Remove completed/error download cards."""
        to_remove = []
        for name, card in self._cards.items():
            if card.status in (DownloadStatus.COMPLETED, DownloadStatus.ERROR, 
                              DownloadStatus.CANCELLED):
                to_remove.append(name)
        
        for name in to_remove:
            card = self._cards.pop(name)
            card.deleteLater()
        
        # Show empty state if no cards left
        if not self._cards:
            self._empty_widget.show()
        
        self._update_status()
        self._update_overall_progress()
    
    def _open_download_folder(self):
        """Open the download directory in file explorer."""
        settings = get_settings()
        path = settings.output_dir
        
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            # Try to create directory
            try:
                os.makedirs(path, exist_ok=True)
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            except Exception:
                pass
    
    def _update_status(self):
        """Update the status label."""
        active = sum(
            1 for card in self._cards.values() 
            if card.status in (DownloadStatus.QUEUED, DownloadStatus.DOWNLOADING)
        )
        completed = sum(
            1 for card in self._cards.values()
            if card.status == DownloadStatus.COMPLETED
        )
        
        if active > 0:
            self._status_label.setText(f"Downloading {active} chapter{'s' if active != 1 else ''}")
        elif completed > 0:
            self._status_label.setText(f"{completed} download{'s' if completed != 1 else ''} completed")
        else:
            self._status_label.setText("No active downloads")
    
    def _update_overall_progress(self):
        """Update overall progress bar."""
        if not self._cards:
            self._overall_progress.setValue(0)
            return
        
        total = len(self._cards)
        completed_count = sum(
            1 for card in self._cards.values()
            if card.status == DownloadStatus.COMPLETED
        )
        
        # Simple percentage based on completed downloads
        if total > 0:
            progress = int((completed_count / total) * 100)
            self._overall_progress.setValue(progress)
    
    def clear_all(self):
        """Clear all download cards."""
        for card in self._cards.values():
            card.deleteLater()
        self._cards.clear()
        self._empty_widget.show()
        self._overall_progress.setValue(0)
        self._update_status()
