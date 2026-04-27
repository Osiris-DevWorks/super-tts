"""Application theme management.

Adapted from `smart-citizen/src/gui/theme.py` — same 4-theme palette pattern
(LIGHT / DARK / SCLE navy / ODW gold) with ODW promoted to default since
this is the Osiris DevWorks-branded entry point. Theme is applied by
swapping the QApplication palette; widgets that need dim "secondary" text
mark themselves with `setProperty("role", "secondary")` and an app-level
QSS rule recolors them on theme change.
"""
import logging
import sys
from pathlib import Path

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication, QProxyStyle, QStyle

from gui import settings as gui_settings

logger = logging.getLogger(__name__)


THEME_LIGHT = "light"
THEME_DARK = "dark"
THEME_SCLE = "scle"
THEME_ODW = "odw"
AVAILABLE_THEMES = (THEME_LIGHT, THEME_DARK, THEME_SCLE, THEME_ODW)
# Default to the Osiris DevWorks palette — this is the ODW-branded build.
DEFAULT_THEME = THEME_ODW

# Secondary text (per theme) — used by the QSS rule installed by apply_theme
# for any QLabel with `role=secondary`. A single shade can't stay readable
# across a 200-gray light window and a 13,24,38 navy window.
_SECONDARY_TEXT_COLORS = {
    THEME_LIGHT: "#2A2A2A",
    THEME_DARK: "#D5D5D5",
    THEME_SCLE: "#D5D5D5",
    THEME_ODW: "#D4B876",
}


# Title and tagline accent colors per theme — used on the branded label at
# the top of the main window so the header reads as "of" the active theme.
_TITLE_COLORS = {
    THEME_LIGHT: "#1565C0",
    THEME_DARK: "#64B5F6",
    THEME_SCLE: "#4FD7E8",
    THEME_ODW: "#C9A961",
}

_TAGLINE_COLORS = {
    THEME_LIGHT: "#555555",
    THEME_DARK: "#A0A0A0",
    THEME_SCLE: "#6FB5D0",
    THEME_ODW: "#A08C5A",
}


def get_title_color(theme: str | None = None) -> str:
    theme = theme or gui_settings.get_theme()
    return _TITLE_COLORS.get(theme, _TITLE_COLORS[DEFAULT_THEME])


def get_tagline_color(theme: str | None = None) -> str:
    theme = theme or gui_settings.get_theme()
    return _TAGLINE_COLORS.get(theme, _TAGLINE_COLORS[DEFAULT_THEME])


# Connection status colors — the Status tab renders the connection dot in
# these. Picked per-theme so the indicator pops without clashing.
_STATUS_OK_COLORS = {
    THEME_LIGHT: "#2E7D32",
    THEME_DARK: "#66BB6A",
    THEME_SCLE: "#4ADE80",
    THEME_ODW: "#A5B989",
}

_STATUS_ERR_COLORS = {
    THEME_LIGHT: "#C62828",
    THEME_DARK: "#EF5350",
    THEME_SCLE: "#FF8A42",
    THEME_ODW: "#C77A4D",
}


def get_status_ok_color(theme: str | None = None) -> str:
    theme = theme or gui_settings.get_theme()
    return _STATUS_OK_COLORS.get(theme, _STATUS_OK_COLORS[DEFAULT_THEME])


def get_status_err_color(theme: str | None = None) -> str:
    theme = theme or gui_settings.get_theme()
    return _STATUS_ERR_COLORS.get(theme, _STATUS_ERR_COLORS[DEFAULT_THEME])


def _light_palette() -> QPalette:
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor(200, 200, 200))
    p.setColor(QPalette.ColorRole.WindowText, QColor(25, 25, 25))
    p.setColor(QPalette.ColorRole.Base, QColor(215, 215, 215))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor(208, 208, 208))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor(240, 240, 218))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor(25, 25, 25))
    p.setColor(QPalette.ColorRole.Text, QColor(25, 25, 25))
    p.setColor(QPalette.ColorRole.Button, QColor(200, 200, 200))
    p.setColor(QPalette.ColorRole.ButtonText, QColor(25, 25, 25))
    p.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    p.setColor(QPalette.ColorRole.Highlight, QColor(21, 101, 192))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.Link, QColor(0, 102, 204))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(90, 90, 90))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(100, 100, 100))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(100, 100, 100))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(100, 100, 100))
    return p


