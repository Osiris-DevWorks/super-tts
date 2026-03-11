"""Tests for GuildQueue and QueueManager"""

import asyncio
import pytest
from utils.queue_manager import GuildQueue, QueueManager, QueuedMessage


class TestGuildQueue:
    """Test GuildQueue FIFO logic"""

    @pytest.mark.asyncio
    async def test_enqueue_message(self):
        """Test enqueuing a message"""
        queue = GuildQueue(guild_id=123)
        message = QueuedMessage(
            user_id=456,
            user_name="test_user",
            text="hello",
            voice_file_path="/tmp/voice.wav",
        )

        result = await queue.enqueue(message)
        assert result is True
        assert queue.queue_size() == 1

    @pytest.mark.asyncio
    async def test_dequeue_message(self):
        """Test dequeuing returns FIFO order"""
        queue = GuildQueue(guild_id=123)
        msg1 = QueuedMessage(user_id=1, user_name="user1", text="msg1", voice_file_path="/tmp/1.wav")
        msg2 = QueuedMessage(user_id=2, user_name="user2", text="msg2", voice_file_path="/tmp/2.wav")

        await queue.enqueue(msg1)
        await queue.enqueue(msg2)

        dequeued = await queue.dequeue()
        assert dequeued.text == "msg1"

    @pytest.mark.asyncio
    async def test_dequeue_empty_queue_returns_none(self):
        """Test dequeue on empty queue returns None (after timeout)"""
        queue = GuildQueue(guild_id=123)
        result = await queue.dequeue()
        assert result is None  # Times out and returns None

    @pytest.mark.asyncio
    async def test_queue_fifo_order(self):
        """Test that messages come out in FIFO order"""
        queue = GuildQueue(guild_id=123)
        messages = [
            QueuedMessage(user_id=i, user_name=f"user{i}", text=f"msg{i}", voice_file_path=f"/tmp/{i}.wav")
            for i in range(5)
        ]

        for msg in messages:
            await queue.enqueue(msg)

        for i in range(5):
            dequeued = await queue.dequeue()
            assert dequeued.text == f"msg{i}"

    @pytest.mark.asyncio
    async def test_queue_size(self):
        """Test queue_size method"""
        queue = GuildQueue(guild_id=123)
        assert queue.queue_size() == 0

        msg = QueuedMessage(user_id=1, user_name="user", text="test", voice_file_path="/tmp/test.wav")
        await queue.enqueue(msg)
        assert queue.queue_size() == 1

    @pytest.mark.asyncio
    async def test_is_empty(self):
        """Test is_empty method"""
        queue = GuildQueue(guild_id=123)
        assert queue.is_empty() is True

        msg = QueuedMessage(user_id=1, user_name="user", text="test", voice_file_path="/tmp/test.wav")
        await queue.enqueue(msg)
        assert queue.is_empty() is False

    @pytest.mark.asyncio
    async def test_clear_queue(self):
        """Test clearing all messages"""
        queue = GuildQueue(guild_id=123)
        for i in range(3):
            msg = QueuedMessage(user_id=i, user_name=f"user{i}", text=f"msg{i}", voice_file_path=f"/tmp/{i}.wav")
            await queue.enqueue(msg)

        assert queue.queue_size() == 3
        await queue.clear()
        assert queue.queue_size() == 0

    def test_guild_queue_respects_capacity(self):
        """Test that queue respects max capacity"""
        max_queue_size = 10
        queue = GuildQueue(guild_id=123, max_queue_size=max_queue_size)
        assert queue.queue.maxsize == max_queue_size


class TestQueueManager:
    """Test QueueManager coordination"""

    def test_create_queue_for_guild(self):
        """Test creating queue for a guild"""
        manager = QueueManager()
        queue = manager.get_or_create_queue(guild_id=123)
        assert queue is not None
        assert queue.guild_id == 123

    def test_reuses_existing_queue(self):
        """Test that same guild gets same queue instance"""
        manager = QueueManager()
        queue1 = manager.get_or_create_queue(guild_id=123)
        queue2 = manager.get_or_create_queue(guild_id=123)
        assert queue1 is queue2

    def test_different_guilds_different_queues(self):
        """Test that different guilds get different queues"""
        manager = QueueManager()
        queue1 = manager.get_or_create_queue(guild_id=111)
        queue2 = manager.get_or_create_queue(guild_id=222)
        assert queue1 is not queue2

    @pytest.mark.asyncio
    async def test_enqueue_via_manager(self):
        """Test enqueueing through manager"""
        manager = QueueManager()
        msg = QueuedMessage(user_id=1, user_name="user", text="test", voice_file_path="/tmp/test.wav")

        result = await manager.enqueue(guild_id=123, message=msg)
        assert result is True

        queue = manager.get_or_create_queue(guild_id=123)
        assert queue.queue_size() == 1

    def test_max_concurrent_limit(self):
        """Test max_concurrent semaphore is set correctly"""
        manager = QueueManager(max_concurrent=8)
        assert manager.max_concurrent == 8
        assert manager.semaphore._value == 8

    @pytest.mark.asyncio
    async def test_set_processor_callback(self):
        """Test setting processor callback"""
        manager = QueueManager()

        async def mock_processor(guild_id, message):
            pass

        manager.set_processor(mock_processor)
        assert manager.processor_callback is not None

    def test_multiple_guild_queues(self):
        """Test manager handles multiple guild queues"""
        manager = QueueManager()
        for guild_id in [111, 222, 333]:
            manager.get_or_create_queue(guild_id)

        assert len(manager.guild_queues) == 3
