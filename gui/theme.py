"""
Design System and Theme for WeebCentral Downloader.
Neon Noir aesthetic: dark backgrounds with cyan/magenta neon accents.
"""

# =============================================================================
# COLOR PALETTE
# =============================================================================

class Colors:
    """Color constants for the Neon Noir theme."""
    
    # Backgrounds (layered depth)
    BG_DARKEST = "#0A0A0F"      # Window background
    BG_DARK = "#12121A"         # Panel background
    BG_MEDIUM = "#1A1A25"       # Card background
    BG_LIGHT = "#252533"        # Input/elevated background
    BG_HOVER = "#2D2D3D"        # Hover states
    
    # Neon accents
    NEON_CYAN = "#00D9FF"       # Primary accent
    NEON_MAGENTA = "#FF00E5"    # Secondary accent
    NEON_VIOLET = "#8B5CF6"     # Tertiary accent
    NEON_GREEN = "#00FF88"      # Success
    NEON_ORANGE = "#FF8800"     # Warning
    NEON_RED = "#FF3366"        # Error
    
    # Text colors
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#A0A0B0"
    TEXT_MUTED = "#606070"
    TEXT_DISABLED = "#404050"
    
    # Borders
    BORDER_DEFAULT = "#2A2A3A"
    BORDER_HOVER = "#3A3A4A"
    BORDER_FOCUS = NEON_CYAN
    
    # Gradients (as QSS format)
    GRADIENT_PRIMARY = f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {NEON_CYAN}, stop:1 {NEON_MAGENTA})"
    GRADIENT_SUCCESS = f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {NEON_GREEN}, stop:1 {NEON_CYAN})"
    GRADIENT_BG = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {BG_DARK}, stop:1 {BG_DARKEST})"


# =============================================================================
# TYPOGRAPHY
# =============================================================================

class Fonts:
    """Font specifications."""
    
    FAMILY_DISPLAY = "Outfit, Segoe UI, Arial, sans-serif"
    FAMILY_BODY = "Inter, Segoe UI, Arial, sans-serif"
    
    SIZE_HERO = 32
    SIZE_H1 = 24
    SIZE_H2 = 20
    SIZE_H3 = 16
    SIZE_BODY = 14
    SIZE_SMALL = 12
    SIZE_TINY = 10


# =============================================================================
# SPACING & SIZING
# =============================================================================

class Spacing:
    """Spacing and sizing constants."""
    
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32
    
    RADIUS_SM = 6
    RADIUS_MD = 10
    RADIUS_LG = 16
    RADIUS_XL = 24
    RADIUS_FULL = 9999


# =============================================================================
# STYLESHEET
# =============================================================================

