"""Shared pytest fixtures and mocks"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_db():
    """Create a mock DB instance for testing"""
    db = AsyncMock()
    db.pool = MagicMock()
    db.execute = AsyncMock()
    db.fetch_one = AsyncMock()
    db.fetch_all = AsyncMock()
    db.health_check = AsyncMock()
    db.connect = AsyncMock()
    db.close = AsyncMock()
    return db


@pytest.fixture
def mock_interaction():
    """Create a mock Discord interaction"""
    interaction = AsyncMock()
    interaction.user = MagicMock()
    interaction.user.id = 123456789
    interaction.guild = MagicMock()
    interaction.guild.id = 987654321
    interaction.guild.roles = []
    interaction.response = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction


@pytest.fixture
def mock_bot():
    """Create a mock Discord bot"""
    bot = AsyncMock()
    bot.user = MagicMock()
    bot.user.id = 111222333
    bot.latency = 0.05
    return bot


@pytest.fixture
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_config_dict():
    """Provide a sample config dictionary"""
    return {
        'tts': {
            'device': 'cuda',
            'model_name': 'supertonic',
        },
        'discord': {
            'prefix': '!',
            'intents': 'all',
        },
        'database': {
            'host': 'localhost',
            'port': 5432,
        }
    }


@pytest.fixture
def mock_supertonic_engine():
    """Mock the Supertonic TTS engine to avoid model download"""
    with patch('tts.supertonic_engine.TTS') as mock_tts_class:
        mock_engine = AsyncMock()
        mock_engine.tts = AsyncMock()
        mock_engine.tts.tts_to_wav = MagicMock(return_value=b'\x00\x01\x02\x03')
        mock_tts_class.return_value = mock_engine
        yield mock_tts_class
