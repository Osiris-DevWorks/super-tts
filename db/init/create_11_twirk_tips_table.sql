-- Create twirk_tips table
CREATE TABLE IF NOT EXISTS twirk_tips (
    id SERIAL PRIMARY KEY,
    tip_text TEXT NOT NULL,
    tip_weight INTEGER NOT NULL DEFAULT 5 CHECK (tip_weight >= 0 AND tip_weight <= 10),
    last_used_at TIMESTAMP,
    created_by_discord_id BIGINT NOT NULL,
    created_by_discord_name TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_twirk_tips_deleted_at ON twirk_tips(deleted_at);
CREATE INDEX IF NOT EXISTS idx_twirk_tips_last_used_at ON twirk_tips(last_used_at);
CREATE INDEX IF NOT EXISTS idx_twirk_tips_created_at ON twirk_tips(created_at);
CREATE INDEX IF NOT EXISTS idx_twirk_tips_weight ON twirk_tips(tip_weight);
