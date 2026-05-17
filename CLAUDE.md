# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Super TTS is a Discord text-to-speech bot built on `discord.py` + `supertonic` (ONNX Runtime) + PostgreSQL. It ships on **two tracks** from one codebase:

1. **Server track** — Docker / Railway deploys, entry point `main.py`. Configured via env vars; fail-fast if `DISCORD_TOKEN` is missing.
2. **Desktop track** — Windows GUI installer (PyQt6 + PyInstaller onedir + Inno Setup), entry point `gui_main.py`. Hosts the same bot inside a `QThread` so a non-technical user can run it locally. Configured via the GUI's Settings tab, persisted to `%APPDATA%\Osiris DevWorks\Super TTS\.env`.

Both tracks import `main.py`; the desktop track sets `SUPER_TTS_GUI_MODE=1` before import to disable the import-time token-missing exit. See **Windows GUI / installer track** below.

Auxiliary docs that are still authoritative: `DATABASE.md` (schema), `RAILWAY.md` / `RAILWAY_ENV_VARS.md` (server deploy), `DOCKER.md` (local), `DISCORD_SETUP.md` (bot perms). Don't duplicate them — extend them.

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

poetry run python gui_main.py           # run the desktop GUI from source

# Build the Windows installer (run from repo root, needs Inno Setup 6 installed):
python scripts\build\build_exe.py                       # build current version
python scripts\build\build_exe.py --increment patch     # bump VERSION.TXT then build
python scripts\build\build_exe.py --increment minor
python scripts\build\build_exe.py --increment major
scripts\build\build_all.bat                             # full pipeline: PyInstaller + ISCC installer.iss
```

`VERSION.TXT` is the single source of truth for the version number — `build_exe.py`, `installer.iss`, and the PyInstaller spec all read from it.

`pytest.ini_options` in `pyproject.toml` sets `asyncio_mode = "auto"` — async tests don't need `@pytest.mark.asyncio`.

## Architecture

### Bootstrap (`main.py`)

1. **`.env` resolution at import time**: if `%APPDATA%\Osiris DevWorks\Super TTS\.env` exists, it is loaded (installer path). Otherwise `load_dotenv()` does its default CWD search (dev / Docker / Railway). Set in stone — both tracks share this resolution.
2. **Token guard**: if `DISCORD_TOKEN` is missing AND `SUPER_TTS_GUI_MODE` is unset → `sys.exit(1)`. The GUI sets `SUPER_TTS_GUI_MODE=1` before importing `main` so its Settings tab can handle a missing token. Do not move this check or wrap it differently — the GUI relies on `import main` not exiting.
3. `DB()` instantiated module-scope (no connection yet — `dsn` is read from `DATABASE_URL`).
4. **`main()` builds a fresh `commands.Bot` per call** via `_build_bot()` — the bot is intentionally NOT a module-level singleton. discord.py's `Bot.start()` consumes the instance, so a module-level bot would make the GUI's Disconnect → Connect cycle one-shot per process. Treat `bot` as request-scoped, not global.
5. In `main()`: `execute_sql_files("db/migrations", db)` runs migrations, then `db.connect()` opens the asyncpg pool.
6. `bot.load_extension("tts_module.tts")` loads the cog, then **the DB instance is monkey-patched onto the cog** (`tts_cog.db = db`) — the cog cannot be constructed with the DB since `commands.Bot.add_cog` wraps construction. The cog defers DB-model instantiation via `TTS._ensure_db_models()`, which is called lazily at the top of every command and listener.
7. GUI bridge: `main.get_current_bot()` / `main.set_ready_observer(callback)` are the supported handles for the GUI thread. `on_ready` invokes the observer at its tail. Do not `add_listener` against `main.bot` — there is no such module attribute.

The lazy DB-model pattern and the per-call bot construction are load-bearing. Don't move model construction into `__init__`, and don't promote `bot` back to module scope.

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

### Windows GUI / installer track

The GUI is a thin PyQt6 shell that runs the bot inside a background thread; the bot code itself is unchanged across tracks.

**Entry point and bootstrap (`gui_main.py`)**

1. Sets `SUPER_TTS_GUI_MODE=1` before any `import main` happens.
2. Pre-loads `%APPDATA%\Osiris DevWorks\Super TTS\.env` into `os.environ` so the Settings and Status tabs can read `DISCORD_TOKEN` / `DATABASE_URL` before the bot thread starts. Same resolution order as `main.py` — APPDATA wins over CWD `.env`.
3. Builds `QApplication`, applies the persisted theme, shows `MainWindow`.

**Threading model (`gui/bot_runner.py`)**

`BotRunner(QThread)` owns an asyncio event loop and runs `main.main()` on it. Each Connect cycle spawns a **fresh `BotRunner`** — relying on `main()` building a fresh `Bot` per call (see Bootstrap step 4). Signals: `starting`, `ready(bot_name, guild_count)`, `error(str)`, `finished_clean`. Disconnect calls `main.get_current_bot().close()` through the loop.

**Tabs (`gui/`)**

| File | Role |
|---|---|
| `gui/main_window.py` | `QTabWidget` host. Opens on Settings tab if `DISCORD_TOKEN` is unset (first-run UX), otherwise on Status with a 150 ms-delayed auto-connect. |
| `gui/status_tab.py` | Connect/Disconnect, live status, guild count |
| `gui/settings_tab.py` | Editable form for `DISCORD_TOKEN`, `DATABASE_URL`, `OWNER_ID`, `HF_TOKEN`, `TTS_DEVICE`, theme. Writes to `%APPDATA%\Osiris DevWorks\Super TTS\.env`. |
| `gui/log_view.py` | In-app log tail attached to the root logger |
| `gui/help_tab.py`, `gui/about_tab.py`, `gui/footer.py`, `gui/theme.py` | Static content + theming |
| `gui/settings.py` | Bridges `QSettings` (theme only — registry path `HKCU\Software\Osiris DevWorks\Super TTS`) and the `.env` file (everything else). Exports `DEFAULT_DATABASE_URL` — the placeholder string the form pre-fills. |

The minimum window height is locked at 760 px so the Settings tab's helper labels don't get scrunched — don't lower it without re-checking that layout.

**Persistence split** — keep this divide intact:

- **`.env` at `%APPDATA%\Osiris DevWorks\Super TTS\.env`** — secrets and runtime config (`DISCORD_TOKEN`, `DATABASE_URL`, `OWNER_ID`, `HF_TOKEN`, `TTS_DEVICE`).
- **`QSettings` (HKCU)** — UI-only preferences (currently just the theme choice).

Rotating `DEFAULT_DATABASE_URL` requires rebuilding and redistributing the installer — it's compiled into the GUI binary.

### Build pipeline

- **Version source**: `VERSION.TXT` at repo root. `scripts/build/build_exe.py --increment {patch|minor|major}` bumps it; `installer.iss` reads it via Inno preprocessor; the PyInstaller spec is regenerated per build with the version baked into the exe name.
- **PyInstaller spec**: `Super-TTS-v{VERSION}.spec` (onedir mode). Bundles `config/`, `db/migrations/`, `voices/`, `assets/`, `VERSION.TXT` as data. Hidden imports include every cog/util module plus `collect_all('supertonic')` + `collect_all('onnxruntime')` + `collect_submodules('PyQt6')`. Excludes `TTS`, `trainer`, dev tools. When the import graph changes (new top-level module, new dynamically-imported voice engine), update the `hiddenimports` list in `scripts/build/build_exe.py` and rebuild.
- **Inno Setup script**: `installer.iss`. Installs to `{localappdata}\Osiris DevWorks\Super TTS` with `PrivilegesRequired=lowest` (no admin prompt). AppId GUID `F7A4D9C1-3B6E-4A2D-9C5F-8E1B7D0A2F4C` — never reuse from a sibling project; it's the upgrade-detection key. The installer **does not prompt for tokens** — token entry is GUI-only, via the Settings tab on first launch.
- **`build_all.bat`** is the convenience pipeline (clean → PyInstaller → ISCC). Two quirks worth keeping: (a) it reads `VERSION.TXT` and checks the exact build folder name because cmd's `if exist` doesn't expand wildcards on directories; (b) it locates `ISCC.exe` via a FOR loop because `if not defined ... if exist "C:\Program Files (x86)\..."` parser-collides on the `(x86)`. Don't "simplify" either back to the naive form.

When adding a new top-level Python module that the bot imports dynamically, also add it to the `hiddenimports` list in `scripts/build/build_exe.py` — PyInstaller's static analysis won't find it.

## Configuration sources (in precedence order)

1. **Environment variables** — `DISCORD_TOKEN`, `DATABASE_URL`, `OWNER_ID`, `LOG_LEVEL`, `TTS_DEVICE`, `HF_TOKEN`. Loaded from `.env` via `python-dotenv` at module import. **Resolution**: `%APPDATA%\Osiris DevWorks\Super TTS\.env` if present (installer path), else `load_dotenv()` CWD search (dev/Docker/Railway).
2. **`SUPER_TTS_GUI_MODE`** — set by `gui_main.py` / `BotRunner` to suppress `main.py`'s import-time token-missing exit. Never set this in server deployments.
3. **`QSettings`** (Windows registry, HKCU) — GUI-only preferences (theme). Never put secrets here.
4. **`config/config.yaml`** — TTS engine settings (`tts.max_concurrent`, `tts.warmup`, `tts.supertonic.device`, `tts.supertonic.voice`), audio sample rates, queue sizes. Read via `utils.config_loader.ConfigLoader`.
5. **CLI argv** — `sys.argv[1]` overrides `LOG_LEVEL` if it's a valid level name.

`TTS_MAX_CONCURRENT` env var is documented in `RAILWAY.md` but is **not currently read** — concurrency comes from `config.yaml`. Either wire the env var in `tts_module/tts.py` (`cog_load`) or remove it from the docs.

## Deploy

- Push to `main` triggers `.github/workflows/deploy.yml` → `railway up --detach` (needs `RAILWAY_TOKEN` secret).
- Railway auto-injects `DATABASE_URL` from the linked Postgres plugin; do not set it manually. The DB layer warns if `DATABASE_URL` contains `localhost`.
- `railway.json` points at the `Dockerfile`; the Dockerfile is multi-stage (poetry install in builder, copy site-packages to slim runtime, run as non-root `ttsbot` UID 1000).

## When adding features

- New slash commands go on the existing `tts_group` / `setup_group` / `voice_group` / `admin_voice_group` in `tts_module/tts.py`. Always call `self._ensure_db_models()` before touching DB models.
- New tables: write an idempotent `create_NN_name.sql` in `db/migrations/`, then add a model class in `tts_module/db_models.py` and instantiate it in `_ensure_db_models()`.
- New voices: drop `<Name>.json` in `voices/`, add `<Name>: 'description'` to `SupertonicEngine.AVAILABLE_VOICES`. If it should be claimable, **don't** add it to the `protected_voices` list. `voices/` is bundled into the PyInstaller build via `datas`, so the new file ships automatically — no spec change needed.
- New top-level Python modules: add to `hiddenimports` in `scripts/build/build_exe.py` (PyInstaller's static analysis misses dynamically-imported modules) and, if it ships data files, append to `datas`.
- New env-var-driven config: surface it in the GUI's Settings tab (`gui/settings_tab.py`) so installer users can set it without editing `%APPDATA%\Osiris DevWorks\Super TTS\.env` by hand.
