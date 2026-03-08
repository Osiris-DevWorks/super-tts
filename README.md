# Super TTS Bot

Ultra-fast Supertonic-based Discord text-to-speech bot. A lightweight, standalone TTS bot powered by Supertonic for real-time voice synthesis.

## Features

- **Supertonic Engine**: Ultra-fast on-device TTS synthesis (~25-50ms per phrase)
- **Multiple Voices**: M1-M5 (male), F1-F5 (female), and custom voice support
- **Discord Integration**: Full Discord.py cog-based architecture
- **Async Queue**: Per-guild message queuing with FIFO ordering
- **User Preferences**: Per-user voice and speed customization via PostgreSQL
- **Rate Limiting**: Built-in per-user rate limiting to prevent abuse

## Requirements

- Python 3.11+
- PostgreSQL (for user preferences and monitoring channels)
- NVIDIA GPU (optional, but recommended for better performance)
- FFmpeg (for audio support)

## Setup

### 1. Install Poetry

If you don't have Poetry installed:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Clone and Setup

```bash
cd super-tts
poetry install
```

### 3. Configure Environment

Create a `.env` file:
```bash
cp .env.example .env
```

Edit `.env` with your Discord bot token and database connection:
```env
DISCORD_TOKEN=your_bot_token_here
DATABASE_URL=postgresql://user:password@localhost:5432/tts_db
```

### 4. Database Setup

Create the PostgreSQL database and tables:
```bash
poetry run python db/init_db.py
```

### 5. Run the Bot

```bash
poetry run python main.py
```

Or with debug logging:
```bash
poetry run python main.py DEBUG
```

## Configuration

Edit `config/config.yaml` to customize:
- TTS device (auto, cuda, rocm, cpu)
- Default voice
- Sample rates
- Queue size
- User preferences

## Poetry Commands

```bash
# Install dependencies
poetry install

# Run the bot
poetry run python main.py

# Add a new dependency
poetry add package_name

# Update dependencies
poetry update

# Generate requirements.txt (if needed)
poetry export -f requirements.txt --output requirements.txt
```

## Project Structure

```
super-tts/
├── tts/                    # TTS engine implementations
│   ├── supertonic_engine.py  # Main Supertonic engine
│   ├── audio_pipeline.py     # Audio processing
│   └── engine_factory.py     # Engine creation
├── tts_module/             # Discord cog
│   ├── tts.py              # Main TTS cog
│   └── db_models.py        # Database models
├── utils/                  # Utilities
│   ├── queue_manager.py    # Message queuing
│   └── config_loader.py    # Config management
├── config/                 # Configuration files
│   └── config.yaml
├── db/                     # Database utilities
├── common/                 # Common utilities
├── pyproject.toml          # Poetry configuration
└── README.md
```

## Dependencies

- **discord.py** ^2.6 - Discord bot framework
- **TTS** ^0.22 - Coqui TTS library
- **torch** ^2.4 - Deep learning framework
- **supertonic** ^1.1 - Supertonic TTS engine
- **asyncpg** ^0.31 - PostgreSQL driver
- **pydub** ^0.25 - Audio processing

## License

MIT
