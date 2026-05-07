"""Background thread that owns the Discord bot's asyncio event loop.

The bot's existing entry point is `main.main()` (an async function). We
host that async function inside a QThread so the Qt GUI stays responsive.
The thread sets `SUPER_TTS_GUI_MODE=1` before importing `main` so the
module-level token-guard skips its `sys.exit(1)` — the GUI handles missing
tokens via the Settings tab instead.

Reconnect: each Connect cycle spawns a fresh BotRunner. main.main() builds
a new discord.py Bot per call (it's no longer a module-level singleton),
so Disconnect → Connect inside the same process works.
"""
from __future__ import annotations

import asyncio
import logging
import os
import traceback

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger("super-tts.gui")


class BotRunner(QThread):
    """Owns the asyncio event loop that the bot lives on."""

    # Emitted when the asyncio loop has been built and we're about to call
    # main.main() — UI uses this to flip status to "Connecting...".
    starting = pyqtSignal()
    # Emitted when discord.py reports the bot is ready (logged in, gateway
    # handshake done). Carries the bot user's display name and guild count.
    ready = pyqtSignal(str, int)
    # Emitted on any unhandled exception escaping main.main().
    error = pyqtSignal(str)
    # Emitted when the loop has fully unwound and the thread is about to exit.
    finished_clean = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._loop: asyncio.AbstractEventLoop | None = None

    def run(self) -> None:  # type: ignore[override]
        # Set the GUI-mode flag BEFORE importing main so the import-time
        # token-missing exit is skipped. This must happen inside the thread
        # since other threads might import main first.
        os.environ["SUPER_TTS_GUI_MODE"] = "1"

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            import main as bot_module

            # Register a single observer with main.py — the bot is no longer
            # a module-level attribute (it's built fresh inside main() so
            # reconnect works), so we can't add_listener() against it from
            # out here. main.py runs the observer at the tail of its own
            # on_ready handler.
            async def _on_ready_for_gui(bot):
                # main.py fires this once at on_connect (bot.user is None,
                # bot.guilds is empty) and again at on_ready (both populated).
                # Emit an empty name on the early call so the Status tab
                # can show generic "Gateway connected" text and update with
                # the real user/guild info on the second emit.
                user = bot.user
                guild_count = len(bot.guilds) if bot.guilds else 0
                name = str(user) if user else ""
                self.ready.emit(name, guild_count)

            bot_module.set_ready_observer(_on_ready_for_gui)

            self.starting.emit()
            logger.info("BotRunner: starting bot via main.main()")
            self._loop.run_until_complete(bot_module.main())

        except SystemExit:
            # main.py calls sys.exit(1) when DISCORD_TOKEN is still missing
            # at start-time. Treat as a clean stop.
            logger.warning("BotRunner: main() exited (likely missing token).")
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"BotRunner: unhandled error: {e}\n{tb}")
            self.error.emit(str(e))
        finally:
            try:
                if self._loop and not self._loop.is_closed():
                    # Give pending callbacks a moment to drain before close
                    pending = asyncio.all_tasks(self._loop)
                    for t in pending:
                        t.cancel()
                    self._loop.close()
            except Exception:
                pass
            self.finished_clean.emit()

    def request_stop(self) -> None:
        """Ask the bot to disconnect cleanly. Schedules `bot.close()` on the
        worker loop. The thread exits when `main.main()` unwinds."""
        if not self._loop or self._loop.is_closed():
            return
        try:
            import main as bot_module

            async def _shutdown():
                bot = bot_module.get_current_bot()
                if bot is None:
                    return
                try:
                    await bot.close()
                except Exception:
                    pass

            asyncio.run_coroutine_threadsafe(_shutdown(), self._loop)
        except Exception as e:
            logger.warning(f"BotRunner.request_stop failed: {e}")
