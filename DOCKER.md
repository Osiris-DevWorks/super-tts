# Docker Setup for Super TTS Bot

This guide explains how to run Super TTS Bot using Docker.

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Discord bot token
- (Optional) NVIDIA GPU with nvidia-docker for GPU acceleration

## Quick Start

### 1. Create `.env` file

Copy the example and fill in your values:
```bash
cp .env.example .env
```

Edit `.env`:
```env
DISCORD_TOKEN=your_discord_bot_token_here
OWNER_ID=your_discord_id_here
DB_USER=postgres
DB_PASSWORD=secure_password_here
DB_NAME=tts_db
LOG_LEVEL=INFO
TTS_DEVICE=auto
```

### 2. Build and Start Services

```bash
# Build images and start services
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop services
docker-compose down
```

### 3. Verify Bot is Running

```bash
# Check container status
docker-compose ps

# Check bot logs
docker-compose logs bot

# Check database connection
docker-compose exec bot python -c "import asyncpg; print('DB OK')"
```

## Docker Images

### Build Custom Image

```bash
# Build with default tag
docker build -t super-tts:latest .

# Build with specific tag
docker build -t super-tts:0.1.0 .

# View image details
docker images super-tts
```

### Run Container Manually

```bash
# Basic run with default network
docker run -it --rm \
  -e DISCORD_TOKEN=your_token \
  -e DATABASE_URL=postgresql://user:pass@db:5432/tts_db \
  super-tts:latest

# Run with volume mounts
docker run -it --rm \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data:/app/data \
  -e DISCORD_TOKEN=your_token \
  super-tts:latest

# Run with GPU support (nvidia-docker)
docker run -it --rm \
  --gpus all \
  -e DISCORD_TOKEN=your_token \
  -e TTS_DEVICE=cuda \
  super-tts:latest
```

## Docker Compose Services

### PostgreSQL Database

- **Image**: `postgres:15-alpine`
- **Port**: 5432 (internal only in compose)
- **Volume**: `postgres_data` (persistent)
- **Health Check**: 10s interval, 5s timeout

To access database directly:
```bash
docker-compose exec postgres psql -U postgres -d tts_db
```

### TTS Bot

- **Image**: Built from Dockerfile
- **Depends On**: postgres service (healthy)
- **Volumes**:
  - `./logs` → `/app/logs` (bot logs)
  - `./data` → `/app/data` (audio files, cache)
  - `./config` → `/app/config` (configuration)

## GPU Support

### NVIDIA GPU

Enable GPU in `docker-compose.yml`:

```yaml
bot:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

Then run with nvidia-docker:
```bash
docker-compose up -d
```

Or manually:
```bash
docker run --gpus all -it super-tts:latest
```

### Verify GPU in Container

```bash
docker-compose exec bot python -c "import torch; print(torch.cuda.is_available())"
```

## Troubleshooting

### Bot Won't Start

Check logs:
```bash
docker-compose logs bot
```

Common issues:
- Missing `DISCORD_TOKEN` environment variable
- Database not healthy yet (wait 30 seconds)
- Invalid bot token

### Database Connection Failed

```bash
# Check database is running and healthy
docker-compose ps

# Check database logs
docker-compose logs postgres

# Verify connectivity
docker-compose exec bot python -c "
import asyncio
import asyncpg
async def test():
    conn = await asyncpg.connect('postgresql://postgres:postgres@postgres:5432/tts_db')
    await conn.close()
asyncio.run(test())
"
```

### High Memory Usage

Reduce cache or adjust Supertonic settings in `config/config.yaml`:

```yaml
tts:
  max_concurrent: 2  # Reduce from 6
  supertonic:
    device: cpu  # Use CPU instead of GPU
```

## Development Workflow

### Local Development with Docker

```bash
# Start just the database
docker-compose up postgres -d

# Run bot locally (outside docker)
poetry install
poetry run python main.py DEBUG
```

### Make Code Changes

1. Edit code locally
2. Restart bot:
   ```bash
   docker-compose restart bot
   # OR rebuild if dependencies changed
   docker-compose up -d --build
   ```

### Database Migrations

```bash
# Access database
docker-compose exec postgres psql -U postgres -d tts_db

# Run migration script
docker-compose exec bot python db/init_db.py
```

## Production Deployment

### Using Docker Swarm

```bash
# Initialize swarm (if needed)
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml tts

# View services
docker service ls

# View logs
docker service logs tts_bot
```

### Using Kubernetes

See `k8s/` directory for Kubernetes manifests.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCORD_TOKEN` | - | Discord bot token (required) |
| `OWNER_ID` | - | Discord owner ID (required) |
| `DB_USER` | postgres | PostgreSQL username |
| `DB_PASSWORD` | postgres | PostgreSQL password |
| `DB_NAME` | tts_db | Database name |
| `DB_HOST` | postgres | Database host |
| `DB_PORT` | 5432 | Database port |
| `TTS_DEVICE` | auto | TTS device (auto/cuda/rocm/cpu) |
| `LOG_LEVEL` | INFO | Logging level |

## Building for Production

```bash
# Build optimized image
docker build \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  -t super-tts:latest \
  -t super-tts:0.1.0 \
  .

# Push to registry
docker tag super-tts:latest myregistry.azurecr.io/super-tts:latest
docker push myregistry.azurecr.io/super-tts:latest
```

## Cleanup

```bash
# Stop services
docker-compose down

# Remove volumes
docker-compose down -v

# Remove all containers and images
docker-compose down --rmi all -v
```

## References

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [NVIDIA Docker Runtime](https://github.com/NVIDIA/nvidia-docker)
