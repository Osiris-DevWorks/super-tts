"""
Queue Manager: Async message queues per guild
Ensures FIFO ordering and fairness for concurrent users
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Callable, Coroutine

logger = logging.getLogger(__name__)


@dataclass
class QueuedMessage:
    """Represents a queued TTS message"""
    user_id: int
    user_name: str
    text: str
    voice_file_path: str
    speed: float = 1.0
    language: str = 'en'
    voice_name: str = 'M1'


class GuildQueue:
    """Per-guild async message queue for TTS"""

    def __init__(self, guild_id: int, max_queue_size: int = 50):
        """
        Initialize guild queue

        Args:
            guild_id: Discord guild ID
            max_queue_size: Maximum messages in queue (prevents spam)
        """
        self.guild_id = guild_id
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.is_processing = False
        self.processor_task: Optional[asyncio.Task] = None

    async def enqueue(self, message: QueuedMessage) -> bool:
        """
        Add message to queue

        Args:
            message: QueuedMessage to enqueue

        Returns:
            True if enqueued, False if queue is full
        """
        try:
            self.queue.put_nowait(message)
            logger.debug(
                f'Enqueued message from {message.user_name} '
                f'(queue size: {self.queue.qsize()})'
            )
            return True
        except asyncio.QueueFull:
            logger.warning(f'Queue full for guild {self.guild_id}')
            return False

    async def dequeue(self) -> Optional[QueuedMessage]:
        """
        Get next message from queue (blocks if empty)

        Returns:
            Next QueuedMessage or None if queue stopped
        """
        try:
            message = await asyncio.wait_for(self.queue.get(), timeout=5.0)
            return message
        except asyncio.TimeoutError:
            return None

    def queue_size(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()

    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return self.queue.empty()

    async def clear(self):
        """Clear all messages from queue"""
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        logger.info(f'Cleared queue for guild {self.guild_id}')


class QueueManager:
    """Global queue manager for all guilds"""

    def __init__(self, max_concurrent: int = 4):
        """Initialize queue manager

        Args:
            max_concurrent: Maximum number of concurrent TTS processing tasks
        """
        self.guild_queues: dict[int, GuildQueue] = {}
        self.processor_callback: Optional[Callable[[QueuedMessage], Coroutine]] = None
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    def get_or_create_queue(self, guild_id: int) -> GuildQueue:
        """
        Get or create queue for guild

        Args:
            guild_id: Discord guild ID

        Returns:
            GuildQueue instance
        """
        if guild_id not in self.guild_queues:
            self.guild_queues[guild_id] = GuildQueue(guild_id)
            logger.debug(f'Created queue for guild {guild_id}')

        return self.guild_queues[guild_id]

    async def enqueue(self, guild_id: int, message: QueuedMessage) -> bool:
        """
        Enqueue message for a guild

        Args:
            guild_id: Discord guild ID
            message: QueuedMessage to enqueue

        Returns:
            True if enqueued successfully
        """
        queue = self.get_or_create_queue(guild_id)
        return await queue.enqueue(message)

    def set_processor(
        self,
        callback: Callable[[int, QueuedMessage], Coroutine]
    ):
        """
        Set callback to process dequeued messages

        Args:
            callback: Async function(guild_id, message) to process messages
        """
        self.processor_callback = callback

    async def start_processor(self, guild_id: int):
        """
        Start processing queue for a guild

        Args:
            guild_id: Discord guild ID
        """
        queue = self.get_or_create_queue(guild_id)

        if queue.is_processing:
            logger.debug(f'Processor already running for guild {guild_id}')
            return

        queue.is_processing = True

        async def _process():
            """Process messages from queue"""
            logger.info(f'Started queue processor for guild {guild_id}')

            while queue.is_processing:
                message = await queue.dequeue()

                if message is None:
                    # Timeout - check if still should process
                    if not queue.is_processing:
                        break
                    continue

                if not self.processor_callback:
                    logger.warning('No processor callback set')
                    continue

                try:
                    # Use semaphore to limit concurrent processing
                    async with self.semaphore:
                        await self.processor_callback(guild_id, message)
                except Exception as e:
                    logger.error(f'Error processing message from {message.user_name}: {e}')

            logger.info(f'Stopped queue processor for guild {guild_id}')

        queue.processor_task = asyncio.create_task(_process())

    async def stop_processor(self, guild_id: int):
        """
        Stop processing queue for a guild

        Args:
            guild_id: Discord guild ID
        """
        queue = self.get_or_create_queue(guild_id)

        if not queue.is_processing:
            return

        queue.is_processing = False
        await queue.clear()

        if queue.processor_task:
            try:
                await queue.processor_task
            except asyncio.CancelledError:
                pass

        logger.info(f'Stopped queue processor for guild {guild_id}')

    def get_queue_info(self, guild_id: int) -> dict:
        """
        Get queue statistics

        Args:
            guild_id: Discord guild ID

        Returns:
            Dictionary with queue info
        """
        queue = self.get_or_create_queue(guild_id)

        return {
            'guild_id': guild_id,
            'queue_size': queue.queue_size(),
            'is_processing': queue.is_processing,
            'is_empty': queue.is_empty()
        }

    async def cleanup(self):
        """Cleanup all queues"""
        for guild_id in list(self.guild_queues.keys()):
            await self.stop_processor(guild_id)

        logger.info('Queue manager cleanup complete')
