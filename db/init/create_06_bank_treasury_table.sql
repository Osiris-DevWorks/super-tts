-- Bank Treasury Table
-- Stores the organization's total bank balance
-- Uses singleton pattern with a single row (id = 1)

CREATE TABLE IF NOT EXISTS bank_treasury (
    id SERIAL PRIMARY KEY,
    balance NUMERIC(20, 2) NOT NULL DEFAULT 0.00 CHECK (balance >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ DEFAULT NULL
);

-- Initialize with a single treasury row (singleton)
-- This ensures there's always a row to update
INSERT INTO bank_treasury (balance)
VALUES (0.00)
ON CONFLICT DO NOTHING;

-- Index for soft deletes
CREATE INDEX IF NOT EXISTS idx_bank_treasury_deleted_at ON bank_treasury (deleted_at);
