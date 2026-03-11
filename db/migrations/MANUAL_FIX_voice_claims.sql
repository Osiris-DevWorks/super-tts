-- MANUAL FIX: Run this directly against Railway PostgreSQL if migration hasn't applied yet
-- This removes the old constraints and creates partial unique indexes

-- Step 1: Drop the old UNIQUE constraints
ALTER TABLE super_tts.voice_claims DROP CONSTRAINT IF EXISTS voice_claims_user_id_key CASCADE;
ALTER TABLE super_tts.voice_claims DROP CONSTRAINT IF EXISTS voice_claims_voice_id_key CASCADE;

-- Step 2: Create partial unique indexes (only for active claims where released_at IS NULL)
CREATE UNIQUE INDEX IF NOT EXISTS idx_voice_claims_active_user_unique
    ON super_tts.voice_claims(user_id)
    WHERE released_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_voice_claims_active_voice_unique
    ON super_tts.voice_claims(voice_id)
    WHERE released_at IS NULL;

-- Verify the changes worked
SELECT * FROM information_schema.table_constraints
WHERE table_schema = 'super_tts' AND table_name = 'voice_claims';
