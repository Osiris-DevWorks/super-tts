import logging
import os
import asyncio
import aiofiles
from db.db import DB

logger = logging.getLogger("super-tts")


async def execute_sql_files(migrations_dir, db):
    """
    Asynchronously executes all SQL files in the specified directory.
    Runs 'create_*' files first, then 'migrate_*' files to ensure tables exist before migrations run.
    """
    logger.info(f"Initializing database using SQL scripts in directory: {migrations_dir}")
    await db.connect()

    # Find all SQL files starting with 'create_' or 'migrate_'
    all_files = [
        file for file in os.listdir(migrations_dir)
        if (file.startswith("create_") or file.startswith("migrate_")) and file.endswith(".sql")
    ]

    # Sort so 'create_' files run first, then 'migrate_' files
    sql_files = sorted(all_files, key=lambda x: (x.startswith("migrate_"), x))

    if not sql_files:
        logger.info("No SQL files (create_* or migrate_*) found.")
        return

    # Execute each SQL file
    for sql_file in sql_files:
        try:
            file_path = os.path.join(migrations_dir, sql_file)
            async with aiofiles.open(file_path, "r") as file:
                sql_script = await file.read()
                logger.info(f"Executing: {sql_file}")
                await db.execute(sql_script)
        except Exception as e:
            logger.error(f"Error executing {sql_file}: {e}")
            raise e

    logger.info("Database initialization complete.")
