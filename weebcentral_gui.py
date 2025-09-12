import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLineEdit, QPushButton, QProgressBar, 
                            QLabel, QDoubleSpinBox, QComboBox, QFrame, QScrollArea,
                            QFileDialog, QMessageBox, QRadioButton, QButtonGroup, QCheckBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QFont
from weebcentral_scraper import WeebCentralScraper
import os

class DownloaderThread(QThread):
    progress = pyqtSignal(str, int)  # chapter_name, progress
    overall_progress = pyqtSignal(int)  # overall progress
    status = pyqtSignal(str)  # status message
    finished = pyqtSignal(bool)
    
    def __init__(self, scraper, max_concurrent_chapters=3):
        super().__init__()
        self.scraper = scraper
        self.is_running = False
        self.active_chapters = set()
        self.max_concurrent_chapters = max_concurrent_chapters
    
    def run(self):
        self.is_running = True
        self.scraper.set_progress_callback(self.update_progress)
        self.scraper.set_stop_flag(lambda: not self.is_running)
        success = self.scraper.run()
        self.finished.emit(success)
    
    def stop(self):
        self.is_running = False
    
    def update_progress(self, chapter_name, progress):
        self.progress.emit(chapter_name, progress)
        if progress == 100:
            self.active_chapters.discard(chapter_name)
        elif progress == 0:
            self.active_chapters.add(chapter_name)

