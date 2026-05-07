"""Branded footer — Osiris DevWorks logo + Discord on the left, donation
cluster on the right. Layout mirrors sc-profile-editor and smart-citizen
for suite-wide consistency.

The Osiris logo is a stacked widget: a base pixmap with the Eye of Horus
glow rendered on top via `osiris-eye-glow.png`. Animating the overlay's
QGraphicsOpacityEffect between 0 and 1 produces a clean pulse without
re-rendering the underlying art.

Pulse semantics here differ from smart-citizen's: we pulse for the entire
duration the bot is connected to Discord, not while a worker runs. The
StatusTab fires `bot_ready` / `bot_idle` signals; MainWindow wires those
to `Footer.start_pulse()` / `Footer.stop_pulse()`.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl, QEasingCurve, QPropertyAnimation
from PyQt6.QtGui import QCursor, QDesktopServices, QPixmap
from PyQt6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QStackedLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


# Public-facing links. Donation handles are shared across Osiris DevWorks
# projects; the GitHub URL is per-project.
_GITHUB_URL = "https://github.com/Osiris-DevWorks/super-tts"
_DISCORD_URL = "https://discord.gg/BNzRegKZ7k"
_PAYPAL_URL = "https://paypal.me/RighteousKill"
_VENMO_URL = "https://venmo.com/u/Amr-Abouelleil"

_LOGO_HEIGHT_PX = 40

# Pulse timing — 1.8s per cycle (in/out) gives a calm "still running"
# heartbeat without being attention-grabbing. Same as smart-citizen.
_PULSE_DURATION_MS = 1800


def _resource_path(rel: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / rel


def _load_scaled_pixmap(asset_name: str) -> QPixmap | None:
    """Load an asset PNG and scale it to the standard footer height.
    Returns None if the file is absent — caller falls back to text."""
    path = _resource_path(os.path.join("assets", asset_name))
    if not path.exists():
        logger.debug(f"footer asset missing: {path}")
        return None
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        logger.debug(f"failed to load pixmap: {path}")
        return None
    if pixmap.height() > _LOGO_HEIGHT_PX:
        pixmap = pixmap.scaledToHeight(
            _LOGO_HEIGHT_PX, Qt.TransformationMode.SmoothTransformation
        )
    return pixmap


def _make_link_label(
    asset_name: str,
    fallback_text: str,
    fallback_qss: str,
    url: str,
    tooltip: str,
) -> QLabel:
    """Build a clickable QLabel — image if asset exists, styled text fallback."""
    label = QLabel()
    pixmap = _load_scaled_pixmap(asset_name)
    if pixmap is not None:
        label.setPixmap(pixmap)
    else:
        label.setText(fallback_text)
        label.setStyleSheet(fallback_qss)
    label.setToolTip(tooltip)
    label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    label.mousePressEvent = lambda _event, u=url: QDesktopServices.openUrl(QUrl(u))
    return label


class Footer(QWidget):
    """Branded footer panel. Holds a pulse-capable Osiris logo on the left
    plus Discord / PayPal / Venmo links."""

    def __init__(self):
        super().__init__()
        self._eye_glow_effect: QGraphicsOpacityEffect | None = None
        self._eye_pulse: QPropertyAnimation | None = None
        self._eye_fadeout: QPropertyAnimation | None = None
        self._build()

    def _build(self):
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 8, 8, 0)

        # ── Left: Osiris logo (with optional eye-glow overlay) + Discord ──
        osiris = self._build_osiris_logo()
        row.addWidget(osiris)

        row.addSpacing(10)

        discord = _make_link_label(
            asset_name="discord.png",
            fallback_text="Join the Discord",
            fallback_qss="font-size: 12px;",
            url=_DISCORD_URL,
            tooltip="Join the Osiris DevWorks Discord for support and updates",
        )
        row.addWidget(discord)

        row.addStretch()

        # ── Right: donations ─────────────────────────────────────────────
        paypal = _make_link_label(
            asset_name="paypal.png",
            fallback_text="Donate via PayPal",
            fallback_qss=(
                "QLabel {"
                " background-color: #0070ba;"
                " color: white;"
                " padding: 8px 16px;"
                " border-radius: 4px;"
                " font-size: 12px;"
                " font-weight: bold;"
                "}"
                "QLabel:hover { background-color: #005ea6; }"
            ),
            url=_PAYPAL_URL,
            tooltip="Support development with a PayPal donation",
        )
        row.addWidget(paypal)

        row.addSpacing(10)

        venmo = _make_link_label(
            asset_name="venmo.png",
            fallback_text="Venmo",
            fallback_qss=(
                "QLabel {"
                " background-color: #008CFF;"
                " color: white;"
                " padding: 8px 16px;"
                " border-radius: 4px;"
                " font-size: 12px;"
                " font-weight: bold;"
                "}"
                "QLabel:hover { background-color: #0070cc; }"
            ),
            url=_VENMO_URL,
            tooltip="Support development with a Venmo donation",
        )
        row.addWidget(venmo)

    def _build_osiris_logo(self) -> QWidget:
        """Stacked logo: base pixmap + animated eye-glow overlay.

        Falls back to a single non-animated label if either asset is
        missing — the pulse just becomes a no-op in that case.
        """
        base_pixmap = _load_scaled_pixmap("osiris-devworks.png")
        glow_pixmap = _load_scaled_pixmap("osiris-eye-glow.png")

        if base_pixmap is None:
            # No logo at all — fall back to text (matches earlier behavior).
            return _make_link_label(
                asset_name="osiris-devworks.png",  # known-missing — uses fallback path
                fallback_text="Osiris DevWorks",
                fallback_qss=(
                    "QLabel {"
                    " background-color: #1a1f2e;"
                    " color: #c9a961;"
                    " padding: 8px 16px;"
                    " border-radius: 4px;"
                    " font-size: 12px;"
                    " font-weight: bold;"
                    "}"
                    "QLabel:hover { background-color: #242938; }"
                ),
                url=_GITHUB_URL,
                tooltip="Open the Super TTS GitHub repository",
            )

        host = QWidget()
        stack = QStackedLayout(host)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)
        stack.setContentsMargins(0, 0, 0, 0)

        base = QLabel()
        base.setPixmap(base_pixmap)
        stack.addWidget(base)

        if glow_pixmap is not None:
            glow_label = QLabel()
            glow_label.setPixmap(glow_pixmap)

            # Opacity-on-pixmap is exact float math and won't re-render the
            # underlying sprite each frame — gives jitter-free pulses.
            self._eye_glow_effect = QGraphicsOpacityEffect(glow_label)
            self._eye_glow_effect.setOpacity(0.0)
            glow_label.setGraphicsEffect(self._eye_glow_effect)

            self._eye_pulse = QPropertyAnimation(self._eye_glow_effect, b"opacity", self)
            self._eye_pulse.setDuration(_PULSE_DURATION_MS)
            self._eye_pulse.setKeyValueAt(0.0, 0.0)
            self._eye_pulse.setKeyValueAt(0.5, 1.0)
            self._eye_pulse.setKeyValueAt(1.0, 0.0)
            self._eye_pulse.setEasingCurve(QEasingCurve.Type.InOutSine)
            self._eye_pulse.setLoopCount(-1)

            # One-shot fade-out so stop_pulse() can ease the current
            # opacity to 0 instead of snapping mid-cycle.
            self._eye_fadeout = QPropertyAnimation(self._eye_glow_effect, b"opacity", self)
            self._eye_fadeout.setEasingCurve(QEasingCurve.Type.InOutSine)
            self._eye_fadeout.setEndValue(0.0)

            stack.addWidget(glow_label)

        # Pin the host to the base pixmap's size — the overlay never
        # expands the paint rect, so no extra padding needed.
        host.setFixedSize(base_pixmap.size())
        host.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        host.setToolTip("Open the Super TTS GitHub repository")
        host.mousePressEvent = lambda _event: QDesktopServices.openUrl(QUrl(_GITHUB_URL))
        return host

    # ── Public pulse API — wired from MainWindow to StatusTab events ─────

    def start_pulse(self):
        """Begin the eye-glow heartbeat. Called when the bot reports ready."""
        if self._eye_pulse is None or self._eye_glow_effect is None:
            return
        if self._eye_fadeout and self._eye_fadeout.state() == QPropertyAnimation.State.Running:
            self._eye_fadeout.stop()
        if self._eye_pulse.state() != QPropertyAnimation.State.Running:
            self._eye_pulse.start()

    def stop_pulse(self):
        """End the heartbeat. Eases from current opacity down to 0 instead
        of snapping off — looks calmer than abrupt disappearance."""
        if self._eye_pulse is None or self._eye_glow_effect is None:
            return
        if self._eye_pulse.state() != QPropertyAnimation.State.Running:
            return
        current = self._eye_glow_effect.opacity()
        self._eye_pulse.stop()
        if self._eye_fadeout is not None:
            self._eye_fadeout.stop()
            self._eye_fadeout.setStartValue(current)
            # Scale fade duration with how bright we are — a near-dark eye
            # should snap quickly, a fully-lit one takes the full ~600ms.
            self._eye_fadeout.setDuration(int(100 + 500 * current))
            self._eye_fadeout.start()
