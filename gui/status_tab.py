"""Status tab — connection control + live log viewer in one panel.

Merged from the older split Status + Logs tabs. Layout:

  [● status]  [Connect]
  Detail line about current state.
  ─────────────────────────────────────────────────
  [LogView toolbar — incl. Min level display filter]
  [LogView buffer ----------------------------]

LOG_LEVEL (the env var the bot's logging system honors at startup) is not
exposed in the GUI; the LogView's "Min level" is a display-side filter and
covers the common case. Power users wanting DEBUG firehose can set
LOG_LEVEL=DEBUG in %APPDATA%\\Osiris DevWorks\\Super TTS\\.env and relaunch.
"""
from __future__ import annotations

import logging
import os

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui import theme as gui_theme
from gui.bot_runner import BotRunner
from gui.log_view import LogView

logger = logging.getLogger(__name__)


class _ConnectingTrack(QWidget):
    """A glowing line that grows from left → right between the Connect
    button and the status dot.

    UX:
      - idle:        nothing painted.
      - connecting:  line fills from 0 to ~0.85 over ~3s with easing.
                     If the bot reports ready while still filling, we
                     snap forward; if it takes longer, the line waits
                     at 0.85 (a soft "almost there" hold).
      - ready:       line completes to 1.0 in ~250ms, flashes in the
                     connected color, then fades out.
      - error:       same finish animation, in the error color.

    The "progress" pyqtProperty is the fill width as a fraction of the
    widget's pixel width.
    """

    _FILL_DURATION_MS = 3000  # 0 → 0.85
    _HOLD_TARGET = 0.85
    _FINISH_DURATION_MS = 250  # current → 1.0
    _FADE_AFTER_FINISH_MS = 600
    _LEAD_GLOW_PX = 8  # thin halo at the leading edge

    def __init__(self):
        super().__init__()
        self.setFixedHeight(2)
        self.setMinimumWidth(40)
        self._progress = 0.0
        self._line_color = QColor("#FFD15E")  # warm yellow during connecting
        self._opacity = 0.0  # fades in on start, out after finish

        # Phase 1: fill from 0 to 0.85 with ease-out so the line starts
        # quickly and decelerates as it approaches the dot.
        self._fill = QPropertyAnimation(self, b"progress", self)
        self._fill.setDuration(self._FILL_DURATION_MS)
        self._fill.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fill.setEndValue(self._HOLD_TARGET)

        # Phase 2: snap to 1.0 when the bot is ready.
        self._finish = QPropertyAnimation(self, b"progress", self)
        self._finish.setDuration(self._FINISH_DURATION_MS)
        self._finish.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._finish.setEndValue(1.0)
        self._finish.finished.connect(self._on_finish_done)

        # Phase 3: fade the whole strip out so connected state is clean.
        self._fade = QPropertyAnimation(self, b"opacity", self)
        self._fade.setDuration(self._FADE_AFTER_FINISH_MS)
        self._fade.setEndValue(0.0)
        self._fade.setEasingCurve(QEasingCurve.Type.InOutSine)

    # ── Animated properties ──────────────────────────────────────────────

    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, value: float) -> None:
        self._progress = value
        self.update()

    progress = pyqtProperty(float, fget=_get_progress, fset=_set_progress)

    def _get_opacity(self) -> float:
        return self._opacity

    def _set_opacity(self, value: float) -> None:
        self._opacity = max(0.0, min(1.0, value))
        self.update()

    opacity = pyqtProperty(float, fget=_get_opacity, fset=_set_opacity)

    # ── Public API — driven by StatusTab lifecycle ───────────────────────

    def start(self):
        """Begin the fill. Called when the bot enters connecting."""
        self._finish.stop()
        self._fade.stop()
        self._fill.stop()
        self._line_color = QColor(gui_theme.get_title_color())
        self._set_progress(0.0)
        self._set_opacity(1.0)
        self._fill.setStartValue(0.0)
        self._fill.start()

    def finish(self, success: bool = True):
        """Snap the fill to 1.0, flash in the connected/error color, fade."""
        if self._fill.state() == QPropertyAnimation.State.Stopped and self._opacity == 0:
            return
        self._fill.stop()
        self._line_color = QColor(
            gui_theme.get_status_ok_color() if success else gui_theme.get_status_err_color()
        )
        self._finish.stop()
        self._finish.setStartValue(self._progress)
        self._finish.start()

    def clear(self):
        """Hide the line immediately. Used on idle / disconnect."""
        self._fill.stop()
        self._finish.stop()
        self._fade.stop()
        self._set_opacity(0.0)
        self._set_progress(0.0)

    def _on_finish_done(self):
        self._fade.stop()
        self._fade.setStartValue(self._opacity)
        self._fade.start()

    # ── Painting ─────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        if self._opacity <= 0.0 or self._progress <= 0.0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        fill_x = self._progress * w

        # Solid fill from x=0 to x=fill_x — the "line growing toward the dot."
        body = QColor(self._line_color)
        body.setAlpha(int(245 * self._opacity))
        painter.fillRect(0, 0, int(fill_x), h, body)

        # Subtle halo at the leading edge — small enough that the tip
        # reads as a clean line with a hint of glow, not a comet trail.
        if fill_x < w:
            halo_end = min(w, fill_x + self._LEAD_GLOW_PX)
            edge_bright = QColor(self._line_color)
            edge_bright.setAlpha(int(140 * self._opacity))
            edge_clear = QColor(self._line_color)
            edge_clear.setAlpha(0)
            gradient = QLinearGradient(fill_x, 0, halo_end, 0)
            gradient.setColorAt(0.0, edge_bright)
            gradient.setColorAt(1.0, edge_clear)
            painter.fillRect(int(fill_x), 0, int(halo_end - fill_x), h, gradient)


