# Super TTS - Discord Text-to-Speech Bot

Ultra-fast Supertonic-based Discord TTS bot with user preferences and channel monitoring.

## Features

- **Fast TTS Synthesis** - Uses Supertonic for high-quality voice synthesis
- **User Preferences** - Save voice, speed, pitch, and language preferences
- **Channel Monitoring** - Auto-convert messages to TTS in monitored channels
- **PostgreSQL Backend** - Persistent data storage with automatic migrations
- **Docker Ready** - Easy deployment with Docker Compose or Railway

## Quick Start

### Prerequisites

- Python 3.11
- PostgreSQL 15+
- Discord bot token

### Local Development

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your values
3. Start with Docker Compose:
   ```bash
   docker-compose up
   ```

### Environment Variables

```bash
DISCORD_TOKEN=your_bot_token
OWNER_ID=your_discord_id
DATABASE_URL=postgresql://user:password@localhost:5432/tts_db
LOG_LEVEL=INFO
TTS_DEVICE=auto
```

## Deployment

See [RAILWAY.md](RAILWAY.md) for Railway deployment instructions.

## Database

The bot automatically creates all required tables on startup. See [DATABASE.md](DATABASE.md) for schema details.

## License

MIT
