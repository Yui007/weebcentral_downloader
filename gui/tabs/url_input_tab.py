"""
URL Input Tab.
First tab where users enter manga URL to fetch information.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QComboBox, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QCursor

from gui.theme import Colors, Spacing, Fonts
from gui.components.animated_button import PrimaryButton
from gui.components.animated_input import AnimatedInput
from gui.config import get_settings, save_settings


class UrlInputTab(QWidget):
    """
    URL Input tab for entering manga URLs.
    Provides URL input field, recent URLs dropdown, and fetch button.
    """
    
    fetchRequested = pyqtSignal(str)  # Emits URL to fetch
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_loading = False
        self._setup_ui()
        self._setup_animations()
        self._load_recent_urls()
    
    def _setup_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.XXL, Spacing.XXL, Spacing.XXL, Spacing.XXL)
        layout.setSpacing(Spacing.XL)
        
        # Spacer to push content to center
        layout.addStretch(1)
        
        # Header section
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setSpacing(Spacing.MD)
        
        # Icon
        icon_label = QLabel("🔗")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"font-size: 64px;")
        header_layout.addWidget(icon_label)
        
        # Title
        title = QLabel("Enter Manga URL")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("title")
        header_layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Paste a WeebCentral manga URL to get started")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: {Fonts.SIZE_BODY}px;
            }}
        """)
        header_layout.addWidget(subtitle)
        
        layout.addWidget(header_widget)
        
        # Input section (centered card)
        input_card = QFrame()
        input_card.setObjectName("card")
        input_card.setMaximumWidth(700)
        input_card.setStyleSheet(f"""
            QFrame#card {{
                background-color: {Colors.BG_MEDIUM};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_XL}px;
                padding: {Spacing.XL}px;
            }}
        """)
        
        card_layout = QVBoxLayout(input_card)
        card_layout.setSpacing(Spacing.LG)
        
        # URL input
        self._url_input = AnimatedInput("https://weebcentral.com/series/...")
        self._url_input.setMinimumHeight(56)
        self._url_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Colors.BG_LIGHT};
                border: 2px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_MD}px;
                padding: {Spacing.MD}px {Spacing.LG}px;
                font-size: {Fonts.SIZE_H3}px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QLineEdit:focus {{
                border-color: {Colors.NEON_CYAN};
            }}
        """)
        self._url_input.returnPressed.connect(self._on_fetch_clicked)
        card_layout.addWidget(self._url_input)
        
        # Recent URLs dropdown
        recent_layout = QHBoxLayout()
        recent_layout.setSpacing(Spacing.SM)
        
        recent_label = QLabel("Recent:")
        recent_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_MUTED};
                font-size: {Fonts.SIZE_SMALL}px;
            }}
        """)
        recent_layout.addWidget(recent_label)
        
        self._recent_combo = QComboBox()
        self._recent_combo.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._recent_combo.setMinimumWidth(300)
        self._recent_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {Colors.BG_LIGHT};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_SM}px;
                padding: {Spacing.SM}px {Spacing.MD}px;
                color: {Colors.TEXT_SECONDARY};
                font-size: {Fonts.SIZE_SMALL}px;
            }}
            QComboBox:hover {{
                border-color: {Colors.NEON_CYAN};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_MEDIUM};
                border: 1px solid {Colors.BORDER_DEFAULT};
                selection-background-color: {Colors.NEON_CYAN};
            }}
        """)
        self._recent_combo.currentTextChanged.connect(self._on_recent_selected)
        recent_layout.addWidget(self._recent_combo, 1)
        
        card_layout.addLayout(recent_layout)
        
        # Fetch button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self._fetch_btn = PrimaryButton("✨ Fetch Manga Info")
        self._fetch_btn.setMinimumWidth(200)
        self._fetch_btn.setMinimumHeight(52)
        self._fetch_btn.clicked.connect(self._on_fetch_clicked)
        btn_layout.addWidget(self._fetch_btn)
        
        btn_layout.addStretch()
        card_layout.addLayout(btn_layout)
        
        # Center the card
        card_container = QHBoxLayout()
        card_container.addStretch()
        card_container.addWidget(input_card)
        card_container.addStretch()
        layout.addLayout(card_container)
        
        # Status message
        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_MUTED};
                font-size: {Fonts.SIZE_BODY}px;
            }}
        """)
        layout.addWidget(self._status_label)
        
        # Spacer
        layout.addStretch(2)
    
    def _setup_animations(self):
        """Setup fade animation for status messages."""
        self._status_opacity = QGraphicsOpacityEffect(self._status_label)
        self._status_opacity.setOpacity(0)
        self._status_label.setGraphicsEffect(self._status_opacity)
        
        self._status_anim = QPropertyAnimation(self._status_opacity, b"opacity", self)
        self._status_anim.setDuration(300)
        self._status_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def _load_recent_urls(self):
        """Load recent URLs from settings."""
        settings = get_settings()
        self._recent_combo.clear()
        self._recent_combo.addItem("Select a recent URL...")
        for url in settings.recent_urls:
            # Show truncated URL
            display = url if len(url) < 60 else url[:57] + "..."
            self._recent_combo.addItem(display, url)
    
    def _on_recent_selected(self, text: str):
        """Handle recent URL selection."""
        if self._recent_combo.currentIndex() > 0:
            url = self._recent_combo.currentData()
            if url:
                self._url_input.setText(url)
    
    def _on_fetch_clicked(self):
        """Handle fetch button click."""
        url = self._url_input.text().strip()
        
        if not url:
            self._show_status("Please enter a manga URL", Colors.NEON_ORANGE)
            return
        
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            self._url_input.setText(url)
        
        if "weebcentral.com" not in url.lower():
            self._show_status("Please enter a valid WeebCentral URL", Colors.NEON_ORANGE)
            return
        
        # Save to recent URLs
        settings = get_settings()
        settings.add_recent_url(url)
        save_settings()
        self._load_recent_urls()
        
        # Set loading state
        self.set_loading(True)
        self._show_status("Fetching manga information...", Colors.NEON_CYAN)
        
        # Emit signal
        self.fetchRequested.emit(url)
    
    def _show_status(self, message: str, color: str = Colors.TEXT_MUTED):
        """Show status message with fade animation."""
        self._status_label.setText(message)
        self._status_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: {Fonts.SIZE_BODY}px;
            }}
        """)
        
        self._status_anim.stop()
        self._status_anim.setStartValue(0)
        self._status_anim.setEndValue(1)
        self._status_anim.start()
    
    def set_loading(self, loading: bool):
        """Set loading state."""
        self._is_loading = loading
        self._fetch_btn.setEnabled(not loading)
        self._url_input.setEnabled(not loading)
        
        if loading:
            self._fetch_btn.setText("⏳ Loading...")
        else:
            self._fetch_btn.setText("✨ Fetch Manga Info")
    
    def show_error(self, message: str):
        """Show error message."""
        self.set_loading(False)
        self._show_status(f"❌ {message}", Colors.NEON_RED)
    
    def show_success(self, message: str):
        """Show success message."""
        self.set_loading(False)
        self._show_status(f"✅ {message}", Colors.NEON_GREEN)
