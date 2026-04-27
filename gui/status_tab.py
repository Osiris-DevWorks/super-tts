"""Status tab — shows whether the bot is connected, with a Connect/Disconnect
button. Auto-connects on launch when a token is configured."""
from __future__ import annotations

import logging
import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gui import theme as gui_theme
from gui.bot_runner import BotRunner

logger = logging.getLogger(__name__)


class StatusTab(QWidget):
    """Connection status + start/stop control."""

    def __init__(self):
        super().__init__()
        self._runner: BotRunner | None = None
        # Tracks whether the bot has ever been started in this process.
        # discord.py Bot instances can only be start()ed once; once stopped,
        # reconnect requires an app relaunch.
        self._has_run = False
        self._setup_ui()
        self._refresh_state()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        # Big status indicator: dot + label
        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        self._dot = QLabel("●")
        self._dot.setFont(QFont("Segoe UI", 20))
        self._dot.setStyleSheet(self._dot_qss(connected=False, error=False))
        status_row.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)

        self._status_label = QLabel("Disconnected")
        f = QFont()
        f.setPointSize(16)
        f.setBold(True)
        self._status_label.setFont(f)
        status_row.addWidget(self._status_label, 0, Qt.AlignmentFlag.AlignVCenter)
        status_row.addStretch()
        layout.addLayout(status_row)

        self._detail_label = QLabel("Bot is not running.")
        self._detail_label.setProperty("role", "secondary")
        self._detail_label.setWordWrap(True)
        layout.addWidget(self._detail_label)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # Action button row
        btn_row = QHBoxLayout()
        self._action_btn = QPushButton("Connect")
        self._action_btn.setMinimumHeight(32)
        self._action_btn.setMinimumWidth(140)
        self._action_btn.clicked.connect(self._on_action_clicked)
        btn_row.addWidget(self._action_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._reconnect_note = QLabel(
            "After disconnecting, restart Super TTS to reconnect "
            "(discord.py limitation: a Bot instance can only start once)."
        )
        self._reconnect_note.setProperty("role", "secondary")
        self._reconnect_note.setWordWrap(True)
        self._reconnect_note.setVisible(False)
        layout.addWidget(self._reconnect_note)

        layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

    # ── State helpers ────────────────────────────────────────────────────

    def _dot_qss(self, *, connected: bool, error: bool) -> str:
        if error:
            color = gui_theme.get_status_err_color()
        elif connected:
            color = gui_theme.get_status_ok_color()
        else:
            color = "#7A7D87"  # neutral gray
        return f"color: {color};"

    def _refresh_state(self):
        """Sync button label + status text to current runner state."""
        running = self._runner is not None and self._runner.isRunning()
        token_configured = bool(os.getenv("DISCORD_TOKEN"))
        self._reconnect_note.setVisible(self._has_run and not running)

        if running:
            self._action_btn.setText("Disconnect")
            self._action_btn.setEnabled(True)
            return

        if not token_configured:
            self._action_btn.setText("Connect")
            self._action_btn.setEnabled(False)
            self._set_status("No token", "Enter a Discord bot token in the Settings tab.", error=True)
            return

        if self._has_run:
            # Already started once this session; disable re-connect.
            self._action_btn.setText("Reconnect (relaunch required)")
            self._action_btn.setEnabled(False)
            return

        self._action_btn.setText("Connect")
        self._action_btn.setEnabled(True)

    def _set_status(self, headline: str, detail: str, *, connected: bool = False, error: bool = False):
        self._status_label.setText(headline)
        self._detail_label.setText(detail)
        self._dot.setStyleSheet(self._dot_qss(connected=connected, error=error))

    # ── Public API ───────────────────────────────────────────────────────

    def auto_connect_if_ready(self):
        """Called once on app launch — connect if a token is configured."""
        if os.getenv("DISCORD_TOKEN") and not self._has_run:
            self._start_bot()

    def on_theme_changed(self):
        """Reapply theme-aware colors. Called by MainWindow after a theme swap."""
        running = self._runner is not None and self._runner.isRunning()
        connected = running and self._has_run  # crude, but fine
        # Re-render the dot color in the new palette
        self._dot.setStyleSheet(self._dot_qss(connected=connected, error=False))

    def shutdown(self):
        """Called from MainWindow.closeEvent to stop the bot cleanly."""
        if self._runner and self._runner.isRunning():
            self._runner.request_stop()
            # Give it up to ~5s to unwind before we yank the thread.
            if not self._runner.wait(5000):
                logger.warning("BotRunner did not stop in time; terminating")
                self._runner.terminate()
                self._runner.wait(1000)

    # ── Slots ────────────────────────────────────────────────────────────

    def _on_action_clicked(self):
        if self._runner and self._runner.isRunning():
            self._stop_bot()
        else:
            self._start_bot()

    def _start_bot(self):
        if self._runner and self._runner.isRunning():
            return
        self._has_run = True
        self._runner = BotRunner()
        self._runner.starting.connect(self._on_starting)
        self._runner.ready.connect(self._on_ready)
        self._runner.error.connect(self._on_error)
        self._runner.finished_clean.connect(self._on_finished)
        self._runner.start()
        self._refresh_state()

    def _stop_bot(self):
        if not self._runner:
            return
        self._set_status("Disconnecting…", "Closing bot connection.", connected=False)
        self._action_btn.setEnabled(False)
        self._runner.request_stop()

    def _on_starting(self):
        self._set_status(
            "Connecting…",
            "Running migrations and connecting to Discord.",
            connected=False,
        )

    def _on_ready(self, user_name: str, guild_count: int):
        guild_word = "guild" if guild_count == 1 else "guilds"
        self._set_status(
            "Connected",
            f"Logged in as {user_name} — in {guild_count} {guild_word}.",
            connected=True,
        )
        self._refresh_state()

    def _on_error(self, msg: str):
        self._set_status("Error", f"Bot crashed: {msg}", error=True)
        self._refresh_state()

    def _on_finished(self):
        if self._status_label.text() not in ("Error",):
            self._set_status(
                "Disconnected",
                "Bot stopped. Restart Super TTS to reconnect.",
                connected=False,
            )
        self._refresh_state()
