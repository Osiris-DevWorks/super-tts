-- Migration: Create leaderboard configuration table
-- Stores the configuration for the live award leaderboard
-- Singleton pattern: only one row (id = 1) manages the entire leaderboard

CREATE TABLE IF NOT EXISTS leaderboard_config (
    id SERIAL PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    message_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Initialize singleton row with empty configuration
INSERT INTO leaderboard_config (id, channel_id, message_id)
VALUES (1, 0, NULL)
ON CONFLICT (id) DO NOTHING;
