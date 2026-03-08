-- Migration: Create bounty submissions table for OCR bounty awards tracking
-- Stores OCR results, validation status, and hostile status checks for bounty screenshots
-- Used by bounty_ocr cog to track processed bounty completions

CREATE TABLE IF NOT EXISTS bounty_submissions (
    id SERIAL PRIMARY KEY,
    discord_user_id BIGINT NOT NULL,
    discord_username VARCHAR(32),
    message_id BIGINT UNIQUE NOT NULL,
    image_url TEXT,
    bounty_name VARCHAR(255),
    status VARCHAR(50), -- 'completed', 'invalid_format', 'ocr_failed', 'not_found', 'not_hostile'
    ocr_raw_text TEXT, -- Full OCR results from top-right quadrant
    validation_errors TEXT, -- If validation failed, why
    target_is_hostile BOOLEAN, -- Whether target citizen is marked hostile (from local DB)
    target_in_hostile_org BOOLEAN, -- Whether target's org is marked hostile (from local DB)
    target_is_predator BOOLEAN, -- Whether target appears as predator in incidents table
    target_citizen_id INTEGER REFERENCES citizens(id) ON DELETE SET NULL, -- Reference to citizens table
    rsi_org_affiliation VARCHAR(255), -- Organization scraped from RSI dossier
    rsi_org_is_known_hostile BOOLEAN, -- Whether RSI org affiliation matches known hostile org
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Index for quick lookup by discord_user_id
CREATE INDEX IF NOT EXISTS idx_bounty_submissions_user_id ON bounty_submissions(discord_user_id);

-- Index for quick lookup by message_id (already unique but good for range queries)
CREATE INDEX IF NOT EXISTS idx_bounty_submissions_message_id ON bounty_submissions(message_id);

-- Index for lookup by bounty_name
CREATE INDEX IF NOT EXISTS idx_bounty_submissions_bounty_name ON bounty_submissions(bounty_name);

-- Index for filtering by status
CREATE INDEX IF NOT EXISTS idx_bounty_submissions_status ON bounty_submissions(status);

-- Index for timestamp range queries
CREATE INDEX IF NOT EXISTS idx_bounty_submissions_created_at ON bounty_submissions(created_at);
