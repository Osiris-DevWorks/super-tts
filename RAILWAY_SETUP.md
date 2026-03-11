# Railway Deployment Setup Guide

## Database Configuration (Critical!)

### The Problem
The bot **cannot start** without a working database connection. If you see errors like:
```
Failed to connect to database after 3 attempts
[Errno 111] Connect call failed ('127.0.0.1', 5432)
```

This means the `DATABASE_URL` environment variable is pointing to `localhost`, which **doesn't work** in Railway's containerized environment.

### Solution: Link PostgreSQL Plugin

1. **Go to your Railway project dashboard**
2. **Click "+ Add Service"** → Select **"Database"** → **PostgreSQL**
3. **Railway will automatically:**
   - Create a PostgreSQL instance
   - Set the `DATABASE_URL` environment variable automatically
   - Inject the correct connection string into your bot service

### Verify Configuration

After linking PostgreSQL:
1. Go to **Variables** tab in your bot service
2. You should see `DATABASE_URL` populated with something like:
   ```
   postgresql://postgres:password@container-xyz:5432/railway
   ```
3. It should **NOT** contain `localhost` or `127.0.0.1`

### Manual Configuration (if auto-linking fails)

If Railway doesn't auto-populate DATABASE_URL:

1. Go to your PostgreSQL service → **Variables** tab
2. Copy the `DATABASE_URL` value
3. Go to your bot service → **Variables** tab
4. Add/update `DATABASE_URL` with the PostgreSQL connection string

## Environment Variables Required

```
DISCORD_TOKEN=your_bot_token_here
OWNER_ID=your_discord_id
DATABASE_URL=postgresql://postgres:password@container:5432/railway
```

## Testing Connection

The bot will attempt to connect on startup:
- Retry 3 times with exponential backoff (1s, 2s, 4s delays)
- If all 3 attempts fail, bot will crash with helpful error message
- Check logs: **"Database connection succeeded"** = working

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `[Errno 111] Connect call failed` | Port unreachable | PostgreSQL plugin not linked, or wrong host in DATABASE_URL |
| `password authentication failed` | Wrong credentials | Check PostgreSQL plugin credentials in Railway |
| `database "tts_db" does not exist` | Schema not initialized | Run migration SQL from `db/migrations/` |

## See Also
- Railway Docs: https://docs.railway.app/guides/databases
- SQLAlchemy Connection Strings: https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls
