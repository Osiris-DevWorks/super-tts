-- Migration: Create org chart configuration table
-- Stores the configuration for the live organization chart
-- Singleton pattern: only one row (id = 1) manages the entire org chart

CREATE TABLE IF NOT EXISTS org_chart_config (
    id SERIAL PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    message_id BIGINT,
    allowed_role_ids BIGINT[] NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Initialize singleton row with empty configuration
INSERT INTO org_chart_config (id, channel_id, message_id, allowed_role_ids)
VALUES (1, 0, NULL, ARRAY[]::BIGINT[])
ON CONFLICT (id) DO NOTHING;
