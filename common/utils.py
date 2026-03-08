from db.db import DB
from discord.ext import commands
from typing import Optional, Callable, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import time
import logging

logger = logging.getLogger("citizen-bot")

# Thread pool for blocking operations like Selenium
_thread_pool = ThreadPoolExecutor(max_workers=4)

# Simple in-memory cache
_cache = {}
_cache_timestamps = {}


# Decorator to handle cursor creation and cleanup
def use_cursor(db: DB):
    def decorator(func: callable) -> callable:
        async def wrapper(self: commands.Cog, *args: tuple, **kwargs: dict) -> Optional[discord.InteractionResponse]:
            with db.connection.cursor() as cursor:
                self.cursor = cursor
                try:
                    return await func(self, *args, **kwargs)
                finally:
                    self.cursor = None
        return wrapper
    return decorator


async def check_db(db, interaction):
    """Check database connection health and attempt reconnection if needed."""
    if not db or not db.pool:
        await interaction.followup.send("Database connection pool is not initialized.", ephemeral=True)
        raise RuntimeError("Database connection pool is not initialized.")

    try:
        await db.ensure_connected()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        await interaction.followup.send("Database connection failed. Please try again later.", ephemeral=True)
        raise RuntimeError(f"Database connection failed: {e}")


async def run_in_executor(func: Callable, *args: Any) -> Any:
    """Run a blocking function in a thread pool executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_thread_pool, func, *args)


def cached(ttl_seconds: int = 300):
    """
    Decorator to cache function results for a specified time-to-live.

    Args:
        ttl_seconds: Time in seconds before cache expires (default: 5 minutes)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Check if cached value exists and is not expired
            if cache_key in _cache:
                timestamp = _cache_timestamps.get(cache_key, 0)
                if time.time() - timestamp < ttl_seconds:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return _cache[cache_key]

            # Call function and cache result
            result = await func(*args, **kwargs)
            _cache[cache_key] = result
            _cache_timestamps[cache_key] = time.time()
            logger.debug(f"Cached result for {func.__name__}")
            return result

        return wrapper
    return decorator


def clear_cache():
    """Clear the entire cache."""
    _cache.clear()
    _cache_timestamps.clear()
    logger.info("Cache cleared")


def clear_expired_cache():
    """Remove expired entries from cache."""
    current_time = time.time()
    expired_keys = [
        key for key, timestamp in _cache_timestamps.items()
        if current_time - timestamp > 300  # Default 5 min TTL
    ]
    for key in expired_keys:
        _cache.pop(key, None)
        _cache_timestamps.pop(key, None)
    if expired_keys:
        logger.debug(f"Cleared {len(expired_keys)} expired cache entries")