"""GUI settings — bridges QSettings (theme choice) and the .env file
(DISCORD_TOKEN, DATABASE_URL, LOG_LEVEL) at %APPDATA%\\Osiris DevWorks\\Super TTS\\.env.

The same .env path is what installer.iss writes during install. The console
build (main.py) and the GUI build read identical env-var keys from it, so
the file is interchangeable across run modes.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Mapping

from PyQt6.QtCore import QSettings

logger = logging.getLogger(__name__)


ORG_NAME = "Osiris DevWorks"
APP_NAME = "Super TTS"

# Keys persisted to QSettings (HKCU\Software\Osiris DevWorks\Super TTS).
# Anything sensitive (token, DB URL) lives in the .env file instead — never
# in the registry.
KEY_THEME = "theme"

# Default theme — kept here so callers can avoid importing gui.theme just
# to read the default (gui.theme imports settings, which would loop).
_DEFAULT_THEME_FALLBACK = "odw"


def _qsettings() -> QSettings:
    return QSettings(ORG_NAME, APP_NAME)


def get_theme() -> str:
    val = _qsettings().value(KEY_THEME, _DEFAULT_THEME_FALLBACK)
    return str(val) if val else _DEFAULT_THEME_FALLBACK


def set_theme(theme: str) -> None:
    _qsettings().setValue(KEY_THEME, theme)
    _qsettings().sync()


def env_file_path() -> Path:
    """Return the .env path the installer wrote (and the GUI maintains)."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / ORG_NAME / APP_NAME / ".env"
    # Cross-platform fallback for dev on macOS/Linux. Not used in the
    # production Windows install but keeps the module importable on any OS.
    return Path.home() / ".config" / "osiris-devworks" / "super-tts" / ".env"


def _parse_env(text: str) -> dict[str, str]:
    """Tiny .env parser — keeps line order semantics simple, handles
    `KEY=VALUE` lines and ignores comments / blanks. Doesn't try to be
    python-dotenv-complete; we only emit a controlled set of keys."""
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        # Strip wrapping quotes if any
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
            v = v[1:-1]
        if k:
            out[k] = v
    return out


def read_env() -> dict[str, str]:
    """Read the persisted .env file. Returns an empty dict if absent."""
    p = env_file_path()
    if not p.is_file():
        return {}
    try:
        return _parse_env(p.read_text(encoding="utf-8"))
    except OSError as e:
        logger.warning(f"Failed to read {p}: {e}")
        return {}


def write_env(values: Mapping[str, str]) -> None:
    """Overwrite the .env file with the given key/value mapping. Creates
    the parent directory if needed. Order is the iteration order of
    `values` — pass a dict with the canonical order if you care."""
    p = env_file_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    body_lines = []
    for k, v in values.items():
        body_lines.append(f"{k}={v}")
    p.write_text("\n".join(body_lines) + "\n", encoding="utf-8")
    logger.info(f"Wrote {len(values)} entries to {p}")


def apply_env_to_process(values: Mapping[str, str]) -> None:
    """Mirror the .env values into os.environ so already-imported modules
    that re-read os.getenv (like main.main()) pick up the latest token."""
    for k, v in values.items():
        os.environ[k] = v
