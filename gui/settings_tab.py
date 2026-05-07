"""Settings tab — manages the .env file at %APPDATA%\\Osiris DevWorks\\Super TTS\\.env
plus the persisted theme choice.

Sensitive values (DISCORD_TOKEN, DATABASE_URL) are stored in the .env file,
not the registry. The theme choice is persisted via QSettings so it survives
.env edits and Windows roaming profiles.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, pyqtSignal
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

        # First-run helper — points at the Discord Developer Portal for the
        # most common "where do I get a token?" question.
        token_help = QLabel(
            'Need a token? Create a Discord application at '
            '<a href="https://discord.com/developers/applications">'
            'discord.com/developers/applications</a>, enable the '
            '<b>Message Content</b>, <b>Server Members</b>, and '
            '<b>Voice States</b> intents under the Bot tab, then copy the token.'
        )
        token_help.setWordWrap(True)
        token_help.setOpenExternalLinks(True)
        token_help.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        outer.addWidget(token_help)

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

        # Discord owner ID — gates admin-only commands. Without it set,
        # admin commands fall back to checking for a role literally named
        # "Admin". Numeric Discord user ID, e.g. 167123456789012345.
        self._owner_edit = QLineEdit()
        self._owner_edit.setPlaceholderText("Your Discord user ID (numeric, e.g. 167123456789012345)")
        form.addRow("Owner ID:", self._owner_edit)

        owner_help = QLabel(
            "Your Discord user ID. In Discord: User Settings → Advanced → "
            "enable Developer Mode, then right-click your name → Copy User ID."
        )
        owner_help.setWordWrap(True)
        owner_help.setProperty("role", "secondary")
        form.addRow("", owner_help)

        # HuggingFace token — optional, used to avoid anonymous rate limits
        # when supertonic downloads its ONNX model on first run.
        self._hf_edit = QLineEdit()
        self._hf_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._hf_edit.setPlaceholderText("hf_... (optional)")
        form.addRow("HuggingFace Token:", self._hf_edit)

        hf_btns = QHBoxLayout()
        self._show_hf_btn = QPushButton("Show")
        self._show_hf_btn.setCheckable(True)
        self._show_hf_btn.setMaximumWidth(80)
        self._show_hf_btn.toggled.connect(self._on_hf_visibility_toggled)
        hf_btns.addWidget(self._show_hf_btn)
        hf_btns.addStretch()
        form.addRow("", _wrap_layout(hf_btns))

        hf_help = QLabel(
            'Optional — only needed if HuggingFace rate-limits the first-run '
            'model download. Create one at '
            '<a href="https://huggingface.co/settings/tokens">'
            'huggingface.co/settings/tokens</a> (read-only is fine).'
        )
        hf_help.setWordWrap(True)
        hf_help.setOpenExternalLinks(True)
        hf_help.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        hf_help.setProperty("role", "secondary")
        form.addRow("", hf_help)

        # TTS device — auto/cpu/cuda. Lets a user with a CUDA-capable GPU
        # flip on hardware acceleration without editing config/config.yaml.
        self._device_combo = QComboBox()
        for dev in gui_settings.TTS_DEVICE_CHOICES:
            self._device_combo.addItem(dev, userData=dev)
        form.addRow("TTS Device:", self._device_combo)

        device_help = QLabel(
            "<b>auto</b>: let Supertonic pick (recommended). "
            "<b>cuda</b>: force NVIDIA GPU — much faster, requires a CUDA-capable card. "
            "<b>cpu</b>: force CPU — works anywhere, slower."
        )
        device_help.setWordWrap(True)
        device_help.setProperty("role", "secondary")
        form.addRow("", device_help)

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

        log_level = (env.get("LOG_LEVEL") or gui_settings.DEFAULT_LOG_LEVEL).upper()
        idx = max(
            0,
            self._log_combo.findData(
                log_level if log_level in _LOG_LEVELS else gui_settings.DEFAULT_LOG_LEVEL
            ),
        )
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
        owner_id = self._owner_edit.text().strip()
        hf_token = self._hf_edit.text().strip()
        tts_device = self._device_combo.currentData() or gui_settings.DEFAULT_TTS_DEVICE
        log_level = self._log_combo.currentData() or "INFO"

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
        # .env via direct edit.
        values: dict[str, str] = {
            "DISCORD_TOKEN": token,
            "DATABASE_URL": db_url,
            "LOG_LEVEL": log_level,
            "TTS_DEVICE": tts_device,
        }
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


def _wrap_layout(layout) -> QWidget:
    """QFormLayout doesn't take a layout in column 1 directly — wrap it."""
    w = QWidget()
    w.setLayout(layout)
    return w
