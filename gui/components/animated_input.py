"""
Animated Input Component.
Modern text input with focus glow and clear button.
"""

from PyQt6.QtWidgets import (
    QLineEdit, QHBoxLayout, QPushButton, QWidget, 
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal
)
from PyQt6.QtGui import QColor, QCursor

from gui.theme import Colors, Spacing


class AnimatedInput(QLineEdit):
    """
    Text input with animated focus glow effect.
    Features smooth border color transition and optional clear button.
    """
    
    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(48)
        
        # Glow effect for focus
        self._glow_radius = 0
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setColor(QColor(Colors.NEON_CYAN))
        self._shadow.setOffset(0, 0)
        self._shadow.setBlurRadius(0)
        self.setGraphicsEffect(self._shadow)
        
        # Focus animation
        self._focus_anim = QPropertyAnimation(self, b"glowRadius", self)
        self._focus_anim.setDuration(200)
        self._focus_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    @pyqtProperty(float)
    def glowRadius(self) -> float:
        return self._glow_radius
    
    @glowRadius.setter
    def glowRadius(self, value: float):
        self._glow_radius = value
        self._shadow.setBlurRadius(value)
    
    def focusInEvent(self, event):
        """Handle focus in - start glow animation."""
        self._focus_anim.stop()
        self._focus_anim.setStartValue(self._glow_radius)
        self._focus_anim.setEndValue(15)
        self._focus_anim.start()
        super().focusInEvent(event)
    
    def focusOutEvent(self, event):
        """Handle focus out - fade out glow."""
        self._focus_anim.stop()
        self._focus_anim.setStartValue(self._glow_radius)
        self._focus_anim.setEndValue(0)
        self._focus_anim.start()
        super().focusOutEvent(event)


class InputWithButton(QWidget):
    """
    Input field with an action button on the right side.
    Useful for URL input with fetch button, or directory with browse.
    """
    
    textChanged = pyqtSignal(str)
    returnPressed = pyqtSignal()
    buttonClicked = pyqtSignal()
    
    def __init__(
        self, 
        placeholder: str = "", 
        button_text: str = "",
        button_icon: str = "",
        parent=None
    ):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)
        
        # Input field
        self._input = AnimatedInput(placeholder)
        self._input.textChanged.connect(self.textChanged.emit)
        self._input.returnPressed.connect(self.returnPressed.emit)
        layout.addWidget(self._input)
        
        # Action button
        self._button = QPushButton(button_icon + button_text if button_icon else button_text)
        self._button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._button.setMinimumHeight(48)
        self._button.setMinimumWidth(100)
        self._button.clicked.connect(self.buttonClicked.emit)
        self._button.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.GRADIENT_PRIMARY};
                border: none;
                border-radius: {Spacing.RADIUS_MD}px;
                color: {Colors.TEXT_PRIMARY};
                font-weight: bold;
                padding: 0 {Spacing.LG}px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #00E5FF, stop:1 #FF1AE8);
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #00C4DB, stop:1 #DB00C4);
            }}
        """)
        layout.addWidget(self._button)
    
    def text(self) -> str:
        """Get input text."""
        return self._input.text()
    
    def setText(self, text: str):
        """Set input text."""
        self._input.setText(text)
    
    def setPlaceholderText(self, text: str):
        """Set placeholder text."""
        self._input.setPlaceholderText(text)
    
    def setButtonText(self, text: str):
        """Set button text."""
        self._button.setText(text)
    
    def setButtonEnabled(self, enabled: bool):
        """Enable or disable the button."""
        self._button.setEnabled(enabled)
    
    def clear(self):
        """Clear the input."""
        self._input.clear()


class SearchInput(AnimatedInput):
    """
    Search input with magnifying glass icon styling.
    """
    
    def __init__(self, placeholder: str = "Search...", parent=None):
        super().__init__(placeholder, parent)
        self.setStyleSheet(f"""
            QLineEdit {{
                padding-left: {Spacing.XL}px;
                background-color: {Colors.BG_LIGHT};
                border: 2px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_MD}px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.NEON_CYAN};
            }}
        """)


class PathInput(InputWithButton):
    """
    Directory/file path input with browse button.
    """
    
    def __init__(self, placeholder: str = "Select directory...", parent=None):
        super().__init__(
            placeholder=placeholder,
            button_text="Browse",
            button_icon="📁 ",
            parent=parent
        )
