-- Create hangar_reference table for storing executive hangar cycle reference points
CREATE TABLE IF NOT EXISTS hangar_reference (
    id SERIAL PRIMARY KEY,
    reference_timestamp TIMESTAMPTZ NOT NULL,
    cycle_number INTEGER NOT NULL,
    is_online BOOLEAN NOT NULL,
    status_message_id BIGINT,
    status_channel_id BIGINT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
