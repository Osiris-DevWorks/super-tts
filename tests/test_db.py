"""Tests for DB connection and retry logic"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from db.db import DB


class TestDBHealthCheck:
    """Test DB.health_check"""

    @pytest.mark.asyncio
    async def test_health_check_fails_without_pool(self):
        """Test health check raises when pool is None"""
        db = DB()
        db.pool = None

        with pytest.raises(Exception, match="Database pool not initialized"):
            await db.health_check()


class TestDBConnect:
    """Test DB.connect initialization"""

    def test_db_initialization(self):
        """Test DB initializes with correct defaults"""
        db = DB()
        assert db.pool is None
        assert db._max_attempts == 3
        assert db._connection_attempts == 0

    @pytest.mark.asyncio
    async def test_connect_fails_after_max_attempts(self):
        """Test connection fails after max attempts"""
        with patch('db.db.asyncpg.create_pool') as mock_create:
            mock_create.side_effect = Exception("Connection failed")

            db = DB()
            db.dsn = "postgresql://localhost/test"
            db._max_attempts = 3

            with pytest.raises(Exception, match="Failed to connect to database after 3 attempts"):
                await db.connect()

    @pytest.mark.asyncio
    async def test_connect_skips_if_healthy(self):
        """Test connect doesn't reconnect if pool is healthy"""
        with patch('db.db.asyncpg.create_pool') as mock_create:
            db = DB()
            db.dsn = "postgresql://localhost/test"
            db.pool = MagicMock()

            # Mock health check to succeed
            db.health_check = AsyncMock()

            await db.connect()

            # create_pool should not be called
            mock_create.assert_not_called()


class TestDBClose:
    """Test DB.close"""

    @pytest.mark.asyncio
    async def test_close_handles_none_pool(self):
        """Test close handles None pool gracefully"""
        db = DB()
        db.pool = None

        await db.close()

        assert db.pool is None


class TestDBEnsureConnected:
    """Test DB.ensure_connected"""

    @pytest.mark.asyncio
    async def test_ensure_connected_succeeds_if_healthy(self):
        """Test ensure_connected does nothing if pool is healthy"""
        db = DB()
        db.health_check = AsyncMock()
        db.connect = AsyncMock()

        await db.ensure_connected()

        db.health_check.assert_called_once()
        db.connect.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_connected_reconnects_if_unhealthy(self):
        """Test ensure_connected reconnects if pool is unhealthy"""
        db = DB()
        db.health_check = AsyncMock(side_effect=Exception("Pool failed"))
        db.connect = AsyncMock()

        await db.ensure_connected()

        db.health_check.assert_called_once()
        db.connect.assert_called_once_with(force_reconnect=True)
