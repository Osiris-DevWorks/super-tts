"""
TTS Engine Factory - Supertonic Only
Factory for creating Supertonic TTS engine instances
"""

import logging
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

            # Get device setting (with fallback to auto)
            device = config.get('device', 'auto')

            # Get model-specific config if it exists (ensure it's always a dict)
            model_config = config.get('model_config', {})
            if model_config is None:
                model_config = {}

            # Create engine instance with configuration
            engine = SupertonicEngine(
                device=device,
                **model_config,
                **kwargs
            )

            logger.info(f"Successfully created Supertonic engine on device: {engine.device}")
            return engine

        except Exception as e:
            logger.error(f"Failed to create Supertonic engine: {e}")
            raise

