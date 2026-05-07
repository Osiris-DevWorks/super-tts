"""Settings tab — manages the .env file at %APPDATA%\\Osiris DevWorks\\Super TTS\\.env
plus the persisted theme choice.

Sensitive values (DISCORD_TOKEN, DATABASE_URL) are stored in the .env file,
not the registry. The theme choice is persisted via QSettings so it survives
.env edits and Windows roaming profiles.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
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


_THEME_CHOICES = (
    (gui_theme.THEME_ODW, "Osiris DevWorks (default)"),
    (gui_theme.THEME_SCLE, "Cyan Citizen"),
    (gui_theme.THEME_DARK, "Dark"),
    (gui_theme.THEME_LIGHT, "Light"),
)


# Per-field help strings shown in "?" badge tooltips. Tooltips render rich
# text (HTML) and auto-wrap; URLs aren't clickable inside a tooltip but the
# user can copy them. Keep these short — the Help tab is the long-form
# walkthrough.
_TOKEN_HELP = (
    "<p>Bot token from the Discord Developer Portal "
    "(<b>discord.com/developers/applications</b>).</p>"
    "<p>Under the <b>Bot</b> tab, enable <b>Message Content Intent</b>, "
    "<b>Server Members Intent</b>, and <b>Voice States Intent</b> before "
    "copying the token. See the <b>Help</b> tab for the full walkthrough.</p>"
)
_DB_URL_HELP = (
    "<p>PostgreSQL connection URL the bot uses for state (monitored "
    "channels, user preferences, voice claims).</p>"
    "<p>Pre-filled with the bundled default — leave it as is unless "
    "you've been told otherwise.</p>"
)
_OWNER_HELP = (
    "<p>Your Discord user ID. Required for admin slash commands "
    "(<code>/tts admin-voice ...</code>) to recognize you as the bot's owner.</p>"
    "<p>To copy it: User Settings → Advanced → enable Developer Mode, "
    "then right-click your name in any channel → Copy User ID.</p>"
)
_HF_HELP = (
    "<p>Optional. Only needed if HuggingFace rate-limits the first-run "
    "Supertonic model download (~1–2 GB).</p>"
    "<p>Get a read-only token at <b>huggingface.co/settings/tokens</b>.</p>"
)
_DEVICE_HELP = (
    "<p><b>auto</b>: let Supertonic pick — recommended.</p>"
    "<p><b>cuda</b>: force NVIDIA GPU — much faster, requires a "
    "CUDA-capable card and onnxruntime-gpu installed.</p>"
    "<p><b>cpu</b>: force CPU — works anywhere, slower.</p>"
)


def _help_badge(tooltip_html: str) -> QLabel:
    """Small "?" indicator that surfaces helper text on hover. Uses a
    semi-transparent gray background so it reads on every theme without
    needing a per-theme stylesheet refresh."""
    badge = QLabel("?")
    badge.setToolTip(tooltip_html)
    badge.setCursor(QCursor(Qt.CursorShape.WhatsThisCursor))
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setFixedSize(18, 18)
    badge.setStyleSheet(
        "QLabel {"
        " border-radius: 9px;"
        " background-color: rgba(127, 127, 127, 0.25);"
        " color: palette(window-text);"
        " font-weight: bold;"
        " font-size: 11px;"
        "}"
        "QLabel:hover { background-color: rgba(127, 127, 127, 0.45); }"
    )
    return badge


class SettingsTab(QWidget):
    """Edit Discord token, DB URL, owner ID, HF token, TTS device, and theme.

    Log level lives on the Status tab now — it sits next to the live log
    feed and applies without restarting."""

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

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(form.labelAlignment().__class__(0))  # left-align labels

        # Each row packs [field][?][Show] into one widget so the form stays
        # compact. Inline helper labels are gone — their content lives on
        # the "?" badges as tooltips, and the long-form walkthrough lives
        # in the Help tab.

        # ── Discord Token ─────────────────────────────────────────────────
        self._token_edit = QLineEdit()
        self._token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._token_edit.setPlaceholderText("Bot token from the Discord Developer Portal")
        self._token_edit.setMinimumWidth(360)
        self._show_token_btn = self._make_show_button(self._on_token_visibility_toggled)
        form.addRow(
            "Discord Token:",
            _row(self._token_edit, _help_badge(_TOKEN_HELP), self._show_token_btn),
        )

        # ── Database URL ──────────────────────────────────────────────────
        self._db_edit = QLineEdit()
        self._db_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._db_edit.setPlaceholderText("postgresql://user:pass@host.proxy.rlwy.net:port/railway")
        self._show_db_btn = self._make_show_button(self._on_db_visibility_toggled)
        form.addRow(
            "Database URL:",
            _row(self._db_edit, _help_badge(_DB_URL_HELP), self._show_db_btn),
        )

        # ── Owner ID ──────────────────────────────────────────────────────
        self._owner_edit = QLineEdit()
        self._owner_edit.setPlaceholderText("Your Discord user ID (numeric, e.g. 167123456789012345)")
        form.addRow(
            "Owner ID:",
            _row(self._owner_edit, _help_badge(_OWNER_HELP)),
        )

        # ── HuggingFace Token ─────────────────────────────────────────────
        self._hf_edit = QLineEdit()
        self._hf_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._hf_edit.setPlaceholderText("hf_... (optional)")
        self._show_hf_btn = self._make_show_button(self._on_hf_visibility_toggled)
        form.addRow(
            "HuggingFace Token:",
            _row(self._hf_edit, _help_badge(_HF_HELP), self._show_hf_btn),
        )

        # ── TTS Device ────────────────────────────────────────────────────
        self._device_combo = QComboBox()
        for dev in gui_settings.TTS_DEVICE_CHOICES:
            self._device_combo.addItem(dev, userData=dev)
        form.addRow(
            "TTS Device:",
            _row(self._device_combo, _help_badge(_DEVICE_HELP)),
        )

        # ── Theme ─────────────────────────────────────────────────────────
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
        # On first launch (.env missing or empty DATABASE_URL), pre-fill with
        # the bundled default so users don't need to know the Railway URL.
        # They can edit it but typically just leave it.
        self._db_edit.setText(env.get("DATABASE_URL") or gui_settings.DEFAULT_DATABASE_URL)
        self._owner_edit.setText(env.get("OWNER_ID", ""))
        self._hf_edit.setText(env.get("HF_TOKEN", ""))

        device = (env.get("TTS_DEVICE") or gui_settings.DEFAULT_TTS_DEVICE).lower()
        if device not in gui_settings.TTS_DEVICE_CHOICES:
            device = gui_settings.DEFAULT_TTS_DEVICE
        self._device_combo.setCurrentIndex(max(0, self._device_combo.findData(device)))

        # Theme comes from QSettings, not .env — so this stays in sync even
        # if the user hand-edits .env without touching the registry.
        current_theme = gui_settings.get_theme()
        idx = max(0, self._theme_combo.findData(current_theme))
        # Block signals during programmatic set so we don't fire theme_changed.
        self._theme_combo.blockSignals(True)
        self._theme_combo.setCurrentIndex(idx)
        self._theme_combo.blockSignals(False)

        # Clear any prior save/load status so the panel starts clean.
        self._status_label.setText("")

    def _save(self):
        token = self._token_edit.text().strip()
        db_url = self._db_edit.text().strip()
        owner_id = self._owner_edit.text().strip()
        hf_token = self._hf_edit.text().strip()
        tts_device = self._device_combo.currentData() or gui_settings.DEFAULT_TTS_DEVICE

        if not token:
            QMessageBox.warning(
                self,
                "Discord Token required",
                "A Discord bot token is required for the bot to log in. "
                "Get one from https://discord.com/developers/applications.",
            )
            return

        if owner_id and not owner_id.isdigit():
            QMessageBox.warning(
                self,
                "Owner ID must be numeric",
                "Discord user IDs are 17–19 digit numbers (e.g. 167123456789012345). "
                "Enable Developer Mode in Discord and right-click your name to copy it.",
            )
            return

        # Only persist OWNER_ID / HF_TOKEN when the user actually filled
        # them in — empty entries shouldn't clobber any value already in
        # .env via direct edit. LOG_LEVEL is owned by the Status tab now,
        # so we preserve whatever was there rather than rewriting it.
        existing = gui_settings.read_env()
        values: dict[str, str] = {
            "DISCORD_TOKEN": token,
            "DATABASE_URL": db_url,
            "TTS_DEVICE": tts_device,
        }
        if existing.get("LOG_LEVEL"):
            values["LOG_LEVEL"] = existing["LOG_LEVEL"]
        if owner_id:
            values["OWNER_ID"] = owner_id
        if hf_token:
            values["HF_TOKEN"] = hf_token

        try:
            gui_settings.write_env(values)
            # Also push into the live process env so that if the user clicks
            # Connect after saving, main.main() picks up the new values.
            gui_settings.apply_env_to_process(values)
        except OSError as e:
            QMessageBox.critical(self, "Save failed", f"Could not write .env file: {e}")
            return

        self._status_label.setText(
            "Saved. Restart Super TTS to apply token, owner ID, and device changes."
        )

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

    def _on_hf_visibility_toggled(self, checked: bool):
        self._hf_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        self._show_hf_btn.setText("Hide" if checked else "Show")

    def _on_theme_picked(self):
        theme = self._theme_combo.currentData()
        if theme:
            gui_settings.set_theme(theme)
            self.theme_changed.emit(theme)

    # ── Small factories ──────────────────────────────────────────────────

    def _make_show_button(self, slot) -> QPushButton:
        """Standard checkable Show/Hide button used by every masked field."""
        btn = QPushButton("Show")
        btn.setCheckable(True)
        btn.setMaximumWidth(80)
        btn.toggled.connect(slot)
        return btn


def _row(*widgets: QWidget) -> QWidget:
    """Pack widgets horizontally into a single column-1 widget for QFormLayout.

    First widget stretches (it's the input), badges and buttons sit at their
    natural width on the right. QFormLayout's column 1 only takes a QWidget,
    so the QHBoxLayout has to be wrapped."""
    box = QHBoxLayout()
    box.setContentsMargins(0, 0, 0, 0)
    box.setSpacing(8)
    for i, w in enumerate(widgets):
        # First widget = the input; give it stretch=1 so it absorbs free space.
        box.addWidget(w, 1 if i == 0 else 0)
    container = QWidget()
    container.setLayout(box)
    return container
