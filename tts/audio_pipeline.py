"""
Audio Pipeline: TTS -> FFmpeg -> Discord Voice
Converts TTS output to Discord-compatible audio with NO username prefixing
"""

import asyncio
import io
import logging
import subprocess
from pathlib import Path
from typing import Optional

import discord
import numpy as np
from discord.ext import commands

from .base_engine import BaseTTSEngine

logger = logging.getLogger(__name__)
# Ensure this logger captures debug messages
logger.setLevel(logging.DEBUG)


class PCMAudioSource(discord.AudioSource):
    """Custom audio source for playing raw PCM data"""

    def __init__(self, data: bytes, sample_rate: int = 48000, channels: int = 2):
        """
        Initialize PCM audio source

        Args:
            data: Raw PCM audio bytes
            sample_rate: Sample rate in Hz
            channels: Number of channels (1=mono, 2=stereo)
        """
        # Pad data to be a multiple of frame size
        # Frame size = sample_rate * 0.02 seconds * bytes_per_sample * channels
        # For 48kHz stereo 16-bit: 48000 * 0.02 * 2 * 2 = 3840 bytes
        frame_size = int(sample_rate * 0.02 * 2 * channels)
        remainder = len(data) % frame_size
        if remainder != 0:
            padding_size = frame_size - remainder
            data = data + (b'\x00' * padding_size)
            logger.debug(f'Padded audio with {padding_size} bytes of silence')

        self.data = io.BytesIO(data)
        self.sample_rate = sample_rate
        self.channels = channels
        self.total_size = len(data)
        self.bytes_read = 0
        logger.debug(f'PCMAudioSource initialized with {self.total_size} bytes at {self.sample_rate}Hz ({self.channels}ch)')

    def read(self) -> bytes:
        """Read the next frame of audio data"""
        # Discord expects 20ms frames at the sample rate
        # For 48kHz stereo 16-bit: 48000 * 0.02 * 2 * 2 = 3840 bytes
        frame_size = int(self.sample_rate * 0.02 * 2 * self.channels)
        frame_data = self.data.read(frame_size)
        self.bytes_read += len(frame_data)

        if len(frame_data) == 0:
            logger.debug(f'PCMAudioSource end of stream: {self.bytes_read}/{self.total_size} bytes read')
        elif len(frame_data) < frame_size:
            logger.debug(f'PCMAudioSource partial frame: {len(frame_data)} bytes (expected {frame_size})')

        return frame_data

    def cleanup(self) -> None:
        """Clean up resources"""
        self.data.close()


