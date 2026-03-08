-- TTS User Preferences Table
-- Stores per-user TTS settings

CREATE TABLE IF NOT EXISTS tts_user_preferences (
    user_id BIGINT PRIMARY KEY,
    voice_name VARCHAR(100) DEFAULT 'default',
    speed DECIMAL(3, 1) DEFAULT 1.0,
    pitch DECIMAL(3, 2) DEFAULT 1.0,
    language VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tts_user_preferences_updated ON tts_user_preferences(updated_at DESC);
