"""
Settings Tab.
Configuration panel with all application settings and JSON persistence.
"""

import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QSlider, QCheckBox, QFileDialog, QMessageBox,
    QScrollArea, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from gui.theme import Colors, Spacing, Fonts
from gui.components.animated_button import AnimatedButton, PrimaryButton
from gui.components.animated_input import PathInput
from gui.config import get_settings, save_settings, reset_settings, SettingsManager


class SettingsSection(QFrame):
    """A collapsible settings section with title."""
    
    def __init__(self, title: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_MEDIUM};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_LG}px;
            }}
        """)
        
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        self._layout.setSpacing(Spacing.MD)
        
        # Section title
        title_label = QLabel(f"{icon} {title}" if icon else title)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.FAMILY_DISPLAY};
                font-size: {Fonts.SIZE_H3}px;
                font-weight: bold;
            }}
        """)
        self._layout.addWidget(title_label)
    
    def add_widget(self, widget: QWidget):
        """Add a widget to the section."""
        self._layout.addWidget(widget)
    
    def add_layout(self, layout):
        """Add a layout to the section."""
        self._layout.addLayout(layout)


class SettingsRow(QWidget):
    """A row in settings with label and control."""
    
    def __init__(self, label: str, description: str = "", parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.XS)
        
        # Label
        self._label = QLabel(label)
        self._label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-size: {Fonts.SIZE_BODY}px;
                font-weight: 500;
            }}
        """)
        layout.addWidget(self._label)
        
        # Description
        if description:
            desc = QLabel(description)
            desc.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.TEXT_MUTED};
                    font-size: {Fonts.SIZE_SMALL}px;
                }}
            """)
            desc.setWordWrap(True)
            layout.addWidget(desc)
        
        # Control container
        self._control_layout = QHBoxLayout()
        self._control_layout.setContentsMargins(0, Spacing.SM, 0, 0)
        layout.addLayout(self._control_layout)
    
    def add_control(self, widget: QWidget):
        """Add a control widget."""
        self._control_layout.addWidget(widget)
    
    def add_stretch(self):
        """Add stretch to control layout."""
        self._control_layout.addStretch()


