-- Fix voice claims constraint to allow re-claiming after release
-- The original UNIQUE constraints prevented users from claiming a voice again after releasing it
-- because the released record still existed in the database.
--
-- Solution: Use partial unique indexes that only apply to ACTIVE claims (released_at IS NULL)
-- This allows:
-- - Only ONE active claim per user_id
-- - Only ONE active claim per voice_id
-- - Users can claim again after releasing (released records don't count)

-- Remove the old UNIQUE constraints (if they exist)
-- PostgreSQL creates implicit constraints named {table}_{columns}_key for UNIQUE clauses
DO $$
BEGIN
    -- Drop user_id constraint if exists
    BEGIN
        ALTER TABLE super_tts.voice_claims DROP CONSTRAINT voice_claims_user_id_key;
    EXCEPTION WHEN OTHERS THEN
        NULL;  -- Constraint may not exist
    END;

    -- Drop voice_id constraint if exists
    BEGIN
        ALTER TABLE super_tts.voice_claims DROP CONSTRAINT voice_claims_voice_id_key;
    EXCEPTION WHEN OTHERS THEN
        NULL;  -- Constraint may not exist
    END;
END $$;

-- Add partial unique indexes (only for active claims where released_at IS NULL)
CREATE UNIQUE INDEX IF NOT EXISTS idx_voice_claims_active_user_unique
    ON super_tts.voice_claims(user_id)
    WHERE released_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_voice_claims_active_voice_unique
    ON super_tts.voice_claims(voice_id)
    WHERE released_at IS NULL;

-- Update comments
COMMENT ON COLUMN super_tts.voice_claims.user_id IS 'Discord user ID who claimed the voice (unique among ACTIVE claims only)';
COMMENT ON COLUMN super_tts.voice_claims.voice_id IS 'Voice identifier that is claimed (unique among ACTIVE claims only)';
