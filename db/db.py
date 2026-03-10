import asyncpg
import asyncio
import os
import logging
from typing import Optional

logger = logging.getLogger("super-tts")


class DB:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.dsn = os.getenv("DATABASE_URL")
        self._connection_attempts = 0
        self._max_attempts = 3

    async def connect(self, force_reconnect: bool = False):
        """Connect to the database with retry logic."""
        if self.pool and not force_reconnect:
            # Check if connection is healthy
            try:
                await self.health_check()
                return
            except Exception as e:
                logger.warning(f"Health check failed, reconnecting: {e}")
                await self.close()

        for attempt in range(self._max_attempts):
            try:
                self.pool = await asyncpg.create_pool(
                    dsn=self.dsn,
                    min_size=1,
                    max_size=10,
                    command_timeout=60,
                    max_inactive_connection_lifetime=300
                )
                logger.info(f"Database connection pool created successfully (attempt {attempt + 1})")
                self._connection_attempts = 0
                return
            except Exception as e:
                self._connection_attempts += 1
                logger.error(f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt == self._max_attempts - 1:
                    raise Exception(f"Failed to connect to database after {self._max_attempts} attempts") from e
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

    async def health_check(self):
        """Check if database connection is healthy."""
        if not self.pool:
            raise Exception("Database pool not initialized")
        async with self.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")

    async def ensure_connected(self):
        """Ensure database is connected, reconnect if necessary."""
        try:
            await self.health_check()
        except Exception:
            logger.warning("Database connection lost, attempting reconnection...")
            await self.connect(force_reconnect=True)

    async def close(self):
        """Close the database connection pool with timeout."""
        if self.pool:
            try:
                # Use timeout to prevent hanging if connections aren't released
                await asyncio.wait_for(self.pool.close(), timeout=10.0)
                logger.info("Database connection pool closed")
            except asyncio.TimeoutError:
                logger.warning("Database pool close() timed out after 10 seconds - forcefully terminating")
            except Exception as e:
                logger.error(f"Error closing database pool: {e}")
            finally:
                self.pool = None

    async def execute(self, query, *args):
        """Execute a query with automatic reconnection on failure."""
        await self.ensure_connected()
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(query, *args)
        except (asyncpg.PostgresConnectionError, asyncpg.InterfaceError) as e:
            logger.error(f"Connection error during execute, retrying: {e}")
            await self.connect(force_reconnect=True)
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(query, *args)

    async def fetch_one(self, query, *args):
        """Fetch one row with automatic reconnection on failure."""
        await self.ensure_connected()
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetchrow(query, *args)
        except (asyncpg.PostgresConnectionError, asyncpg.InterfaceError) as e:
            logger.error(f"Connection error during fetch_one, retrying: {e}")
            await self.connect(force_reconnect=True)
            async with self.pool.acquire() as conn:
                return await conn.fetchrow(query, *args)

    async def fetch_all(self, query, *args):
        """Fetch all rows with automatic reconnection on failure."""
        await self.ensure_connected()
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetch(query, *args)
        except (asyncpg.PostgresConnectionError, asyncpg.InterfaceError) as e:
            logger.error(f"Connection error during fetch_all, retrying: {e}")
            await self.connect(force_reconnect=True)
            async with self.pool.acquire() as conn:
                return await conn.fetch(query, *args)
