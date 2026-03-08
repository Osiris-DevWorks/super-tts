-- Create the award_types table
CREATE TABLE IF NOT EXISTS award_types (
    id SERIAL PRIMARY KEY,                                -- Auto-incrementing primary key
    award_type TEXT NOT NULL UNIQUE,                      -- Name of the award type (must be unique)
    token TEXT NOT NULL,                                  -- Token or emoji associated with the award
    max_count INTEGER DEFAULT NULL CHECK (max_count IS NULL OR max_count >= 0), -- Maximum awards (NULL = unlimited)
    multiplier INTEGER NOT NULL DEFAULT 1 CHECK (multiplier >= 1), -- Number of tokens per award
    description TEXT DEFAULT NULL,                        -- Description of the award
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Timestamp when the award type was created
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,      -- Timestamp when the award type was last updated
    deleted_at TIMESTAMPTZ DEFAULT NULL                   -- Timestamp when the award type was soft-deleted
);

-- Create an index on the award_type column for faster lookups
CREATE INDEX IF NOT EXISTS idx_award_types_name ON award_types (award_type);

-- Create an index on the deleted_at column for filtering active/inactive awards
CREATE INDEX IF NOT EXISTS idx_award_types_deleted_at ON award_types (deleted_at);
