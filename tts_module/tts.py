"""
TTS Text-to-Speech Cog for Super TTS Bot
Integrates Supertonic for high-quality voice synthesis
Uses PostgreSQL database with super_tts schema
"""

import logging
import asyncio
import time
import traceback
from pathlib import Path

import discord
from discord.ext import commands, tasks
from discord import app_commands

from tts.engine_factory import TTSEngineFactory
from tts.audio_pipeline import AudioPipeline, PCMAudioSource
from utils.queue_manager import QueueManager, QueuedMessage
from tts_module.db_models import TTSMonitoredChannels, TTSUserPreferences, TTSUserSubscriptions, TTSVoiceClaims
from utils.config_loader import ConfigLoader
from common.roles import has_any_role

logger = logging.getLogger("super-tts")


async def is_admin_or_owner(interaction: discord.Interaction) -> bool:
    """Check if user is Admin role or bot owner"""
    # Check if bot owner
    if interaction.user.id == interaction.client.owner_id:
        return True

    # Check if has Admin role
    admin_role = discord.utils.find(lambda r: r.name == "Admin", interaction.guild.roles)
    if admin_role and admin_role in interaction.user.roles:
        return True

    return False


class TTS(commands.Cog):
    """Text-to-Speech voice synthesis cog"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = None  # Database connection will be passed from main.py

        # TTS components
        self.tts_engine = None
        self.pipeline = None
        self.queue_manager = None
        self.monitored_channels = None  # Requires database connection
        self.user_preferences = None    # Requires database connection
        self.user_subscriptions = None  # Requires database connection
        self.voice_claims = None        # Requires database connection
        self.config = None
        self.initialized = False

        # Rate limiting: track last TTS message per user per guild
        self.user_tts_cooldown = {}  # {(guild_id, user_id): timestamp}
        self.tts_cooldown_seconds = 2.0  # Minimum seconds between TTS messages
        self._db_models_initialized = False

    def _ensure_db_models(self):
        """Lazily initialize database models after main.py sets self.db"""
        if not self._db_models_initialized and self.db is not None:
            self.monitored_channels = TTSMonitoredChannels(self.db)
            self.user_preferences = TTSUserPreferences(self.db)
            self.user_subscriptions = TTSUserSubscriptions(self.db)
            self.voice_claims = TTSVoiceClaims(self.db)
            self._db_models_initialized = True
            logger.info("TTS database models initialized")

    async def cog_load(self):
        """Initialize TTS components when cog loads"""
        try:
            logger.info("Initializing TTS Engine...")

            # Load config
            self.config = ConfigLoader(Path('config/config.yaml'))

            # Get model name from config (default to xtts_v2 for backward compatibility)
            model_name = self.config.get('tts.model', 'xtts_v2')

            # Get engine-specific configuration
            engines_config = self.config.get('tts.engines', {})
            engine_config = engines_config.get(model_name, {})

            # Create TTS engine using factory pattern
            self.tts_engine = TTSEngineFactory.create(
                model_name=model_name,
                config=engine_config
            )

            logger.info(f'Using TTS model: {self.tts_engine.model_name} on device: {self.tts_engine.device}')

            # Warmup if configured (run in thread pool to avoid blocking event loop)
            if self.config.get('tts.warmup', True):
                logger.info('Warming up TTS model...')
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.tts_engine.warmup)

            # Initialize audio pipeline
            self.pipeline = AudioPipeline(self.tts_engine)

            # Ensure database models are initialized
            self._ensure_db_models()

            # Initialize queue manager with concurrent processing limit
            max_concurrent = self.config.get('tts.max_concurrent', 4)
            self.queue_manager = QueueManager(max_concurrent=max_concurrent)

            # Set up queue processor
            async def process_queue(guild_id: int, message: QueuedMessage):
                """Process a queued TTS message with streaming synthesis"""
                try:
                    voice_file = Path(message.voice_file_path)
                    guild = self.bot.get_guild(guild_id)

                    if not guild:
                        logger.error(f'Guild {guild_id} not found')
                        return

                    if not guild.voice_client:
                        logger.error(f'Voice client not connected for guild {guild_id}')
                        return

                    if not guild.voice_client.is_connected():
                        logger.error(f'Voice client not actually connected for guild {guild_id}')
                        return

                    # Wait for current playback to finish
                    while guild.voice_client and guild.voice_client.is_playing():
                        await asyncio.sleep(0.1)

                    # Check again if still connected
                    if not guild.voice_client or not guild.voice_client.is_connected():
                        logger.warning(f'Voice client disconnected before synthesis for: {message.text}')
                        return

                    def on_playback_error(error):
                        if error:
                            logger.error(f'Playback error: {error}')

                    # Synthesize and convert with mixed precision optimization (Task #1)
                    pcm_audio = await self.pipeline.synthesize_and_convert(
                        text=message.text,
                        voice_file=voice_file,
                        speed=message.speed,
                        language=message.language,
                        voice_name=message.voice_name
                    )

                    if not pcm_audio:
                        logger.error(f'Failed to synthesize audio for: {message.text}')
                        return

                    source = PCMAudioSource(pcm_audio, sample_rate=48000, channels=2)

                    # Check again if still connected
                    if not guild.voice_client or not guild.voice_client.is_connected():
                        logger.warning(f'Voice client disconnected during synthesis for: {message.text}')
                        return

                    guild.voice_client.play(source, after=on_playback_error)
                    logger.info(f'Playing TTS for {message.user_name}: {message.text[:50]}...')

                except Exception as e:
                    logger.error(f'Error processing queue message: {e}')
                    logger.error(traceback.format_exc())

            self.queue_manager.set_processor(process_queue)
            self.initialized = True
            logger.info("TTS Engine initialized successfully")

        except Exception as e:
            logger.error(f'Failed to initialize TTS Engine: {e}')
            self.initialized = False

        # Start background cleanup task
        self.cleanup_expired_subscriptions.start()

    @tasks.loop(hours=1)
    async def cleanup_expired_subscriptions(self):
        """Background task to periodically cleanup expired subscriptions and release voices"""
        try:
            if not self.user_subscriptions:
                return

            # Check and cleanup expired subscriptions
            expired_count = await self.user_subscriptions.check_and_cleanup_expired()

            if expired_count > 0:
                # Release voices for all expired subscriptions
                expired_subs = await self.user_subscriptions.list_expired_subscriptions()
                for sub_info in expired_subs:
                    await self.voice_claims.release_voices_for_subscription(sub_info['id'])

                logger.info(f'Cleanup task: Processed {expired_count} expired subscriptions')

        except Exception as e:
            logger.error(f'Error in cleanup_expired_subscriptions task: {e}')

    @cleanup_expired_subscriptions.before_loop
    async def before_cleanup_expired_subscriptions(self):
        """Wait for bot to be ready before starting cleanup task"""
        await self.bot.wait_until_ready()

    # TTS Command Group
    tts_group = app_commands.Group(name="tts", description="Text-to-Speech commands")

    # Setup subgroup for admin commands
    setup_group = app_commands.Group(
        name="setup",
        description="Admin setup commands for TTS",
        parent=tts_group
    )

    # Voice subgroup for voice selection
    voice_group = app_commands.Group(
        name="voice",
        description="Manage TTS voice selection",
        parent=tts_group
    )

    # Admin voice subgroup for subscription management
    admin_voice_group = app_commands.Group(
        name="admin-voice",
        description="Admin commands for voice subscription management",
        parent=tts_group
    )

    @setup_group.command(name="add", description="Add a channel for auto-TTS")
    @app_commands.describe(channel="Text channel to enable auto-TTS in")
    @has_any_role("Admin", "Tester", "Sentinel Prime", "Sentinel Supreme", "Sentinel Commander")
    async def setup_add(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Add a channel to auto-TTS monitoring"""
        if not self.initialized:
            await interaction.response.send_message("TTS engine not initialized", ephemeral=True)
            return

        # Ensure database models are initialized
        self._ensure_db_models()

        try:
            # Check if already monitored
            is_monitored = await self.monitored_channels.is_channel_monitored(channel.id)
            if is_monitored:
                await interaction.response.send_message(
                    f'Channel {channel.mention} is already monitored!',
                    ephemeral=True
                )
                return

            # Add to database
            success = await self.monitored_channels.add_channel(
                channel_id=channel.id,
                guild_id=interaction.guild_id,
                channel_name=channel.name,
                added_by=interaction.user.id
            )

            if success:
                embed = discord.Embed(
                    title="Channel Added",
                    description=f'{channel.mention} is now monitored for auto-TTS',
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="How it works",
                    value=(
                        f"Users with the **TTS** role can now:\n"
                        f"1. Join a voice channel\n"
                        f"2. Type in {channel.mention}\n"
                        f"3. Messages automatically convert to speech!\n\n"
                        f"⚠️ Unlike Discord native TTS, this works even if users don't have the text channel open."
                    ),
                    inline=False
                )
                embed.set_footer(text=f"Added by {interaction.user.name}")

                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f'Added monitored channel: {channel.name} by {interaction.user}')
            else:
                await interaction.response.send_message(
                    f'Failed to add channel {channel.mention}',
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f'Error adding monitored channel: {e}')
            await interaction.response.send_message(f'Error: {e}', ephemeral=True)

    @setup_group.command(name="remove", description="Remove a channel from auto-TTS")
    @app_commands.describe(channel="Text channel to disable auto-TTS in")
    @has_any_role("Admin", "Tester", "Sentinel Prime", "Sentinel Supreme", "Sentinel Commander")
    async def setup_remove(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Remove a channel from auto-TTS monitoring"""
        if not self.initialized:
            await interaction.response.send_message("TTS engine not initialized", ephemeral=True)
            return

        # Ensure database models are initialized
        self._ensure_db_models()

        try:
            is_monitored = await self.monitored_channels.is_channel_monitored(channel.id)
            if not is_monitored:
                await interaction.response.send_message(
                    f'Channel {channel.mention} is not currently monitored!',
                    ephemeral=True
                )
                return

            success = await self.monitored_channels.remove_channel(channel.id)

            if success:
                embed = discord.Embed(
                    title="Channel Removed",
                    description=f'{channel.mention} is no longer monitored for auto-TTS',
                    color=discord.Color.red()
                )
                embed.set_footer(text=f"Removed by {interaction.user.name}")

                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f'Removed monitored channel: {channel.name} by {interaction.user}')
            else:
                await interaction.response.send_message(
                    f'Failed to remove channel {channel.mention}',
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f'Error removing monitored channel: {e}')
            await interaction.response.send_message(f'Error: {e}', ephemeral=True)

    @setup_group.command(name="list", description="List all monitored channels")
    @has_any_role("Admin", "Tester", "Sentinel Prime", "Sentinel Supreme", "Sentinel Commander")
    async def setup_list(self, interaction: discord.Interaction):
        """List all auto-TTS channels in this guild"""
        if not self.initialized:
            await interaction.response.send_message("TTS engine not initialized", ephemeral=True)
            return

        # Ensure database models are initialized
        self._ensure_db_models()

        try:
            channels = await self.monitored_channels.get_monitored_channels(interaction.guild_id)

            if not channels:
                await interaction.response.send_message(
                    'No channels are currently monitored for auto-TTS.',
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title="Auto-TTS Monitored Channels",
                color=discord.Color.blue()
            )

            for channel_info in channels:
                channel_id = channel_info['channel_id']
                channel_name = channel_info['channel_name']
                added_by = channel_info['added_by']

                try:
                    channel = interaction.guild.get_channel(channel_id)
                    mention = channel.mention if channel else f"#{channel_name} (ID: {channel_id})"
                except (AttributeError, TypeError):
                    mention = f"#{channel_name} (ID: {channel_id})"

                try:
                    user = await self.bot.fetch_user(added_by)
                    added_by_name = user.name
                except (discord.NotFound, discord.Forbidden):
                    added_by_name = f"User ID: {added_by}"

                embed.add_field(
                    name=mention,
                    value=f"Added by: {added_by_name}",
                    inline=False
                )

            embed.set_footer(text=f"Total: {len(channels)} channel(s)")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f'Error listing monitored channels: {e}')
            await interaction.response.send_message(f'Error: {e}', ephemeral=True)

    # ========== Admin Voice Subscription Commands ==========

    @admin_voice_group.command(name="grant-subscription", description="Grant a user voice claiming subscription")
    @app_commands.describe(
        user="User to grant subscription to",
        tier="Subscription tier (default: voice_subscriber)",
        expires_at="Expiration date in ISO format (YYYY-MM-DD) or None for no expiration"
    )
    @app_commands.check(is_admin_or_owner)
    async def grant_subscription(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        tier: str = "voice_subscriber",
        expires_at: str = None
    ):
        """Grant a voice subscription to a user"""
        if not self.initialized:
            await interaction.response.send_message("TTS engine not initialized", ephemeral=True)
            return

        # Ensure database models are initialized
        self._ensure_db_models()

        try:
            success, message = await self.user_subscriptions.grant_subscription(
                user_id=user.id,
                tier=tier,
                granted_by=interaction.user.id,
                expires_at=expires_at,
                notes=None
            )

            if success:
                embed = discord.Embed(
                    title="✅ Subscription Granted",
                    description=message,
                    color=discord.Color.green()
                )
                embed.add_field(name="User", value=user.mention)
                embed.add_field(name="Tier", value=tier)
                if expires_at:
                    embed.add_field(name="Expires", value=expires_at)
                else:
                    embed.add_field(name="Expires", value="Never")
                embed.add_field(name="Granted by", value=interaction.user.mention)

                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f'Admin {interaction.user} granted subscription to {user}')
            else:
                await interaction.response.send_message(f"❌ {message}", ephemeral=True)

        except Exception as e:
            logger.error(f'Failed to grant subscription: {e}')
            await interaction.response.send_message(f'Error: {e}', ephemeral=True)

    @admin_voice_group.command(name="revoke-subscription", description="Revoke a user's subscription")
    @app_commands.describe(user="User whose subscription to revoke")
    @app_commands.check(is_admin_or_owner)
    async def revoke_subscription(self, interaction: discord.Interaction, user: discord.User):
        """Revoke a user's subscription"""
        if not self.initialized:
            await interaction.response.send_message("TTS engine not initialized", ephemeral=True)
            return

        # Ensure database models are initialized
        self._ensure_db_models()

        try:
            # Release any claimed voices first
            claimed_voice = await self.voice_claims.get_user_claimed_voice(user.id)

            success, message = await self.user_subscriptions.revoke_subscription(user.id)

            if success:
                # Release voice if user had one
                if claimed_voice:
                    await self.voice_claims.release_voice(user.id)
                    voice_note = f"\n**Claimed voice released:** {claimed_voice}"
                else:
                    voice_note = ""

                embed = discord.Embed(
                    title="✅ Subscription Revoked",
                    description=f"{message}{voice_note}",
                    color=discord.Color.orange()
                )
                embed.add_field(name="User", value=user.mention)
                embed.add_field(name="Revoked by", value=interaction.user.mention)

                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f'Admin {interaction.user} revoked subscription for {user}')
            else:
                await interaction.response.send_message(f"❌ {message}", ephemeral=True)

        except Exception as e:
            logger.error(f'Failed to revoke subscription: {e}')
            await interaction.response.send_message(f'Error: {e}', ephemeral=True)

    @admin_voice_group.command(name="list-subscriptions", description="List all active subscriptions")
    @app_commands.check(is_admin_or_owner)
    async def list_subscriptions(self, interaction: discord.Interaction):
        """List all active voice claiming subscriptions"""
        if not self.initialized:
            await interaction.response.send_message("TTS engine not initialized", ephemeral=True)
            return

        try:
            subs = await self.user_subscriptions.list_subscribers()

            if not subs:
                await interaction.response.send_message(
                    "No active subscriptions found.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title="Active Voice Subscriptions",
                color=discord.Color.blue()
            )

            for sub in subs:
                user_id = sub['user_id']
                tier = sub['tier']
                granted_date = sub['subscribed_at'].strftime('%Y-%m-%d') if sub['subscribed_at'] else 'Unknown'
                expires = sub['expires_at'].strftime('%Y-%m-%d') if sub['expires_at'] else 'Never'

                # Get claimed voice if any
                claimed_voice = await self.voice_claims.get_user_claimed_voice(user_id)
                claimed_text = f"\n**Claimed Voice:** {claimed_voice}" if claimed_voice else "\n**Claimed Voice:** None"

                try:
                    user = await self.bot.fetch_user(user_id)
                    user_name = user.name
                except:
                    user_name = f"ID: {user_id}"

                embed.add_field(
                    name=f"{user_name}",
                    value=f"**Tier:** {tier}\n**Granted:** {granted_date}\n**Expires:** {expires}{claimed_text}",
                    inline=False
                )

            embed.set_footer(text=f"Total: {len(subs)} subscription(s)")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f'Failed to list subscriptions: {e}')
            await interaction.response.send_message(f'Error: {e}', ephemeral=True)

    @admin_voice_group.command(name="subscription-info", description="Show detailed subscription info for a user")
    @app_commands.describe(user="User to check subscription for")
    @app_commands.check(is_admin_or_owner)
    async def subscription_info(self, interaction: discord.Interaction, user: discord.User):
        """Get detailed subscription information for a user"""
        if not self.initialized:
            await interaction.response.send_message("TTS engine not initialized", ephemeral=True)
            return

        try:
            sub_info = await self.user_subscriptions.get_subscription(user.id)

            if not sub_info:
                await interaction.response.send_message(
                    f"{user.mention} does not have an active subscription.",
                    ephemeral=True
                )
                return

            # Get claimed voice if any
            claimed_voice = await self.voice_claims.get_user_claimed_voice(user.id)

            embed = discord.Embed(
                title=f"Subscription Info: {user.name}",
                color=discord.Color.blue()
            )

            embed.add_field(name="User", value=user.mention, inline=False)
            embed.add_field(name="Tier", value=sub_info['tier'])
            embed.add_field(name="Status", value="✅ Active" if sub_info['is_active'] else "❌ Inactive")
            embed.add_field(name="Subscribed", value=sub_info['subscribed_at'].strftime('%Y-%m-%d %H:%M:%S'))
            expires = sub_info['expires_at'].strftime('%Y-%m-%d') if sub_info['expires_at'] else 'Never'
            embed.add_field(name="Expires", value=expires)
            embed.add_field(name="Claimed Voice", value=claimed_voice or "None", inline=False)

            if sub_info['notes']:
                embed.add_field(name="Notes", value=sub_info['notes'], inline=False)

            if sub_info['granted_by']:
                try:
                    granted_by_user = await self.bot.fetch_user(sub_info['granted_by'])
                    embed.add_field(name="Granted by", value=granted_by_user.mention)
                except:
                    embed.add_field(name="Granted by", value=f"ID: {sub_info['granted_by']}")

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f'Failed to get subscription info: {e}')
            await interaction.response.send_message(f'Error: {e}', ephemeral=True)

    @admin_voice_group.command(name="cleanup-expired", description="Manually cleanup expired subscriptions")
    @app_commands.check(is_admin_or_owner)
    async def cleanup_expired_subscriptions_cmd(self, interaction: discord.Interaction):
        """Manually trigger cleanup of expired subscriptions"""
        if not self.initialized:
            await interaction.response.send_message("TTS engine not initialized", ephemeral=True)
            return

        try:
            await interaction.response.defer(ephemeral=True)

            # Run cleanup
            expired_count = await self.user_subscriptions.check_and_cleanup_expired()

            # Release voices for expired subscriptions
            expired_subs = await self.user_subscriptions.list_expired_subscriptions()
            voices_released = 0
            for sub_info in expired_subs:
                count = await self.voice_claims.release_voices_for_subscription(sub_info['id'])
                voices_released += count

            embed = discord.Embed(
                title="✅ Cleanup Completed",
                color=discord.Color.green()
            )
            embed.add_field(name="Subscriptions Processed", value=str(expired_count))
            embed.add_field(name="Voices Released", value=str(voices_released))
            embed.add_field(name="Executed by", value=interaction.user.mention)

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f'Admin {interaction.user} ran manual subscription cleanup: {expired_count} subs, {voices_released} voices')

        except Exception as e:
            logger.error(f'Failed to cleanup expired subscriptions: {e}')
            await interaction.followup.send(f'Error: {e}', ephemeral=True)

    @admin_voice_group.command(name="reassign-voice", description="Reassign any voice to any subscribed user")
    @app_commands.describe(
        voice="Voice ID to reassign (e.g., Tichro, M1, F2)",
        user="User to assign the voice to"
    )
    @app_commands.check(is_admin_or_owner)
    async def reassign_voice(self, interaction: discord.Interaction, voice: str, user: discord.User):
        """Force reassign a voice to a user (admin only)"""
        if not self.initialized:
            await interaction.response.send_message("TTS engine not initialized", ephemeral=True)
            return

        # Ensure database models are initialized
        self._ensure_db_models()

        try:
            await interaction.response.defer(ephemeral=True)

            # Get available voices
            if not hasattr(self.tts_engine, 'AVAILABLE_VOICES'):
                await interaction.followup.send(
                    "Current TTS engine does not support voice selection",
                    ephemeral=True
                )
                return

            voices = self.tts_engine.AVAILABLE_VOICES

            # Find voice case-insensitively
            voice_lower = voice.lower()
            matched_voice = None
            for available_voice in voices.keys():
                if available_voice.lower() == voice_lower:
                    matched_voice = available_voice
                    break

            if matched_voice is None:
                available = ', '.join(sorted(voices.keys()))
                await interaction.followup.send(
                    f'Invalid voice **{voice}**\nAvailable: {available}',
                    ephemeral=True
                )
                return

            voice = matched_voice

            # Check if voice is protected (cannot be reassigned)
            protected_voices = ['M1', 'M2', 'M3', 'M4', 'M5', 'F1', 'F2', 'F3', 'F4', 'F5']
            if voice in protected_voices:
                await interaction.followup.send(
                    f'Voice **{voice}** is a public voice and cannot be reassigned.',
                    ephemeral=True
                )
                return

            # Check if target user has an active subscription
            is_subscribed = await self.user_subscriptions.is_subscribed(user.id)
            if not is_subscribed:
                await interaction.followup.send(
                    f'{user.mention} does not have an active subscription. Grant them a subscription first.',
                    ephemeral=True
                )
                return

            # Get target user's subscription
            sub_info = await self.user_subscriptions.get_subscription(user.id)

            # Release voice if currently claimed by someone else
            current_owner = await self.voice_claims.get_voice_owner(voice)
            if current_owner and current_owner != user.id:
                await self.voice_claims.release_voice(current_owner)
                try:
                    previous_user = await self.bot.fetch_user(current_owner)
                    previous_name = previous_user.mention
                except:
                    previous_name = f"User {current_owner}"

                # Reset previous owner's voice to M1
                await self.user_preferences.set_preferences(current_owner, voice_name='M1')
                previous_note = f"\n**Released from:** {previous_name}"
            else:
                previous_note = ""

            # Release any previously claimed voice from target user
            user_previous_voice = await self.voice_claims.get_user_claimed_voice(user.id)
            if user_previous_voice:
                await self.voice_claims.release_voice(user.id)
                released_note = f"\n**Released previous voice:** {user_previous_voice}"
            else:
                released_note = ""

            # Claim the voice for the target user
            success, message = await self.voice_claims.claim_voice(
                user.id,
                voice,
                sub_info['id'],
                voice_description=voices[voice]
            )

            if success:
                # Auto-set as preferred voice
                await self.user_preferences.set_preferences(user.id, voice_name=voice)

                embed = discord.Embed(
                    title="✅ Voice Reassigned",
                    description=f"{message}",
                    color=discord.Color.green()
                )
                embed.add_field(name="Voice", value=f"**{voice}** - {voices[voice]}", inline=False)
                embed.add_field(name="Assigned to", value=user.mention)
                embed.add_field(name="Reassigned by", value=interaction.user.mention)
                if previous_note:
                    embed.add_field(name="Previous Owner", value=previous_note.strip(), inline=False)
                if released_note:
                    embed.add_field(name="Previous Voice Released", value=released_note.strip(), inline=False)

                await interaction.followup.send(embed=embed, ephemeral=True)
                logger.info(f'Admin {interaction.user} reassigned voice {voice} to {user}')
            else:
                await interaction.followup.send(
                    f"❌ Failed to reassign voice: {message}",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f'Failed to reassign voice: {e}')
            await interaction.followup.send(f'Error: {e}', ephemeral=True)


    @tts_group.command(name="speed", description="Adjust speech speed")
    @app_commands.describe(speed="Speed multiplier (0.5 = slow, 1.0 = normal, 2.0 = fast)")
    async def speed(self, interaction: discord.Interaction, speed: float):
        """Set user's speech speed"""
        if not self.initialized:
            await interaction.response.send_message("TTS engine not initialized", ephemeral=True)
            return

        try:
            # Validate speed
            if speed < 0.5 or speed > 2.0:
                await interaction.response.send_message(
                    'Speed must be between 0.5 and 2.0',
                    ephemeral=True
                )
                return

            # Save preference
            success = await self.user_preferences.set_preferences(
                interaction.user.id,
                speed=speed
            )

            if success:
                await interaction.response.send_message(
                    f'Speed set to **{speed}x**',
                    ephemeral=True
                )
                logger.info(f'User {interaction.user} set speed to {speed}')
            else:
                await interaction.response.send_message(
                    'Failed to save speed preference',
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f'Failed to set speed: {e}')
            await interaction.response.send_message(f'Error: {e}', ephemeral=True)

    @voice_group.command(name="list", description="List available TTS voices")
    async def voice_list(self, interaction: discord.Interaction):
        """List all available voices with descriptions"""
        if not self.initialized:
            await interaction.response.send_message("TTS engine not initialized", ephemeral=True)
            return

        # Ensure database models are initialized
        self._ensure_db_models()

        try:
            # Get available voices from engine
            if hasattr(self.tts_engine, 'AVAILABLE_VOICES'):
                voices = self.tts_engine.AVAILABLE_VOICES
            else:
                await interaction.response.send_message(
                    f"Current TTS engine ({self.tts_engine.model_name}) does not support voice selection",
                    ephemeral=True
                )
                return

            # Check user subscription status
            is_subscribed = await self.user_subscriptions.is_subscribed(interaction.user.id)
            user_claimed_voice = None
            all_claimed_voices = {}

            if is_subscribed:
                user_claimed_voice = await self.voice_claims.get_user_claimed_voice(interaction.user.id)
                all_claimed_voices = await self.voice_claims.get_all_claimed_voices()

            # Create embed with voice options
            embed = discord.Embed(
                title='Available TTS Voices',
                description=f'Using {self.tts_engine.model_name} engine',
                color=discord.Color.blue()
            )

            # Add subscription status
            if is_subscribed:
                sub_info = await self.user_subscriptions.get_subscription(interaction.user.id)
                expires = sub_info['expires_at'].strftime('%Y-%m-%d') if sub_info['expires_at'] else 'Never'
                embed.add_field(
                    name="📋 Your Subscription Status",
                    value=f"✅ Active (Tier: {sub_info['tier']})\nExpires: {expires}",
                    inline=False
                )
            else:
                embed.add_field(
                    name="📋 Subscription Status",
                    value="❌ Not subscribed\nAsk the server owner to grant you subscription access to claim exclusive voices!",
                    inline=False
                )

            # Protected voices that are always public and cannot be claimed
            protected_voices = ['M1', 'M2', 'M3', 'M4', 'M5', 'F1', 'F2', 'F3', 'F4', 'F5']

            # Show claimed voices section
            if is_subscribed and user_claimed_voice:
                embed.add_field(
                    name="✨ Your Claimed Voice",
                    value=f"**{user_claimed_voice}** - {voices.get(user_claimed_voice, 'N/A')}\n*(Exclusive for you while subscribed)*",
                    inline=False
                )

            # Show always-public voices
            public_voices = {v: desc for v, desc in voices.items() if v in protected_voices}
            if public_voices:
                embed.add_field(
                    name="🔓 Public Voices (Always Available - Cannot Claim)",
                    value="\n".join([f"`{v}` - {desc}" for v, desc in sorted(public_voices.items())]),
                    inline=False
                )

            # Show claimable unclaimed voices
            if is_subscribed:
                claimable_unclaimed = {v: desc for v, desc in voices.items()
                                      if v not in all_claimed_voices and v not in protected_voices}
            else:
                claimable_unclaimed = {v: desc for v, desc in voices.items() if v not in protected_voices}

            if claimable_unclaimed:
                claim_status = "(Available to claim)" if is_subscribed else "(Use `/tts voice set` to use)"
                embed.add_field(
                    name=f"🎤 Claimable Voices {claim_status}",
                    value="\n".join([f"`{v}` - {desc}" for v, desc in sorted(claimable_unclaimed.items())]),
                    inline=False
                )

            # Note: We don't show claimed voices that the user doesn't own
            # This prevents harassment and keeps voice ownership private

            # Add usage instructions
            if is_subscribed:
                embed.add_field(
                    name="Usage",
                    value="""
• `/tts voice claim-voice <voice>` - Claim an exclusive voice (1 per subscription)
• `/tts voice claim-release` - Release your claimed voice
• `/tts voice set <voice>` - Change your voice to any unclaimed voice or your claimed voice
                    """,
                    inline=False
                )
            else:
                embed.add_field(
                    name="Usage",
                    value="Use `/tts voice set <voice_id>` to change your voice to any public voice",
                    inline=False
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f'Failed to list voices: {e}')
            await interaction.response.send_message(f'Error: {e}', ephemeral=True)

    @voice_group.command(name="set", description="Change your TTS voice")
    @app_commands.describe(voice="Voice ID (e.g., M1, F2, M4)")
    async def voice_set(self, interaction: discord.Interaction, voice: str):
        """Set user's preferred voice"""
        if not self.initialized:
            await interaction.response.send_message("TTS engine not initialized", ephemeral=True)
            return

        # Ensure database models are initialized
        self._ensure_db_models()

        try:
            # Get available voices
            if not hasattr(self.tts_engine, 'AVAILABLE_VOICES'):
                await interaction.response.send_message(
                    f"Current TTS engine does not support voice selection",
                    ephemeral=True
                )
                return

            voices = self.tts_engine.AVAILABLE_VOICES

            # Find voice case-insensitively to support different naming schemes
            # (e.g., Supertonic uses M1/M2, ChatterBox uses male_1/male_2)
            voice_lower = voice.lower()
            matched_voice = None
            for available_voice in voices.keys():
                if available_voice.lower() == voice_lower:
                    matched_voice = available_voice
                    break

            if matched_voice is None:
                available = ', '.join(sorted(voices.keys()))
                await interaction.response.send_message(
                    f'Invalid voice **{voice}**\nAvailable: {available}',
                    ephemeral=True
                )
                return

            voice = matched_voice

            # Check if voice is claimed by someone else
            voice_owner = await self.voice_claims.get_voice_owner(voice)
            if voice_owner and voice_owner != interaction.user.id:
                try:
                    owner = await self.bot.fetch_user(voice_owner)
                    owner_name = owner.mention
                except:
                    owner_name = f"User {voice_owner}"

                await interaction.response.send_message(
                    f'Voice **{voice}** is exclusively claimed by {owner_name}.\n'
                    f'If you have a subscription, you can claim your own exclusive voice with `/tts claim-voice`',
                    ephemeral=True
                )
                return

            # Save preference
            success = await self.user_preferences.set_preferences(
                interaction.user.id,
                voice_name=voice
            )

            if success:
                await interaction.response.send_message(
                    f'Voice set to **{voice}** - {voices[voice]}',
                    ephemeral=True
                )
                logger.info(f'User {interaction.user} set voice to {voice}')
            else:
                await interaction.response.send_message(
                    'Failed to save voice preference',
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f'Failed to set voice: {e}')
            await interaction.response.send_message(f'Error: {e}', ephemeral=True)

    @voice_group.command(name="claim-voice", description="Claim an exclusive voice (requires subscription)")
    @app_commands.describe(voice="Voice ID to claim (e.g., M1, F2)")
    async def claim_voice(self, interaction: discord.Interaction, voice: str):
        """Claim an exclusive voice while subscribed"""
        if not self.initialized:
            await interaction.response.send_message("TTS engine not initialized", ephemeral=True)
            return

        # Ensure database models are initialized
        self._ensure_db_models()

        try:
            # Check if user has active subscription
            is_subscribed = await self.user_subscriptions.is_subscribed(interaction.user.id)
            if not is_subscribed:
                await interaction.response.send_message(
                    "You need an active subscription to claim voices. Contact the server owner to grant you subscription access.",
                    ephemeral=True
                )
                return

            # Get subscription info
            sub_info = await self.user_subscriptions.get_subscription(interaction.user.id)
            if not sub_info:
                await interaction.response.send_message(
                    "Subscription not found. Contact the server owner.",
                    ephemeral=True
                )
                return

            # Check if user already has a claimed voice
            has_claim = await self.voice_claims.user_has_claimed_voice(interaction.user.id)
            if has_claim:
                current_voice = await self.voice_claims.get_user_claimed_voice(interaction.user.id)
                await interaction.response.send_message(
                    f"You already claimed voice **{current_voice}**. Release it first with `/tts claim-release`",
                    ephemeral=True
                )
                return

            # Get available voices
            if not hasattr(self.tts_engine, 'AVAILABLE_VOICES'):
                await interaction.response.send_message(
                    "Current TTS engine does not support voice selection",
                    ephemeral=True
                )
                return

            voices = self.tts_engine.AVAILABLE_VOICES

            # Find voice case-insensitively
            voice_lower = voice.lower()
            matched_voice = None
            for available_voice in voices.keys():
                if available_voice.lower() == voice_lower:
                    matched_voice = available_voice
                    break

            if matched_voice is None:
                available = ', '.join(sorted(voices.keys()))
                await interaction.response.send_message(
                    f'Invalid voice **{voice}**\nAvailable: {available}',
                    ephemeral=True
                )
                return

            voice = matched_voice

            # Check if voice is in protected/public-only list
            protected_voices = ['M1', 'M2', 'M3', 'M4', 'M5', 'F1', 'F2', 'F3', 'F4', 'F5']
            if voice in protected_voices:
                await interaction.response.send_message(
                    f'Voice **{voice}** is a public voice and cannot be claimed. It must remain available to all users.',
                    ephemeral=True
                )
                return

            # Check if voice is already claimed
            is_claimed = await self.voice_claims.is_voice_claimed(voice)
            if is_claimed:
                owner_id = await self.voice_claims.get_voice_owner(voice)
                await interaction.response.send_message(
                    f'Voice **{voice}** is already claimed by <@{owner_id}>',
                    ephemeral=True
                )
                return

            # Claim the voice
            success, message = await self.voice_claims.claim_voice(
                interaction.user.id,
                voice,
                sub_info['id'],
                voice_description=voices[voice]
            )

            if success:
                # Auto-set claimed voice as preferred voice
                await self.user_preferences.set_preferences(
                    interaction.user.id,
                    voice_name=voice
                )
                await interaction.response.send_message(
                    f"✅ {message}\nVoice **{voice}** is now your exclusive voice for this subscription!",
                    ephemeral=True
                )
                logger.info(f'User {interaction.user} claimed voice {voice}')
            else:
                await interaction.response.send_message(
                    f"❌ {message}",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f'Failed to claim voice: {e}')
            await interaction.response.send_message(f'Error: {e}', ephemeral=True)

    @voice_group.command(name="claim-release", description="Release your claimed exclusive voice")
    async def claim_release(self, interaction: discord.Interaction):
        """Release a claimed exclusive voice"""
        if not self.initialized:
            await interaction.response.send_message("TTS engine not initialized", ephemeral=True)
            return

        # Ensure database models are initialized
        self._ensure_db_models()

        try:
            # Check if user has a claimed voice
            has_claim = await self.voice_claims.user_has_claimed_voice(interaction.user.id)
            if not has_claim:
                await interaction.response.send_message(
                    "You do not have a claimed voice to release",
                    ephemeral=True
                )
                return

            # Release the voice
            success, message, voice_id = await self.voice_claims.release_voice(interaction.user.id)

            if success:
                # Reset voice preference to default (M1)
                await self.user_preferences.set_preferences(
                    interaction.user.id,
                    voice_name='M1'
                )
                await interaction.response.send_message(
                    f"✅ {message}\nYour voice preference has been reset to M1.",
                    ephemeral=True
                )
                logger.info(f'User {interaction.user} released voice {voice_id}')
            else:
                await interaction.response.send_message(
                    f"❌ {message}",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f'Failed to release voice: {e}')
            await interaction.response.send_message(f'Error: {e}', ephemeral=True)


    @tts_group.command(name="check_perms", description="Check bot's voice channel permissions")
    async def check_perms(self, interaction: discord.Interaction):
        """Check bot permissions for the user's current voice channel"""
        await interaction.response.defer(ephemeral=True)

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send(
                "You need to be in a voice channel first!",
                ephemeral=True
            )
            return

        voice_channel = interaction.user.voice.channel
        guild = interaction.guild
        bot_member = guild.me

        # Get all permissions
        bot_permissions = voice_channel.permissions_for(bot_member)

        # Check channel overwrites
        overwrites = voice_channel.overwrites
        bot_overwrite = overwrites.get(bot_member)
        bot_role_overwrites = {role: overwrite for role, overwrite in overwrites.items() if isinstance(role, discord.Role) and role in bot_member.roles}

        embed = discord.Embed(
            title="Bot Permission Check",
            description=f"Channel: **{voice_channel.name}**",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Critical Permissions",
            value=f"✅ CONNECT: {bot_permissions.connect}\n"
                  f"✅ SPEAK: {bot_permissions.speak}",
            inline=False
        )

        embed.add_field(
            name="Bot Roles",
            value=f"{', '.join([r.mention for r in bot_member.roles[1:]])}",
            inline=False
        )

        if bot_overwrite:
            embed.add_field(
                name="Direct Bot Overwrite",
                value=f"Allow: {bot_overwrite.pair()[0]}\nDeny: {bot_overwrite.pair()[1]}",
                inline=False
            )

        if bot_role_overwrites:
            overwrite_text = ""
            for role, overwrite in bot_role_overwrites.items():
                overwrite_text += f"{role.mention}: Allow={overwrite.pair()[0]}, Deny={overwrite.pair()[1]}\n"
            embed.add_field(
                name="Role Overwrites Affecting Bot",
                value=overwrite_text,
                inline=False
            )

        if not bot_permissions.connect:
            embed.color = discord.Color.red()
            embed.add_field(
                name="⚠️ Issue Found",
                value="Bot cannot connect! Check role permissions or channel overwrites.",
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @tts_group.command(name="help", description="Show TTS help information")
    async def tts_help(self, interaction: discord.Interaction):
        """Show help and usage information"""
        embed = discord.Embed(
            title='TTS Bot Help',
            description='Convert text to natural speech in voice channels',
            color=discord.Color.blue()
        )

        embed.add_field(
            name='Auto-TTS (Monitored Channels)',
            value=(
                "Just type in a monitored channel while in a voice channel.\n"
                "Bot automatically speaks your message!\n"
                "No commands needed!"
            ),
            inline=False
        )

        embed.add_field(
            name='Voice Channel',
            value=(
                '/tts join - Join your voice channel\n'
                '/tts leave - Leave voice channel'
            ),
            inline=False
        )

        embed.add_field(
            name='Customization',
            value=(
                '/tts speed <0.5-2.0> - Adjust speech speed\n'
                '/tts voice list - Show available voices\n'
                '/tts voice set <voice> - Change your voice'
            ),
            inline=False
        )

        embed.add_field(
            name='Admin Setup',
            value=(
                '/tts setup add <channel> - Enable auto-TTS in channel\n'
                '/tts setup remove <channel> - Disable auto-TTS\n'
                '/tts setup list - Show monitored channels'
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tts_group.command(name="join", description="Join your current voice channel")
    async def join(self, interaction: discord.Interaction):
        """Join the user's voice channel"""
        # Defer response immediately (takes up to 3 seconds before showing "application did not respond")
        await interaction.response.defer(ephemeral=True)

        if not self.initialized:
            await interaction.followup.send("TTS engine not initialized", ephemeral=True)
            return

        # Check if user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send(
                "You need to be in a voice channel first!",
                ephemeral=True
            )
            return

        voice_channel = interaction.user.voice.channel
        guild = interaction.guild

        # Check bot permissions (warning only - still try to connect)
        bot_permissions = voice_channel.permissions_for(guild.me)
        logger.debug(f'Bot permissions for {voice_channel.name}: connect={bot_permissions.connect}, speak={bot_permissions.speak}')

        if not bot_permissions.connect:
            logger.warning(f'Bot may be missing CONNECT permission in {voice_channel.name} - attempting anyway')
        if not bot_permissions.speak:
            logger.warning(f'Bot missing SPEAK permission in {voice_channel.name}')

        try:
            if guild.voice_client is None:
                # Try to connect with retry logic
                max_retries = 3
                last_error = None

                for attempt in range(max_retries):
                    try:
                        # Use self_deaf=True to reduce overhead (bot only sends audio, doesn't receive)
                        # Increase timeout to 90 seconds for slow Discord voice servers
                        logger.debug(f'Attempting voice connection (attempt {attempt + 1}/{max_retries}, timeout=90s, self_deaf=True)')
                        await voice_channel.connect(timeout=90.0, self_deaf=True)
                        logger.debug(f'Voice connection successful on attempt {attempt + 1}')
                        break
                    except asyncio.TimeoutError as e:
                        last_error = e
                        if attempt < max_retries - 1:
                            logger.warning(f'Voice connection timeout (attempt {attempt + 1}/{max_retries}), retrying in 5 seconds...')
                            await asyncio.sleep(5)  # Wait before retry
                        else:
                            logger.error(f'Voice connection failed after {max_retries} attempts (timeout)')
                            raise

                await self.queue_manager.start_processor(guild.id)
                await interaction.followup.send(
                    f"Joined **{voice_channel.name}**",
                    ephemeral=True
                )
                logger.info(f'Bot joined {voice_channel} via command')
            elif guild.voice_client.channel == voice_channel:
                await interaction.followup.send(
                    f"Already in **{voice_channel.name}**",
                    ephemeral=True
                )
            else:
                await guild.voice_client.move_to(voice_channel)
                await interaction.followup.send(
                    f"Moved to **{voice_channel.name}**",
                    ephemeral=True
                )
                logger.info(f'Bot moved to {voice_channel} via command')

        except asyncio.TimeoutError as e:
            logger.error(f'Failed to join voice channel: Connection timeout after retries')
            logger.error(f'Timeout details: {e}')
            await interaction.followup.send(
                "Failed to join: Discord voice connection timeout (>90s). The voice server may be experiencing issues. Try again in a moment.",
                ephemeral=True
            )
        except Exception as e:
            import traceback
            logger.error(f'Failed to join voice channel: {type(e).__name__}: {e}')
            logger.error(traceback.format_exc())
            await interaction.followup.send(f"Failed to join: {type(e).__name__}: {e}", ephemeral=True)

    @tts_group.command(name="leave", description="Leave the current voice channel")
    async def leave(self, interaction: discord.Interaction):
        """Leave the voice channel"""
        guild = interaction.guild

        if guild.voice_client is None:
            await interaction.response.send_message(
                "I'm not in a voice channel",
                ephemeral=True
            )
            return

        # Defer to extend the interaction window before long operations
        await interaction.response.defer(ephemeral=True)

        try:
            channel_name = guild.voice_client.channel.name
            await guild.voice_client.disconnect(force=True)
            await self.queue_manager.stop_processor(guild.id)
            await interaction.followup.send(
                f"Left **{channel_name}**",
                ephemeral=True
            )
            logger.info(f'Bot left voice channel via command')

        except Exception as e:
            logger.error(f'Failed to leave voice channel: {e}')
            await interaction.followup.send(f"Failed to leave: {e}", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Auto-convert messages to TTS in monitored channels"""
        if message.author.bot or message.content.startswith('/'):
            return

        if not self.initialized:
            return

        # Ensure database models are initialized
        self._ensure_db_models()

        # Check if this is a monitored channel
        is_monitored = await self.monitored_channels.is_channel_monitored(message.channel.id)
        if not is_monitored:
            return

        guild = message.guild
        if not guild:
            return

        # Check rate limit (prevent spam)
        cooldown_key = (message.guild.id, message.author.id)
        current_time = time.time()
        last_tts_time = self.user_tts_cooldown.get(cooldown_key, 0)

        if current_time - last_tts_time < self.tts_cooldown_seconds:
            remaining = round(self.tts_cooldown_seconds - (current_time - last_tts_time), 1)
            await message.channel.send(
                f'{message.author.mention} Please wait {remaining}s before using TTS again.',
                delete_after=5
            )
            return

        self.user_tts_cooldown[cooldown_key] = current_time

        # Check if user is in a voice channel
        user_voice = message.author.voice
        if not user_voice:
            return

        try:
            # Validate message length
            max_message_length = 500
            if len(message.content) > max_message_length:
                await message.channel.send(
                    f'{message.author.mention} Message too long for TTS (max {max_message_length} characters). '
                    f'Your message is {len(message.content)} characters.',
                    delete_after=10
                )
                return

            # Auto-join voice channel if bot isn't already connected
            if guild.voice_client is None:
                try:
                    # Use longer timeout (90 seconds) for voice connection
                    logger.debug(f'Auto-joining {user_voice.channel} in {guild.name}')
                    await user_voice.channel.connect(timeout=90.0, self_deaf=True)
                    logger.info(f'Bot auto-joined {user_voice.channel} in {guild.name}')
                    await self.queue_manager.start_processor(guild.id)
                except asyncio.TimeoutError:
                    logger.error(f'Failed to auto-join voice channel: Connection timeout (>90s)')
                    return
                except Exception as e:
                    logger.error(f'Failed to auto-join voice channel: {e}')
                    return
            elif guild.voice_client and not guild.voice_client.is_connected():
                # Only attempt reconnect if connection state is explicitly stale
                try:
                    channel_name = user_voice.channel.name
                    is_private = isinstance(user_voice.channel, discord.VoiceChannel)
                    logger.debug(f'Stale connection detected in {channel_name} (private={is_private}). Attempting reconnect.')

                    try:
                        await guild.voice_client.disconnect(force=True)
                    except Exception as disconnect_err:
                        logger.debug(f'Error disconnecting stale client: {disconnect_err}')

                    await user_voice.channel.connect(timeout=90.0, self_deaf=True)
                    logger.info(f'Bot reconnected to {user_voice.channel} in {guild.name}')
                    await self.queue_manager.start_processor(guild.id)
                except asyncio.TimeoutError:
                    logger.error(f'Failed to reconnect to voice channel: Connection timeout (>90s)')
                    return
                except Exception as e:
                    logger.error(f'Failed to reconnect to voice channel: {type(e).__name__}: {e}')
                    logger.debug(f'Reconnect error details: {e}')
                    return
            elif guild.voice_client.channel != user_voice.channel:
                await guild.voice_client.move_to(user_voice.channel)
                logger.info(f'Bot moved to {user_voice.channel}')

            # Get user preferences (speed, language, and voice)
            prefs = await self.user_preferences.get_preferences(message.author.id)

            # Validate and bounds-check speed
            speed = max(0.5, min(2.0, prefs['speed']))

            # Validate language against supported languages
            supported_languages = self.tts_engine.get_available_languages()
            language = prefs['language'] if prefs['language'] in supported_languages else 'en'

            # Get user's voice: claimed voice takes priority over preference
            voice_name = prefs.get('voice_name', 'M1')
            if self.voice_claims:
                claimed_voice = await self.voice_claims.get_user_claimed_voice(message.author.id)
                if claimed_voice:
                    voice_name = claimed_voice
                    logger.debug(f'Using claimed voice {claimed_voice} for user {message.author}')

            # Check if the selected voice is claimed by someone else
            if self.voice_claims:
                voice_owner = await self.voice_claims.get_voice_owner(voice_name)
                if voice_owner and voice_owner != message.author.id:
                    # Voice is claimed by someone else - send ephemeral error and don't process TTS
                    try:
                        embed = discord.Embed(
                            title="Voice Not Available",
                            description=f"The voice **{voice_name}** is exclusively claimed by another user and cannot be used.",
                            color=discord.Color.red()
                        )
                        await message.reply(embed=embed, ephemeral=True)
                    except Exception as e:
                        logger.warning(f'Failed to send voice restriction message: {e}')
                    logger.debug(f'User {message.author} tried to use claimed voice {voice_name} owned by {voice_owner}')
                    return

            # Create queued message (Supertonic uses voice_name, not voice_file_path)
            queued_msg = QueuedMessage(
                user_id=message.author.id,
                user_name=message.author.name,
                text=message.content,
                voice_file_path='',  # Not used by Supertonic
                speed=speed,
                language=language,
                voice_name=voice_name
            )

            success = await self.queue_manager.enqueue(guild.id, queued_msg)

            if not success:
                logger.warning(f'Failed to enqueue message from {message.author}')

            logger.debug(f'Enqueued TTS message from {message.author}: {message.content[:50]}...')

        except Exception as e:
            import traceback
            logger.error(f'Error handling auto-TTS message: {e}')
            logger.error(traceback.format_exc())

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Handle voice state changes"""
        if not self.initialized:
            return

        if member == self.bot.user:
            if before.channel and not after.channel:
                guild = before.channel.guild
                await self.queue_manager.stop_processor(guild.id)
                logger.info(f'Bot left voice channel in {guild.name}')
        else:
            # Check if a user left a channel where the bot is connected
            if before.channel and not after.channel:
                guild = before.channel.guild
                if guild.voice_client and guild.voice_client.channel == before.channel:
                    # Count non-bot users in the channel
                    users_in_channel = [m for m in before.channel.members if not m.bot]
                    if not users_in_channel:
                        # No users left, disconnect bot
                        try:
                            logger.info(f'Last user left {before.channel.name}, disconnecting bot')
                            await guild.voice_client.disconnect(force=True)
                            await self.queue_manager.stop_processor(guild.id)
                        except Exception as e:
                            logger.error(f'Failed to auto-disconnect: {e}')

    @commands.Cog.listener()
    async def on_ready(self):
        """Initialize database models after main.py sets self.db"""
        self._ensure_db_models()


async def setup(bot: commands.Bot):
    """Load cog"""
    await bot.add_cog(TTS(bot))
    logger.info('TTS Cog loaded')
