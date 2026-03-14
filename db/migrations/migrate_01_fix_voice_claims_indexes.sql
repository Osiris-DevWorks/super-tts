-- Fix voice_claims table to support soft deletes with partial unique indexes
-- Remove old unique constraints that don't account for released_at
ALTER TABLE super_tts.voice_claims DROP CONSTRAINT IF EXISTS voice_claims_user_id_key;
ALTER TABLE super_tts.voice_claims DROP CONSTRAINT IF EXISTS voice_claims_voice_id_key;

-- Add partial unique indexes that only apply to active (not released) claims
CREATE UNIQUE INDEX IF NOT EXISTS idx_voice_claims_user_id_active
    ON super_tts.voice_claims(user_id)
    WHERE released_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_voice_claims_voice_id_active
    ON super_tts.voice_claims(voice_id)
    WHERE released_at IS NULL;

-- Verify the indexes exist
COMMENT ON INDEX super_tts.idx_voice_claims_user_id_active IS 'Ensures only one active claim per user';
COMMENT ON INDEX super_tts.idx_voice_claims_voice_id_active IS 'Ensures only one user can have each voice (when not released)';