def _dark_palette() -> QPalette:
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    p.setColor(QPalette.ColorRole.WindowText, QColor(232, 232, 232))
    p.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 48))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor(45, 45, 48))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor(232, 232, 232))
    p.setColor(QPalette.ColorRole.Text, QColor(232, 232, 232))
    p.setColor(QPalette.ColorRole.Button, QColor(55, 55, 58))
    p.setColor(QPalette.ColorRole.ButtonText, QColor(232, 232, 232))
    p.setColor(QPalette.ColorRole.BrightText, QColor(255, 80, 80))
    p.setColor(QPalette.ColorRole.Highlight, QColor(59, 130, 246))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.Link, QColor(100, 170, 255))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(175, 175, 175))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(150, 150, 150))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(150, 150, 150))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(150, 150, 150))
    return p


def _scle_palette() -> QPalette:
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor(13, 24, 38))
    p.setColor(QPalette.ColorRole.WindowText, QColor(216, 232, 240))
    p.setColor(QPalette.ColorRole.Base, QColor(13, 24, 38))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor(21, 37, 56))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor(21, 37, 56))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor(216, 232, 240))
    p.setColor(QPalette.ColorRole.Text, QColor(216, 232, 240))
    p.setColor(QPalette.ColorRole.Button, QColor(26, 45, 68))
    p.setColor(QPalette.ColorRole.ButtonText, QColor(216, 232, 240))
    p.setColor(QPalette.ColorRole.BrightText, QColor(255, 138, 66))
    p.setColor(QPalette.ColorRole.Highlight, QColor(0, 153, 204))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(10, 18, 32))
    p.setColor(QPalette.ColorRole.Link, QColor(79, 215, 232))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(111, 181, 208))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(88, 120, 144))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(88, 120, 144))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(88, 120, 144))
    return p


def _odw_palette() -> QPalette:
    """Osiris DevWorks branded palette — navy charcoal + antique gold."""
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor(26, 31, 46))
    p.setColor(QPalette.ColorRole.WindowText, QColor(240, 230, 207))
    p.setColor(QPalette.ColorRole.Base, QColor(26, 31, 46))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor(36, 41, 56))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor(36, 41, 56))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor(240, 230, 207))
    p.setColor(QPalette.ColorRole.Text, QColor(240, 230, 207))
    p.setColor(QPalette.ColorRole.Button, QColor(36, 41, 56))
    p.setColor(QPalette.ColorRole.ButtonText, QColor(240, 230, 207))
    p.setColor(QPalette.ColorRole.BrightText, QColor(199, 122, 77))
    p.setColor(QPalette.ColorRole.Highlight, QColor(212, 160, 23))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(26, 31, 46))
    p.setColor(QPalette.ColorRole.Link, QColor(212, 184, 118))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(160, 140, 90))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(100, 90, 70))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(100, 90, 70))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(100, 90, 70))
    return p


def _palette_for(theme: str) -> QPalette:
    if theme == THEME_DARK:
        return _dark_palette()
    if theme == THEME_SCLE:
        return _scle_palette()
    if theme == THEME_ODW:
        return _odw_palette()
    return _light_palette()


def _app_stylesheet_for(theme: str) -> str:
    secondary = _SECONDARY_TEXT_COLORS.get(theme, _SECONDARY_TEXT_COLORS[DEFAULT_THEME])
    return f'QLabel[role="secondary"] {{ color: {secondary}; }}'


# Tooltip wake-up tuning — see the smart-citizen variant for the rationale.
_TOOLTIP_WAKE_UP_DELAY_MS = 800
_TOOLTIP_FALL_ASLEEP_DELAY_MS = 0


class _SuperTTSProxyStyle(QProxyStyle):
    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.StyleHint.SH_ToolTip_WakeUpDelay:
            return _TOOLTIP_WAKE_UP_DELAY_MS
        if hint == QStyle.StyleHint.SH_ToolTip_FallAsleepDelay:
            return _TOOLTIP_FALL_ASLEEP_DELAY_MS
        return super().styleHint(hint, option, widget, returnData)


def apply_theme(app: QApplication, theme: str) -> None:
    """Apply the named theme to the application."""
    if theme not in AVAILABLE_THEMES:
        logger.warning(f"Unknown theme {theme!r}; using {DEFAULT_THEME}")
        theme = DEFAULT_THEME

    current_delay = app.style().styleHint(QStyle.StyleHint.SH_ToolTip_WakeUpDelay)
    if current_delay != _TOOLTIP_WAKE_UP_DELAY_MS:
        app.setStyle(_SuperTTSProxyStyle("Fusion"))
    app.setPalette(_palette_for(theme))
    app.setStyleSheet(_app_stylesheet_for(theme))
    logger.info(f"Applied theme: {theme}")