class ModernButton(QPushButton):
    def __init__(self, text, primary=False):
        super().__init__(text)
        self.setMinimumHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        if primary:
            self.setProperty('class', 'primary')
        self.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 8px;
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton[class="primary"] {
                background-color: #3498db;
            }
            QPushButton[class="primary"]:hover {
                background-color: #2980b9;
            }
        """)

class ModernInput(QLineEdit):
    def __init__(self, placeholder):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(40)
        self.setStyleSheet("""
            QLineEdit {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                padding: 8px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
        """)

class DownloadCard(QFrame):
    def __init__(self, chapter_name):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                padding: 16px;
                margin: 8px;
            }
        """)
        
        layout = QVBoxLayout()
        self.chapter_label = QLabel(chapter_name)
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                text-align: center;
                background-color: #ecf0f1;
            }
            QProgressBar::chunk {
                background-color: #2ecc71;
                border-radius: 4px;
            }
        """)
        
        layout.addWidget(self.chapter_label)
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WeebCentral Manga Downloader")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f6fa;
            }
            QLabel {
                color: #2c3e50;
            }
            QRadioButton {
                color: #2c3e50;
            }
            QDoubleSpinBox {
                padding: 5px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
            }
        """)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("WeebCentral Manga Downloader")
        header.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(header)
        
        # URL input
        url_layout = QVBoxLayout()
        url_label = QLabel("Manga URL:")
        self.url_input = ModernInput("Enter manga URL (e.g., https://weebcentral.com/manga/...)")
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)
        
        # Chapter selection
        chapter_layout = QVBoxLayout()
        chapter_label = QLabel("Chapter Selection:")
        chapter_layout.addWidget(chapter_label)
        
        # Radio buttons for selection type
        self.selection_group = QButtonGroup()
        
        # All chapters
        self.radio_all = QRadioButton("All Chapters")
        self.radio_all.setChecked(True)
        chapter_layout.addWidget(self.radio_all)
        self.selection_group.addButton(self.radio_all)
        
        # Single chapter
        self.radio_single = QRadioButton("Single Chapter")
        chapter_layout.addWidget(self.radio_single)
        self.selection_group.addButton(self.radio_single)
        
        self.single_chapter = QDoubleSpinBox()
        self.single_chapter.setEnabled(False)
        self.single_chapter.setMinimum(0)
        self.single_chapter.setMaximum(9999.9)
        self.single_chapter.setDecimals(1)
        chapter_layout.addWidget(self.single_chapter)
        
        # Chapter range
        self.radio_range = QRadioButton("Chapter Range")
        chapter_layout.addWidget(self.radio_range)
        self.selection_group.addButton(self.radio_range)
        
        range_widget = QWidget()
        range_layout = QHBoxLayout(range_widget)
        self.chapter_start = QDoubleSpinBox()
        self.chapter_end = QDoubleSpinBox()
        for spinbox in (self.chapter_start, self.chapter_end):
            spinbox.setEnabled(False)
            spinbox.setMinimum(0)
            spinbox.setMaximum(9999.9)
            spinbox.setDecimals(1)
        range_layout.addWidget(self.chapter_start)
        range_layout.addWidget(QLabel("to"))
        range_layout.addWidget(self.chapter_end)
        chapter_layout.addWidget(range_widget)
        
        # Connect radio buttons
        self.radio_all.toggled.connect(lambda: self.update_chapter_inputs("all"))
        self.radio_single.toggled.connect(lambda: self.update_chapter_inputs("single"))
        self.radio_range.toggled.connect(lambda: self.update_chapter_inputs("range"))
        
        layout.addLayout(chapter_layout)
        
        # Output directory
        dir_layout = QHBoxLayout()
        self.output_dir = ModernInput("Output directory")
        self.browse_btn = ModernButton("Browse")
        self.browse_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(self.output_dir)
        dir_layout.addWidget(self.browse_btn)
        layout.addLayout(dir_layout)
        
        # Conversion options
        conversion_layout = QHBoxLayout()
        self.pdf_checkbox = QCheckBox("Convert to PDF")
        self.pdf_checkbox.setStyleSheet("QCheckBox { color: #2c3e50; }")
        self.cbz_checkbox = QCheckBox("Convert to CBZ")
        self.cbz_checkbox.setStyleSheet("QCheckBox { color: #2c3e50; }")
        self.delete_checkbox = QCheckBox("Delete images after conversion")
        self.delete_checkbox.setStyleSheet("QCheckBox { color: #2c3e50; }")
        conversion_layout.addWidget(self.pdf_checkbox)
        conversion_layout.addWidget(self.cbz_checkbox)
        conversion_layout.addWidget(self.delete_checkbox)
        layout.addLayout(conversion_layout)
        
        # Overall progress
        self.overall_progress = QProgressBar()
        self.overall_progress.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                text-align: center;
                background-color: #ecf0f1;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.overall_progress)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.download_btn = ModernButton("Start Download", primary=True)
        self.stop_btn = ModernButton("Stop")
        self.stop_btn.setEnabled(False)
        self.download_btn.clicked.connect(self.start_download)
        self.stop_btn.clicked.connect(self.stop_download)
        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.stop_btn)
        layout.addLayout(button_layout)
        
        # Downloads area
        self.downloads_area = QScrollArea()
        self.downloads_widget = QWidget()
        self.downloads_layout = QVBoxLayout(self.downloads_widget)
        self.downloads_area.setWidget(self.downloads_widget)
        self.downloads_area.setWidgetResizable(True)
        self.downloads_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #bdc3c7;
                border-radius: 8px;
                background: white;
            }
        """)
        layout.addWidget(self.downloads_area)
        
        self.download_thread = None
    
    def update_chapter_inputs(self, mode):
        self.single_chapter.setEnabled(mode == "single")
        self.chapter_start.setEnabled(mode == "range")
        self.chapter_end.setEnabled(mode == "range")
    
    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.output_dir.setText(dir_path)
    
    def get_chapter_range(self):
        if self.radio_all.isChecked():
            return None
        elif self.radio_single.isChecked():
            return float(self.single_chapter.value())
        else:  # range
            return (float(self.chapter_start.value()), float(self.chapter_end.value()))
    
    def start_download(self):
        url = self.url_input.text()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a manga URL")
            return
        
        chapter_range = self.get_chapter_range()
        output_dir = self.output_dir.text() or "downloads"
        
        # Clear previous downloads
        while self.downloads_layout.count():
            item = self.downloads_layout.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        
        self.overall_progress.setValue(0)
        self.status_label.setText("Starting download...")
        
        scraper = WeebCentralScraper(
            manga_url=url,
            chapter_range=chapter_range,
            output_dir=output_dir,
            convert_to_pdf=self.pdf_checkbox.isChecked(),
            convert_to_cbz=self.cbz_checkbox.isChecked(),
            delete_images_after_conversion=self.delete_checkbox.isChecked()
        )
        
        self.download_thread = DownloaderThread(scraper)
        self.download_thread.progress.connect(self.update_progress)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.start()
        
        self.download_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
    
    def stop_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.stop()
            self.status_label.setText("Stopping download...")
            self.stop_btn.setEnabled(False)
    
    def update_progress(self, chapter_name, progress):
        # Find or create download card
        card = None
        for i in range(self.downloads_layout.count()):
            item = self.downloads_layout.itemAt(i)
            if item:
                widget = item.widget()
                if isinstance(widget, DownloadCard) and widget.chapter_label.text() == chapter_name:
                    card = widget
                    break
        
        if not card:
            card = DownloadCard(chapter_name)
            self.downloads_layout.insertWidget(0, card)  # Add new cards at the top
        
        if card:
            card.progress_bar.setValue(progress)
        
        # Update overall progress
        total_progress = 0
        count = 0
        for i in range(self.downloads_layout.count()):
            item = self.downloads_layout.itemAt(i)
            if item:
                widget = item.widget()
                if isinstance(widget, DownloadCard):
                    total_progress += widget.progress_bar.value()
                    count += 1
        
        if count > 0:
            self.overall_progress.setValue(total_progress // count)
    
    def download_finished(self, success):
        self.download_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if success:
            self.status_label.setText("Download completed successfully!")
            QMessageBox.information(self, "Success", "Download completed successfully!")
        else:
            self.status_label.setText("Download failed. Check logs for details.")
            QMessageBox.warning(self, "Error", "Download failed. Check logs for details.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
