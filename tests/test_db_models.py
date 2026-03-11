"""Tests for TTS database models"""

import pytest
from unittest.mock import AsyncMock
from tts_module.db_models import (
    TTSMonitoredChannels,
    TTSUserPreferences,
    TTSUserSubscriptions,
    TTSVoiceClaims
)


class TestTTSMonitoredChannels:
    """Test TTSMonitoredChannels"""

    @pytest.mark.asyncio
    async def test_add_channel(self, mock_db):
        """Test adding a monitored channel"""
        channels = TTSMonitoredChannels(mock_db)
        result = await channels.add_channel(
            channel_id=123,
            guild_id=456,
            channel_name="general",
            added_by=789
        )
        assert result is True
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_channel_fails_on_exception(self, mock_db):
        """Test add_channel returns False on exception"""
        mock_db.execute.side_effect = Exception("DB error")
        channels = TTSMonitoredChannels(mock_db)

        result = await channels.add_channel(123, 456, "general", 789)
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_channel(self, mock_db):
        """Test removing a monitored channel"""
        channels = TTSMonitoredChannels(mock_db)
        result = await channels.remove_channel(channel_id=123)

        assert result is True
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_channel_monitored_true(self, mock_db):
        """Test checking if channel is monitored"""
        mock_db.fetch_one.return_value = {'channel_id': 123}
        channels = TTSMonitoredChannels(mock_db)

        result = await channels.is_channel_monitored(123)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_channel_monitored_false(self, mock_db):
        """Test channel not monitored"""
        mock_db.fetch_one.return_value = None
        channels = TTSMonitoredChannels(mock_db)

        result = await channels.is_channel_monitored(123)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_monitored_channels(self, mock_db):
        """Test getting all monitored channels for guild"""
        mock_db.fetch_all.return_value = [
            {
                'channel_id': 111,
                'channel_name': 'general',
                'added_by': 789,
                'created_at': '2024-01-01'
            }
        ]
        channels = TTSMonitoredChannels(mock_db)

        result = await channels.get_monitored_channels(guild_id=456)
        assert len(result) == 1
        assert result[0]['channel_id'] == 111

    @pytest.mark.asyncio
    async def test_get_all_monitored_channels(self, mock_db):
        """Test getting all monitored channels across all guilds"""
        mock_db.fetch_all.return_value = [
            {'channel_id': 111},
            {'channel_id': 222},
        ]
        channels = TTSMonitoredChannels(mock_db)

        result = await channels.get_all_monitored_channels()
        assert len(result) == 2
        assert 111 in result
        assert 222 in result


