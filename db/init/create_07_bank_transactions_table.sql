-- Bank Transactions Table
-- Tracks all monetary deposits, withdrawals, and distributions
-- Requires approval from RK Leadership before completion

CREATE TABLE IF NOT EXISTS bank_transactions (
    id SERIAL PRIMARY KEY,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('deposit', 'withdrawal', 'distribution')),
    amount NUMERIC(20, 2) NOT NULL CHECK (amount > 0),
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')) DEFAULT 'pending',
    notes TEXT,

    -- User who submitted the request
    submitted_by_discord_id BIGINT NOT NULL,
    submitted_by_discord_name TEXT NOT NULL,

    -- User who processed the request (admin approval/rejection)
    processed_by_discord_id BIGINT,
    processed_by_discord_name TEXT,
    processed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ DEFAULT NULL,

    FOREIGN KEY (submitted_by_discord_id) REFERENCES citizens(discord_user_id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_bank_transactions_status ON bank_transactions (status);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_submitted_by ON bank_transactions (submitted_by_discord_id);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_type ON bank_transactions (transaction_type);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_created_at ON bank_transactions (created_at);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_deleted_at ON bank_transactions (deleted_at) WHERE deleted_at IS NULL;
