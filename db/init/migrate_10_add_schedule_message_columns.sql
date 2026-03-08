-- Add schedule message tracking columns to hangar_reference table
ALTER TABLE hangar_reference
ADD COLUMN IF NOT EXISTS schedule_message_id BIGINT,
ADD COLUMN IF NOT EXISTS schedule_channel_id BIGINT,
ADD COLUMN IF NOT EXISTS schedule_days INTEGER DEFAULT 7;
