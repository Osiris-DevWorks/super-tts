"""
Build script for creating the Super TTS executable.

Usage:
    python scripts/build/build_exe.py                    # Build without bumping version
    python scripts/build/build_exe.py --increment patch  # 0.1.0 -> 0.1.1
    python scripts/build/build_exe.py --increment minor  # 0.1.0 -> 0.2.0
    python scripts/build/build_exe.py --increment major  # 0.1.0 -> 1.0.0

Produces dist/Super-TTS-v{VERSION}/Super-TTS-v{VERSION}.exe in onedir mode.
That directory is what installer.iss bundles into the Setup .exe.
"""

import os
import shutil
import sys

import PyInstaller.__main__

# Resolve the project root from this file's location: scripts/build/ -> repo root
build_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(build_dir))


def _bump_version(text: str, kind: str) -> str:
    parts = [int(p) for p in text.strip().split(".")]
    while len(parts) < 3:
        parts.append(0)
    major, minor, patch = parts[:3]
    if kind == "major":
        major, minor, patch = major + 1, 0, 0
    elif kind == "minor":
        minor, patch = minor + 1, 0
    elif kind == "patch":
        patch += 1
    else:
        raise ValueError(f"Unknown bump kind: {kind}")
    return f"{major}.{minor}.{patch}"


# Optional --increment patch|minor|major bump, mirroring smart-citizen
increment_kind = None
if len(sys.argv) > 2 and sys.argv[1] == "--increment":
    increment_kind = sys.argv[2].lower()
    if increment_kind not in ("major", "minor", "patch"):
        print(f"Error: invalid increment '{increment_kind}'. Use major | minor | patch.")
        sys.exit(1)

version_file = os.path.join(root_dir, "VERSION.TXT")
with open(version_file, "r", encoding="utf-8") as f:
    current_version = f.read().strip()

if increment_kind:
    current_version = _bump_version(current_version, increment_kind)
    with open(version_file, "w", encoding="utf-8") as f:
        f.write(current_version + "\n")
    print(f"Bumped VERSION.TXT to {current_version}")

print()
print("=" * 60)
print(f"Building Super TTS v{current_version}")
print("=" * 60)
print()

# Clean previous builds so stale data doesn't end up in the installer
print("Cleaning old builds...")
for folder in ("build", "dist"):
    path = os.path.join(root_dir, folder)
    if os.path.exists(path):
        shutil.rmtree(path)
        print(f"  - Removed {folder}/")
print()

exe_name = f"Super-TTS-v{current_version}"

config_dir = os.path.join(root_dir, "config")
migrations_dir = os.path.join(root_dir, "db", "migrations")
voices_dir = os.path.join(root_dir, "voices")
icon_path = os.path.join(root_dir, "assets", "super-tts.ico")

args = [
    # Entry point is the GUI wrapper — it sets SUPER_TTS_GUI_MODE=1 then
    # imports main.py and runs the bot in a QThread. Docker/Railway still
    # use main.py directly and never load gui_main.py.
    os.path.join(root_dir, "gui_main.py"),
    "--name", exe_name,
    # --windowed = no console window. The bot's stdout/stderr is surfaced
    # in the in-app Logs tab via the Qt-bridge logging handler in
    # gui/log_tab.py, so a console would just be a duplicate (and an ugly
    # one — it'd briefly flash on launch and confuse end users).
    "--windowed",
    "--noupx",  # AV scanners flag UPX-packed exes; sibling projects also disabled
    "--onedir",
    "--distpath", os.path.join(root_dir, "dist"),
    "--workpath", os.path.join(root_dir, "build"),
    "--specpath", root_dir,

    # Bundled data files. Without these, the bot can't find its config,
    # migrations, or voices when run from the installed location.
    "--add-data", f"{config_dir}{os.pathsep}config",
    "--add-data", f"{migrations_dir}{os.pathsep}db{os.sep}migrations",
    "--add-data", f"{voices_dir}{os.pathsep}voices",
    "--add-data", f"{version_file}{os.pathsep}.",

    # Hidden imports — modules PyInstaller's static graph misses because
    # they're loaded dynamically (asyncpg cython bits, discord voice,
    # the cog discovered via load_extension at runtime, scipy submodules,
    # PyQt6 platform plugins, and the bot module imported lazily inside
    # gui/bot_runner.py's QThread).
    "--hidden-import=asyncpg",
    "--hidden-import=asyncpg.pgproto.pgproto",
    "--hidden-import=discord",
    "--hidden-import=discord.voice_client",
    "--hidden-import=nacl",
    "--hidden-import=nacl.bindings",
    "--hidden-import=scipy.signal",
    "--hidden-import=scipy._lib.messagestream",
    "--hidden-import=main",
    "--hidden-import=tts_module.tts",
    "--hidden-import=tts_module.db_models",
    "--hidden-import=tts.supertonic_engine",
    "--hidden-import=tts.engine_factory",
    "--hidden-import=tts.audio_pipeline",
    "--hidden-import=tts.base_engine",
    "--hidden-import=utils.queue_manager",
    "--hidden-import=utils.config_loader",
    "--hidden-import=db.db",
    "--hidden-import=db.init_db",
    "--hidden-import=common.constants",
    "--hidden-import=common.roles",
    "--hidden-import=gui.main_window",
    "--hidden-import=gui.status_tab",
    "--hidden-import=gui.settings_tab",
    "--hidden-import=gui.log_tab",
    "--hidden-import=gui.about_tab",
    "--hidden-import=gui.bot_runner",
    "--hidden-import=gui.theme",
    "--hidden-import=gui.settings",

    # Pull every submodule + datafile of these packages — dynamic
    # registries / native shims / platform plugins that the static graph
    # alone won't catch.
    "--collect-all=supertonic",
    "--collect-all=onnxruntime",
    "--collect-submodules=PyQt6",

    # Drop dev tooling and the dead Coqui-TTS code path. Coqui ships a huge
    # transitive footprint (extra torch builds, trainer, etc.) that nothing
    # at runtime references — `tts/__init__.py` lazy-imports
    # `tts.engine.TTSEngine` and nothing in the live cog pulls that path.
    # Excluding here keeps pyproject.toml + poetry.lock untouched (so the
    # Railway/Docker build stays bit-for-bit identical) while still
    # shrinking the installer.
    "--exclude-module=TTS",
    "--exclude-module=trainer",
    "--exclude-module=pytest",
    "--exclude-module=black",
    "--exclude-module=mypy",
    "--exclude-module=flake8",
]

if os.path.exists(icon_path):
    args.extend(["--icon", icon_path])

print(f"Building --onedir bundle for {exe_name}...")
print(f"  Output: dist/{exe_name}/")
print()

try:
    PyInstaller.__main__.run(args)
except Exception as e:
    print(f"\nError: PyInstaller build failed: {e}")
    sys.exit(1)

print()
print("=" * 60)
print("Build successful.")
print("=" * 60)
print(f"  dist/{exe_name}/{exe_name}.exe")
print()
print("Next: run scripts/build/build_all.bat (or ISCC installer.iss) to wrap this")
print("into the Setup installer.")
