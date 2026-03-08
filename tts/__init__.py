"""TTS Engine Package"""

# Lazy imports to avoid blocking on torch/torchaudio initialization
def __getattr__(name):
    if name == 'TTSEngine':
        from .engine import TTSEngine
        return TTSEngine
    elif name == 'AudioPipeline':
        from .audio_pipeline import AudioPipeline
        return AudioPipeline
    elif name == 'DiscordAudioPlayer':
        from .audio_pipeline import DiscordAudioPlayer
        return DiscordAudioPlayer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ['TTSEngine', 'AudioPipeline', 'DiscordAudioPlayer']
