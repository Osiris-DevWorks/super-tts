"""
TTS Database Models
Uses citizen-bot's existing PostgreSQL database
"""

import logging
from db.db import DB

logger = logging.getLogger("citizen-bot")


class TTSMonitoredChannels:
    """Manage monitored channels for auto-TTS"""

    def __init__(self, db: DB):
        """
        Initialize with database connection

        Args:
            db: Citizen-bot's DB instance
        """
        self.db = db

    async def add_channel(self, channel_id: int, guild_id: int, channel_name: str, added_by: int) -> bool:
        """
        Add a channel to monitoring

        Args:
            channel_id: Discord channel ID
            guild_id: Discord guild ID
            channel_name: Channel name
            added_by: User ID who added it

        Returns:
            True if successful
        """
        try:
            query = '''
                INSERT INTO tts_monitored_channels (channel_id, guild_id, channel_name, added_by)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (channel_id) DO NOTHING
            '''
            await self.db.execute(query, channel_id, guild_id, channel_name, added_by)
            logger.info(f'Added monitored channel: {channel_name} ({channel_id})')
            return True

        except Exception as e:
            logger.error(f'Failed to add monitored channel {channel_id}: {e}')
            return False

    async def remove_channel(self, channel_id: int) -> bool:
        """
        Remove a channel from monitoring

        Args:
            channel_id: Discord channel ID

        Returns:
            True if successful
        """
        try:
            query = 'DELETE FROM tts_monitored_channels WHERE channel_id = $1'
            await self.db.execute(query, channel_id)
            logger.info(f'Removed monitored channel: {channel_id}')
            return True

        except Exception as e:
            logger.error(f'Failed to remove monitored channel {channel_id}: {e}')
            return False

    async def is_channel_monitored(self, channel_id: int) -> bool:
        """
        Check if a channel is monitored

        Args:
            channel_id: Discord channel ID

        Returns:
            True if channel is monitored
        """
        try:
            query = 'SELECT channel_id FROM tts_monitored_channels WHERE channel_id = $1'
            result = await self.db.fetch_one(query, channel_id)
            return result is not None

        except Exception as e:
            logger.error(f'Error checking monitored channel {channel_id}: {e}')
            return False

    async def get_monitored_channels(self, guild_id: int) -> list:
        """
        Get all monitored channels for a guild

        Args:
            guild_id: Discord guild ID

        Returns:
            List of channel info dicts
        """
        try:
            query = '''
                SELECT channel_id, channel_name, added_by, created_at
                FROM tts_monitored_channels
                WHERE guild_id = $1
                ORDER BY created_at DESC
            '''
            rows = await self.db.fetch_all(query, guild_id)

            return [
                {
                    'channel_id': row['channel_id'],
                    'channel_name': row['channel_name'],
                    'added_by': row['added_by'],
                    'created_at': row['created_at']
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f'Failed to get monitored channels for guild {guild_id}: {e}')
            return []

    async def get_all_monitored_channels(self) -> list:
        """
        Get all monitored channel IDs across all guilds

        Returns:
            List of channel IDs
        """
        try:
            query = 'SELECT channel_id FROM tts_monitored_channels'
            rows = await self.db.fetch_all(query)
            return [row['channel_id'] for row in rows]

        except Exception as e:
            logger.error(f'Failed to get all monitored channels: {e}')
            return []


class TTSUserPreferences:
    """Manage user TTS preferences"""

    def __init__(self, db: DB):
        """
        Initialize with database connection

        Args:
            db: Citizen-bot's DB instance
        """
        self.db = db

    async def get_preferences(self, user_id: int) -> dict:
        """
        Get user preferences

        Args:
            user_id: Discord user ID

        Returns:
            Dictionary with user preferences
        """
        try:
            query = '''
                SELECT voice_name, speed, pitch, language
                FROM tts_user_preferences
                WHERE user_id = $1
            '''
            result = await self.db.fetch_one(query, user_id)

            if result:
                return {
                    'voice_name': result['voice_name'],
                    'speed': float(result['speed']),
                    'pitch': float(result['pitch']),
                    'language': result['language']
                }

            # Return defaults if user not found
            return {
                'voice_name': 'default',
                'speed': 1.0,
                'pitch': 1.0,
                'language': 'en'
            }

        except Exception as e:
            logger.error(f'Failed to get preferences for user {user_id}: {e}')
            return {
                'voice_name': 'default',
                'speed': 1.0,
                'pitch': 1.0,
                'language': 'en'
            }

    async def set_preferences(
        self,
        user_id: int,
        voice_name: str = None,
        speed: float = None,
        pitch: float = None,
        language: str = None
    ) -> bool:
        """
        Update user preferences

        Args:
            user_id: Discord user ID
            voice_name: Voice name
            speed: Speech speed (0.5-2.0)
            pitch: Voice pitch (0.8-1.2)
            language: Language code (en, es, fr, de, it, pt, pl, tr, ru, nl, el, hu, zh-cn, ja, ko, ar)

        Returns:
            True if successful
        """
        try:
            # Validate and bounds-check parameters
            supported_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'pl', 'tr', 'ru', 'nl',
                                 'el', 'hu', 'zh-cn', 'ja', 'ko', 'ar']

            # Validate language
            if language and language not in supported_languages:
                logger.warning(f'Invalid language: {language}, using default: en')
                language = 'en'

            # Validate speed bounds
            if speed is not None:
                speed = max(0.5, min(2.0, speed))

            # Validate pitch bounds
            if pitch is not None:
                pitch = max(0.8, min(1.2, pitch))

            # Try to update existing user
            query = '''
                INSERT INTO tts_user_preferences (user_id, voice_name, speed, pitch, language)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id) DO UPDATE SET
                    voice_name = COALESCE(EXCLUDED.voice_name, tts_user_preferences.voice_name),
                    speed = COALESCE(EXCLUDED.speed, tts_user_preferences.speed),
                    pitch = COALESCE(EXCLUDED.pitch, tts_user_preferences.pitch),
                    language = COALESCE(EXCLUDED.language, tts_user_preferences.language),
                    updated_at = CURRENT_TIMESTAMP
            '''

            await self.db.execute(
                query,
                user_id,
                voice_name or 'default',
                speed or 1.0,
                pitch or 1.0,
                language or 'en'
            )

            return True

        except Exception as e:
            logger.error(f'Failed to set preferences for user {user_id}: {e}')
            return False
