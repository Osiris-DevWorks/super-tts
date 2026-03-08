-- Create hangar_schedule_messages table for tracking live schedule embeds
CREATE TABLE IF NOT EXISTS hangar_schedule_messages (
    id SERIAL PRIMARY KEY,
    message_id BIGINT NOT NULL UNIQUE,
    channel_id BIGINT NOT NULL,
    days_projected INTEGER NOT NULL DEFAULT 7,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