def get_stylesheet() -> str:
    """Generate the complete QSS stylesheet."""
    
    return f"""
/* ==========================================================================
   GLOBAL STYLES
   ========================================================================== */

QWidget {{
    background-color: {Colors.BG_DARKEST};
    color: {Colors.TEXT_PRIMARY};
    font-family: {Fonts.FAMILY_BODY};
    font-size: {Fonts.SIZE_BODY}px;
}}

/* ==========================================================================
   MAIN WINDOW
   ========================================================================== */

QMainWindow {{
    background-color: {Colors.BG_DARKEST};
}}

/* ==========================================================================
   LABELS
   ========================================================================== */

QLabel {{
    color: {Colors.TEXT_PRIMARY};
    background: transparent;
}}

QLabel#title {{
    font-family: {Fonts.FAMILY_DISPLAY};
    font-size: {Fonts.SIZE_HERO}px;
    font-weight: bold;
    color: {Colors.TEXT_PRIMARY};
}}

QLabel#subtitle {{
    font-size: {Fonts.SIZE_H2}px;
    color: {Colors.TEXT_SECONDARY};
}}

QLabel#section-header {{
    font-family: {Fonts.FAMILY_DISPLAY};
    font-size: {Fonts.SIZE_H3}px;
    font-weight: bold;
    color: {Colors.TEXT_PRIMARY};
    padding: {Spacing.SM}px 0;
}}

QLabel#muted {{
    color: {Colors.TEXT_MUTED};
    font-size: {Fonts.SIZE_SMALL}px;
}}

/* ==========================================================================
   BUTTONS
   ========================================================================== */

QPushButton {{
    background-color: {Colors.BG_LIGHT};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER_DEFAULT};
    border-radius: {Spacing.RADIUS_MD}px;
    padding: {Spacing.MD}px {Spacing.LG}px;
    font-size: {Fonts.SIZE_BODY}px;
    font-weight: 500;
    min-height: 20px;
}}

QPushButton:hover {{
    background-color: {Colors.BG_HOVER};
    border-color: {Colors.BORDER_HOVER};
}}

QPushButton:pressed {{
    background-color: {Colors.BG_MEDIUM};
}}

QPushButton:disabled {{
    background-color: {Colors.BG_DARK};
    color: {Colors.TEXT_DISABLED};
    border-color: {Colors.BG_MEDIUM};
}}

QPushButton#primary {{
    background: {Colors.GRADIENT_PRIMARY};
    border: none;
    color: {Colors.TEXT_PRIMARY};
    font-weight: bold;
}}

QPushButton#primary:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00E5FF, stop:1 #FF1AE8);
}}

QPushButton#primary:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00C4DB, stop:1 #DB00C4);
}}

QPushButton#danger {{
    background-color: {Colors.NEON_RED};
    border: none;
}}

QPushButton#success {{
    background: {Colors.GRADIENT_SUCCESS};
    border: none;
}}

/* Sidebar navigation buttons */
QPushButton#nav-button {{
    background: transparent;
    border: none;
    border-radius: {Spacing.RADIUS_MD}px;
    padding: {Spacing.MD}px;
    text-align: left;
}}

QPushButton#nav-button:hover {{
    background-color: {Colors.BG_LIGHT};
}}

QPushButton#nav-button:checked {{
    background: {Colors.GRADIENT_PRIMARY};
}}

/* ==========================================================================
   INPUTS
   ========================================================================== */

QLineEdit {{
    background-color: {Colors.BG_LIGHT};
    color: {Colors.TEXT_PRIMARY};
    border: 2px solid {Colors.BORDER_DEFAULT};
    border-radius: {Spacing.RADIUS_MD}px;
    padding: {Spacing.MD}px {Spacing.LG}px;
    font-size: {Fonts.SIZE_BODY}px;
    selection-background-color: {Colors.NEON_CYAN};
}}

QLineEdit:hover {{
    border-color: {Colors.BORDER_HOVER};
}}

QLineEdit:focus {{
    border-color: {Colors.NEON_CYAN};
}}

QLineEdit:disabled {{
    background-color: {Colors.BG_DARK};
    color: {Colors.TEXT_DISABLED};
}}

/* Placeholder text */
QLineEdit[echoMode="2"] {{
    lineedit-password-character: 9679;
}}

/* ==========================================================================
   SPINBOXES
   ========================================================================== */

QSpinBox, QDoubleSpinBox {{
    background-color: {Colors.BG_LIGHT};
    color: {Colors.TEXT_PRIMARY};
    border: 2px solid {Colors.BORDER_DEFAULT};
    border-radius: {Spacing.RADIUS_MD}px;
    padding: {Spacing.SM}px {Spacing.MD}px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {Colors.NEON_CYAN};
}}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background-color: {Colors.BG_HOVER};
    border: none;
    width: 20px;
}}

/* ==========================================================================
   CHECKBOXES & RADIO BUTTONS
   ========================================================================== */

QCheckBox, QRadioButton {{
    color: {Colors.TEXT_PRIMARY};
    spacing: {Spacing.SM}px;
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 20px;
    height: 20px;
    border: 2px solid {Colors.BORDER_DEFAULT};
    background-color: {Colors.BG_LIGHT};
}}

QCheckBox::indicator {{
    border-radius: {Spacing.RADIUS_SM}px;
}}

QRadioButton::indicator {{
    border-radius: 10px;
}}

QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {Colors.NEON_CYAN};
}}

QCheckBox::indicator:checked {{
    background-color: {Colors.NEON_CYAN};
    border-color: {Colors.NEON_CYAN};
}}

QRadioButton::indicator:checked {{
    background-color: {Colors.NEON_CYAN};
    border-color: {Colors.NEON_CYAN};
}}

/* ==========================================================================
   PROGRESS BARS
   ========================================================================== */

QProgressBar {{
    background-color: {Colors.BG_LIGHT};
    border: none;
    border-radius: {Spacing.RADIUS_SM}px;
    text-align: center;
    color: {Colors.TEXT_PRIMARY};
    font-weight: bold;
    font-size: {Fonts.SIZE_SMALL}px;
    min-height: 20px;
}}

QProgressBar::chunk {{
    background: {Colors.GRADIENT_PRIMARY};
    border-radius: {Spacing.RADIUS_SM}px;
}}

/* ==========================================================================
   SCROLL AREAS & LISTS
   ========================================================================== */

QScrollArea {{
    background-color: transparent;
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

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

QListWidget::item:selected {{
    background: {Colors.GRADIENT_PRIMARY};
}}

/* ==========================================================================
   SCROLLBARS
   ========================================================================== */

QScrollBar:vertical {{
    background-color: {Colors.BG_DARK};
    width: 12px;
    border-radius: 6px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {Colors.BG_HOVER};
    border-radius: 6px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {Colors.NEON_CYAN};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {Colors.BG_DARK};
    height: 12px;
    border-radius: 6px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background-color: {Colors.BG_HOVER};
    border-radius: 6px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {Colors.NEON_CYAN};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ==========================================================================
   FRAMES & CARDS
   ========================================================================== */

QFrame#card {{
    background-color: {Colors.BG_MEDIUM};
    border: 1px solid {Colors.BORDER_DEFAULT};
    border-radius: {Spacing.RADIUS_LG}px;
}}

QFrame#glass-card {{
    background-color: rgba(26, 26, 37, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: {Spacing.RADIUS_LG}px;
}}

/* ==========================================================================
   TAB WIDGET
   ========================================================================== */

QTabWidget::pane {{
    background-color: {Colors.BG_DARK};
    border: none;
}}

QTabBar::tab {{
    background-color: {Colors.BG_MEDIUM};
    color: {Colors.TEXT_SECONDARY};
    padding: {Spacing.MD}px {Spacing.XL}px;
    border: none;
    border-top-left-radius: {Spacing.RADIUS_MD}px;
    border-top-right-radius: {Spacing.RADIUS_MD}px;
    margin-right: 2px;
}}

QTabBar::tab:hover {{
    background-color: {Colors.BG_HOVER};
    color: {Colors.TEXT_PRIMARY};
}}

QTabBar::tab:selected {{
    background: {Colors.GRADIENT_PRIMARY};
    color: {Colors.TEXT_PRIMARY};
}}

/* ==========================================================================
   SLIDERS
   ========================================================================== */

QSlider::groove:horizontal {{
    background-color: {Colors.BG_LIGHT};
    height: 8px;
    border-radius: 4px;
}}

QSlider::handle:horizontal {{
    background: {Colors.GRADIENT_PRIMARY};
    width: 20px;
    height: 20px;
    margin: -6px 0;
    border-radius: 10px;
}}

QSlider::handle:horizontal:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00E5FF, stop:1 #FF1AE8);
}}

QSlider::sub-page:horizontal {{
    background: {Colors.GRADIENT_PRIMARY};
    border-radius: 4px;
}}

/* ==========================================================================
   COMBOBOXES
   ========================================================================== */

QComboBox {{
    background-color: {Colors.BG_LIGHT};
    color: {Colors.TEXT_PRIMARY};
    border: 2px solid {Colors.BORDER_DEFAULT};
    border-radius: {Spacing.RADIUS_MD}px;
    padding: {Spacing.SM}px {Spacing.MD}px;
    min-height: 20px;
}}

QComboBox:hover {{
    border-color: {Colors.BORDER_HOVER};
}}

QComboBox:focus {{
    border-color: {Colors.NEON_CYAN};
}}

QComboBox::drop-down {{
    border: none;
    width: 30px;
}}

QComboBox QAbstractItemView {{
    background-color: {Colors.BG_MEDIUM};
    border: 1px solid {Colors.BORDER_DEFAULT};
    border-radius: {Spacing.RADIUS_MD}px;
    selection-background-color: {Colors.NEON_CYAN};
}}

/* ==========================================================================
   TOOLTIPS
   ========================================================================== */

QToolTip {{
    background-color: {Colors.BG_MEDIUM};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.NEON_CYAN};
    border-radius: {Spacing.RADIUS_SM}px;
    padding: {Spacing.SM}px {Spacing.MD}px;
}}

/* ==========================================================================
   MESSAGE BOX
   ========================================================================== */

QMessageBox {{
    background-color: {Colors.BG_DARK};
}}

QMessageBox QLabel {{
    color: {Colors.TEXT_PRIMARY};
}}

QMessageBox QPushButton {{
    min-width: 80px;
}}
"""
