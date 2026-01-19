"""
Chapter List Component.
Styled list widget for manga chapter selection with checkboxes and range input.
"""

from typing import List, Optional
from dataclasses import dataclass
import re

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QFrame, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor

from gui.theme import Colors, Spacing


@dataclass
class ChapterItem:
    """Data class representing a chapter."""
    name: str
    url: str
    index: int = 0


class ChapterListWidget(QWidget):
    """
    Chapter selection list with toolbar controls.
    Supports multi-selection with checkboxes, filtering, and range selection.
    """
    
    selectionChanged = pyqtSignal(list)  # Emits list of selected ChapterItems
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._chapters: List[ChapterItem] = []
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)
        
        # Toolbar
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_MEDIUM};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_MD}px;
                padding: {Spacing.SM}px;
            }}
        """)
        toolbar_layout = QVBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        toolbar_layout.setSpacing(Spacing.SM)
        
        # First row: Filter and buttons
        row1 = QHBoxLayout()
        row1.setSpacing(Spacing.SM)
        
        # Search/filter
        self._filter_input = QLineEdit()
        self._filter_input.setPlaceholderText("🔍 Filter chapters...")
        self._filter_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Colors.BG_LIGHT};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_SM}px;
                padding: {Spacing.SM}px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QLineEdit:focus {{
                border-color: {Colors.NEON_CYAN};
            }}
        """)
        self._filter_input.textChanged.connect(self._filter_chapters)
        row1.addWidget(self._filter_input)
        
        # Selection buttons
        btn_style = f"""
            QPushButton {{
                background-color: {Colors.BG_LIGHT};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_SM}px;
                padding: {Spacing.SM}px {Spacing.MD}px;
                color: {Colors.TEXT_PRIMARY};
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_HOVER};
                border-color: {Colors.NEON_CYAN};
            }}
        """
        
        self._btn_all = QPushButton("Select All")
        self._btn_all.setStyleSheet(btn_style)
        self._btn_all.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_all.clicked.connect(self._select_all)
        row1.addWidget(self._btn_all)
        
        self._btn_none = QPushButton("Deselect All")
        self._btn_none.setStyleSheet(btn_style)
        self._btn_none.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_none.clicked.connect(self._deselect_all)
        row1.addWidget(self._btn_none)
        
        self._btn_invert = QPushButton("Invert")
        self._btn_invert.setStyleSheet(btn_style)
        self._btn_invert.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_invert.clicked.connect(self._invert_selection)
        row1.addWidget(self._btn_invert)
        
        toolbar_layout.addLayout(row1)
        
        # Second row: Range selection
        row2 = QHBoxLayout()
        row2.setSpacing(Spacing.SM)
        
        range_label = QLabel("Select Range:")
        range_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 12px;
            }}
        """)
        row2.addWidget(range_label)
        
        self._range_input = QLineEdit()
        self._range_input.setPlaceholderText("e.g., 1-50 or 1,5,10-20")
        self._range_input.setMinimumWidth(180)
        self._range_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Colors.BG_LIGHT};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_SM}px;
                padding: {Spacing.SM}px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QLineEdit:focus {{
                border-color: {Colors.NEON_CYAN};
            }}
        """)
        row2.addWidget(self._range_input)
        
        self._btn_apply_range = QPushButton("Apply Range")
        self._btn_apply_range.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.GRADIENT_PRIMARY};
                border: none;
                border-radius: {Spacing.RADIUS_SM}px;
                padding: {Spacing.SM}px {Spacing.MD}px;
                color: {Colors.TEXT_PRIMARY};
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00E5FF, stop:1 #FF1AE8);
            }}
        """)
        self._btn_apply_range.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_apply_range.clicked.connect(self._apply_range_selection)
        row2.addWidget(self._btn_apply_range)
        
        row2.addStretch()
        toolbar_layout.addLayout(row2)
        
        layout.addWidget(toolbar)
        
        # Chapter list
        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._list.itemChanged.connect(self._on_item_changed)
        self._list.setStyleSheet(f"""
            QListWidget {{
                background-color: {Colors.BG_MEDIUM};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_MD}px;
                padding: {Spacing.SM}px;
                outline: none;
            }}
            QListWidget::item {{
                background-color: transparent;
                color: {Colors.TEXT_PRIMARY};
                padding: {Spacing.SM}px {Spacing.MD}px;
                border-radius: {Spacing.RADIUS_SM}px;
                margin: 2px 0;
            }}
            QListWidget::item:hover {{
                background-color: {Colors.BG_HOVER};
            }}
        """)
        layout.addWidget(self._list)
        
        # Selection count
        self._count_label = QLabel("0 chapters selected")
        self._count_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_MUTED};
                font-size: 12px;
                padding: {Spacing.SM}px;
            }}
        """)
        layout.addWidget(self._count_label)
    
    def set_chapters(self, chapters: List[ChapterItem]):
        """Set the chapter list."""
        self._chapters = chapters
        self._list.clear()
        
        for chapter in chapters:
            item = QListWidgetItem(chapter.name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, chapter)
            self._list.addItem(item)
        
        self._update_count()
    
    def clear_chapters(self):
        """Clear all chapters."""
        self._chapters = []
        self._list.clear()
        self._update_count()
    
    def get_selected_chapters(self) -> List[ChapterItem]:
        """Get list of selected chapters."""
        selected = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                chapter = item.data(Qt.ItemDataRole.UserRole)
                if chapter:
                    selected.append(chapter)
        return selected
    
    def _select_all(self):
        """Select all visible chapters."""
        for i in range(self._list.count()):
            item = self._list.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.CheckState.Checked)
        self._update_count()
    
    def _deselect_all(self):
        """Deselect all chapters."""
        for i in range(self._list.count()):
            item = self._list.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)
        self._update_count()
    
    def _invert_selection(self):
        """Invert current selection."""
        for i in range(self._list.count()):
            item = self._list.item(i)
            if not item.isHidden():
                if item.checkState() == Qt.CheckState.Checked:
                    item.setCheckState(Qt.CheckState.Unchecked)
                else:
                    item.setCheckState(Qt.CheckState.Checked)
        self._update_count()
    
    def _apply_range_selection(self):
        """Apply range selection from input field."""
        range_text = self._range_input.text().strip()
        if not range_text:
            return
        
        # Parse the range input (e.g., "1-50" or "1,5,10-20")
        indices_to_select = set()
        
        try:
            parts = range_text.replace(" ", "").split(",")
            for part in parts:
                if "-" in part:
                    # Range like "1-50"
                    start_end = part.split("-")
                    if len(start_end) == 2:
                        start = int(start_end[0])
                        end = int(start_end[1])
                        for i in range(start, end + 1):
                            indices_to_select.add(i)
                else:
                    # Single number
                    indices_to_select.add(int(part))
        except ValueError:
            return  # Invalid input, ignore
        
        # Apply selection - indices are 1-based in input, 0-based in list
        self._deselect_all()  # First deselect all
        
        for i in range(self._list.count()):
            # Check if 1-based index is in selection set
            if (i + 1) in indices_to_select:
                item = self._list.item(i)
                item.setCheckState(Qt.CheckState.Checked)
        
        self._update_count()
    
    def _filter_chapters(self, text: str):
        """Filter chapters by name."""
        text = text.lower()
        for i in range(self._list.count()):
            item = self._list.item(i)
            if text in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)
    
    def _on_item_changed(self, item: QListWidgetItem):
        """Handle item check state change."""
        self._update_count()
        self.selectionChanged.emit(self.get_selected_chapters())
    
    def _update_count(self):
        """Update the selection count label."""
        selected = len(self.get_selected_chapters())
        total = len(self._chapters)
        self._count_label.setText(f"{selected} of {total} chapters selected")
