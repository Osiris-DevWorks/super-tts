# Railway Deployment Guide

## Overview

Super-TTS is configured for deployment on [Railway](https://railway.app) - a simple platform-as-a-service that deploys from Docker images.

## Prerequisites

1. Railway account (sign up at https://railway.app)
2. GitHub account with this repository connected
3. Discord bot token
4. Discord server ID (Guild ID)
5. Your Discord user ID (Owner ID)

## Setup Steps

### 1. Connect GitHub to Railway

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Authorize Railway with GitHub and select the `super-tts` repository

### 2. Configure PostgreSQL Database

1. In your Railway project, click "Add Service"
2. Select "PostgreSQL"
3. Railway will automatically provision a PostgreSQL database
4. The `DATABASE_URL` will be automatically injected as an environment variable

### 3. Set Environment Variables

In the Railway dashboard, add the following environment variables for the bot service:

```
DISCORD_TOKEN=your_discord_bot_token_here
OWNER_ID=your_discord_user_id_here
LOG_LEVEL=INFO
TTS_DEVICE=auto
TTS_MAX_CONCURRENT=6
```

### 4. Deploy

Push your code to the `main` branch. Railway will:
1. Detect the Dockerfile
2. Build the Docker image
3. Deploy to Railway's infrastructure
4. Run migrations and start the bot

## Architecture

```
GitHub Repository
    ↓
  Webhook (on push to main)
    ↓
Railway CI/CD
    ↓
Build Docker Image
    ↓
Deploy Service
```

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Discord bot token | `token_here` |
| `OWNER_ID` | Your Discord user ID | `123456789` |
| `DATABASE_URL` | PostgreSQL connection | Auto-set by Railway |
| `LOG_LEVEL` | Logging level | `INFO` |
| `TTS_DEVICE` | TTS computation device | `auto`, `cuda`, `cpu` |
| `TTS_MAX_CONCURRENT` | Max concurrent TTS jobs | `6` |

## Monitoring

1. View logs: Railway Dashboard → Your Project → Bot Service → Logs
2. View deployment history: Railway Dashboard → Your Project → Deployments
3. Check health: Railway Dashboard → Your Project → Service Status

## Troubleshooting

### Build fails
- Check logs in Railway dashboard
- Ensure `Dockerfile` is in the repository root
- Verify Python 3.11 compatibility

### Bot crashes
- Check Discord token is valid
- Verify environment variables are set
- Review logs in Railway dashboard

### Database connection issues
- Ensure PostgreSQL service is running
- Check `DATABASE_URL` is correctly injected
- Verify database credentials

## Manual Deployment

You can also deploy manually using the Railway CLI:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link

# Deploy
railway up
```

## Alternative: GitHub Actions Deployment

The repository includes a GitHub Actions workflow (`.github/workflows/deploy.yml`) that automatically deploys to Railway when you push to `main`.

To enable:
1. Add `RAILWAY_TOKEN` secret to your GitHub repository
   - Go to Settings → Secrets and variables → Actions
   - Create `RAILWAY_TOKEN` from Railway dashboard (Account → Tokens)
2. Push to main branch - deployment starts automatically

## Cost

Railway offers:
- **Free tier**: $5 credit/month
- **Usage-based pricing**: Pay for what you use
- **PostgreSQL**: Included in free tier
- **Bot service**: Starts at $7/month (typical usage)

Check [Railway Pricing](https://railway.app/pricing) for current rates.

## Resources

- [Railway Documentation](https://docs.railway.app)
- [Railway Discord Community](https://discord.gg/railway)
- [Docker Documentation](https://docs.docker.com)
