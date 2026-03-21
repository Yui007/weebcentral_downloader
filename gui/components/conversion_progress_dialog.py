"""
Conversion Progress Dialog.
Shows progress when converting chapters to PDF/EPUB/CBZ.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from gui.theme import Colors, Spacing, Fonts


class ConversionProgressDialog(QDialog):
    """
    Dialog showing conversion progress with auto-close on completion.
    """
    
    def __init__(self, title: str, total_chapters: int, parent=None):
        super().__init__(parent)
        self.total_chapters = total_chapters
        self.current_chapter = 0
        self.converted_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        
        self._setup_ui(title)
    
    def _setup_ui(self, title: str):
        """Initialize UI components."""
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(500)
        
        # Set window flags to remove close button
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.CustomizeWindowHint | 
            Qt.WindowType.WindowTitleHint
        )
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        layout.setSpacing(Spacing.LG)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.FAMILY_DISPLAY};
                font-size: {Fonts.SIZE_H2}px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(title_label)
        
        # Status label
        self.status_label = QLabel("Preparing conversion...")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: {Fonts.SIZE_BODY}px;
            }}
        """)
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(self.total_chapters)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v / %m chapters")
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {Colors.BG_LIGHT};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_SM}px;
                text-align: center;
                color: {Colors.TEXT_PRIMARY};
                font-weight: bold;
                font-size: {Fonts.SIZE_BODY}px;
                min-height: 30px;
            }}
            QProgressBar::chunk {{
                background: {Colors.GRADIENT_PRIMARY};
                border-radius: {Spacing.RADIUS_SM}px;
            }}
        """)
        layout.addWidget(self.progress_bar)
        
        # Details label
        self.details_label = QLabel("")
        self.details_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_MUTED};
                font-size: {Fonts.SIZE_SMALL}px;
            }}
        """)
        layout.addWidget(self.details_label)
        
        # Cancel button (hidden initially, shown only during processing)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_MEDIUM};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_SM}px;
                padding: {Spacing.SM}px {Spacing.LG}px;
                font-size: {Fonts.SIZE_BODY}px;
            }}
            QPushButton:hover {{
                background-color: {Colors.NEON_RED};
                border-color: {Colors.NEON_RED};
            }}
        """)
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.hide()
        layout.addWidget(self.cancel_button)
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_DARK};
            }}
        """)
    
    def update_progress(self, chapter_name: str, success: bool):
        """Update progress for a chapter."""
        self.current_chapter += 1
        
        if success:
            self.converted_count += 1
            status = "✅ Converted"
        else:
            self.skipped_count += 1
            status = "⏭️ Skipped"
        
        self.progress_bar.setValue(self.current_chapter)
        self.status_label.setText(f"{status}: {chapter_name}")
        
        # Update details
        self.details_label.setText(
            f"Converted: {self.converted_count} | "
            f"Skipped: {self.skipped_count} | "
            f"Failed: {self.failed_count}"
        )
    
    def mark_failed(self, chapter_name: str):
        """Mark a chapter as failed."""
        self.current_chapter += 1
        self.failed_count += 1
        
        self.progress_bar.setValue(self.current_chapter)
        self.status_label.setText(f"❌ Failed: {chapter_name}")
        
        # Update details
        self.details_label.setText(
            f"Converted: {self.converted_count} | "
            f"Skipped: {self.skipped_count} | "
            f"Failed: {self.failed_count}"
        )
    
    def finish(self, success: bool = True):
        """Finish conversion and auto-close after delay."""
        if success:
            self.status_label.setText("✅ Conversion complete!")
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.NEON_GREEN};
                    font-size: {Fonts.SIZE_BODY}px;
                    font-weight: bold;
                }}
            """)
        else:
            self.status_label.setText("❌ Conversion cancelled")
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.NEON_RED};
                    font-size: {Fonts.SIZE_BODY}px;
                    font-weight: bold;
                }}
            """)
        
        self.cancel_button.hide()
        
        # Auto-close after 2 seconds
        QTimer.singleShot(2000, self.accept)
    
    def show_cancel_button(self):
        """Show the cancel button during processing."""
        self.cancel_button.show()
