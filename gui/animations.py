"""
Animation utilities for the WeebCentral Downloader GUI.
Provides smooth transitions, fade effects, and micro-interactions.
"""

from PyQt6.QtCore import (
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QSequentialAnimationGroup, QPoint, QSize, Qt, pyqtProperty, QObject
)
from PyQt6.QtWidgets import QWidget, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor

from gui.theme import Colors


class AnimationDuration:
    """Standard animation durations in milliseconds."""
    INSTANT = 100
    FAST = 150
    NORMAL = 250
    SLOW = 400
    VERY_SLOW = 600


class AnimationMixin:
    """Mixin class to add animation capabilities to widgets."""
    
    def fade_in(self, duration: int = AnimationDuration.NORMAL):
        """Animate widget opacity from 0 to 1."""
        effect = self._ensure_opacity_effect()
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        return anim
    
    def fade_out(self, duration: int = AnimationDuration.NORMAL):
        """Animate widget opacity from 1 to 0."""
        effect = self._ensure_opacity_effect()
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(duration)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.start()
        return anim
    
    def _ensure_opacity_effect(self) -> QGraphicsOpacityEffect:
        """Ensure widget has an opacity effect."""
        effect = self.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(effect)
        return effect


def create_fade_animation(
    widget: QWidget, 
    start: float = 0.0, 
    end: float = 1.0,
    duration: int = AnimationDuration.NORMAL
) -> QPropertyAnimation:
    """Create a fade animation for a widget."""
    effect = widget.graphicsEffect()
    if not isinstance(effect, QGraphicsOpacityEffect):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(start)
    anim.setEndValue(end)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    return anim


def create_slide_animation(
    widget: QWidget,
    start_pos: QPoint,
    end_pos: QPoint,
    duration: int = AnimationDuration.NORMAL
) -> QPropertyAnimation:
    """Create a slide animation for a widget."""
    anim = QPropertyAnimation(widget, b"pos", widget)
    anim.setDuration(duration)
    anim.setStartValue(start_pos)
    anim.setEndValue(end_pos)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    return anim


def create_size_animation(
    widget: QWidget,
    start_size: QSize,
    end_size: QSize,
    duration: int = AnimationDuration.NORMAL
) -> QPropertyAnimation:
    """Create a size animation for a widget."""
    anim = QPropertyAnimation(widget, b"size", widget)
    anim.setDuration(duration)
    anim.setStartValue(start_size)
    anim.setEndValue(end_size)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    return anim


def create_glow_effect(
    color: str = Colors.NEON_CYAN,
    blur_radius: int = 20,
    offset: tuple = (0, 0)
) -> QGraphicsDropShadowEffect:
    """Create a glow/shadow effect."""
    effect = QGraphicsDropShadowEffect()
    effect.setColor(QColor(color))
    effect.setBlurRadius(blur_radius)
    effect.setOffset(offset[0], offset[1])
    return effect


class GlowAnimator(QObject):
    """Animates the glow effect intensity on a widget."""
    
    def __init__(self, widget: QWidget, color: str = Colors.NEON_CYAN):
        super().__init__(widget)
        self._widget = widget
        self._color = color
        self._blur_radius = 0
        
        self._effect = QGraphicsDropShadowEffect(widget)
        self._effect.setColor(QColor(color))
        self._effect.setOffset(0, 0)
        self._effect.setBlurRadius(0)
        widget.setGraphicsEffect(self._effect)
        
        self._animation = QPropertyAnimation(self, b"blurRadius", self)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    @pyqtProperty(float)
    def blurRadius(self) -> float:
        return self._blur_radius
    
    @blurRadius.setter
    def blurRadius(self, value: float):
        self._blur_radius = value
        self._effect.setBlurRadius(value)
    
    def glow_in(self, target: float = 25, duration: int = AnimationDuration.NORMAL):
        """Animate glow to target intensity."""
        self._animation.stop()
        self._animation.setDuration(duration)
        self._animation.setStartValue(self._blur_radius)
        self._animation.setEndValue(target)
        self._animation.start()
    
    def glow_out(self, duration: int = AnimationDuration.NORMAL):
        """Animate glow to zero."""
        self._animation.stop()
        self._animation.setDuration(duration)
        self._animation.setStartValue(self._blur_radius)
        self._animation.setEndValue(0)
        self._animation.start()


class PulseAnimator(QObject):
    """Creates a pulsing glow effect."""
    
    def __init__(self, widget: QWidget, color: str = Colors.NEON_CYAN):
        super().__init__(widget)
        self._widget = widget
        self._glow = GlowAnimator(widget, color)
        
        self._anim_in = QPropertyAnimation(self._glow, b"blurRadius", self)
        self._anim_in.setDuration(800)
        self._anim_in.setStartValue(5)
        self._anim_in.setEndValue(25)
        self._anim_in.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        self._anim_out = QPropertyAnimation(self._glow, b"blurRadius", self)
        self._anim_out.setDuration(800)
        self._anim_out.setStartValue(25)
        self._anim_out.setEndValue(5)
        self._anim_out.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        self._sequence = QSequentialAnimationGroup(self)
        self._sequence.addAnimation(self._anim_in)
        self._sequence.addAnimation(self._anim_out)
        self._sequence.setLoopCount(-1)  # Infinite loop
    
    def start(self):
        """Start pulsing animation."""
        self._sequence.start()
    
    def stop(self):
        """Stop pulsing animation."""
        self._sequence.stop()
        self._glow.glow_out()


def animate_button_press(widget: QWidget, duration: int = AnimationDuration.FAST):
    """Animate a button press effect (scale down and back)."""
    original_size = widget.size()
    pressed_size = QSize(
        int(original_size.width() * 0.95),
        int(original_size.height() * 0.95)
    )
    
    group = QSequentialAnimationGroup(widget)
    
    # Scale down
    anim_down = create_size_animation(widget, original_size, pressed_size, duration // 2)
    group.addAnimation(anim_down)
    
    # Scale up
    anim_up = create_size_animation(widget, pressed_size, original_size, duration // 2)
    group.addAnimation(anim_up)
    
    group.start()
    return group


def stagger_animations(
    animations: list,
    stagger_delay: int = 50
) -> QSequentialAnimationGroup:
    """Create staggered animation group with delays between items."""
    from PyQt6.QtCore import QPauseAnimation
    
    group = QSequentialAnimationGroup()
    
    for i, anim in enumerate(animations):
        if i > 0:
            pause = QPauseAnimation(stagger_delay)
            group.addAnimation(pause)
        
        # Wrap each animation in a parallel group to run simultaneously
        parallel = QParallelAnimationGroup()
        parallel.addAnimation(anim)
        group.addAnimation(parallel)
    
    return group