class SettingsTab(QWidget):
    """
    Settings tab with all application configuration options.
    Settings are persisted to JSON file.
    """
    
    settingsChanged = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.LG)
        
        # Scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(Spacing.LG)
        
        # ─────────────────────────────────────────────────────────────
        # Download Settings Section
        # ─────────────────────────────────────────────────────────────
        download_section = SettingsSection("Download Settings", "📥")
        
        # Output directory
        dir_row = SettingsRow("Output Directory", "Where downloaded manga will be saved")
        self._output_dir = PathInput("Select download folder...")
        self._output_dir.buttonClicked.connect(self._browse_directory)
        dir_row.add_control(self._output_dir)
        download_section.add_widget(dir_row)
        
        # Concurrent chapter downloads
        threads_row = SettingsRow(
            "Concurrent Chapters", 
            "Number of chapters to download simultaneously (1-8)"
        )
        self._threads_slider = QSlider(Qt.Orientation.Horizontal)
        self._threads_slider.setMinimum(1)
        self._threads_slider.setMaximum(8)
        self._threads_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._threads_slider.setTickInterval(1)
        self._threads_slider.valueChanged.connect(self._on_threads_changed)
        threads_row.add_control(self._threads_slider)
        
        self._threads_label = QLabel("4")
        self._threads_label.setMinimumWidth(30)
        self._threads_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.NEON_CYAN};
                font-weight: bold;
                font-size: {Fonts.SIZE_BODY}px;
            }}
        """)
        threads_row.add_control(self._threads_label)
        download_section.add_widget(threads_row)
        
        # Concurrent image downloads
        img_threads_row = SettingsRow(
            "Concurrent Images", 
            "Number of images to download simultaneously per chapter (1-10)"
        )
        self._img_threads_slider = QSlider(Qt.Orientation.Horizontal)
        self._img_threads_slider.setMinimum(1)
        self._img_threads_slider.setMaximum(10)
        self._img_threads_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._img_threads_slider.setTickInterval(1)
        self._img_threads_slider.valueChanged.connect(self._on_img_threads_changed)
        img_threads_row.add_control(self._img_threads_slider)
        
        self._img_threads_label = QLabel("4")
        self._img_threads_label.setMinimumWidth(30)
        self._img_threads_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.NEON_CYAN};
                font-weight: bold;
                font-size: {Fonts.SIZE_BODY}px;
            }}
        """)
        img_threads_row.add_control(self._img_threads_label)
        download_section.add_widget(img_threads_row)
        
        # Request delay
        delay_row = SettingsRow(
            "Request Delay", 
            "Delay between requests in seconds (0.5-5.0)"
        )
        self._delay_slider = QSlider(Qt.Orientation.Horizontal)
        self._delay_slider.setMinimum(5)  # 0.5 seconds
        self._delay_slider.setMaximum(50)  # 5.0 seconds
        self._delay_slider.setTickInterval(5)
        self._delay_slider.valueChanged.connect(self._on_delay_changed)
        delay_row.add_control(self._delay_slider)
        
        self._delay_label = QLabel("1.0s")
        self._delay_label.setMinimumWidth(40)
        self._delay_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.NEON_CYAN};
                font-weight: bold;
                font-size: {Fonts.SIZE_BODY}px;
            }}
        """)
        delay_row.add_control(self._delay_label)
        download_section.add_widget(delay_row)
        
        scroll_layout.addWidget(download_section)
        
        # ─────────────────────────────────────────────────────────────
        # Conversion Settings Section
        # ─────────────────────────────────────────────────────────────
        conversion_section = SettingsSection("Conversion Options", "🔄")
        
        # PDF conversion
        self._pdf_check = QCheckBox("Convert to PDF")
        self._pdf_check.setStyleSheet(f"""
            QCheckBox {{
                color: {Colors.TEXT_PRIMARY};
                font-size: {Fonts.SIZE_BODY}px;
                spacing: {Spacing.SM}px;
            }}
        """)
        conversion_section.add_widget(self._pdf_check)
        
        # CBZ conversion  
        self._cbz_check = QCheckBox("Convert to CBZ (Comic Book Archive)")
        self._cbz_check.setStyleSheet(f"""
            QCheckBox {{
                color: {Colors.TEXT_PRIMARY};
                font-size: {Fonts.SIZE_BODY}px;
                spacing: {Spacing.SM}px;
            }}
        """)
        conversion_section.add_widget(self._cbz_check)
        
        # EPUB conversion
        self._epub_check = QCheckBox("Convert to EPUB (Electronic Book)")
        self._epub_check.setStyleSheet(f"""
            QCheckBox {{
                color: {Colors.TEXT_PRIMARY};
                font-size: {Fonts.SIZE_BODY}px;
                spacing: {Spacing.SM}px;
            }}
        """)
        conversion_section.add_widget(self._epub_check)
        
        # Merge chapters option
        self._merge_check = QCheckBox("Merge all chapters into single file")
        self._merge_check.setStyleSheet(f"""
            QCheckBox {{
                color: {Colors.TEXT_PRIMARY};
                font-size: {Fonts.SIZE_BODY}px;
                spacing: {Spacing.SM}px;
            }}
        """)
        merge_hint = QLabel("Creates one PDF/CBZ/EPUB with all chapters instead of separate files")
        merge_hint.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_MUTED};
                font-size: {Fonts.SIZE_SMALL}px;
                margin-left: 24px;
            }}
        """)
        conversion_section.add_widget(self._merge_check)
        conversion_section.add_widget(merge_hint)
        
        # Delete images after conversion
        self._delete_check = QCheckBox("Delete images after conversion")
        self._delete_check.setStyleSheet(f"""
            QCheckBox {{
                color: {Colors.TEXT_PRIMARY};
                font-size: {Fonts.SIZE_BODY}px;
                spacing: {Spacing.SM}px;
            }}
        """)
        delete_hint = QLabel("Only takes effect if PDF, CBZ, or EPUB conversion is enabled")
        delete_hint.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_MUTED};
                font-size: {Fonts.SIZE_SMALL}px;
                margin-left: 24px;
            }}
        """)
        conversion_section.add_widget(self._delete_check)
        conversion_section.add_widget(delete_hint)
        
        scroll_layout.addWidget(conversion_section)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)
        
        # ─────────────────────────────────────────────────────────────
        # Action Buttons
        # ─────────────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(Spacing.MD)
        
        self._reset_btn = AnimatedButton("🔄 Reset to Defaults")
        self._reset_btn.clicked.connect(self._reset_settings)
        btn_layout.addWidget(self._reset_btn)
        
        btn_layout.addStretch()
        
        self._save_btn = PrimaryButton("💾 Save Settings")
        self._save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self._save_btn)
        
        layout.addLayout(btn_layout)
    
    def _load_settings(self):
        """Load current settings into UI."""
        settings = get_settings()
        
        self._output_dir.setText(settings.output_dir)
        self._threads_slider.setValue(settings.max_threads)
        self._threads_label.setText(str(settings.max_threads))
        self._img_threads_slider.setValue(settings.max_image_threads)
        self._img_threads_label.setText(str(settings.max_image_threads))
        self._delay_slider.setValue(int(settings.delay * 10))
        self._delay_label.setText(f"{settings.delay:.1f}s")
        self._pdf_check.setChecked(settings.convert_to_pdf)
        self._cbz_check.setChecked(settings.convert_to_cbz)
        self._epub_check.setChecked(settings.convert_to_epub)
        self._merge_check.setChecked(settings.merge_chapters)
        self._delete_check.setChecked(settings.delete_images_after_conversion)
    
    def _save_settings(self):
        """Save current UI state to settings."""
        settings = get_settings()
        
        settings.output_dir = self._output_dir.text() or "downloads"
        settings.max_threads = self._threads_slider.value()
        settings.max_image_threads = self._img_threads_slider.value()
        settings.delay = self._delay_slider.value() / 10.0
        settings.convert_to_pdf = self._pdf_check.isChecked()
        settings.convert_to_cbz = self._cbz_check.isChecked()
        settings.convert_to_epub = self._epub_check.isChecked()
        settings.merge_chapters = self._merge_check.isChecked()
        settings.delete_images_after_conversion = self._delete_check.isChecked()
        
        save_settings()
        self.settingsChanged.emit()
        
        QMessageBox.information(
            self, 
            "Settings Saved", 
            "Your settings have been saved successfully!"
        )
    
    def _reset_settings(self):
        """Reset settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            reset_settings()
            self._load_settings()
            self.settingsChanged.emit()
    
    def _browse_directory(self):
        """Open directory browser."""
        current = self._output_dir.text() or os.getcwd()
        dir_path = QFileDialog.getExistingDirectory(
            self, 
            "Select Output Directory",
            current
        )
        if dir_path:
            self._output_dir.setText(dir_path)
    
    def _on_threads_changed(self, value: int):
        """Handle threads slider change."""
        self._threads_label.setText(str(value))
    
    def _on_img_threads_changed(self, value: int):
        """Handle image threads slider change."""
        self._img_threads_label.setText(str(value))
    
    def _on_delay_changed(self, value: int):
        """Handle delay slider change."""
        delay = value / 10.0
        self._delay_label.setText(f"{delay:.1f}s")
