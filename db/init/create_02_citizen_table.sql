CREATE TABLE IF NOT EXISTS citizens (
    id SERIAL PRIMARY KEY,
    rsi_handle TEXT NOT NULL UNIQUE,
    rsi_dossier_url TEXT NOT NULL UNIQUE,
    rsi_org_id TEXT NOT NULL,
    rsi_org_rank TEXT NOT NULL,
    visibility TEXT NOT NULL CHECK (visibility IN ('V', 'H', 'R', 'U')),
    discord_user_id BIGINT UNIQUE,
    discord_name TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);
