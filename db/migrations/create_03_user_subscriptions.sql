-- User Subscriptions Table
-- Tracks which users have active subscriptions to voice claiming features
CREATE TABLE IF NOT EXISTS super_tts.user_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    subscription_tier VARCHAR(50) NOT NULL DEFAULT 'voice_subscriber',
    subscribed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    granted_by BIGINT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id
    ON super_tts.user_subscriptions(user_id);

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_expires_at
    ON super_tts.user_subscriptions(expires_at);

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_is_active
    ON super_tts.user_subscriptions(is_active);

COMMENT ON TABLE super_tts.user_subscriptions IS 'User subscriptions for voice claiming feature';
COMMENT ON COLUMN super_tts.user_subscriptions.id IS 'Subscription ID (primary key)';
COMMENT ON COLUMN super_tts.user_subscriptions.user_id IS 'Discord user ID (unique - one subscription per user)';
COMMENT ON COLUMN super_tts.user_subscriptions.subscription_tier IS 'Subscription tier name (e.g., voice_subscriber)';
COMMENT ON COLUMN super_tts.user_subscriptions.subscribed_at IS 'When subscription was activated';
COMMENT ON COLUMN super_tts.user_subscriptions.expires_at IS 'Subscription expiration date (NULL = no expiration)';
COMMENT ON COLUMN super_tts.user_subscriptions.is_active IS 'Whether subscription is currently active';
COMMENT ON COLUMN super_tts.user_subscriptions.granted_by IS 'Discord user ID of owner who granted subscription';
COMMENT ON COLUMN super_tts.user_subscriptions.notes IS 'Optional notes from owner';
