"""Log tab — in-app log viewer with export capability.

Adapted from `smart-citizen/src/gui/log_tab.py`. Bridges the stdlib logging
system to a Qt widget via a `_LogEmitter` signal so log records arriving
from worker threads render safely on the main thread.
"""
import logging
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Maximum lines kept in the viewer before oldest lines are dropped.
_MAX_LINES = 2000

_LEVEL_COLORS = {
    logging.DEBUG: "#888888",
    logging.INFO: "#cccccc",
    logging.WARNING: "#ff9800",
    logging.ERROR: "#f44336",
    logging.CRITICAL: "#f44336",
}


class _LogEmitter(QObject):
    """Signal carrier — lives on the main thread, signals deliver records
    via Qt's queued connection regardless of which thread emitted."""

    record_emitted = pyqtSignal(str, int)  # formatted message, levelno


class _QtLogHandler(logging.Handler):
    """logging.Handler that forwards records to a _LogEmitter signal."""

    def __init__(self, emitter: _LogEmitter):
        super().__init__()
        self._emitter = emitter

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self._emitter.record_emitted.emit(msg, record.levelno)
        except Exception:
            self.handleError(record)


class LogTab(QWidget):
    """Tab showing a live stream of application log output."""

    def __init__(self):
        super().__init__()
        self._line_count = 0
        self._emitter = _LogEmitter()
        self._handler = _QtLogHandler(self._emitter)
        self._handler.setFormatter(
            logging.Formatter(
                "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        self._emitter.record_emitted.connect(self._append_record)
        self._setup_ui()
        self._install_handler()

    # ── UI ────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("Min level:"))
        self._level_combo = QComboBox()
        self._level_combo.setToolTip(
            "Minimum severity to display. Entries below the selected level "
            "are hidden (DEBUG < INFO < WARNING < ERROR)."
        )
        for level, name in [
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
        ]:
            self._level_combo.addItem(name, userData=level)
        self._level_combo.setCurrentIndex(1)  # default: INFO
        self._level_combo.currentIndexChanged.connect(self._on_level_changed)
        toolbar.addWidget(self._level_combo)

        toolbar.addSpacing(16)

        self._autoscroll_cb = QCheckBox("Auto-scroll")
        self._autoscroll_cb.setToolTip(
            "Automatically scroll to the newest log entry as it arrives. "
            "Turn off to pin the view while inspecting older lines."
        )
        self._autoscroll_cb.setChecked(True)
        toolbar.addWidget(self._autoscroll_cb)

        toolbar.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setMaximumWidth(70)
        clear_btn.clicked.connect(self._clear)
        toolbar.addWidget(clear_btn)

        export_btn = QPushButton("Export to file…")
        export_btn.setMaximumWidth(130)
        export_btn.clicked.connect(self._export)
        toolbar.addWidget(export_btn)

        layout.addLayout(toolbar)

        self._view = QPlainTextEdit()
        self._view.setReadOnly(True)
        self._view.setMaximumBlockCount(_MAX_LINES)
        self._view.setFont(QFont("Consolas", 9))
        self._view.setStyleSheet(
            "QPlainTextEdit { background: #1e1e1e; color: #cccccc; border: none; }"
        )
        self._view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self._view)

        self._status_label = QLabel("0 lines")
        self._status_label.setProperty("role", "secondary")
        self._status_label.setStyleSheet("font-size: 10px;")
        layout.addWidget(self._status_label)

    # ── Handler lifecycle ────────────────────────────────────────────────

    def _install_handler(self):
        root = logging.getLogger()
        # Make sure root accepts everything so our handler-level filter can
        # actually surface DEBUG when the user picks it from the combo.
        if root.level == logging.NOTSET or root.level > logging.DEBUG:
            root.setLevel(logging.DEBUG)
        self._on_level_changed()
        root.addHandler(self._handler)

    def remove_handler(self):
        """Call on app close to avoid logging to a destroyed widget."""
        logging.getLogger().removeHandler(self._handler)

    # ── Slots ────────────────────────────────────────────────────────────

    def _on_level_changed(self):
        level = self._level_combo.currentData()
        if level is not None:
            self._handler.setLevel(level)

    def _append_record(self, msg: str, levelno: int):
        color = _LEVEL_COLORS.get(levelno, "#cccccc")
        bold = levelno >= logging.ERROR

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Weight.Bold)

        cursor = self._view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(msg + "\n", fmt)

        self._line_count = self._view.document().blockCount()
        self._status_label.setText(f"{self._line_count} lines")

        if self._autoscroll_cb.isChecked():
            self._view.setTextCursor(cursor)
            self._view.ensureCursorVisible()

    def _clear(self):
        self._view.clear()
        self._line_count = 0
        self._status_label.setText("0 lines")

    def _export(self):
        default_name = f"super-tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export log",
            default_name,
            "Log files (*.log);;Text files (*.txt);;All files (*)",
        )
        if not path:
            return
        try:
            Path(path).write_text(self._view.toPlainText(), encoding="utf-8")
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.critical(self, "Export failed", str(e))