class StatusTab(QWidget):
    """Connection status + start/stop control + live log feed."""

    # External lifecycle signals — MainWindow wires these to the footer's
    # eye-glow pulse so the brand mark animates while the bot is connected.
    bot_ready = pyqtSignal()
    bot_idle = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._runner: BotRunner | None = None
        self._setup_ui()
        self._refresh_state()

    # ── UI ────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # ── Top row: button on the left, status indicator right-justified ─
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self._action_btn = QPushButton("Connect")
        self._action_btn.setMinimumHeight(30)
        self._action_btn.setMinimumWidth(140)
        self._action_btn.clicked.connect(self._on_action_clicked)
        top_row.addWidget(self._action_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        # Glowing comet track between the button and the dot — animates
        # while connecting, eases into the dot on ready, fades out after.
        self._track = _ConnectingTrack()
        top_row.addWidget(self._track, 1, Qt.AlignmentFlag.AlignVCenter)

        self._dot = QLabel("●")
        self._dot.setFont(QFont("Segoe UI", 20))
        self._dot.setStyleSheet(self._dot_qss(connected=False, error=False))
        top_row.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)

        # Use the branded header font so the status text reads as part of
        # the same visual system as the SUPER TTS title.
        self._status_label = QLabel("Disconnected")
        status_font = QFont(gui_theme.BRAND_FONT_FAMILY)
        status_font.setPointSize(15)
        self._status_label.setFont(status_font)
        top_row.addWidget(self._status_label, 0, Qt.AlignmentFlag.AlignVCenter)

        layout.addLayout(top_row)

        # ── Detail line ───────────────────────────────────────────────────
        self._detail_label = QLabel("Bot is not running.")
        self._detail_label.setProperty("role", "secondary")
        self._detail_label.setWordWrap(True)
        layout.addWidget(self._detail_label)

        # ── Divider ───────────────────────────────────────────────────────
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # ── Embedded log viewer (takes the rest of the space) ─────────────
        self._log_view = LogView()
        layout.addWidget(self._log_view, 1)

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

        if running:
            self._action_btn.setText("Disconnect")
            self._action_btn.setEnabled(True)
            return

        if not token_configured:
            self._action_btn.setText("Connect")
            self._action_btn.setEnabled(False)
            self._set_status(
                "No token",
                "Enter a Discord bot token in the Settings tab.",
                error=True,
            )
            return

        self._action_btn.setText("Connect")
        self._action_btn.setEnabled(True)

    def _set_status(
        self,
        headline: str,
        detail: str,
        *,
        connected: bool = False,
        error: bool = False,
    ):
        self._status_label.setText(headline)
        self._detail_label.setText(detail)
        self._dot.setStyleSheet(self._dot_qss(connected=connected, error=error))

    # ── Public API ───────────────────────────────────────────────────────

    def auto_connect_if_ready(self):
        """Called once on app launch — connect if a token is configured."""
        running = self._runner is not None and self._runner.isRunning()
        if os.getenv("DISCORD_TOKEN") and not running:
            self._start_bot()

    def on_theme_changed(self):
        """Reapply theme-aware colors. Called by MainWindow after a theme swap."""
        running = self._runner is not None and self._runner.isRunning()
        self._dot.setStyleSheet(self._dot_qss(connected=running, error=False))

    def shutdown(self):
        """Called from MainWindow.closeEvent to stop the bot cleanly and
        detach the embedded log handler before the widget is destroyed."""
        if self._runner and self._runner.isRunning():
            self._runner.request_stop()
            # Give it up to ~5s to unwind before we yank the thread.
            if not self._runner.wait(5000):
                logger.warning("BotRunner did not stop in time; terminating")
                self._runner.terminate()
                self._runner.wait(1000)
        try:
            self._log_view.remove_handler()
        except Exception:
            pass

    # ── Connect/disconnect slots ─────────────────────────────────────────

    def _on_action_clicked(self):
        if self._runner and self._runner.isRunning():
            self._stop_bot()
        else:
            self._start_bot()

    def _start_bot(self):
        if self._runner and self._runner.isRunning():
            return
        # Each Connect cycle gets a fresh BotRunner thread (and main.py
        # builds a fresh discord.py Bot inside it). The previous runner,
        # if any, is fully finished and can be released.
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
        self._track.start()

    def _on_ready(self, user_name: str, guild_count: int):
        # Called twice per connect cycle: once at on_connect (empty
        # user_name, no guilds) and once at on_ready (full info). Both
        # times we mark the tab Connected, finish the comet, and emit
        # bot_ready — repeated finish() / emit() are idempotent.
        if user_name:
            guild_word = "guild" if guild_count == 1 else "guilds"
            detail = f"Logged in as {user_name} — in {guild_count} {guild_word}."
        else:
            detail = "Gateway connected."
        self._set_status("Connected", detail, connected=True)
        self._track.finish(success=True)
        self._refresh_state()
        self.bot_ready.emit()

    def _on_error(self, msg: str):
        self._set_status("Error", f"Bot crashed: {msg}", error=True)
        self._track.finish(success=False)
        self._refresh_state()
        self.bot_idle.emit()

    def _on_finished(self):
        if self._status_label.text() not in ("Error",):
            self._set_status(
                "Disconnected",
                "Bot stopped. Click Connect to start it again.",
                connected=False,
            )
        self._track.clear()
        self._refresh_state()
        self.bot_idle.emit()
