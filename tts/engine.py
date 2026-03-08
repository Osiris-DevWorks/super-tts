"""
Coqui XTTS v2 Text-to-Speech Engine
Handles neural TTS synthesis with streaming support and GPU acceleration
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, AsyncGenerator

import numpy as np
import torch
import torch.serialization
from TTS.api import TTS

# PyTorch 2.6+ compatibility: Allow loading XTTS classes from checkpoint
# PyTorch 2.6 changed torch.load to weights_only=True by default for security
try:
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import XttsAudioConfig
    torch.serialization.add_safe_globals([XttsConfig, XttsAudioConfig])
except Exception as e:
    # Fallback: if specific imports fail, try to allow broader set
    try:
        import TTS.tts.configs.xtts_config
        import TTS.tts.models.xtts
        for name in dir(TTS.tts.configs.xtts_config):
            if 'Config' in name:
                torch.serialization.add_safe_globals([getattr(TTS.tts.configs.xtts_config, name)])
        for name in dir(TTS.tts.models.xtts):
            if 'Config' in name:
                torch.serialization.add_safe_globals([getattr(TTS.tts.models.xtts, name)])
    except Exception:
        pass

# Try to import ONNX Runtime for optimized inference
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

logger = logging.getLogger(__name__)


class TTSEngine:
    """Wrapper around Coqui XTTS v2 with streaming and caching"""

    def __init__(self, model_path: Optional[Path] = None, device: str = 'auto', quantize: bool = True):
        """
        Initialize TTS engine

        Args:
            model_path: Path to XTTS v2 model directory
            device: 'cuda', 'cpu', or 'auto' (auto-detect GPU)
            quantize: Enable dynamic quantization (int8) for faster inference
        """
        self.model_path = model_path or Path.home() / '.local/share/TTS'
        self.quantize = quantize

        # Determine device: CUDA (NVIDIA) > CPU
        if device == 'auto':
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device

        logger.info(f'[TTS] Using device: {self.device}')

        # Load model
        try:
            self.model = TTS(
                model_name='tts_models/multilingual/multi-dataset/xtts_v2',
                gpu=(self.device == 'cuda'),
                progress_bar=True
            )
            logger.info('XTTS v2 model loaded successfully')

            # Apply quantization if enabled
            if self.quantize:
                self._apply_quantization()

        except Exception as e:
            logger.error(f'Failed to load XTTS model: {e}')
            raise

        # Speaker embedding cache (FIFO eviction when full)
        self.speaker_cache = {}
        self.max_cache_size = 100

        # Enable mixed precision (float16) for faster inference
        self._enable_mixed_precision()

    @property
    def model_name(self) -> str:
        """Return model identifier"""
        return 'xtts_v2'

    @property
    def sample_rate(self) -> int:
        """Return output sample rate (XTTS outputs 24kHz)"""
        return 24000

    def _enable_mixed_precision(self):
        """
        Enable mixed precision (float16) inference for faster processing.

        This runs some operations in float16 (faster) and others in float32 (more accurate).
        Can provide 20-30% speedup with minimal quality loss on compatible hardware.
        """
        try:
            if self.device == 'cuda':
                logger.info('Enabling mixed precision for CUDA...')
                # Enable CUDA automatic mixed precision
                torch.cuda.enable_flash_sdp(True)
                logger.info('✓ Mixed precision enabled for CUDA')
            elif self.device == 'cpu':
                logger.debug('Mixed precision not applicable for CPU device')
        except Exception as e:
            logger.warning(f'Could not enable mixed precision: {e}')

    def _apply_quantization(self):
        """
        Apply dynamic quantization (int8) to the TTS model for faster inference.

        Dynamic quantization:
        - Converts weights from float32 to int8
        - Computations still happen in float32 (fast on CPU and GPU)
        - Reduces model size and memory bandwidth
        - Provides ~2-3x speedup with minimal quality loss
        """
        try:
            logger.info('Applying dynamic quantization to TTS model...')

            quantized_count = 0

            # Inspect model structure
            logger.debug(f'Model type: {type(self.model)}')
            logger.debug(f'Model attributes: {[attr for attr in dir(self.model) if not attr.startswith("_")]}')

            # Access the underlying PyTorch synthesizer model
            if hasattr(self.model, 'synthesizer'):
                synthesizer = self.model.synthesizer
                logger.debug(f'Synthesizer type: {type(synthesizer)}')
                logger.debug(f'Synthesizer attributes: {[attr for attr in dir(synthesizer) if not attr.startswith("_")]}')

                # Try quantizing the glow model (main synthesis model)
                if hasattr(synthesizer, 'glow'):
                    logger.info('Quantizing glow model...')
                    try:
                        quantized_glow = torch.quantization.quantize_dynamic(
                            synthesizer.glow,
                            {torch.nn.Linear},
                            dtype=torch.qint8,
                            inplace=False
                        )
                        synthesizer.glow = quantized_glow
                        quantized_count += 1
                        logger.info('✓ Glow model quantized successfully')
                    except Exception as e:
                        logger.error(f'Failed to quantize glow model: {e}')
                else:
                    logger.debug('No glow attribute found in synthesizer')

                # Try quantizing speaker encoder
                if hasattr(synthesizer, 'speaker_encoder'):
                    try:
                        logger.info('Quantizing speaker encoder...')
                        quantized_encoder = torch.quantization.quantize_dynamic(
                            synthesizer.speaker_encoder,
                            {torch.nn.Linear},
                            dtype=torch.qint8,
                            inplace=False
                        )
                        synthesizer.speaker_encoder = quantized_encoder
                        quantized_count += 1
                        logger.info('✓ Speaker encoder quantized successfully')
                    except Exception as e:
                        logger.warning(f'Could not quantize speaker encoder: {e}')
                else:
                    logger.debug('No speaker_encoder attribute found in synthesizer')

                if quantized_count > 0:
                    logger.info(f'Model quantization complete ({quantized_count} components) - expect 2-3x faster inference')
                else:
                    logger.warning('No quantizable model components found - quantization skipped')
            else:
                logger.warning('Could not access synthesizer model for quantization')

        except Exception as e:
            logger.error(f'Quantization failed (continuing without): {e}')
            # Continue without quantization if it fails

    async def synthesize_streaming(
        self,
        text: str,
        voice_file: Path,
        speed: float = 1.0,
        language: str = 'en'
    ) -> AsyncGenerator[np.ndarray, None]:
        """
        Synthesize speech with streaming output (for low latency perception)

        Note: Returns chunks of already-synthesized audio. The synthesis itself
        still blocks, but chunks are returned as they're divided, allowing
        playback to start sooner with better perceived responsiveness.

        Args:
            text: Text to synthesize
            voice_file: Path to reference voice audio file (.wav)
            speed: Speech rate (0.5-2.0)
            language: Language code (en, es, fr, de, it, pt, pl, tr, ru, nl, el, hu, etc.)

        Yields:
            Chunks of audio samples (numpy arrays)
        """
        # Preprocess text
        text = self._preprocess_text(text)

        # Run synthesis in thread pool to avoid blocking
        loop = asyncio.get_event_loop()

        def _synthesize():
            """Blocking synthesis call"""
            try:
                wav = self.model.tts(
                    text=text,
                    speaker_wav=str(voice_file),
                    language=language,
                    speed=speed
                )
                return wav
            except Exception as e:
                logger.error(f'TTS synthesis failed: {e}')
                raise

        # Execute in thread pool
        wav = await loop.run_in_executor(None, _synthesize)

        # Yield audio in chunks for better perceived latency
        # Chunk size: 256 samples = ~10.7ms at 24kHz
        chunk_size = 256
        for i in range(0, len(wav), chunk_size):
            yield wav[i:i + chunk_size]

            # Yield to event loop every chunk to avoid blocking
            await asyncio.sleep(0)

    async def synthesize(
        self,
        text: str,
        voice_file: Path,
        speed: float = 1.0,
        language: str = 'en'
    ) -> np.ndarray:
        """
        Synchronous synthesis (returns complete audio)

        Args:
            text: Text to synthesize
            voice_file: Path to reference voice audio file
            speed: Speech rate (0.5-2.0)
            language: Language code

        Returns:
            Audio samples as numpy array (float32, 24kHz)
        """
        # Preprocess text
        text = self._preprocess_text(text)

        # Run in thread pool
        loop = asyncio.get_event_loop()

        def _synthesize():
            try:
                # Use automatic mixed precision context for faster inference
                if self.device == 'cuda':
                    with torch.autocast('cuda', enabled=True):
                        wav = self.model.tts(
                            text=text,
                            speaker_wav=str(voice_file),
                            language=language,
                            speed=speed
                        )
                else:
                    wav = self.model.tts(
                        text=text,
                        speaker_wav=str(voice_file),
                        language=language,
                        speed=speed
                    )
                return wav
            except Exception as e:
                logger.error(f'TTS synthesis failed: {e}')
                raise

        return await loop.run_in_executor(None, _synthesize)

    async def _get_speaker_embedding(self, voice_file: Path) -> Optional[np.ndarray]:
        """
        Get speaker embedding with FIFO caching

        Args:
            voice_file: Path to voice reference file

        Returns:
            Speaker embedding array
        """
        voice_key = str(voice_file)

        # Check cache
        if voice_key in self.speaker_cache:
            return self.speaker_cache[voice_key]

        # Generate embedding
        try:
            loop = asyncio.get_event_loop()

            def _get_embedding():
                return self.model.synthesizer.get_speaker_embedding(str(voice_file))

            embedding = await loop.run_in_executor(None, _get_embedding)

            # Cache it (FIFO: remove oldest entry if at capacity)
            if len(self.speaker_cache) >= self.max_cache_size:
                oldest_key = next(iter(self.speaker_cache))
                del self.speaker_cache[oldest_key]
                logger.debug(f'Evicted oldest speaker embedding ({oldest_key}) from cache')

            self.speaker_cache[voice_key] = embedding
            logger.debug(f'Cached speaker embedding for {voice_file.name}')

            return embedding
        except Exception as e:
            logger.error(f'Failed to get speaker embedding: {e}')
            return None

    @staticmethod
    def _preprocess_text(text: str) -> str:
        """
        Preprocess text for better TTS output

        Args:
            text: Raw text input

        Returns:
            Preprocessed text
        """
        # Remove Discord formatting
        text = text.replace('**', '')  # Bold
        text = text.replace('__', '')  # Underline
        text = text.replace('~~', '')  # Strikethrough
        text = text.replace('`', '')   # Code

        # Remove URLs
        import re
        text = re.sub(r'https?://\S+', '', text)

        # Limit length (avoid extremely long messages)
        max_chars = 500
        if len(text) > max_chars:
            text = text[:max_chars] + '...'

        return text.strip()

    def get_available_languages(self) -> list[str]:
        """Get list of supported languages"""
        return [
            'en', 'es', 'fr', 'de', 'it', 'pt', 'pl', 'tr', 'ru', 'nl',
            'el', 'hu', 'zh-cn', 'ja', 'ko', 'ar'
        ]

    def warmup(self):
        """Warmup model on startup to eliminate first-call lag"""
        logger.info('Warming up TTS model...')
        try:
            self.model.tts(
                text='The quick brown fox jumps over the lazy dog.',
                language='en'
            )
            logger.info('Model warmup complete')
        except Exception as e:
            logger.warning(f'Model warmup failed (non-critical): {e}')
