"""
Download Card Component.
Displays individual chapter download progress with animations.
"""

from enum import Enum
from typing import Optional

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QPushButton, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QCursor

from gui.theme import Colors, Spacing, Fonts


class DownloadStatus(Enum):
    """Download status states."""
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class DownloadCard(QFrame):
    """
    Card displaying download progress for a single chapter.
    Features animated progress bar and status indicators.
    """
    
    cancelRequested = pyqtSignal(str)  # Emits chapter name
    
    def __init__(self, chapter_name: str, parent=None):
        super().__init__(parent)
        self._chapter_name = chapter_name
        self._status = DownloadStatus.QUEUED
        self._progress = 0
        
        self._setup_ui()
        self._setup_animations()
    
    def _setup_ui(self):
        """Initialize UI components."""
        self.setObjectName("card")
        self.setStyleSheet(f"""
            QFrame#card {{
                background-color: {Colors.BG_MEDIUM};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_LG}px;
                padding: {Spacing.MD}px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        layout.setSpacing(Spacing.SM)
        
        # Header row
        header = QHBoxLayout()
        header.setSpacing(Spacing.SM)
        
        # Status icon
        self._status_icon = QLabel("⏳")
        self._status_icon.setStyleSheet(f"font-size: 16px;")
        header.addWidget(self._status_icon)
        
        # Chapter name
        self._name_label = QLabel(self._chapter_name)
        self._name_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-weight: bold;
                font-size: {Fonts.SIZE_BODY}px;
            }}
        """)
        header.addWidget(self._name_label, 1)
        
        # Status text
        self._status_label = QLabel("Queued")
        self._status_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_MUTED};
                font-size: {Fonts.SIZE_SMALL}px;
            }}
        """)
        header.addWidget(self._status_label)
        
        # Cancel button
        self._cancel_btn = QPushButton("✕")
        self._cancel_btn.setFixedSize(28, 28)
        self._cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {Colors.TEXT_MUTED};
                font-size: 14px;
                border-radius: 14px;
            }}
            QPushButton:hover {{
                background-color: {Colors.NEON_RED};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        self._cancel_btn.clicked.connect(self._on_cancel)
        header.addWidget(self._cancel_btn)
        
        layout.addLayout(header)
        
        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("%p%")
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {Colors.BG_LIGHT};
                border: none;
                border-radius: {Spacing.RADIUS_SM}px;
                text-align: center;
                color: {Colors.TEXT_PRIMARY};
                font-weight: bold;
                font-size: {Fonts.SIZE_SMALL}px;
                min-height: 20px;
            }}
            QProgressBar::chunk {{
                background: {Colors.GRADIENT_PRIMARY};
                border-radius: {Spacing.RADIUS_SM}px;
            }}
        """)
        layout.addWidget(self._progress_bar)
    
    def _setup_animations(self):
        """Setup fade animation for the card."""
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0)
        self.setGraphicsEffect(self._opacity_effect)
        
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_anim.setDuration(300)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def fade_in(self):
        """Animate card appearance."""
        self._fade_anim.stop()
        self._fade_anim.setStartValue(0)
        self._fade_anim.setEndValue(1)
        self._fade_anim.start()
    
    @property
    def chapter_name(self) -> str:
        return self._chapter_name
    
    @property
    def status(self) -> DownloadStatus:
        return self._status
    
    def set_progress(self, progress: int):
        """Update download progress (0-100)."""
        self._progress = max(0, min(100, progress))
        self._progress_bar.setValue(self._progress)
        
        if self._status == DownloadStatus.QUEUED and progress > 0:
            self.set_status(DownloadStatus.DOWNLOADING)
    
    def set_status(self, status: DownloadStatus):
        """Update download status with visual feedback."""
        self._status = status
        
        status_config = {
            DownloadStatus.QUEUED: ("⏳", "Queued", Colors.TEXT_MUTED),
            DownloadStatus.DOWNLOADING: ("⬇️", "Downloading...", Colors.NEON_CYAN),
            DownloadStatus.COMPLETED: ("✅", "Completed", Colors.NEON_GREEN),
            DownloadStatus.ERROR: ("❌", "Error", Colors.NEON_RED),
            DownloadStatus.CANCELLED: ("⛔", "Cancelled", Colors.NEON_ORANGE),
        }
        
        icon, text, color = status_config.get(
            status, ("❓", "Unknown", Colors.TEXT_MUTED)
        )
        
        self._status_icon.setText(icon)
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: {Fonts.SIZE_SMALL}px;
            }}
        """)
        
        # Hide cancel button when completed/error
        if status in (DownloadStatus.COMPLETED, DownloadStatus.ERROR, 
                      DownloadStatus.CANCELLED):
            self._cancel_btn.hide()
            self._progress_bar.setValue(100 if status == DownloadStatus.COMPLETED else self._progress)
    
    def _on_cancel(self):
        """Handle cancel button click."""
        self.cancelRequested.emit(self._chapter_name)
        self.set_status(DownloadStatus.CANCELLED)
