-- Voice Claims Table
-- Tracks which user has claimed which voice. Claims are only valid if user has active subscription.
CREATE TABLE IF NOT EXISTS super_tts.voice_claims (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    voice_id VARCHAR(50) NOT NULL UNIQUE,
    subscription_id INTEGER NOT NULL,
    voice_description TEXT,
    claimed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    released_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_voice_claims_subscription
        FOREIGN KEY (subscription_id) REFERENCES super_tts.user_subscriptions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_voice_claims_user_id
    ON super_tts.voice_claims(user_id);

CREATE INDEX IF NOT EXISTS idx_voice_claims_voice_id
    ON super_tts.voice_claims(voice_id);

CREATE INDEX IF NOT EXISTS idx_voice_claims_subscription_id
    ON super_tts.voice_claims(subscription_id);

CREATE INDEX IF NOT EXISTS idx_voice_claims_released_at
    ON super_tts.voice_claims(released_at);

COMMENT ON TABLE super_tts.voice_claims IS 'Voice claims linked to active user subscriptions';
COMMENT ON COLUMN super_tts.voice_claims.id IS 'Claim ID (primary key)';
COMMENT ON COLUMN super_tts.voice_claims.user_id IS 'Discord user ID who claimed the voice (unique)';
COMMENT ON COLUMN super_tts.voice_claims.voice_id IS 'Voice identifier that is claimed (unique)';
COMMENT ON COLUMN super_tts.voice_claims.subscription_id IS 'Foreign key to active user_subscriptions.id';
COMMENT ON COLUMN super_tts.voice_claims.voice_description IS 'Optional description/notes about the claimed voice';
COMMENT ON COLUMN super_tts.voice_claims.claimed_at IS 'When the voice was claimed';
COMMENT ON COLUMN super_tts.voice_claims.released_at IS 'When the voice was released (NULL if still claimed)';
