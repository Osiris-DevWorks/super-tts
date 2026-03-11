"""
TTS Database Models
Manages super-tts schema in PostgreSQL database
"""

import logging
from db.db import DB

logger = logging.getLogger("super-tts")


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
                INSERT INTO super_tts.monitored_channels (channel_id, guild_id, channel_name, added_by)
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
            query = 'DELETE FROM super_tts.monitored_channels WHERE channel_id = $1'
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
            query = 'SELECT channel_id FROM super_tts.monitored_channels WHERE channel_id = $1'
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
                FROM super_tts.monitored_channels
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
            query = 'SELECT channel_id FROM super_tts.monitored_channels'
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
                FROM super_tts.user_preferences
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
                'voice_name': 'M1',
                'speed': 1.0,
                'pitch': 1.0,
                'language': 'en'
            }

        except Exception as e:
            logger.error(f'Failed to get preferences for user {user_id}: {e}')
            return {
                'voice_name': 'M1',
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
                INSERT INTO super_tts.user_preferences (user_id, voice_name, speed, pitch, language)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id) DO UPDATE SET
                    voice_name = COALESCE(EXCLUDED.voice_name, super_tts.user_preferences.voice_name),
                    speed = COALESCE(EXCLUDED.speed, super_tts.user_preferences.speed),
                    pitch = COALESCE(EXCLUDED.pitch, super_tts.user_preferences.pitch),
                    language = COALESCE(EXCLUDED.language, super_tts.user_preferences.language),
                    updated_at = CURRENT_TIMESTAMP
            '''

            await self.db.execute(
                query,
                user_id,
                voice_name or 'M1',
                speed or 1.0,
                pitch or 1.0,
                language or 'en'
            )

            return True

        except Exception as e:
            logger.error(f'Failed to set preferences for user {user_id}: {e}')
            return False


class TTSUserSubscriptions:
    """Manage user subscriptions for voice claiming feature"""

    def __init__(self, db: DB):
        """
        Initialize with database connection

        Args:
            db: Citizen-bot's DB instance
        """
        self.db = db

    async def grant_subscription(
        self,
        user_id: int,
        tier: str = 'voice_subscriber',
        granted_by: int = None,
        expires_at: str = None,
        notes: str = None
    ) -> tuple:
        """
        Grant a subscription to a user

        Args:
            user_id: Discord user ID
            tier: Subscription tier (default: 'voice_subscriber')
            granted_by: User ID of owner who granted subscription
            expires_at: ISO format datetime or None for no expiration
            notes: Optional notes from owner

        Returns:
            (success: bool, message: str)
        """
        try:
            query = '''
                INSERT INTO super_tts.user_subscriptions (user_id, subscription_tier, granted_by, expires_at, notes, is_active)
                VALUES ($1, $2, $3, $4, $5, TRUE)
                ON CONFLICT (user_id) DO UPDATE SET
                    is_active = TRUE,
                    subscription_tier = EXCLUDED.subscription_tier,
                    expires_at = EXCLUDED.expires_at,
                    granted_by = EXCLUDED.granted_by,
                    notes = EXCLUDED.notes,
                    updated_at = CURRENT_TIMESTAMP
            '''
            await self.db.execute(query, user_id, tier, granted_by, expires_at, notes)
            logger.info(f'Granted subscription to user {user_id}: tier={tier}, expires_at={expires_at}')
            return (True, f'Subscription granted to <@{user_id}> (tier: {tier})')

        except Exception as e:
            logger.error(f'Failed to grant subscription to user {user_id}: {e}')
            return (False, f'Failed to grant subscription: {e}')

    async def revoke_subscription(self, user_id: int) -> tuple:
        """
        Revoke a user's subscription

        Args:
            user_id: Discord user ID

        Returns:
            (success: bool, message: str)
        """
        try:
            query = '''
                UPDATE super_tts.user_subscriptions
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $1
            '''
            await self.db.execute(query, user_id)
            logger.info(f'Revoked subscription for user {user_id}')
            return (True, f'Subscription revoked for <@{user_id}>')

        except Exception as e:
            logger.error(f'Failed to revoke subscription for user {user_id}: {e}')
            return (False, f'Failed to revoke subscription: {e}')

    async def get_subscription(self, user_id: int) -> dict:
        """
        Get subscription details for a user

        Args:
            user_id: Discord user ID

        Returns:
            Dictionary with subscription details or None if not subscribed
        """
        try:
            query = '''
                SELECT id, subscription_tier, subscribed_at, expires_at, is_active, granted_by, notes
                FROM super_tts.user_subscriptions
                WHERE user_id = $1
            '''
            result = await self.db.fetch_one(query, user_id)

            if result:
                return {
                    'id': result['id'],
                    'user_id': user_id,
                    'tier': result['subscription_tier'],
                    'subscribed_at': result['subscribed_at'],
                    'expires_at': result['expires_at'],
                    'is_active': result['is_active'],
                    'granted_by': result['granted_by'],
                    'notes': result['notes']
                }

            return None

        except Exception as e:
            logger.error(f'Failed to get subscription for user {user_id}: {e}')
            return None

    async def is_subscribed(self, user_id: int) -> bool:
        """
        Check if user has an active subscription

        Args:
            user_id: Discord user ID

        Returns:
            True if user has active subscription
        """
        try:
            query = '''
                SELECT id FROM super_tts.user_subscriptions
                WHERE user_id = $1 AND is_active = TRUE
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            '''
            result = await self.db.fetch_one(query, user_id)
            return result is not None

        except Exception as e:
            logger.error(f'Failed to check subscription for user {user_id}: {e}')
            return False

    async def list_subscribers(self) -> list:
        """
        Get all active subscriptions

        Returns:
            List of subscription info dicts
        """
        try:
            query = '''
                SELECT id, user_id, subscription_tier, subscribed_at, expires_at, is_active, granted_by, notes
                FROM super_tts.user_subscriptions
                WHERE is_active = TRUE
                ORDER BY subscribed_at DESC
            '''
            rows = await self.db.fetch_all(query)

            return [
                {
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'tier': row['subscription_tier'],
                    'subscribed_at': row['subscribed_at'],
                    'expires_at': row['expires_at'],
                    'is_active': row['is_active'],
                    'granted_by': row['granted_by'],
                    'notes': row['notes']
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f'Failed to list subscribers: {e}')
            return []

    async def list_expired_subscriptions(self) -> list:
        """
        Get all subscriptions that have expired

        Returns:
            List of expired subscription IDs
        """
        try:
            query = '''
                SELECT id, user_id, expires_at
                FROM super_tts.user_subscriptions
                WHERE expires_at IS NOT NULL AND expires_at <= CURRENT_TIMESTAMP
                AND is_active = TRUE
            '''
            rows = await self.db.fetch_all(query)
            return [{'id': row['id'], 'user_id': row['user_id'], 'expires_at': row['expires_at']} for row in rows]

        except Exception as e:
            logger.error(f'Failed to list expired subscriptions: {e}')
            return []

    async def check_and_cleanup_expired(self) -> int:
        """
        Mark expired subscriptions as inactive and release their voices

        Returns:
            Count of expired subscriptions processed
        """
        try:
            # Get expired subscriptions
            expired = await self.list_expired_subscriptions()

            if not expired:
                return 0

            # Mark as inactive
            query = '''
                UPDATE super_tts.user_subscriptions
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE expires_at IS NOT NULL AND expires_at <= CURRENT_TIMESTAMP
                AND is_active = TRUE
            '''
            await self.db.execute(query)

            logger.info(f'Cleaned up {len(expired)} expired subscriptions')
            return len(expired)

        except Exception as e:
            logger.error(f'Failed to cleanup expired subscriptions: {e}')
            return 0

    async def update_subscription_notes(self, user_id: int, notes: str) -> tuple:
        """
        Update notes for a subscription

        Args:
            user_id: Discord user ID
            notes: Updated notes text

        Returns:
            (success: bool, message: str)
        """
        try:
            query = '''
                UPDATE super_tts.user_subscriptions
                SET notes = $1, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $2
            '''
            await self.db.execute(query, notes, user_id)
            return (True, f'Updated notes for <@{user_id}>')

        except Exception as e:
            logger.error(f'Failed to update notes for user {user_id}: {e}')
            return (False, f'Failed to update notes: {e}')


class TTSVoiceClaims:
    """Manage voice claims linked to active subscriptions"""

    def __init__(self, db: DB):
        """
        Initialize with database connection

        Args:
            db: Citizen-bot's DB instance
        """
        self.db = db

    async def claim_voice(self, user_id: int, voice_id: str, subscription_id: int, voice_description: str = None) -> tuple:
        """
        Claim a voice for a user

        Args:
            user_id: Discord user ID
            voice_id: Voice identifier
            subscription_id: Active subscription ID
            voice_description: Optional description

        Returns:
            (success: bool, message: str)
        """
        try:
            query = '''
                INSERT INTO super_tts.voice_claims (user_id, voice_id, subscription_id, voice_description)
                VALUES ($1, $2, $3, $4)
            '''
            await self.db.execute(query, user_id, voice_id, subscription_id, voice_description)
            logger.info(f'User {user_id} claimed voice {voice_id}')
            return (True, f'Successfully claimed voice **{voice_id}**')

        except Exception as e:
            if 'duplicate key' in str(e).lower():
                # Check if voice is already claimed
                owner = await self.get_voice_owner(voice_id)
                if owner:
                    return (False, f'Voice **{voice_id}** is already claimed by <@{owner}>')
                owner_id = await self.get_user_claimed_voice(user_id)
                if owner_id:
                    return (False, f'You already claimed voice **{owner_id}**. Release it first with `/tts claim-release`')
            logger.error(f'Failed to claim voice {voice_id} for user {user_id}: {e}')
            return (False, f'Failed to claim voice: {e}')

    async def release_voice(self, user_id: int) -> tuple:
        """
        Release a claimed voice

        Args:
            user_id: Discord user ID

        Returns:
            (success: bool, message: str, voice_id: str or None)
        """
        try:
            # Get the voice being released
            query = '''
                SELECT voice_id FROM super_tts.voice_claims
                WHERE user_id = $1 AND released_at IS NULL
            '''
            result = await self.db.fetch_one(query, user_id)

            if not result:
                return (False, 'You do not have a claimed voice', None)

            voice_id = result['voice_id']

            # Mark as released
            query = '''
                UPDATE super_tts.voice_claims
                SET released_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $1 AND released_at IS NULL
            '''
            await self.db.execute(query, user_id)
            logger.info(f'User {user_id} released voice {voice_id}')
            return (True, f'Released voice **{voice_id}**', voice_id)

        except Exception as e:
            logger.error(f'Failed to release voice for user {user_id}: {e}')
            return (False, f'Failed to release voice: {e}', None)

    async def get_claimed_voices(self, user_id: int) -> list:
        """
        Get all claimed voices for a user

        Args:
            user_id: Discord user ID

        Returns:
            List of claimed voice IDs
        """
        try:
            query = '''
                SELECT voice_id FROM super_tts.voice_claims
                WHERE user_id = $1 AND released_at IS NULL
            '''
            rows = await self.db.fetch_all(query, user_id)
            return [row['voice_id'] for row in rows]

        except Exception as e:
            logger.error(f'Failed to get claimed voices for user {user_id}: {e}')
            return []

    async def get_voice_owner(self, voice_id: str) -> int:
        """
        Get the user ID who owns a claimed voice

        Args:
            voice_id: Voice identifier

        Returns:
            User ID or None if not claimed
        """
        try:
            query = '''
                SELECT user_id FROM super_tts.voice_claims
                WHERE voice_id = $1 AND released_at IS NULL
            '''
            result = await self.db.fetch_one(query, voice_id)
            return result['user_id'] if result else None

        except Exception as e:
            logger.error(f'Failed to get voice owner for {voice_id}: {e}')
            return None

    async def get_user_claimed_voice(self, user_id: int) -> str:
        """
        Get the voice claimed by a user

        Args:
            user_id: Discord user ID

        Returns:
            Voice ID or None if no claimed voice
        """
        try:
            query = '''
                SELECT voice_id FROM super_tts.voice_claims
                WHERE user_id = $1 AND released_at IS NULL
            '''
            result = await self.db.fetch_one(query, user_id)
            return result['voice_id'] if result else None

        except Exception as e:
            logger.error(f'Failed to get claimed voice for user {user_id}: {e}')
            return None

    async def get_all_claimed_voices(self) -> dict:
        """
        Get all active voice claims

        Returns:
            Dict mapping voice_id -> user_id
        """
        try:
            query = '''
                SELECT voice_id, user_id FROM super_tts.voice_claims
                WHERE released_at IS NULL
            '''
            rows = await self.db.fetch_all(query)
            return {row['voice_id']: row['user_id'] for row in rows}

        except Exception as e:
            logger.error(f'Failed to get all claimed voices: {e}')
            return {}

    async def is_voice_claimed(self, voice_id: str) -> bool:
        """
        Check if a voice is claimed

        Args:
            voice_id: Voice identifier

        Returns:
            True if voice is claimed
        """
        owner = await self.get_voice_owner(voice_id)
        return owner is not None

    async def get_unclaimed_voices(self, all_voices: dict) -> dict:
        """
        Filter out claimed voices from available voices

        Args:
            all_voices: Dictionary of all available voices

        Returns:
            Dictionary with only unclaimed voices
        """
        try:
            claimed = await self.get_all_claimed_voices()
            return {voice_id: voice for voice_id, voice in all_voices.items() if voice_id not in claimed}

        except Exception as e:
            logger.error(f'Failed to get unclaimed voices: {e}')
            return all_voices

    async def user_has_claimed_voice(self, user_id: int) -> bool:
        """
        Check if user has a claimed voice

        Args:
            user_id: Discord user ID

        Returns:
            True if user has claimed a voice
        """
        voice = await self.get_user_claimed_voice(user_id)
        return voice is not None

    async def release_voices_for_subscription(self, subscription_id: int) -> int:
        """
        Release all voices claimed by a subscription (e.g., on unsubscribe)

        Args:
            subscription_id: Subscription ID

        Returns:
            Count of voices released
        """
        try:
            # Get voices for this subscription
            query = '''
                SELECT COUNT(*) as count FROM super_tts.voice_claims
                WHERE subscription_id = $1 AND released_at IS NULL
            '''
            result = await self.db.fetch_one(query, subscription_id)
            count = result['count'] if result else 0

            # Release all
            query = '''
                UPDATE super_tts.voice_claims
                SET released_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE subscription_id = $1 AND released_at IS NULL
            '''
            await self.db.execute(query, subscription_id)
            logger.info(f'Released {count} voices for subscription {subscription_id}')
            return count

        except Exception as e:
            logger.error(f'Failed to release voices for subscription {subscription_id}: {e}')
            return 0
