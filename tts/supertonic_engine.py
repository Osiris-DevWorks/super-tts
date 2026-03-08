"""
Supertonic Text-to-Speech Engine
Lightning-fast, on-device TTS using ONNX Runtime
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, AsyncGenerator

import numpy as np

from .base_engine import BaseTTSEngine

logger = logging.getLogger(__name__)


class SupertonicEngine(BaseTTSEngine):
    """Lightning-fast TTS engine using Supertonic"""

    # Supertonic supported languages and voices
    SUPPORTED_LANGUAGES = ['en', 'ko', 'es', 'pt', 'fr']
    AVAILABLE_VOICES = {
        'default': 'Mature and wise',
        'M1': 'Male - Warm and conversational',
        'M2': 'Male - Formal and professional',
        'M3': 'Male - Clear and neutral',
        'M4': 'Male - Balanced and steady',
        'M5': 'Male - Smooth and deep',
        'F1': 'Female - Friendly and upbeat',
        'F2': 'Female - Eloquent and refined',
        'F3': 'Female - Clear and natural',
        'F4': 'Female - Bright and energetic',
        'F5': 'Female - Warm and intimate',
    }

    def __init__(self, device: str = 'auto', voice: str = 'M3', **kwargs):
        """
        Initialize Supertonic TTS engine.

        Args:
            device: 'cuda', 'cpu', or 'auto' (auto-detect GPU) - Note: Supertonic handles this internally
            voice: Voice name (M1, M2, M3, M4, F1, F2, F3) - defaults to M3
            **kwargs: Additional arguments (ignored for compatibility)
        """
        try:
            from supertonic import TTS
        except ImportError as e:
            raise ImportError(
                f"Supertonic not installed or import failed: {e}. Install with: pip install supertonic"
            )

        self._device = device
        self.voice_name = voice

        logger.info(f'[Supertonic] Initializing with voice: {voice}')

        try:
            # Initialize Supertonic TTS (auto-downloads model on first run)
            self.tts = TTS(auto_download=True)
            
            # Pre-load the voice style
            self.voice_style = self.tts.get_voice_style(voice_name=voice)
            logger.info(f'Supertonic TTS initialized with voice: {voice}')
        except Exception as e:
            logger.error(f'Failed to load Supertonic engine: {e}')
            raise

    @property
    def device(self) -> str:
        """Return current device"""
        return self._device

    @property
    def model_name(self) -> str:
        """Return model identifier"""
        return 'supertonic'

    @property
    def sample_rate(self) -> int:
        """Return output sample rate (Supertonic outputs ~45kHz)"""
        return 45000

    async def synthesize(
        self,
        text: str,
        voice_file: Path,
        speed: float = 1.0,
        language: str = 'en',
        voice_name: str = None
    ) -> np.ndarray:
        """
        Synthesize text to speech using Supertonic.

        Args:
            text: Text to synthesize
            voice_file: Path to voice file (ignored by Supertonic, uses voice config)
            speed: Speech rate (affects synthesis, default 1.0)
            language: Language code (Supertonic handles multilingual)
            voice_name: Voice ID (M1-M4, F1-F3) - overrides instance voice if provided

        Returns:
            Audio samples as numpy array (float32, ~45kHz)
        """
        # Preprocess text
        text = self._preprocess_text(text)

        # Use provided voice_name or fall back to instance voice
        selected_voice = voice_name or self.voice_name

        # Validate voice
        if selected_voice not in self.AVAILABLE_VOICES:
            logger.warning(f'Invalid voice {selected_voice}, using default {self.voice_name}')
            selected_voice = self.voice_name

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()

        def _synthesize():
            try:
                logger.debug(f'Supertonic synthesizing with voice {selected_voice}: {text[:50]}...')

                # Get voice style for selected voice
                voice_style = self.tts.get_voice_style(voice_name=selected_voice)

                # Synthesize using Supertonic
                wav, duration = self.tts.synthesize(text, voice_style=voice_style)

                # Flatten 2D array to 1D (Supertonic returns (channels, samples))
                if len(wav.shape) == 2:
                    wav = wav.flatten()

                # Ensure it's float32
                if wav.dtype != np.float32:
                    wav = wav.astype(np.float32)

                # Normalize to [-1, 1] if needed
                if wav.max() > 1.0:
                    wav = wav / 32768.0

                return wav

            except Exception as e:
                logger.error(f'Supertonic synthesis failed: {e}')
                raise

        return await loop.run_in_executor(None, _synthesize)

    async def synthesize_streaming(
        self,
        text: str,
        voice_file: Path,
        speed: float = 1.0,
        language: str = 'en',
        voice_name: str = None
    ) -> AsyncGenerator[np.ndarray, None]:
        """
        Stream audio chunks during synthesis.

        Args:
            text: Text to synthesize
            voice_file: Path to voice file (ignored)
            speed: Speech rate
            language: Language code
            voice_name: Voice ID (M1-M4, F1-F3) - overrides instance voice if provided

        Yields:
            NumPy arrays of float32 audio chunks at ~45kHz
        """
        # Get full audio
        wav = await self.synthesize(text, voice_file, speed, language, voice_name)

        # Yield in chunks
        chunk_size = 256
        for i in range(0, len(wav), chunk_size):
            yield wav[i:i + chunk_size]
            await asyncio.sleep(0)

    def get_available_languages(self) -> list[str]:
        """Get list of supported languages"""
        return self.SUPPORTED_LANGUAGES

    def warmup(self) -> None:
        """Warmup model to eliminate first-call latency"""
        logger.info('Warming up Supertonic model...')
        try:
            _ = self.tts.synthesize(
                "The quick brown fox jumps over the lazy dog.",
                voice_style=self.voice_style
            )
            logger.info('Supertonic warmup complete')
        except Exception as e:
            logger.warning(f'Supertonic warmup failed (non-critical): {e}')

    @staticmethod
    def _preprocess_text(text: str) -> str:
        """Preprocess text for TTS"""
        import re

        # Remove Discord formatting while preserving word boundaries
        text = text.replace('**', ' ')
        text = text.replace('__', ' ')
        text = text.replace('~~', ' ')
        text = text.replace('`', ' ')

        # Remove URLs with space preservation
        text = re.sub(r'https?://\S+', ' ', text)

        # Remove other URLs and email addresses
        text = re.sub(r'www\.\S+', ' ', text)

        # Clean up multiple spaces
        text = re.sub(r'\s+', ' ', text)

        # Limit length
        max_chars = 500
        if len(text) > max_chars:
            text = text[:max_chars] + '...'

        return text.strip()
