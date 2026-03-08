-- TTS Monitored Channels Table
-- Stores which text channels have auto-TTS enabled

CREATE TABLE IF NOT EXISTS tts_monitored_channels (
    channel_id BIGINT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_name VARCHAR(255) NOT NULL,
    added_by BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tts_monitored_guild ON tts_monitored_channels(guild_id);
CREATE INDEX IF NOT EXISTS idx_tts_monitored_created ON tts_monitored_channels(created_at DESC);
