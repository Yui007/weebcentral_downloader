"""
Manga Info Tab.
Displays manga information with cover, metadata, and chapter list.
"""

from typing import Optional, List, Dict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QScrollArea, QSplitter, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal

from gui.theme import Colors, Spacing, Fonts
from gui.components.animated_button import PrimaryButton, AnimatedButton
from gui.components.manga_info_card import MangaInfoCard
from gui.components.chapter_list import ChapterListWidget, ChapterItem


class MangaInfoTab(QWidget):
    """
    Manga Information tab showing cover, details, and chapter selection.
    """
    
    downloadRequested = pyqtSignal(list)  # Emits list of ChapterItems
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._manga_url = ""
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.LG)
        
        # Empty state (shown when no manga loaded)
        self._empty_widget = QWidget()
        empty_layout = QVBoxLayout(self._empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        empty_icon = QLabel("📖")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon.setStyleSheet("font-size: 64px;")
        empty_layout.addWidget(empty_icon)
        
        empty_text = QLabel("No manga loaded")
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_text.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: {Fonts.SIZE_H2}px;
            }}
        """)
        empty_layout.addWidget(empty_text)
        
        empty_hint = QLabel("Enter a URL in the first tab to get started")
        empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_hint.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_MUTED};
                font-size: {Fonts.SIZE_BODY}px;
            }}
        """)
        empty_layout.addWidget(empty_hint)
        
        layout.addWidget(self._empty_widget)
        
        # Content widget (shown when manga is loaded)
        self._content_widget = QWidget()
        self._content_widget.hide()
        content_layout = QVBoxLayout(self._content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(Spacing.LG)
        
        # Manga info card
        self._info_card = MangaInfoCard()
        content_layout.addWidget(self._info_card)
        
        # Chapters section header
        chapters_header = QHBoxLayout()
        chapters_header.setSpacing(Spacing.MD)
        
        chapters_title = QLabel("📑 Chapters")
        chapters_title.setObjectName("section-header")
        chapters_header.addWidget(chapters_title)
        
        chapters_header.addStretch()
        content_layout.addLayout(chapters_header)
        
        # Chapter list
        self._chapter_list = ChapterListWidget()
        self._chapter_list.selectionChanged.connect(self._on_selection_changed)
        content_layout.addWidget(self._chapter_list, 1)
        
        # Download section
        download_frame = QFrame()
        download_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_MEDIUM};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_LG}px;
                padding: {Spacing.MD}px;
            }}
        """)
        download_layout = QHBoxLayout(download_frame)
        download_layout.setSpacing(Spacing.MD)
        
        self._selection_label = QLabel("0 chapters selected")
        self._selection_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: {Fonts.SIZE_BODY}px;
            }}
        """)
        download_layout.addWidget(self._selection_label)
        
        download_layout.addStretch()
        
        self._download_btn = PrimaryButton("⬇️ Download Selected")
        self._download_btn.setEnabled(False)
        self._download_btn.clicked.connect(self._on_download_clicked)
        download_layout.addWidget(self._download_btn)
        
        content_layout.addWidget(download_frame)
        
        layout.addWidget(self._content_widget)
    
    def set_manga_info(
        self,
        url: str,
        title: str,
        cover_url: Optional[str] = None,
        cover_data: Optional[bytes] = None,
        description: str = "",
        metadata: Optional[Dict[str, str]] = None,
        tags: Optional[List[str]] = None,
        chapters: Optional[List[Dict]] = None
    ):
        """Set manga information and display it."""
        self._manga_url = url
        
        # Update info card
        self._info_card.set_manga_info(
            title=title,
            cover_url=cover_url,
            cover_bytes=cover_data,
            description=description,
            metadata=metadata,
            tags=tags
        )
        
        # Update chapter list
        if chapters:
            chapter_items = [
                ChapterItem(
                    name=ch.get("name", f"Chapter {i+1}"),
                    url=ch.get("url", ""),
                    index=i
                )
                for i, ch in enumerate(chapters)
            ]
            self._chapter_list.set_chapters(chapter_items)
        else:
            self._chapter_list.clear_chapters()
        
        # Show content, hide empty state
        self._empty_widget.hide()
        self._content_widget.show()
    
    def clear(self):
        """Clear manga information and show empty state."""
        self._manga_url = ""
        self._info_card.clear()
        self._chapter_list.clear_chapters()
        self._content_widget.hide()
        self._empty_widget.show()
    
    def _on_selection_changed(self, selected: List[ChapterItem]):
        """Handle chapter selection change."""
        count = len(selected)
        self._selection_label.setText(f"{count} chapter{'s' if count != 1 else ''} selected")
        self._download_btn.setEnabled(count > 0)
    
    def _on_download_clicked(self):
        """Handle download button click."""
        selected = self._chapter_list.get_selected_chapters()
        if selected:
            self.downloadRequested.emit(selected)
    
    def get_manga_url(self) -> str:
        """Get the current manga URL."""
        return self._manga_url
