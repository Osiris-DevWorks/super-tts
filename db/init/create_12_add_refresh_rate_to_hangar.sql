-- Add refresh_rate_seconds column to hangar_reference table
ALTER TABLE hangar_reference
ADD COLUMN IF NOT EXISTS refresh_rate_seconds INTEGER DEFAULT 60;
