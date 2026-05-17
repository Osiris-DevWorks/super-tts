"""
TTS Engine Factory - Supertonic Only
Factory for creating Supertonic TTS engine instances
"""

import logging
import os
from typing import Optional

from .base_engine import BaseTTSEngine
from .supertonic_engine import SupertonicEngine

logger = logging.getLogger(__name__)


class TTSEngineFactory:
    """Factory for creating Supertonic TTS engine instances"""

    @classmethod
    def create(
        cls,
        config: Optional[dict] = None,
        **kwargs
    ) -> BaseTTSEngine:
        """
        Create Supertonic TTS engine instance.

        Args:
            config: Configuration dictionary with model settings
            **kwargs: Additional arguments passed to engine constructor

        Returns:
            Instance of Supertonic TTS engine

        Raises:
            Exception: If engine initialization fails
        """
        logger.info("Creating Supertonic TTS engine")

        try:
            # Extract engine-specific configuration
            if config is None:
                config = {}

            # Device: env var (set by GUI Settings tab) wins over config.yaml.
            # Lets a user with a CUDA-capable box flip to GPU without editing
            # the bundled config file.
            device = os.getenv('TTS_DEVICE') or config.get('device', 'auto')

            # Pass everything else from config.yaml's tts.supertonic block
            # straight through as engine kwargs (voice, etc). Explicit kwargs
            # passed to create() still win on the right of the merge.
            engine_kwargs = {k: v for k, v in config.items() if k != 'device'}
            engine_kwargs.update(kwargs)

            engine = SupertonicEngine(device=device, **engine_kwargs)

            logger.info(f"Successfully created Supertonic engine on device: {engine.device}")
            return engine

        except Exception as e:
            logger.error(f"Failed to create Supertonic engine: {e}")
            raise

