# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Super TTS is a Discord text-to-speech bot built on `discord.py` + `supertonic` (ONNX Runtime) + PostgreSQL, deployed via Docker / Railway. Auxiliary docs that are still authoritative: `DATABASE.md` (schema), `RAILWAY.md` / `RAILWAY_ENV_VARS.md` (deploy), `DOCKER.md` (local), `DISCORD_SETUP.md` (bot perms). Don't duplicate them — extend them.

## Commands

Poetry is the source of truth (`pyproject.toml`); pip/requirements files are not used.

```bash
poetry install                          # full install (heavy: torch, supertonic, onnxruntime)
poetry run python main.py               # run bot (default LOG_LEVEL=INFO)
poetry run python main.py DEBUG         # run with debug logging — log level is positional argv[1]

poetry run pytest tests/ -v             # full test suite
poetry run pytest tests/test_db.py -v   # single file
poetry run pytest tests/test_db.py::TestDB::test_connect -v   # single test

poetry run black .                      # format (line-length 100, target py3.11)
poetry run flake8                       # lint
poetry run mypy .                       # types (ignore_missing_imports = true)

docker-compose up                       # local: spins up postgres + bot
docker-compose up postgres -d           # just the DB, then run main.py locally
```

`pytest.ini_options` in `pyproject.toml` sets `asyncio_mode = "auto"` — async tests don't need `@pytest.mark.asyncio`.

## Architecture

### Bootstrap (`main.py`)

1. `DB()` instantiated module-scope (no connection yet — `dsn` is read from `DATABASE_URL`).
2. In `main()`: `execute_sql_files("db/migrations", db)` runs migrations, then `db.connect()` opens the asyncpg pool.
3. `bot.load_extension("tts_module.tts")` loads the cog, then **the DB instance is monkey-patched onto the cog** (`tts_cog.db = db`) — the cog cannot be constructed with the DB since `commands.Bot.add_cog` wraps construction. The cog defers DB-model instantiation via `TTS._ensure_db_models()`, which is called lazily at the top of every command and listener.

This pattern is load-bearing: removing the lazy guard or moving model construction into `__init__` will break loading order.

### TTS pipeline

```
Discord message  →  on_message listener (tts_module/tts.py)
                 →  QueueManager.enqueue(guild_id, QueuedMessage)
                 →  per-guild asyncio.Queue, drained by a processor task
                 →  AudioPipeline.synthesize_and_convert (tts/audio_pipeline.py)
                       ├─ SupertonicEngine.synthesize (ONNX, in thread executor)
                       └─ ffmpeg subprocess: 24kHz mono → 48kHz stereo PCM
                 →  PCMAudioSource fed to guild.voice_client.play()
```

Concurrency cap: `tts.max_concurrent` in `config/config.yaml` (default 20) is enforced by `QueueManager` via `asyncio.Semaphore`.

### TTS engine layer (`tts/`)

`TTSEngineFactory.create()` is a factory in name only — it always returns `SupertonicEngine`. The `BaseTTSEngine` abstraction and factory are vestigial from a multi-engine era; do not add new engines without removing the dead branches. `engine.py` is unused.

`SupertonicEngine` does two things on init that surprise people:
- Calls `TTS(auto_download=True)` which downloads the ONNX model from HuggingFace on first run (set `HF_TOKEN` to avoid rate limits).
- Copies every `voices/*.json` into `~/.cache/supertonic2/voice_styles/`, matching filenames against `AVAILABLE_VOICES` keys case-insensitively. New custom voices ship as `voices/<Name>.json` with the `<Name>` also added to `AVAILABLE_VOICES`.

All voice styles are pre-cached at startup (`_voice_style_cache`) — synthesis is keyed lookup, not disk I/O.

### Database (`db/` + `tts_module/db_models.py`)

Schema name is `super_tts`. Migrations in `db/migrations/` run in this order on every boot via `execute_sql_files`:
1. All `create_*.sql` files, sorted alphabetically.
2. All `migrate_*.sql` files, sorted alphabetically.

The runner has **no migration tracking** — every file must be idempotent (`CREATE TABLE IF NOT EXISTS`, `ALTER ... IF NOT EXISTS`, `ON CONFLICT DO NOTHING`). When adding a migration, follow the `create_NN_*.sql` / `migrate_NN_*.sql` numbering and assume it will run again on the next deploy.

