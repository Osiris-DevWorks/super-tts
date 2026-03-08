"""
Base TTS Engine Interface
Abstract base class that all TTS models must implement for unified architecture
"""

from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator
from pathlib import Path

import numpy as np


class BaseTTSEngine(ABC):
    """Base interface for all TTS engines"""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_file: Path,
        speed: float = 1.0,
        language: str = 'en'
    ) -> np.ndarray:
        """
        Synthesize text to speech.

        Args:
            text: Text to synthesize
            voice_file: Path to voice file for speaker embedding/selection
            speed: Speed of speech (0.5-2.0, where 1.0 is normal)
            language: Language code (e.g., 'en', 'es', 'fr')

        Returns:
            NumPy array of float32 audio samples at 24kHz
        """
        pass

    @abstractmethod
    async def synthesize_streaming(
        self,
        text: str,
        voice_file: Path,
        speed: float = 1.0,
        language: str = 'en'
    ) -> AsyncGenerator[np.ndarray, None]:
        """
        Stream audio chunks during synthesis.

        Args:
            text: Text to synthesize
            voice_file: Path to voice file for speaker embedding/selection
            speed: Speed of speech (0.5-2.0)
            language: Language code

        Yields:
            NumPy arrays of float32 audio chunks at 24kHz
        """
        pass

    @abstractmethod
    def get_available_languages(self) -> list[str]:
        """
        Return list of supported language codes.

        Returns:
            List of language codes (e.g., ['en', 'es', 'fr'])
        """
        pass

    @abstractmethod
    def warmup(self) -> None:
        """
        Warm up model to eliminate first-call latency.

        This should load the model into memory and run a dummy inference
        to optimize runtime performance on subsequent calls.
        """
        pass

    @property
    @abstractmethod
    def device(self) -> str:
        """
        Return current device.

        Returns:
            'cuda' for NVIDIA GPU, 'cpu' for CPU, etc.
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """
        Return model identifier for logging and configuration.

        Returns:
            Model identifier string (e.g., 'xtts_v2', 'piper', 'soprano')
        """
        pass

    @property
    def sample_rate(self) -> int:
        """
        Return output sample rate of synthesized audio.

        Returns:
            Sample rate in Hz (default 24000 for compatibility)
        """
        return 24000
