# Super TTS Database Setup

## Overview

Super TTS uses PostgreSQL to store user preferences and monitored channels configuration. The database is automatically initialized on bot startup with all required tables and schema.

## Database Schema

The bot creates a `super_tts` schema containing:

### Tables

#### `super_tts.monitored_channels`
Stores Discord channels where auto-TTS is enabled.

| Column | Type | Description |
|--------|------|-------------|
| `channel_id` | BIGINT (PK) | Discord channel ID |
| `guild_id` | BIGINT | Discord guild/server ID |
| `channel_name` | VARCHAR(255) | Channel name at time of monitoring |
| `added_by` | BIGINT | User ID who enabled monitoring |
| `created_at` | TIMESTAMP | When monitoring was enabled |
| `updated_at` | TIMESTAMP | Last update timestamp |

#### `super_tts.user_preferences`
Stores individual user TTS preferences.

| Column | Type | Description |
|--------|------|-------------|
| `user_id` | BIGINT (PK) | Discord user ID |
| `voice_name` | VARCHAR(100) | Preferred voice for TTS |
| `speed` | FLOAT | Speech speed (0.5-2.0) |
| `pitch` | FLOAT | Voice pitch (0.8-1.2) |
| `language` | VARCHAR(10) | Language code |
| `created_at` | TIMESTAMP | When preferences were created |
| `updated_at` | TIMESTAMP | Last update timestamp |

## Automatic Migration System

The bot automatically runs database migrations on startup:

1. **Schema Creation** (`create_01_schema.sql`)
   - Creates the `super_tts` schema

2. **Table Creation** (`create_02_tts_tables.sql`)
   - Creates `monitored_channels` and `user_preferences` tables
   - Sets up indexes and constraints
   - Adds helpful comments

Migration files are located in `db/migrations/` and run in alphabetical order:
- Files starting with `create_` run first (for initial schema)
- Files starting with `migrate_` run after (for updates)

## Environment Variables

| Variable | Required | Example |
|----------|----------|---------|
| `DATABASE_URL` | Yes | `postgresql://user:pass@localhost:5432/tts_db` |
| `DB_HOST` | No | `localhost` |
| `DB_PORT` | No | `5432` |
| `DB_USER` | No | `postgres` |
| `DB_PASSWORD` | No | `password` |
| `DB_NAME` | No | `tts_db` |

The bot uses `DATABASE_URL` if provided. Other DB_* variables are optional and mainly for local reference.

## Local Development

### Using Docker Compose

```bash
docker-compose up
```

This starts:
- PostgreSQL database on `localhost:5432`
- Super TTS bot container

### Manual Setup

1. Install PostgreSQL
2. Create a database:
   ```sql
   CREATE DATABASE tts_db;
   ```

3. Set `DATABASE_URL`:
   ```bash
   export DATABASE_URL="postgresql://postgres:password@localhost:5432/tts_db"
   ```

4. Run the bot:
   ```bash
   python main.py
   ```

The bot automatically creates all required tables on first run.

## Railway Deployment

Railway automatically:
1. Provisions a PostgreSQL database
2. Sets `DATABASE_URL` environment variable
3. Runs your bot container

The bot will automatically initialize the database on first deployment.

## Adding New Migrations

To add a new migration:

1. Create a file in `db/migrations/` named `migrate_NNNN_description.sql`
   - Example: `migrate_0003_add_user_stats.sql`

2. Add your SQL:
   ```sql
   ALTER TABLE super_tts.user_preferences
   ADD COLUMN stats_json JSONB;
   ```

3. Commit and push - the bot will automatically run it on next deployment

## Database Connection Details

### Connection Pool
- Min size: 1 connection
- Max size: 10 connections
- Command timeout: 60 seconds
- Inactive connection lifetime: 300 seconds

### Automatic Reconnection
The bot includes automatic reconnection logic:
- Health checks run continuously
- Failed connections trigger automatic reconnect
- Exponential backoff prevents connection storms

## Debugging

### Check database connection:
```bash
# In bot logs, look for:
"Database connection pool created successfully"
"Database migrations completed successfully"
```

### Verify tables exist:
```bash
psql $DATABASE_URL -c "\dt super_tts.*"
```

### Monitor queries:
Enable debug logging in PostgreSQL to see all queries.

## Backup and Recovery

For Railway deployments, use Railway's built-in backup features:
1. Go to Railway dashboard
2. Navigate to PostgreSQL service
3. Use the backup/restore tools

For local development, use `pg_dump`:
```bash
pg_dump $DATABASE_URL > backup.sql
```

## Security

- Database credentials stored in `DATABASE_URL` environment variable
- Never commit `.env` files (use `.env.example`)
- Railway encrypts database credentials automatically
- Non-root user runs bot container for additional security