`MANUAL_FIX_voice_claims.sql` is a manual repair script — it does not get auto-run (no `create_`/`migrate_` prefix) and exists for one-off DB surgery.

Four model classes wrap the schema (all in `tts_module/db_models.py`): `TTSMonitoredChannels`, `TTSUserPreferences`, `TTSUserSubscriptions`, `TTSVoiceClaims`. The voice-claim system is the non-trivial part — it ties claims to subscriptions via FK with `ON DELETE CASCADE`, and the cog's `cleanup_expired_subscriptions` background task (hourly) is what releases voices when subs lapse.

### Voice claims domain rules

These rules live in code, not the schema, and are duplicated across `claim_voice`, `voice_set`, `reassign_voice` — change them in all three:

- `M1`–`M5`, `F1`–`F5` are **protected/public**: cannot be claimed, cannot be reassigned. The list is hardcoded as `protected_voices = ['M1','M2',...,'F5']` (search for that literal).
- One claim per user (enforced by partial unique index — see `fix_05_voice_claims_partial_unique.sql`).
- A user with a claim can still `voice_set` to a different voice; their preference wins over their claim. See the on_message handler comment "respect user preference change even with claimed voice" (commit `55bda3f`).
- A claimed voice rejects synthesis from non-owners with an ephemeral reply, message dropped (no fallback voice).

### Duplicate package: `utils/` vs `tts_module/`

`utils/queue_manager.py` and `tts_module/queue_manager.py` are **near-identical files** (same line count, slight content drift), and the same goes for `config_loader.py`. The cog imports from `utils.*`; nothing currently imports from `tts_module.queue_manager` / `tts_module.config_loader`. Treat `utils/` as canonical. If you edit one, mirror to the other or delete the dead copy — but check imports first.

### `common/` is a partial copy from citizen-bot

`common/load_sql.py` references `PROJECT_ROOT` from `common.constants` and is **not** what runs migrations (that's `db/init_db.py:execute_sql_files`). `common/roles.py:has_any_role` is currently a no-op decorator that always returns `True` — every `@has_any_role(...)` admin command is effectively unguarded. The real admin gate is `is_admin_or_owner` in `tts_module/tts.py`, which checks `interaction.client.owner_id` and an "Admin" role by name. If you tighten access control, fix `roles.py` rather than adding more `is_admin_or_owner` checks.

## Configuration sources (in precedence order)

1. **Environment variables** — `DISCORD_TOKEN`, `DATABASE_URL`, `OWNER_ID`, `LOG_LEVEL`, `TTS_DEVICE`, `HF_TOKEN`. Loaded from `.env` via `python-dotenv` at module import.
2. **`config/config.yaml`** — TTS engine settings (`tts.max_concurrent`, `tts.warmup`, `tts.supertonic.device`, `tts.supertonic.voice`), audio sample rates, queue sizes. Read via `utils.config_loader.ConfigLoader`.
3. **CLI argv** — `sys.argv[1]` overrides `LOG_LEVEL` if it's a valid level name.

`TTS_MAX_CONCURRENT` env var is documented in `RAILWAY.md` but is **not currently read** — concurrency comes from `config.yaml`. Either wire the env var in `tts_module/tts.py` (`cog_load`) or remove it from the docs.

## Deploy

- Push to `main` triggers `.github/workflows/deploy.yml` → `railway up --detach` (needs `RAILWAY_TOKEN` secret).
- Railway auto-injects `DATABASE_URL` from the linked Postgres plugin; do not set it manually. The DB layer warns if `DATABASE_URL` contains `localhost`.
- `railway.json` points at the `Dockerfile`; the Dockerfile is multi-stage (poetry install in builder, copy site-packages to slim runtime, run as non-root `ttsbot` UID 1000).

## When adding features

- New slash commands go on the existing `tts_group` / `setup_group` / `voice_group` / `admin_voice_group` in `tts_module/tts.py`. Always call `self._ensure_db_models()` before touching DB models.
- New tables: write an idempotent `create_NN_name.sql` in `db/migrations/`, then add a model class in `tts_module/db_models.py` and instantiate it in `_ensure_db_models()`.
- New voices: drop `<Name>.json` in `voices/`, add `<Name>: 'description'` to `SupertonicEngine.AVAILABLE_VOICES`. If it should be claimable, **don't** add it to the `protected_voices` list.
