import logging
import os
import pandas as pd
import aiofiles
from db.db import DB
from db.backup import backup_database

# Configure logging
log = logging.getLogger("citizen-bot")


async def execute_sql_files(directory, db):
    """
    Asynchronously executes all SQL files in the specified directory.
    Runs 'create_*' files first, then 'migrate_*' files to ensure tables exist before migrations run.
    Creates a database backup before running any migrations.
    """
    log.info(f"Initializing database using SQL scripts in directory: {directory}")
    await db.connect()

    # Find all SQL files starting with 'create_' or 'migrate_'
    all_files = [
        file for file in os.listdir(directory)
        if (file.startswith("create_") or file.startswith("migrate_")) and file.endswith(".sql")
    ]

    # Sort so 'create_' files run first, then 'migrate_' files
    sql_files = sorted(all_files, key=lambda x: (x.startswith("migrate_"), x))

    if not sql_files:
        log.warning("No SQL files (create_* or migrate_*) found.")
        await db.close()
        return

    # Check if there are any migration files
    has_migrations = any(f.startswith("migrate_") for f in sql_files)

    # Create a backup before running migrations (only if database already exists and has tables)
    if has_migrations:
        try:
            await backup_before_migrations(db)
        except Exception as e:
            log.error(f"Backup failed, but continuing with migrations: {e}")
            # Don't fail startup just because backup failed

    # Execute each SQL file
    for sql_file in sql_files:
        try:
            file_path = os.path.join(directory, sql_file)
            async with aiofiles.open(file_path, "r") as file:
                sql_script = await file.read()
                log.info(f"Executing: {sql_file}")
                await db.execute(sql_script)
        except Exception as e:
            log.error(f"Error executing {sql_file}: {e}")
            raise e

    log.info("Database initialization complete.")
    await db.close()


async def backup_before_migrations(db):
    """
    Create a database backup before running migrations.
    Only backs up if the database has existing tables (not fresh install).
    """
    try:
        # Check if database has any existing tables
        query = """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """
        result = await db.fetch_one(query)
        table_count = result[0] if result else 0

        if table_count == 0:
            log.info("No existing tables found. Skipping backup (fresh install).")
            return

        # Parse DATABASE_URL to extract connection parameters
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            log.warning("DATABASE_URL not set. Skipping backup.")
            return

        db_config = parse_database_url(database_url)

        # Create backup directory
        backup_dir = os.path.join(os.path.dirname(__file__), 'backups')

        # Run backup with retention of 10 backups
        backup_filepath = await backup_database(db_config, backup_dir, keep_backups=10)
        log.info(f"Database backup created at: {backup_filepath}")

    except Exception as e:
        log.error(f"Error creating backup before migrations: {e}")
        raise


def parse_database_url(database_url: str) -> dict:
    """
    Parse a PostgreSQL DATABASE_URL into connection components.
    Format: postgresql://user:password@host:port/database
    """
    from urllib.parse import urlparse

    parsed = urlparse(database_url)

    return {
        'host': parsed.hostname or 'localhost',
        'port': str(parsed.port or 5432),
        'user': parsed.username or 'postgres',
        'password': parsed.password or '',
        'database': parsed.path.lstrip('/') if parsed.path else 'citizen_bot',
    }


async def load_seed_csv_files(seeds_dir, db):
    """
    Asynchronously loads all seed CSV files into the database, but only if the corresponding table is empty.
    """
    log.info(f"Loading seed data from directory: {seeds_dir}")
    await db.connect()

    # Find all CSV files in the seeds directory
    csv_files = sorted([
        file for file in os.listdir(seeds_dir)
        if file.endswith(".csv")
    ])

    if not csv_files:
        log.warning("No CSV files found in the seeds directory.")
        await db.close()
        return

    for csv_file in csv_files:
        try:
            table_name = csv_file.split(".")[0]  # Infer table name from the file name
            file_path = os.path.join(seeds_dir, csv_file)

            # Check if the table is empty
            log.info(f"Checking if table '{table_name}' is empty.")
            count = await db.fetchone(f"SELECT COUNT(*) FROM {table_name};")
            if count[0] > 0:
                log.info(f"Table '{table_name}' already contains data. Skipping seed load.")
                continue

            # Load the CSV file into a pandas DataFrame (synchronous)
            df = pd.read_csv(file_path)
            log.info(f"Loading data into table: {table_name}")

            # Insert data into the database using async operations
            columns = ", ".join(df.columns)
            placeholders = ", ".join([f"${i+1}" for i in range(len(df.columns))])
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            await db.conn.executemany(query, df.values.tolist())

            log.info(f"Successfully loaded data into table '{table_name}'.")

        except Exception as e:
            log.error(f"Error loading {csv_file} into table '{table_name}': {e}")
            raise e

    log.info("Seed data loading complete.")
    await db.close()
