"""Settings tab — manages the .env file at %APPDATA%\\Osiris DevWorks\\Super TTS\\.env
plus the persisted theme choice.

Sensitive values (DISCORD_TOKEN, DATABASE_URL) are stored in the .env file,
not the registry. The theme choice is persisted via QSettings so it survives
.env edits and Windows roaming profiles.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from gui import settings as gui_settings
from gui import theme as gui_theme

logger = logging.getLogger(__name__)


_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
_THEME_CHOICES = (
    (gui_theme.THEME_ODW, "Osiris DevWorks (default)"),
    (gui_theme.THEME_SCLE, "SC Localization Editor (navy + cyan)"),
    (gui_theme.THEME_DARK, "Dark"),
    (gui_theme.THEME_LIGHT, "Light"),
)


class SettingsTab(QWidget):
    """Edit Discord token, DB URL, log level, and UI theme."""

    # Emitted with the new theme key when the user picks a theme. The main
    # window listens and calls gui_theme.apply_theme() so swap is live.
    theme_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        intro = QLabel(
            "Configuration is stored at "
            "<code>%APPDATA%\\Osiris DevWorks\\Super TTS\\.env</code>. "
            "Changes apply on the next launch — for the token in particular, "
            "save here and then restart Super TTS."
        )
        intro.setWordWrap(True)
        intro.setProperty("role", "secondary")
        outer.addWidget(intro)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(form.labelAlignment().__class__(0))  # left-align labels

        self._token_edit = QLineEdit()
        self._token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._token_edit.setPlaceholderText("Bot token from the Discord Developer Portal")
        self._token_edit.setMinimumWidth(360)
        form.addRow("Discord Token:", self._token_edit)

        # "Show" toggle for the token — convenient for users sanity-checking
        # what they pasted. Defaults to masked.
        token_btns = QHBoxLayout()
        self._show_token_btn = QPushButton("Show")
        self._show_token_btn.setCheckable(True)
        self._show_token_btn.setMaximumWidth(80)
        self._show_token_btn.toggled.connect(self._on_token_visibility_toggled)
        token_btns.addWidget(self._show_token_btn)
        token_btns.addStretch()
        form.addRow("", _wrap_layout(token_btns))

        self._db_edit = QLineEdit()
        self._db_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._db_edit.setPlaceholderText("postgresql://user:pass@host.proxy.rlwy.net:port/railway")
        form.addRow("Database URL:", self._db_edit)

        db_btns = QHBoxLayout()
        self._show_db_btn = QPushButton("Show")
        self._show_db_btn.setCheckable(True)
        self._show_db_btn.setMaximumWidth(80)
        self._show_db_btn.toggled.connect(self._on_db_visibility_toggled)
        db_btns.addWidget(self._show_db_btn)
        db_btns.addStretch()
        form.addRow("", _wrap_layout(db_btns))

        self._log_combo = QComboBox()
        for lvl in _LOG_LEVELS:
            self._log_combo.addItem(lvl, userData=lvl)
        form.addRow("Log Level:", self._log_combo)

        self._theme_combo = QComboBox()
        for key, label in _THEME_CHOICES:
            self._theme_combo.addItem(label, userData=key)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_picked)
        form.addRow("Theme:", self._theme_combo)

        outer.addLayout(form)

        # Action row
        actions = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setMinimumWidth(100)
        save_btn.clicked.connect(self._save)
        actions.addWidget(save_btn)

        reload_btn = QPushButton("Reload from disk")
        reload_btn.setMinimumWidth(140)
        reload_btn.clicked.connect(self._load)
        actions.addWidget(reload_btn)

        actions.addStretch()
        outer.addLayout(actions)

        self._status_label = QLabel("")
        self._status_label.setProperty("role", "secondary")
        outer.addWidget(self._status_label)

        outer.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    # ── Loaders / savers ─────────────────────────────────────────────────

    def _load(self):
        env = gui_settings.read_env()
        self._token_edit.setText(env.get("DISCORD_TOKEN", ""))
        self._db_edit.setText(env.get("DATABASE_URL", ""))

        log_level = env.get("LOG_LEVEL", "INFO").upper()
        idx = max(0, self._log_combo.findData(log_level if log_level in _LOG_LEVELS else "INFO"))
        self._log_combo.setCurrentIndex(idx)

        # Theme comes from QSettings, not .env — so this stays in sync even
        # if the user hand-edits .env without touching the registry.
        current_theme = gui_settings.get_theme()
        idx = max(0, self._theme_combo.findData(current_theme))
        # Block signals during programmatic set so we don't fire theme_changed.
        self._theme_combo.blockSignals(True)
        self._theme_combo.setCurrentIndex(idx)
        self._theme_combo.blockSignals(False)

        self._status_label.setText(f"Loaded from {gui_settings.env_file_path()}.")

    def _save(self):
        token = self._token_edit.text().strip()
        db_url = self._db_edit.text().strip()
        log_level = self._log_combo.currentData() or "INFO"

        if not token:
            QMessageBox.warning(
                self,
                "Discord Token required",
                "A Discord bot token is required for the bot to log in. "
                "Get one from https://discord.com/developers/applications.",
            )
            return

        values = {
            "DISCORD_TOKEN": token,
            "DATABASE_URL": db_url,
            "LOG_LEVEL": log_level,
        }
        try:
            gui_settings.write_env(values)
            # Also push into the live process env so that if the user clicks
            # Connect after saving, main.main() picks up the new token.
            gui_settings.apply_env_to_process(values)
        except OSError as e:
            QMessageBox.critical(self, "Save failed", f"Could not write .env file: {e}")
            return

        self._status_label.setText("Saved. Restart Super TTS to apply token changes.")

    # ── Slots ────────────────────────────────────────────────────────────

    def _on_token_visibility_toggled(self, checked: bool):
        self._token_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        self._show_token_btn.setText("Hide" if checked else "Show")

    def _on_db_visibility_toggled(self, checked: bool):
        self._db_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        self._show_db_btn.setText("Hide" if checked else "Show")

    def _on_theme_picked(self):
        theme = self._theme_combo.currentData()
        if theme:
            gui_settings.set_theme(theme)
            self.theme_changed.emit(theme)


def _wrap_layout(layout) -> QWidget:
    """QFormLayout doesn't take a layout in column 1 directly — wrap it."""
    w = QWidget()
    w.setLayout(layout)
    return w
