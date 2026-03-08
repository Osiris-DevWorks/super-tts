CREATE TABLE IF NOT EXISTS organizations (
    id SERIAL PRIMARY KEY,                              -- Auto-incrementing primary key
    rsi_org_id TEXT NOT NULL UNIQUE,                    -- RSI organization ID (must be unique)
    rsi_org_name TEXT,                                  -- RSI organization display name
    primary_org BOOLEAN DEFAULT FALSE,                  -- Whether this is the primary organization
    disposition TEXT CHECK (disposition IN ('self', 'ally', 'friendly', 'neutral', 'hostile', 'unknown')) DEFAULT 'unknown',
    num_redacted INTEGER DEFAULT 0,                     -- Number of redacted citizens in the organization
    num_hidden INTEGER DEFAULT 0,                       -- Number of hidden citizens in the organization
    num_visible INTEGER DEFAULT 0,                      -- Number of visible citizens in the organization
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Timestamp when the record was created
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,   -- Timestamp when the record was last updated
    deleted_at TIMESTAMPTZ DEFAULT NULL                 -- Timestamp when the record was soft-deleted
);

-- Index for quick lookup by RSI org ID
CREATE INDEX IF NOT EXISTS idx_organizations_rsi_org_id ON organizations (rsi_org_id);
