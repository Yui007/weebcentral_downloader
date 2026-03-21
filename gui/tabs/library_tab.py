"""
Library Tab.
Manage downloaded manga, view info, and trigger conversions.
"""

from typing import Optional, Dict, List
import os
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QScrollArea, QPushButton, QListWidget,
    QListWidgetItem, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QCursor, QPixmap

from gui.theme import Colors, Spacing, Fonts
from gui.components.animated_button import AnimatedButton
from gui.config import get_settings


class LibraryItem(QFrame):
    """Single manga item in the library list."""
    
    clicked = pyqtSignal(str)  # Emits manga directory path
    
    def __init__(self, manga_title: str, manga_path: str, chapter_count: int, parent=None):
        super().__init__(parent)
        self.manga_title = manga_title
        self.manga_path = manga_path
        self.chapter_count = chapter_count
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize UI components."""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_MEDIUM};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_MD}px;
                padding: {Spacing.MD}px;
            }}
            QFrame:hover {{
                background-color: {Colors.BG_LIGHT};
                border-color: {Colors.NEON_CYAN};
            }}
        """)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        layout.setSpacing(Spacing.XS)
        
        # Title
        title = QLabel(self.manga_title)
        title.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-weight: bold;
                font-size: {Fonts.SIZE_BODY}px;
            }}
        """)
        title.setWordWrap(True)
        layout.addWidget(title)
        
        # Chapter count
        count = QLabel(f"{self.chapter_count} chapter{'s' if self.chapter_count != 1 else ''}")
        count.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_MUTED};
                font-size: {Fonts.SIZE_SMALL}px;
            }}
        """)
        layout.addWidget(count)
    
    def mousePressEvent(self, event):
        """Handle click event."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.manga_path)
        super().mousePressEvent(event)


class LibraryTab(QWidget):
    """
    Library tab for managing downloaded manga.
    Shows manga info and allows downloading missing chapters and conversions.
    """
    
    downloadMissingChapters = pyqtSignal(str, list)  # manga_url, missing_chapters
    convertToPDF = pyqtSignal(str)  # manga_path
    convertToEPUB = pyqtSignal(str)  # manga_path
    convertToCBZ = pyqtSignal(str)  # manga_path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._manga_list: List[Dict] = []
        self._current_manga: Optional[Dict] = None
        self._setup_ui()
        self._scan_library()
    
    def _setup_ui(self):
        """Initialize UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # ═════════════════════════════════════════════════════════════════
        # Left Panel - Manga List
        # ═════════════════════════════════════════════════════════════════
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.MD, Spacing.LG)
        left_layout.setSpacing(Spacing.MD)
        
        # Header
        header = QLabel("📚 Library")
        header.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.FAMILY_DISPLAY};
                font-size: {Fonts.SIZE_H2}px;
                font-weight: bold;
            }}
        """)
        left_layout.addWidget(header)
        
        # Refresh button
        refresh_btn = AnimatedButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._scan_library)
        left_layout.addWidget(refresh_btn)
        
        # Manga list scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
        """)
        
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(Spacing.SM)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Empty state
        self._empty_label = QLabel("No manga found\n\nDownload some manga to see them here!")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_MUTED};
                font-size: {Fonts.SIZE_BODY}px;
                padding: {Spacing.XL}px;
            }}
        """)
        self._list_layout.addWidget(self._empty_label)
        
        scroll.setWidget(self._list_widget)
        left_layout.addWidget(scroll, 1)
        
        # ═════════════════════════════════════════════════════════════════
        # Right Panel - Manga Details
        # ═════════════════════════════════════════════════════════════════
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(Spacing.MD, Spacing.LG, Spacing.LG, Spacing.LG)
        right_layout.setSpacing(Spacing.LG)
        
        # Details scroll area
        details_scroll = QScrollArea()
        details_scroll.setWidgetResizable(True)
        details_scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
        """)
        
        self._details_widget = QWidget()
        self._details_layout = QVBoxLayout(self._details_widget)
        self._details_layout.setContentsMargins(0, 0, 0, 0)
        self._details_layout.setSpacing(Spacing.LG)
        self._details_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Empty state for details
        empty_details = QLabel("Select a manga to view details")
        empty_details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_details.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_MUTED};
                font-size: {Fonts.SIZE_H3}px;
                padding: {Spacing.XL}px;
            }}
        """)
        self._details_layout.addWidget(empty_details)
        
        details_scroll.setWidget(self._details_widget)
        right_layout.addWidget(details_scroll, 1)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)
    
    def _scan_library(self):
        """Scan downloads directory for manga."""
        settings = get_settings()
        downloads_dir = Path(settings.output_dir)
        
        if not downloads_dir.exists():
            return
        
        self._manga_list.clear()
        
        # Clear existing items
        while self._list_layout.count() > 0:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Scan for manga directories
        for manga_dir in sorted(downloads_dir.iterdir()):
            if not manga_dir.is_dir():
                continue
            
            # Skip hidden directories
            if manga_dir.name.startswith('.'):
                continue
            
            # Count chapters (subdirectories, excluding hidden ones)
            chapters = [d for d in manga_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
            
            if len(chapters) == 0:
                continue
            
            manga_info = {
                'title': manga_dir.name,
                'path': str(manga_dir),
                'chapter_count': len(chapters),
                'chapters': [c.name for c in chapters]
            }
            
            # Try to load metadata if exists
            metadata_file = manga_dir / '.metadata.json'
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        # Merge metadata but keep chapter count from actual scan
                        actual_chapter_count = manga_info['chapter_count']
                        manga_info.update(metadata)
                        manga_info['chapter_count'] = actual_chapter_count  # Use actual count
                except Exception:
                    pass
            
            self._manga_list.append(manga_info)
        
        # Show manga items or empty state
        if self._manga_list:
            # Only hide if the label still exists
            try:
                if self._empty_label and not self._empty_label.isHidden():
                    self._empty_label.hide()
            except RuntimeError:
                pass  # Label was already deleted
            
            for manga in self._manga_list:
                item = LibraryItem(
                    manga['title'],
                    manga['path'],
                    manga['chapter_count']
                )
                item.clicked.connect(self._on_manga_selected)
                self._list_layout.addWidget(item)
        else:
            # Only show if the label still exists
            try:
                if self._empty_label and self._empty_label.isHidden():
                    self._empty_label.show()
            except RuntimeError:
                pass  # Label was already deleted
    
    def _on_manga_selected(self, manga_path: str):
        """Handle manga selection."""
        # Find manga info
        manga_info = None
        for manga in self._manga_list:
            if manga['path'] == manga_path:
                manga_info = manga
                break
        
        if not manga_info:
            return
        
        self._current_manga = manga_info
        self._show_manga_details(manga_info)
    
    def _show_manga_details(self, manga_info: Dict):
        """Display manga details in right panel."""
        # Clear existing details
        while self._details_layout.count() > 0:
            item = self._details_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Cover image (if available)
        cover_path = Path(manga_info['path']) / 'cover.jpg'
        if not cover_path.exists():
            cover_path = Path(manga_info['path']) / 'cover.png'
        if not cover_path.exists():
            cover_path = Path(manga_info['path']) / 'cover.webp'
        
        if cover_path.exists():
            cover_label = QLabel()
            pixmap = QPixmap(str(cover_path))
            if not pixmap.isNull():
                # Scale to reasonable size while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(200, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                cover_label.setPixmap(scaled_pixmap)
                cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._details_layout.addWidget(cover_label)
        
        # Title
        title = QLabel(manga_info['title'])
        title.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.FAMILY_DISPLAY};
                font-size: {Fonts.SIZE_H2}px;
                font-weight: bold;
            }}
        """)
        title.setWordWrap(True)
        self._details_layout.addWidget(title)
        
        # URL (if available)
        if manga_info.get('url'):
            url_label = QLabel(f"🔗 <a href='{manga_info['url']}' style='color: {Colors.NEON_CYAN};'>{manga_info['url']}</a>")
            url_label.setOpenExternalLinks(True)
            url_label.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.TEXT_SECONDARY};
                    font-size: {Fonts.SIZE_SMALL}px;
                }}
            """)
            url_label.setWordWrap(True)
            self._details_layout.addWidget(url_label)
        
        # Chapter count
        count_label = QLabel(f"📖 {manga_info['chapter_count']} chapters downloaded")
        count_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: {Fonts.SIZE_BODY}px;
            }}
        """)
        self._details_layout.addWidget(count_label)
        
        # Download date (if available)
        if manga_info.get('download_date'):
            date_label = QLabel(f"📅 Downloaded: {manga_info['download_date']}")
            date_label.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.TEXT_MUTED};
                    font-size: {Fonts.SIZE_SMALL}px;
                }}
            """)
            self._details_layout.addWidget(date_label)
        
        # Description (always show, with placeholder if empty)
        desc_frame = QFrame()
        desc_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_MEDIUM};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_LG}px;
                padding: {Spacing.LG}px;
            }}
        """)
        desc_layout = QVBoxLayout(desc_frame)
        desc_layout.setSpacing(Spacing.SM)
        
        desc_title = QLabel("📝 Description")
        desc_title.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-weight: bold;
                font-size: {Fonts.SIZE_H3}px;
            }}
        """)
        desc_layout.addWidget(desc_title)
        
        # Show description or placeholder
        description = manga_info.get('description', '')
        if not description:
            description = "No description available. Update metadata to add description."
            desc_color = Colors.TEXT_MUTED
        else:
            desc_color = Colors.TEXT_SECONDARY
        
        desc_text = QLabel(description)
        desc_text.setStyleSheet(f"""
            QLabel {{
                color: {desc_color};
                font-size: {Fonts.SIZE_SMALL}px;
                font-style: {'italic' if not manga_info.get('description') else 'normal'};
            }}
        """)
        desc_text.setWordWrap(True)
        desc_layout.addWidget(desc_text)
        
        self._details_layout.addWidget(desc_frame)
        
        # Tags (if available)
        if manga_info.get('tags'):
            tags_frame = QFrame()
            tags_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_MEDIUM};
                    border: 1px solid {Colors.BORDER_DEFAULT};
                    border-radius: {Spacing.RADIUS_LG}px;
                    padding: {Spacing.LG}px;
                }}
            """)
            tags_layout = QVBoxLayout(tags_frame)
            tags_layout.setSpacing(Spacing.SM)
            
            tags_title = QLabel("🏷️ Tags")
            tags_title.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.TEXT_PRIMARY};
                    font-weight: bold;
                    font-size: {Fonts.SIZE_H3}px;
                }}
            """)
            tags_layout.addWidget(tags_title)
            
            # Create tag badges
            tags_container = QWidget()
            tags_flow = QHBoxLayout(tags_container)
            tags_flow.setSpacing(Spacing.XS)
            tags_flow.setContentsMargins(0, 0, 0, 0)
            
            for tag in manga_info['tags'][:10]:  # Limit to 10 tags
                tag_label = QLabel(tag)
                tag_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: {Colors.BG_LIGHT};
                        color: {Colors.NEON_CYAN};
                        border: 1px solid {Colors.NEON_CYAN};
                        border-radius: {Spacing.RADIUS_SM}px;
                        padding: {Spacing.XS}px {Spacing.SM}px;
                        font-size: {Fonts.SIZE_TINY}px;
                    }}
                """)
                tags_flow.addWidget(tag_label)
            
            tags_flow.addStretch()
            tags_layout.addWidget(tags_container)
            
            self._details_layout.addWidget(tags_frame)
        
        # Additional metadata (if available)
        if manga_info.get('metadata'):
            metadata = manga_info['metadata']
            if metadata:
                meta_frame = QFrame()
                meta_frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: {Colors.BG_MEDIUM};
                        border: 1px solid {Colors.BORDER_DEFAULT};
                        border-radius: {Spacing.RADIUS_LG}px;
                        padding: {Spacing.LG}px;
                    }}
                """)
                meta_layout = QVBoxLayout(meta_frame)
                meta_layout.setSpacing(Spacing.SM)
                
                meta_title = QLabel("ℹ️ Information")
                meta_title.setStyleSheet(f"""
                    QLabel {{
                        color: {Colors.TEXT_PRIMARY};
                        font-weight: bold;
                        font-size: {Fonts.SIZE_H3}px;
                    }}
                """)
                meta_layout.addWidget(meta_title)
                
                for key, value in metadata.items():
                    if value:
                        meta_item = QLabel(f"<b>{key}:</b> {value}")
                        meta_item.setStyleSheet(f"""
                            QLabel {{
                                color: {Colors.TEXT_SECONDARY};
                                font-size: {Fonts.SIZE_SMALL}px;
                            }}
                        """)
                        meta_item.setWordWrap(True)
                        meta_layout.addWidget(meta_item)
                
                self._details_layout.addWidget(meta_frame)
        
        # Action buttons
        actions_frame = QFrame()
        actions_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_MEDIUM};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_LG}px;
                padding: {Spacing.LG}px;
            }}
        """)
        actions_layout = QVBoxLayout(actions_frame)
        actions_layout.setSpacing(Spacing.MD)
        
        actions_title = QLabel("⚙️ Actions")
        actions_title.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-weight: bold;
                font-size: {Fonts.SIZE_H3}px;
            }}
        """)
        actions_layout.addWidget(actions_title)
        
        # Download missing chapters button
        if manga_info.get('url'):
            download_btn = AnimatedButton("📥 Download Missing Chapters")
            download_btn.clicked.connect(lambda: self._download_missing_chapters(manga_info))
            actions_layout.addWidget(download_btn)
        
        # Convert to PDF button
        pdf_btn = AnimatedButton("📄 Convert All to PDF")
        pdf_btn.clicked.connect(lambda: self.convertToPDF.emit(manga_info['path']))
        actions_layout.addWidget(pdf_btn)
        
        # Convert to EPUB button
        epub_btn = AnimatedButton("📚 Convert All to EPUB")
        epub_btn.clicked.connect(lambda: self.convertToEPUB.emit(manga_info['path']))
        actions_layout.addWidget(epub_btn)
        
        # Convert to CBZ button
        cbz_btn = AnimatedButton("📦 Convert All to CBZ")
        cbz_btn.clicked.connect(lambda: self.convertToCBZ.emit(manga_info['path']))
        actions_layout.addWidget(cbz_btn)
        
        # Open folder button
        open_btn = AnimatedButton("📁 Open Folder")
        open_btn.clicked.connect(lambda: self._open_folder(manga_info['path']))
        actions_layout.addWidget(open_btn)
        
        self._details_layout.addWidget(actions_frame)
        
        # Chapter list
        chapters_frame = QFrame()
        chapters_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_MEDIUM};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_LG}px;
                padding: {Spacing.LG}px;
            }}
        """)
        chapters_layout = QVBoxLayout(chapters_frame)
        chapters_layout.setSpacing(Spacing.SM)
        
        chapters_title = QLabel(f"📑 Chapters ({len(manga_info['chapters'])})")
        chapters_title.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-weight: bold;
                font-size: {Fonts.SIZE_H3}px;
            }}
        """)
        chapters_layout.addWidget(chapters_title)
        
        # Chapter list
        chapter_list = QListWidget()
        chapter_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {Colors.BG_LIGHT};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_SM}px;
                color: {Colors.TEXT_PRIMARY};
                font-size: {Fonts.SIZE_SMALL}px;
                padding: {Spacing.SM}px;
            }}
            QListWidget::item {{
                padding: {Spacing.XS}px;
            }}
            QListWidget::item:hover {{
                background-color: {Colors.BG_MEDIUM};
            }}
        """)
        for chapter in sorted(manga_info['chapters']):
            chapter_list.addItem(chapter)
        chapters_layout.addWidget(chapter_list)
        
        self._details_layout.addWidget(chapters_frame)
        self._details_layout.addStretch()
    
    def _download_missing_chapters(self, manga_info: Dict):
        """Trigger download of missing chapters."""
        # This would need to fetch the manga info again and compare
        # For now, emit signal with manga URL
        if manga_info.get('url'):
            self.downloadMissingChapters.emit(manga_info['url'], [])
    
    def _open_folder(self, path: str):
        """Open manga folder in file explorer."""
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
    
    def refresh(self):
        """Refresh the library."""
        self._scan_library()
