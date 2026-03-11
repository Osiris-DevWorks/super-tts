# Railway Environment Variables - What You Actually Need

## TL;DR: Minimum Required for Railway

Only **2 environment variables** are required:

```
DISCORD_TOKEN=your_discord_bot_token_here
DATABASE_URL=postgresql://...    (auto-populated by Railway PostgreSQL plugin)
```

**1 optional but recommended:**
```
HF_TOKEN=hf_...    (Get from https://huggingface.co/settings/tokens)
```

---

## Full Analysis

### ✅ REQUIRED - Actually Used in Code

| Variable | Purpose | Where Used | Required? |
|----------|---------|-----------|-----------|
| `DISCORD_TOKEN` | Authenticate bot with Discord | `main.py` line 39, 106 | **YES** |
| `DATABASE_URL` | PostgreSQL connection string | `db/db.py` line 13 | **YES** |

### ⭐ RECOMMENDED - Optional but Improves Performance

| Variable | Purpose | Where Used | Required? |
|----------|---------|-----------|-----------|
| `HF_TOKEN` | Hugging Face Hub authentication | TTS model downloads | **NO** (but recommended) |

### ❌ NOT USED - Can Be Deleted

These variables are in `.env.example` but **not referenced anywhere** in the codebase:

| Variable | Why It's Not Used | Can Delete? |
|----------|------------------|-------------|
| `OWNER_ID` | Never referenced in code | **YES** |
| `DB_HOST` | Only `DATABASE_URL` is used | **YES** |
| `DB_PORT` | Only `DATABASE_URL` is used | **YES** |
| `DB_USER` | Only `DATABASE_URL` is used | **YES** |
| `DB_PASSWORD` | Only `DATABASE_URL` is used | **YES** |
| `DB_NAME` | Only `DATABASE_URL` is used | **YES** |
| `TTS_DEFAULT_VOICE` | Not implemented in code | **YES** |
| `TTS_DEVICE` | Not implemented in code | **YES** |
| `TTS_MAX_CONCURRENT` | Not implemented in code | **YES** |
| `BOT_ACTIVITY_NAME` | Not implemented in code | **YES** |
| `BOT_ACTIVITY_TYPE` | Not implemented in code | **YES** |
| `LOG_FILE` | Not implemented in code | **YES** |
| `PREFIX` | Hardcoded as "/" in `main.py` line 51 | **YES** |
| `LOG_LEVEL` | Taken from command-line arg, not env var | **YES** |

---

## Railway Setup (Simplified)

1. **Set DISCORD_TOKEN**
   - Variables tab → Add `DISCORD_TOKEN` → paste your Discord bot token

2. **Link PostgreSQL plugin**
   - "+ Add Service" → Database → PostgreSQL
   - Railway auto-populates `DATABASE_URL`

3. **That's it!** ✅

No need to set DB_HOST, DB_PORT, DB_USER, etc. - they're ignored by the code.

---

## Recommendation

Update `.env.example` to only include:
- `DISCORD_TOKEN`
- `DATABASE_URL` (with comment that Railway auto-populates this)

Delete all the unused variables to reduce confusion.

---

## HF_TOKEN Setup (Optional but Recommended)

**Why?** The TTS engine downloads models from Hugging Face Hub. Without authentication:
- ❌ Lower rate limits (may be throttled if many downloads)
- ❌ Slower downloads
- ✅ Still works, just suboptimal

**How to get HF_TOKEN:**

1. Go to https://huggingface.co/settings/tokens
2. Create a new token (read-only is fine)
3. Copy the token value
4. Add to Railway Variables: `HF_TOKEN=hf_xxxxx`

**In Railway:**
1. Go to your bot service → Variables tab
2. Add new variable: `HF_TOKEN`
3. Paste your token value
4. Redeploy

The warning will disappear and downloads will be faster!
