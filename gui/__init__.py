"""
WeebCentral Downloader - Modern PyQt6 GUI
A sleek, animated manga downloader interface with tabbed navigation.
"""

import sys
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase, QFont
from PyQt6.QtCore import Qt

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_gui():
    """Launch the WeebCentral Downloader GUI application."""
    # Enable high DPI scaling
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set application metadata
    app.setApplicationName("WeebCentral Downloader")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("WeebCentral")
    
    # Load custom fonts
    _load_fonts()
    
    # Import here to avoid circular imports
    from gui.main_window import MainWindow
    from gui.theme import get_stylesheet
    
    # Apply theme
    app.setStyleSheet(get_stylesheet())
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


def _load_fonts():
    """Load custom fonts for the application."""
    fonts_dir = os.path.join(os.path.dirname(__file__), "fonts")
    
    # Try to load Outfit and Inter fonts if available
    font_files = [
        "Outfit-Regular.ttf",
        "Outfit-Bold.ttf",
        "Outfit-Medium.ttf",
        "Inter-Regular.ttf",
        "Inter-Medium.ttf",
    ]
    
    for font_file in font_files:
        font_path = os.path.join(fonts_dir, font_file)
        if os.path.exists(font_path):
            QFontDatabase.addApplicationFont(font_path)


if __name__ == "__main__":
    run_gui()
