import logging
import os
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path

log = logging.getLogger("citizen-bot")


async def backup_database(db_config: dict, backup_dir: str, keep_backups: int = 10) -> str:
    """
    Create a backup of the PostgreSQL database before running migrations.
    Keeps only the last N backups, deleting older ones.

    Args:
        db_config: Dictionary with keys: host, port, user, password, database
        backup_dir: Directory to store backups
        keep_backups: Number of recent backups to keep (default: 10)

    Returns:
        Path to the created backup file
    """
    # Create backup directory if it doesn't exist
    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)

    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"citizen_bot_backup_{timestamp}.sql"
    backup_filepath = backup_path / backup_filename

    try:
        log.info(f"Starting database backup to {backup_filepath}")

        # Prepare pg_dump environment variables
        env = os.environ.copy()
        env['PGPASSWORD'] = db_config['password']

        # Build pg_dump command
        dump_cmd = [
            'pg_dump',
            '-h', db_config['host'],
            '-p', str(db_config['port']),
            '-U', db_config['user'],
            '-d', db_config['database'],
            '--verbose',
        ]

        # Run pg_dump asynchronously
        process = await asyncio.create_subprocess_exec(
            *dump_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            log.error(f"pg_dump failed: {error_msg}")
            raise Exception(f"Database backup failed: {error_msg}")

        # Write backup to file
        with open(backup_filepath, 'wb') as f:
            f.write(stdout)

        backup_size_mb = backup_filepath.stat().st_size / (1024 * 1024)
        log.info(f"Database backup completed successfully: {backup_filename} ({backup_size_mb:.2f} MB)")

        # Clean up old backups, keeping only the last N
        await cleanup_old_backups(backup_path, keep_backups)

        return str(backup_filepath)

    except Exception as e:
        log.error(f"Failed to backup database: {e}")
        raise


async def cleanup_old_backups(backup_dir: Path, keep_count: int = 10):
    """
    Delete old backup files, keeping only the most recent N backups.

    Args:
        backup_dir: Directory containing backup files
        keep_count: Number of recent backups to keep
    """
    try:
        # List all backup files in the directory
        backup_files = sorted(
            backup_dir.glob("citizen_bot_backup_*.sql"),
            key=lambda x: x.stat().st_mtime,
            reverse=True  # Most recent first
        )

        # If we have more than keep_count backups, delete the oldest ones
        if len(backup_files) > keep_count:
            files_to_delete = backup_files[keep_count:]
            for old_backup in files_to_delete:
                try:
                    old_backup.unlink()
                    backup_size_mb = old_backup.stat().st_size / (1024 * 1024) if old_backup.exists() else 0
                    log.info(f"Deleted old backup: {old_backup.name} ({backup_size_mb:.2f} MB)")
                except Exception as e:
                    log.warning(f"Failed to delete old backup {old_backup.name}: {e}")

        # Log current backup count
        remaining_backups = list(backup_dir.glob("citizen_bot_backup_*.sql"))
        log.info(f"Backup retention: {len(remaining_backups)} backups kept (max: {keep_count})")

    except Exception as e:
        log.error(f"Error during backup cleanup: {e}")
        # Don't raise here - backup cleanup shouldn't fail the entire startup
