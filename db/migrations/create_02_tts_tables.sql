-- TTS Monitored Channels Table
-- Stores Discord channels where the bot should auto-convert messages to TTS
CREATE TABLE IF NOT EXISTS super_tts.monitored_channels (
    channel_id BIGINT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_name VARCHAR(255) NOT NULL,
    added_by BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_monitored_channels_guild_id
    ON super_tts.monitored_channels(guild_id);

COMMENT ON TABLE super_tts.monitored_channels IS 'Discord channels monitored for auto-TTS conversion';
COMMENT ON COLUMN super_tts.monitored_channels.channel_id IS 'Discord channel ID (primary key)';
COMMENT ON COLUMN super_tts.monitored_channels.guild_id IS 'Discord guild/server ID';
COMMENT ON COLUMN super_tts.monitored_channels.channel_name IS 'Channel name at time of monitoring';
COMMENT ON COLUMN super_tts.monitored_channels.added_by IS 'User ID who added this channel';
COMMENT ON COLUMN super_tts.monitored_channels.created_at IS 'When the monitoring was added';


-- TTS User Preferences Table
-- Stores individual user TTS preferences (voice, speed, pitch, language)
CREATE TABLE IF NOT EXISTS super_tts.user_preferences (
    user_id BIGINT PRIMARY KEY,
    voice_name VARCHAR(100) DEFAULT 'default',
    speed FLOAT DEFAULT 1.0 CHECK (speed >= 0.5 AND speed <= 2.0),
    pitch FLOAT DEFAULT 1.0 CHECK (pitch >= 0.8 AND pitch <= 1.2),
    language VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE super_tts.user_preferences IS 'User-specific TTS synthesis preferences';
COMMENT ON COLUMN super_tts.user_preferences.user_id IS 'Discord user ID (primary key)';
COMMENT ON COLUMN super_tts.user_preferences.voice_name IS 'Preferred voice name for TTS';
COMMENT ON COLUMN super_tts.user_preferences.speed IS 'Speech speed multiplier (0.5-2.0)';
COMMENT ON COLUMN super_tts.user_preferences.pitch IS 'Voice pitch multiplier (0.8-1.2)';
COMMENT ON COLUMN super_tts.user_preferences.language IS 'Preferred language code (en, es, fr, de, it, pt, pl, tr, ru, nl, el, hu, zh-cn, ja, ko, ar)';
COMMENT ON COLUMN super_tts.user_preferences.created_at IS 'When preferences were first set';
COMMENT ON COLUMN super_tts.user_preferences.updated_at IS 'When preferences were last updated';
