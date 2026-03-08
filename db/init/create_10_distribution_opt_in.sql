-- Distribution Stipend Percentage Table
-- Tracks the stipend percentage (0-100) for each member
-- 0 = opted out, 100 = opted in at full rate, custom 1-99 = partial rate

CREATE TABLE IF NOT EXISTS distribution_opt_in (
    id SERIAL PRIMARY KEY,

    -- Member information
    discord_user_id BIGINT NOT NULL UNIQUE,
    discord_username TEXT NOT NULL,

    -- Stipend percentage (0-100, 0 = opted out, 100 = full rate)
    stipend_percentage INTEGER NOT NULL DEFAULT 100 CHECK (stipend_percentage >= 0 AND stipend_percentage <= 100),

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key
    FOREIGN KEY (discord_user_id) REFERENCES citizens(discord_user_id) ON DELETE CASCADE
);

-- Index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_distribution_opt_in_user ON distribution_opt_in (discord_user_id);
CREATE INDEX IF NOT EXISTS idx_distribution_opt_in_percentage ON distribution_opt_in (stipend_percentage);
