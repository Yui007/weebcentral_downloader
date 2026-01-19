"""
Manga Info Card Component.
Displays manga cover image, title, and metadata.
"""

from typing import Optional, Dict, List
import os

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QScrollArea, QWidget, QGraphicsOpacityEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from gui.theme import Colors, Spacing, Fonts


class CoverImage(QLabel):
    """
    Cover image display with loading state and shimmer effect.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(200, 280)
        self.setMaximumSize(220, 310)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        self._network_manager = QNetworkAccessManager(self)
        self._network_manager.finished.connect(self._on_image_loaded)
        
        self._set_placeholder()
    
    def _set_placeholder(self):
        """Show placeholder when no image is loaded."""
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {Colors.BG_LIGHT};
                border: 2px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_LG}px;
                color: {Colors.TEXT_MUTED};
                font-size: {Fonts.SIZE_H1}px;
            }}
        """)
        self.setText("📚")
    
    def load_from_url(self, url: str):
        """Load cover image from URL."""
        if not url:
            self._set_placeholder()
            return
        
        self.setText("⏳")
        request = QNetworkRequest(url)
        self._network_manager.get(request)
    
    def load_from_file(self, path: str):
        """Load cover image from local file."""
        if os.path.exists(path):
            pixmap = QPixmap(path)
            self._set_pixmap(pixmap)
        else:
            self._set_placeholder()
    
    def load_from_bytes(self, data: bytes):
        """Load cover image from bytes."""
        image = QImage()
        if image.loadFromData(data):
            pixmap = QPixmap.fromImage(image)
            self._set_pixmap(pixmap)
        else:
            self._set_placeholder()
    
    def _on_image_loaded(self, reply: QNetworkReply):
        """Handle network image load complete."""
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            image = QImage()
            if image.loadFromData(data):
                pixmap = QPixmap.fromImage(image)
                self._set_pixmap(pixmap)
            else:
                self._set_placeholder()
        else:
            self._set_placeholder()
        reply.deleteLater()
    
    def _set_pixmap(self, pixmap: QPixmap):
        """Set the pixmap with proper scaling and styling."""
        scaled = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: transparent;
                border: 2px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_LG}px;
            }}
        """)


class TagPill(QLabel):
    """Small tag/genre pill display."""
    
    def __init__(self, text: str, color: str = Colors.NEON_CYAN, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color}33;
                color: {color};
                border: 1px solid {color};
                border-radius: 10px;
                padding: 4px 10px;
                font-size: {Fonts.SIZE_SMALL}px;
                font-weight: bold;
            }}
        """)


class MangaInfoCard(QFrame):
    """
    Card displaying manga information.
    Shows cover image, title, and metadata fields.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
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
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.XL)
        
        # Cover image
        self._cover = CoverImage()
        layout.addWidget(self._cover)
        
        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(Spacing.MD)
        layout.addLayout(info_layout, 1)
        
        # Title
        self._title = QLabel("No manga loaded")
        self._title.setWordWrap(True)
        self._title.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.FAMILY_DISPLAY};
                font-size: {Fonts.SIZE_H1}px;
                font-weight: bold;
            }}
        """)
        info_layout.addWidget(self._title)
        
        # Metadata grid
        self._metadata_widget = QWidget()
        self._metadata_layout = QVBoxLayout(self._metadata_widget)
        self._metadata_layout.setContentsMargins(0, 0, 0, 0)
        self._metadata_layout.setSpacing(Spacing.SM)
        info_layout.addWidget(self._metadata_widget)
        
        # Tags container
        self._tags_widget = QWidget()
        self._tags_layout = QHBoxLayout(self._tags_widget)
        self._tags_layout.setContentsMargins(0, 0, 0, 0)
        self._tags_layout.setSpacing(Spacing.SM)
        self._tags_layout.addStretch()
        info_layout.addWidget(self._tags_widget)
        
        # Description
        self._description = QLabel("")
        self._description.setWordWrap(True)
        self._description.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: {Fonts.SIZE_BODY}px;
                line-height: 1.5;
            }}
        """)
        info_layout.addWidget(self._description)
        
        info_layout.addStretch()
    
    def _setup_animations(self):
        """Setup fade animation."""
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0)
        self.setGraphicsEffect(self._opacity)
        
        self._fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.setDuration(400)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def fade_in(self):
        """Animate card appearance."""
        self._fade.stop()
        self._fade.setStartValue(0)
        self._fade.setEndValue(1)
        self._fade.start()
    
    def set_manga_info(
        self,
        title: str,
        cover_url: Optional[str] = None,
        cover_path: Optional[str] = None,
        cover_bytes: Optional[bytes] = None,
        description: str = "",
        metadata: Optional[Dict[str, str]] = None,
        tags: Optional[List[str]] = None
    ):
        """Update the card with manga information."""
        self._title.setText(title)
        
        # Load cover
        if cover_bytes:
            self._cover.load_from_bytes(cover_bytes)
        elif cover_path:
            self._cover.load_from_file(cover_path)
        elif cover_url:
            self._cover.load_from_url(cover_url)
        
        # Clear and set metadata
        self._clear_layout(self._metadata_layout)
        if metadata:
            for key, value in metadata.items():
                row = QHBoxLayout()
                row.setSpacing(Spacing.MD)
                
                key_label = QLabel(f"{key}:")
                key_label.setStyleSheet(f"""
                    QLabel {{
                        color: {Colors.TEXT_MUTED};
                        font-size: {Fonts.SIZE_BODY}px;
                        font-weight: bold;
                        min-width: 80px;
                    }}
                """)
                row.addWidget(key_label)
                
                value_label = QLabel(str(value))
                value_label.setWordWrap(True)
                value_label.setStyleSheet(f"""
                    QLabel {{
                        color: {Colors.TEXT_PRIMARY};
                        font-size: {Fonts.SIZE_BODY}px;
                    }}
                """)
                row.addWidget(value_label, 1)
                
                self._metadata_layout.addLayout(row)
        
        # Clear and set tags
        self._clear_layout(self._tags_layout)
        if tags:
            for tag in tags[:8]:  # Limit to 8 tags
                pill = TagPill(tag)
                self._tags_layout.insertWidget(self._tags_layout.count() - 1, pill)
        self._tags_layout.addStretch()
        
        # Set description
        self._description.setText(description[:500] + "..." if len(description) > 500 else description)
        
        self.fade_in()
    
    def clear(self):
        """Clear all manga information."""
        self._title.setText("No manga loaded")
        self._cover._set_placeholder()
        self._description.setText("")
        self._clear_layout(self._metadata_layout)
        self._clear_layout(self._tags_layout)
        self._tags_layout.addStretch()
    
    def _clear_layout(self, layout):
        """Remove all items from a layout."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