class TestTTSUserPreferences:
    """Test TTSUserPreferences"""

    @pytest.mark.asyncio
    async def test_get_preferences_found(self, mock_db):
        """Test getting user preferences when they exist"""
        mock_db.fetch_one.return_value = {
            'voice_name': 'F2',
            'speed': 1.5,
            'pitch': 1.0,
            'language': 'en'
        }
        prefs = TTSUserPreferences(mock_db)

        result = await prefs.get_preferences(user_id=123)
        assert result['voice_name'] == 'F2'
        assert result['speed'] == 1.5

    @pytest.mark.asyncio
    async def test_get_preferences_defaults(self, mock_db):
        """Test getting defaults when user not found"""
        mock_db.fetch_one.return_value = None
        prefs = TTSUserPreferences(mock_db)

        result = await prefs.get_preferences(user_id=123)
        assert result['voice_name'] == 'M1'
        assert result['speed'] == 1.0
        assert result['pitch'] == 1.0
        assert result['language'] == 'en'

    @pytest.mark.asyncio
    async def test_set_preferences_bounds_speed(self, mock_db):
        """Test speed is bounded to 0.5-2.0"""
        prefs = TTSUserPreferences(mock_db)

        await prefs.set_preferences(user_id=123, speed=0.1)
        # Speed should be clamped to 0.5
        call_args = mock_db.execute.call_args
        assert call_args[0][3] == 0.5  # speed parameter (4th arg after query)

        mock_db.reset_mock()
        await prefs.set_preferences(user_id=123, speed=3.0)
        # Speed should be clamped to 2.0
        call_args = mock_db.execute.call_args
        assert call_args[0][3] == 2.0

    @pytest.mark.asyncio
    async def test_set_preferences_bounds_pitch(self, mock_db):
        """Test pitch is bounded to 0.8-1.2"""
        prefs = TTSUserPreferences(mock_db)

        await prefs.set_preferences(user_id=123, pitch=0.5)
        call_args = mock_db.execute.call_args
        assert call_args[0][4] == 0.8  # pitch parameter (5th arg after query)

        mock_db.reset_mock()
        await prefs.set_preferences(user_id=123, pitch=1.5)
        call_args = mock_db.execute.call_args
        assert call_args[0][4] == 1.2

    @pytest.mark.asyncio
    async def test_set_preferences_invalid_language(self, mock_db):
        """Test invalid language defaults to en"""
        prefs = TTSUserPreferences(mock_db)

        await prefs.set_preferences(user_id=123, language="invalid")
        call_args = mock_db.execute.call_args
        assert call_args[0][5] == 'en'  # language parameter (6th arg after query)

    @pytest.mark.asyncio
    async def test_set_preferences_valid_languages(self, mock_db):
        """Test valid language codes are accepted"""
        prefs = TTSUserPreferences(mock_db)

        for lang in ['es', 'fr', 'de', 'ja', 'ko']:
            mock_db.reset_mock()
            await prefs.set_preferences(user_id=123, language=lang)
            call_args = mock_db.execute.call_args
            assert call_args[0][5] == lang  # 6th argument

    @pytest.mark.asyncio
    async def test_set_preferences_returns_true(self, mock_db):
        """Test set_preferences returns True on success"""
        prefs = TTSUserPreferences(mock_db)
        result = await prefs.set_preferences(user_id=123, speed=1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_set_preferences_fails_on_exception(self, mock_db):
        """Test set_preferences returns False on exception"""
        mock_db.execute.side_effect = Exception("DB error")
        prefs = TTSUserPreferences(mock_db)

        result = await prefs.set_preferences(user_id=123, speed=1.0)
        assert result is False


class TestTTSUserSubscriptions:
    """Test TTSUserSubscriptions"""

    @pytest.mark.asyncio
    async def test_grant_subscription(self, mock_db):
        """Test granting a subscription"""
        subs = TTSUserSubscriptions(mock_db)

        success, msg = await subs.grant_subscription(
            user_id=123,
            tier='voice_subscriber',
            granted_by=999
        )
        assert success is True
        assert '123' in msg

    @pytest.mark.asyncio
    async def test_revoke_subscription(self, mock_db):
        """Test revoking a subscription"""
        subs = TTSUserSubscriptions(mock_db)

        success, msg = await subs.revoke_subscription(user_id=123)
        assert success is True
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_subscription_found(self, mock_db):
        """Test getting subscription when it exists"""
        mock_db.fetch_one.return_value = {
            'id': 1,
            'subscription_tier': 'voice_subscriber',
            'subscribed_at': '2024-01-01',
            'expires_at': None,
            'is_active': True,
            'granted_by': 999,
            'notes': 'Test subscription'
        }
        subs = TTSUserSubscriptions(mock_db)

        result = await subs.get_subscription(user_id=123)
        assert result['tier'] == 'voice_subscriber'
        assert result['is_active'] is True

    @pytest.mark.asyncio
    async def test_get_subscription_not_found(self, mock_db):
        """Test getting subscription when it doesn't exist"""
        mock_db.fetch_one.return_value = None
        subs = TTSUserSubscriptions(mock_db)

        result = await subs.get_subscription(user_id=123)
        assert result is None

    @pytest.mark.asyncio
    async def test_is_subscribed_true(self, mock_db):
        """Test checking if user is subscribed (active)"""
        mock_db.fetch_one.return_value = {'id': 1}
        subs = TTSUserSubscriptions(mock_db)

        result = await subs.is_subscribed(user_id=123)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_subscribed_false(self, mock_db):
        """Test checking if user is not subscribed"""
        mock_db.fetch_one.return_value = None
        subs = TTSUserSubscriptions(mock_db)

        result = await subs.is_subscribed(user_id=123)
        assert result is False

    @pytest.mark.asyncio
    async def test_list_subscribers(self, mock_db):
        """Test listing all subscribers"""
        mock_db.fetch_all.return_value = [
            {
                'id': 1,
                'user_id': 111,
                'subscription_tier': 'voice_subscriber',
                'subscribed_at': '2024-01-01',
                'expires_at': None,
                'is_active': True,
                'granted_by': 999,
                'notes': 'First'
            }
        ]
        subs = TTSUserSubscriptions(mock_db)

        result = await subs.list_subscribers()
        assert len(result) == 1
        assert result[0]['user_id'] == 111

    @pytest.mark.asyncio
    async def test_list_expired_subscriptions(self, mock_db):
        """Test listing expired subscriptions"""
        mock_db.fetch_all.return_value = [
            {'id': 1, 'user_id': 123, 'expires_at': '2024-01-01'}
        ]
        subs = TTSUserSubscriptions(mock_db)

        result = await subs.list_expired_subscriptions()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_check_and_cleanup_expired(self, mock_db):
        """Test cleanup of expired subscriptions"""
        mock_db.fetch_all.return_value = [
            {'id': 1, 'user_id': 123, 'expires_at': '2024-01-01'}
        ]
        subs = TTSUserSubscriptions(mock_db)

        count = await subs.check_and_cleanup_expired()
        assert count == 1


class TestTTSVoiceClaims:
    """Test TTSVoiceClaims"""

    @pytest.mark.asyncio
    async def test_claim_voice_success(self, mock_db):
        """Test claiming a voice"""
        claims = TTSVoiceClaims(mock_db)

        success, msg = await claims.claim_voice(
            user_id=123,
            voice_id='premium_voice',
            subscription_id=1
        )
        assert success is True
        assert 'premium_voice' in msg

    @pytest.mark.asyncio
    async def test_claim_voice_duplicate_key(self, mock_db):
        """Test claiming a voice that's already claimed"""
        mock_db.execute.side_effect = Exception("duplicate key value violates unique constraint")
        mock_db.fetch_one.return_value = {'voice_owner': 999}  # Someone else claimed it

        claims = TTSVoiceClaims(mock_db)

        # First claim gets the voice owner lookup
        claims.get_voice_owner = AsyncMock(return_value=999)
        success, msg = await claims.claim_voice(
            user_id=123,
            voice_id='premium_voice',
            subscription_id=1
        )
        assert success is False

    @pytest.mark.asyncio
    async def test_release_voice_success(self, mock_db):
        """Test releasing a claimed voice"""
        mock_db.fetch_one.return_value = {'voice_id': 'premium_voice'}
        claims = TTSVoiceClaims(mock_db)

        success, msg, voice_id = await claims.release_voice(user_id=123)
        assert success is True
        assert voice_id == 'premium_voice'

    @pytest.mark.asyncio
    async def test_release_voice_none_claimed(self, mock_db):
        """Test releasing when no voice is claimed"""
        mock_db.fetch_one.return_value = None
        claims = TTSVoiceClaims(mock_db)

        success, msg, voice_id = await claims.release_voice(user_id=123)
        assert success is False
        assert voice_id is None
