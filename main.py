#!/usr/bin/env python3
"""
Super TTS Bot - Main Entry Point
Ultra-fast Supertonic-based Discord TTS bot
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import Awaitable, Callable, Optional

from dotenv import load_dotenv
import discord
from discord.ext import commands

# Load environment variables. When installed via the Windows installer, the
# user's token + DB URL live at %APPDATA%\Osiris DevWorks\Super TTS\.env. In
# every other environment (dev, Docker, Railway), fall back to the original
# behavior: load_dotenv() searches CWD for .env, and Railway/Docker just
# inject env vars directly so .env absence is fine.
_appdata = os.environ.get("APPDATA")
_appdata_env = Path(_appdata) / "Osiris DevWorks" / "Super TTS" / ".env" if _appdata else None
if _appdata_env and _appdata_env.is_file():
    load_dotenv(_appdata_env)
else:
    load_dotenv()

# Import database modules
from db import DB, execute_sql_files

# Setup logging
LOG_LEVEL = "INFO"
if len(sys.argv) > 1:
    arg_level = sys.argv[1].upper()
    if arg_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        LOG_LEVEL = arg_level

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize database
db = DB()

# Get Discord token
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
# When the GUI imports this module it sets SUPER_TTS_GUI_MODE=1; in that case
# we skip the import-time exit and let the GUI handle a missing token via its
# Settings tab. Console/Docker/Railway runs (no env var) keep the original
# fail-fast behavior unchanged.
if not DISCORD_TOKEN and not os.environ.get("SUPER_TTS_GUI_MODE"):
    logger.error(
        "DISCORD_TOKEN environment variable not set. "
        "If you installed via the installer, edit "
        "%APPDATA%\\Osiris DevWorks\\Super TTS\\.env and set DISCORD_TOKEN, "
        "then re-launch."
    )
    if getattr(sys, "frozen", False):
        input("Press Enter to exit...")
    sys.exit(1)

# Bot intents are identical for every invocation, so they stay module-level.
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.guilds = True


def _read_owner_id() -> int | None:
    raw = os.getenv("OWNER_ID")
    try:
        return int(raw) if raw else None
    except ValueError:
        logger.warning(f"OWNER_ID={raw!r} is not a valid integer; ignoring")
        return None


# GUI bridge — the BotRunner thread needs to (a) get a handle on the active
# Bot to call .close() during Disconnect, and (b) be notified when on_ready
# fires so the Status tab can flip to green. The Bot is no longer module-
# level (so reconnect can build a fresh one), so these accessors replace
# the old `import main; main.bot.add_listener(...)` pattern.
_current_bot: Optional[commands.Bot] = None
_ready_observer: Optional[Callable[[commands.Bot], Awaitable[None]]] = None


def get_current_bot() -> Optional[commands.Bot]:
    """Return the currently running Bot, or None if main() hasn't built it."""
    return _current_bot


def set_ready_observer(
    callback: Optional[Callable[[commands.Bot], Awaitable[None]]],
) -> None:
    """Install a coroutine that runs alongside on_ready every time the bot
    finishes its gateway handshake. Pass None to clear. Single-observer to
    avoid stale callbacks from prior reconnect cycles piling up."""
    global _ready_observer
    _ready_observer = callback


def _build_bot() -> commands.Bot:
    """Construct a fresh Bot, with on_ready / on_message wired against it.

    Done per main() invocation rather than at import time. discord.py's
    `Bot.start()` consumes the instance — once `Bot.close()` runs, that
    Bot can never `start()` again. Reusing a module-level Bot meant the
    GUI's "Disconnect → Connect" cycle was a one-shot per process. Building
    fresh each call lets the GUI reconnect in-process without a relaunch.
    """
    global _current_bot
    bot = commands.Bot(
        command_prefix="/", intents=intents, owner_id=_read_owner_id()
    )
    _current_bot = bot

    @bot.event
    async def on_connect():
        # Fires as soon as the gateway websocket is open and IDENTIFY'd —
        # this is the "Shard ID None has connected to Gateway" moment.
        # Trigger the GUI observer here so the Status tab flips to green
        # at the earliest possible point, matching what feels like
        # "connected" in the log. The bot.user attribute may not be
        # populated yet (READY hasn't arrived), so the observer reads it
        # defensively.
        if _ready_observer is not None:
            try:
                await _ready_observer(bot)
            except Exception as e:
                logger.warning(f"ready observer raised on connect: {e}")

    @bot.event
    async def on_ready():
        logger.info(f"Bot is ready! Logged in as {bot.user}")
        logger.info(f"Super TTS Bot reporting for duty!")
        logger.info(f"Log level: {LOG_LEVEL}")

        # Re-fire the observer now that bot.user + bot.guilds are
        # populated, so the Status tab's detail line gets the real
        # "Logged in as Super TTS#7019 — in 1 guild." text instead of
        # the placeholder shown at on_connect.
        if _ready_observer is not None:
            try:
                await _ready_observer(bot)
            except Exception as e:
                logger.warning(f"ready observer raised: {e}")

        # Slash-command sync runs as a background task so it can take its
        # time (or fail) without blocking on_ready or any other listener.
        async def _do_sync():
            try:
                synced = await bot.tree.sync()
                logger.info(f"Synced {len(synced)} command(s)")
            except Exception as e:
                logger.error(f"Failed to sync commands: {e}")

        asyncio.create_task(_do_sync())

    @bot.event
    async def on_message(message: discord.Message):
        # Lets slash commands + cog listeners run.
        await bot.process_commands(message)

    return bot


async def _load_extensions(bot: commands.Bot):
    """Load the TTS cog onto the given bot and monkey-patch the DB."""
    try:
        await bot.load_extension("tts_module.tts")
        logger.info("TTS cog loaded successfully")
        tts_cog = bot.get_cog("TTS")
        if tts_cog:
            tts_cog.db = db
            logger.info("Database connection passed to TTS cog")
    except Exception as e:
        logger.error(f"Failed to load TTS cog: {e}")
        raise


async def main():
    """Main entry point. Idempotent enough to be re-invoked from the GUI's
    BotRunner thread when the user clicks Disconnect → Connect."""
    try:
        # Run migrations + open DB pool. db.connect() reuses an existing
        # healthy pool, so reconnects skip the migration round-trip cost
        # when the same process has already initialized the database.
        migrations_dir = Path(__file__).parent / "db" / "migrations"
        logger.info("Running database migrations...")
        await execute_sql_files(str(migrations_dir), db)
        logger.info("Database migrations completed successfully")
        await db.connect()
        logger.info("Database connection pool established")

        bot = _build_bot()
        async with bot:
            await _load_extensions(bot)
            # Re-read DISCORD_TOKEN at start time so the GUI can set the env
            # var after the user enters their token in Settings, without us
            # having captured the (then-absent) value at import time.
            await bot.start(os.getenv("DISCORD_TOKEN") or DISCORD_TOKEN)
    finally:
        global _current_bot
        _current_bot = None
        await db.close()


if __name__ == "__main__":
    try:
        import asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
        sys.exit(1)