class StreamingPCMAudioSource(discord.AudioSource):
    """Streaming audio source that plays audio chunks as they arrive"""

    def __init__(self, sample_rate: int = 48000, channels: int = 2):
        """
        Initialize streaming PCM audio source

        Args:
            sample_rate: Sample rate in Hz
            channels: Number of channels (1=mono, 2=stereo)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.frame_size = int(sample_rate * 0.02 * 2 * channels)

        # Queue to hold incoming audio chunks (converted to PCM)
        self.chunk_queue: asyncio.Queue = asyncio.Queue()
        self.buffer = io.BytesIO()
        self.finished = False
        self.bytes_read = 0

        logger.debug(f'StreamingPCMAudioSource initialized (frame_size={self.frame_size})')

    def read(self) -> bytes:
        """Read the next frame of audio data from buffer"""
        # If buffer doesn't have enough data, try to get more from queue
        while self.buffer.getbuffer().nbytes < self.frame_size and not self.finished:
            try:
                # Non-blocking get - if queue is empty, we'll just work with what we have
                chunk = self.chunk_queue.get_nowait()
                self.buffer.write(chunk)
            except asyncio.QueueEmpty:
                break

        # Read a frame from buffer
        frame_data = self.buffer.read(self.frame_size)
        self.bytes_read += len(frame_data)

        # If we got less than a frame, pad with silence if finished, or return what we have
        if len(frame_data) < self.frame_size:
            if self.finished:
                # Pad with silence to complete the frame
                padding = b'\x00' * (self.frame_size - len(frame_data))
                frame_data += padding
                logger.debug(f'StreamingPCMAudioSource finished: {self.bytes_read} bytes read total')

        return frame_data

    async def add_chunk(self, chunk: bytes):
        """Add audio chunk to streaming queue"""
        await self.chunk_queue.put(chunk)

    def mark_finished(self):
        """Signal that no more chunks will arrive"""
        self.finished = True

    def cleanup(self) -> None:
        """Clean up resources"""
        self.buffer.close()


class AudioPipeline:
    """Converts TTS output to Discord voice format via FFmpeg"""

    def __init__(self, tts_engine: BaseTTSEngine):
        """
        Initialize audio pipeline

        Args:
            tts_engine: BaseTTSEngine instance for synthesis
        """
        self.tts_engine = tts_engine

    async def synthesize_and_convert(
        self,
        text: str,
        voice_file: Path,
        speed: float = 1.0,
        language: str = 'en',
        voice_name: str = None
    ) -> Optional[bytes]:
        """
        Synthesize text and convert to Discord audio format (Opus 48kHz)

        Args:
            text: Text to synthesize
            voice_file: Path to voice reference file
            speed: Speech speed (0.5-2.0)
            language: Language code
            voice_name: Voice ID for engines that support it (e.g., Supertonic)

        Returns:
            PCM audio bytes ready for Discord, or None on failure
        """
        try:
            # Step 1: Synthesize audio (sample rate depends on engine)
            logger.debug(f'Synthesizing: "{text[:50]}..."')

            # Pass voice_name if engine supports it
            if voice_name and hasattr(self.tts_engine.synthesize, '__code__') and 'voice_name' in self.tts_engine.synthesize.__code__.co_varnames:
                wav = await self.tts_engine.synthesize(
                    text=text,
                    voice_file=voice_file,
                    speed=speed,
                    language=language,
                    voice_name=voice_name
                )
            else:
                wav = await self.tts_engine.synthesize(
                    text=text,
                    voice_file=voice_file,
                    speed=speed,
                    language=language
                )

            logger.debug(f'TTS synthesis returned audio')

            # Step 2: Convert to 48kHz PCM for Discord (output: stereo)
            input_sr = self.tts_engine.sample_rate
            logger.debug(f'Converting audio format from {input_sr}Hz to 48kHz stereo')
            pcm_audio = await self._convert_to_discord_format(wav, input_sample_rate=input_sr)

            if pcm_audio:
                duration = len(pcm_audio) / 48000 / 2 / 2  # Divide by 2 twice for stereo
                logger.debug(f'Audio conversion complete: {len(pcm_audio)} bytes (~{duration:.2f}s at 48kHz stereo)')
            else:
                logger.error('Audio conversion returned empty data')
            return pcm_audio

        except Exception as e:
            logger.error(f'Audio pipeline failed: {e}')
            import traceback
            logger.error(traceback.format_exc())
            return None

    async def synthesize_and_convert_streaming(
        self,
        text: str,
        voice_file: Path,
        speed: float = 1.0,
        language: str = 'en',
        voice_name: str = None
    ) -> StreamingPCMAudioSource:
        """
        Synthesize text and convert to Discord audio format with streaming

        Args:
            text: Text to synthesize
            voice_file: Path to voice reference file
            speed: Speech speed (0.5-2.0)
            language: Language code
            voice_name: Voice ID for engines that support it (e.g., Supertonic)

        Returns:
            StreamingPCMAudioSource that will play audio as chunks arrive
        """
        source = StreamingPCMAudioSource()

        # Start synthesis in background task
        async def _synthesize_and_stream():
            try:
                logger.debug(f'Starting streaming synthesis: "{text[:50]}..."')

                # Pass voice_name if engine supports it
                if voice_name and hasattr(self.tts_engine.synthesize_streaming, '__code__') and 'voice_name' in self.tts_engine.synthesize_streaming.__code__.co_varnames:
                    wav_chunks = self.tts_engine.synthesize_streaming(
                        text=text,
                        voice_file=voice_file,
                        speed=speed,
                        language=language,
                        voice_name=voice_name
                    )
                else:
                    wav_chunks = self.tts_engine.synthesize_streaming(
                        text=text,
                        voice_file=voice_file,
                        speed=speed,
                        language=language
                    )

                # Process each chunk asynchronously
                async for wav_chunk in wav_chunks:
                    try:
                        # Convert chunk to Discord format
                        pcm_chunk = await self._convert_to_discord_format(wav_chunk)
                        if pcm_chunk:
                            await source.add_chunk(pcm_chunk)
                    except Exception as e:
                        logger.error(f'Error converting audio chunk: {e}')

                source.mark_finished()
                logger.debug('Streaming synthesis complete')

            except Exception as e:
                logger.error(f'Streaming synthesis failed: {e}')
                source.mark_finished()

        # Launch synthesis task without waiting
        asyncio.create_task(_synthesize_and_stream())
        return source

    async def _convert_to_discord_format(self, wav: np.ndarray, input_sample_rate: int = 24000) -> bytes:
        """
        Convert TTS output to Discord format (48kHz PCM)

        Args:
            wav: Audio samples as float32 numpy array
            input_sample_rate: Sample rate of input audio (24kHz or 32kHz from Supertonic/Soprano)

        Returns:
            PCM audio bytes (48kHz, 16-bit)
        """
        loop = asyncio.get_event_loop()

        def _convert():
            """Fast resampling using scipy resample_poly for speed"""
            # Convert to numpy array if it's a list
            wav_array = np.array(wav) if isinstance(wav, list) else wav

            # Ensure float32
            if wav_array.dtype != np.float32:
                wav_array = wav_array.astype(np.float32)

            # Normalize to [-1, 1]
            if np.abs(wav_array).max() > 1.0:
                wav_array = wav_array / 32768.0

            try:
                # Try using scipy for faster resampling (if available)
                from scipy.signal import resample_poly
                from math import gcd

                # Calculate resampling ratio using GCD for efficient polyphase filter
                g = gcd(48000, input_sample_rate)
                up = 48000 // g
                down = input_sample_rate // g

                # Use fast polyphase resampling
                resampled = resample_poly(wav_array, up, down)
                logger.debug(f'Resampled {input_sample_rate}Hz -> 48kHz using resample_poly '
                             f'(up={up}, down={down}, {len(wav_array)} -> {len(resampled)} samples)')

            except ImportError:
                logger.debug('scipy not available, using simple linear interpolation fallback')
                # Fallback: simple linear interpolation without scipy
                ratio = 48000.0 / input_sample_rate
                num_samples = int(len(wav_array) * ratio)
                indices = np.linspace(0, len(wav_array) - 1, num_samples)
                resampled = np.interp(indices, np.arange(len(wav_array)), wav_array)

            # Ensure bounds
            resampled = np.clip(resampled, -1.0, 1.0)

            # Convert to stereo by duplicating channels (left=right)
            resampled_int16 = (resampled * 32767).astype(np.int16)
            stereo = np.zeros(len(resampled_int16) * 2, dtype=np.int16)
            stereo[0::2] = resampled_int16  # Left channel
            stereo[1::2] = resampled_int16  # Right channel

            return stereo.tobytes()

        return await loop.run_in_executor(None, _convert)

    @staticmethod
    def get_discord_pcm_generator(pcm_audio: bytes):
        """
        Create a generator for discord.py audio sink

        Args:
            pcm_audio: PCM audio bytes

        Yields:
            Audio chunks (frames)
        """
        chunk_size = 3840  # 48kHz stereo frame size (20ms)
        for i in range(0, len(pcm_audio), chunk_size):
            yield pcm_audio[i:i + chunk_size]


class DiscordAudioPlayer:
    """Handles audio playback in Discord voice channels"""

    def __init__(self, bot: commands.Bot, pipeline: AudioPipeline):
        """
        Initialize Discord audio player

        Args:
            bot: Discord bot instance
            pipeline: AudioPipeline instance
        """
        self.bot = bot
        self.pipeline = pipeline

    async def play_in_voice_channel(
        self,
        guild_id: int,
        text: str,
        voice_file: Path,
        speed: float = 1.0,
        language: str = 'en'
    ) -> bool:
        """
        Play synthesized speech in a Discord voice channel

        Args:
            guild_id: Discord guild ID
            text: Text to synthesize
            voice_file: Path to voice reference file
            speed: Speech speed
            language: Language code

        Returns:
            True if playback started successfully, False otherwise
        """
        guild = self.bot.get_guild(guild_id)
        if not guild:
            logger.error(f'Guild {guild_id} not found')
            return False

        # Find bot's voice client in guild
        voice_client = guild.voice_client
        if not voice_client or not voice_client.is_connected():
            logger.warning(f'Bot not connected to voice in guild {guild_id}')
            return False

        try:
            # Synthesize and convert audio
            pcm_audio = await self.pipeline.synthesize_and_convert(
                text=text,
                voice_file=voice_file,
                speed=speed,
                language=language
            )

            if not pcm_audio:
                logger.error('Audio synthesis failed')
                return False

            # Create audio source from PCM data
            source = PCMAudioSource(pcm_audio, sample_rate=48000, channels=2)

            # Play in voice channel (no username prefix - pure message audio)
            voice_client.play(source)

            return True

        except Exception as e:
            logger.error(f'Failed to play audio in voice channel: {e}')
            return False
