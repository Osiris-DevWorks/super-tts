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

# Setup bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="/", intents=intents)


@bot.event
async def on_ready():
    """Called when bot is ready"""
    logger.info(f"Bot is ready! Logged in as {bot.user}")
    logger.info(f"Super TTS Bot reporting for duty!")
    logger.info(f"Log level: {LOG_LEVEL}")

    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")


@bot.event
async def on_message(message: discord.Message):
    """Handle message events"""
    # This allows slash commands and cog listeners to work
    await bot.process_commands(message)


async def load_extensions():
    """Load TTS cog"""
    try:
        await bot.load_extension("tts_module.tts")
        logger.info("TTS cog loaded successfully")

        # Pass database to TTS cog after loading
        tts_cog = bot.get_cog("TTS")
        if tts_cog:
            tts_cog.db = db
            logger.info("Database connection passed to TTS cog")
    except Exception as e:
        logger.error(f"Failed to load TTS cog: {e}")
        raise


async def main():
    """Main entry point"""
    try:
        # Initialize database and run migrations
        migrations_dir = Path(__file__).parent / "db" / "migrations"
        logger.info("Running database migrations...")
        await execute_sql_files(str(migrations_dir), db)
        logger.info("Database migrations completed successfully")

        # Connect database pool for the bot
        await db.connect()
        logger.info("Database connection pool established")

        async with bot:
            await load_extensions()
            await bot.start(DISCORD_TOKEN)
    finally:
        # Ensure database is closed
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
