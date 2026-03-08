-- Add foreign key columns and timestamps for incident tracking
-- This migration adds:
-- 1. victim_org_id and predator_org_id columns to replace string-based org references
-- 2. incident_date for when the griefing actually occurred
-- 3. approved_at and approved_by_user_id for approval tracking

ALTER TABLE incidents
ADD COLUMN IF NOT EXISTS victim_org_id TEXT,
ADD COLUMN IF NOT EXISTS predator_org_id TEXT,
ADD COLUMN IF NOT EXISTS incident_date TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS approved_by_user_id BIGINT;
