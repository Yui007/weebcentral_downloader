"""
Animated Button Components.
Custom buttons with hover glow, press effects, and gradient backgrounds.
"""

from PyQt6.QtWidgets import QPushButton, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor, QCursor

from gui.theme import Colors, Spacing


class AnimatedButton(QPushButton):
    """
    Button with smooth hover and press animations.
    Features glow effect on hover and scale feedback on press.
    """
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(44)
        
        # Glow effect
        self._glow_radius = 0
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setColor(QColor(Colors.NEON_CYAN))
        self._shadow.setOffset(0, 0)
        self._shadow.setBlurRadius(0)
        self.setGraphicsEffect(self._shadow)
        
        # Hover animation
        self._hover_anim = QPropertyAnimation(self, b"glowRadius", self)
        self._hover_anim.setDuration(200)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    @pyqtProperty(float)
    def glowRadius(self) -> float:
        return self._glow_radius
    
    @glowRadius.setter
    def glowRadius(self, value: float):
        self._glow_radius = value
        self._shadow.setBlurRadius(value)
    
    def set_glow_color(self, color: str):
        """Set the glow effect color."""
        self._shadow.setColor(QColor(color))
    
    def enterEvent(self, event):
        """Handle mouse enter - start glow animation."""
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._glow_radius)
        self._hover_anim.setEndValue(20)
        self._hover_anim.start()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave - fade out glow."""
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._glow_radius)
        self._hover_anim.setEndValue(0)
        self._hover_anim.start()
        super().leaveEvent(event)


class PrimaryButton(AnimatedButton):
    """
    Primary action button with gradient background.
    Uses cyan-to-magenta gradient with enhanced glow.
    """
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("primary")
        self.set_glow_color(Colors.NEON_MAGENTA)
        
        # Larger minimum size for primary actions
        self.setMinimumHeight(48)
        self.setMinimumWidth(120)


class DangerButton(AnimatedButton):
    """Red themed button for destructive actions."""
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("danger")
        self.set_glow_color(Colors.NEON_RED)


class SuccessButton(AnimatedButton):
    """Green themed button for confirmatory actions."""
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("success")
        self.set_glow_color(Colors.NEON_GREEN)


class IconButton(AnimatedButton):
    """
    Compact button designed for icons.
    Square shape with centered content.
    """
    
    def __init__(self, icon_text: str = "", parent=None):
        super().__init__(icon_text, parent)
        self.setFixedSize(44, 44)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_LIGHT};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_MD}px;
                font-size: 18px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_HOVER};
                border-color: {Colors.NEON_CYAN};
            }}
        """)


class NavButton(AnimatedButton):
    """
    Navigation sidebar button.
    Supports checked state with gradient fill.
    """
    
    def __init__(self, icon: str = "", text: str = "", parent=None):
        super().__init__(parent=parent)
        self.setObjectName("nav-button")
        self.setCheckable(True)
        self.setMinimumHeight(50)
        
        # Display icon and text
        if icon and text:
            self.setText(f"  {icon}  {text}")
        elif icon:
            self.setText(icon)
        else:
            self.setText(text)
        
        # Left-align text
        self.setStyleSheet(f"""
            QPushButton#nav-button {{
                text-align: left;
                padding-left: {Spacing.LG}px;
                font-size: 14px;
                background: transparent;
                border: none;
                border-radius: {Spacing.RADIUS_MD}px;
                color: {Colors.TEXT_SECONDARY};
            }}
            QPushButton#nav-button:hover {{
                background-color: {Colors.BG_HOVER};
                color: {Colors.TEXT_PRIMARY};
            }}
            QPushButton#nav-button:checked {{
                background: {Colors.GRADIENT_PRIMARY};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        
        # Custom glow for nav buttons
        self.set_glow_color(Colors.NEON_CYAN)
    
    def enterEvent(self, event):
        """Subtle glow on hover for nav buttons."""
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._glow_radius)
        self._hover_anim.setEndValue(10)
        self._hover_anim.start()
        # Skip parent's enterEvent to avoid double animation
        QPushButton.enterEvent(self, event)
    
    def leaveEvent(self, event):
        """Fade out glow."""
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._glow_radius)
        self._hover_anim.setEndValue(0)
        self._hover_anim.start()
        QPushButton.leaveEvent(self, event)
