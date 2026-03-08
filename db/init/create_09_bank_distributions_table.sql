-- Bank Distributions Table
-- Tracks monthly distributions of org funds to eligible members
-- Eligibility based on event participation (awards)

CREATE TABLE IF NOT EXISTS bank_distributions (
    id SERIAL PRIMARY KEY,

    -- Distribution date (1st of the month)
    distribution_date DATE NOT NULL,

    -- Recipient information
    recipient_discord_id BIGINT NOT NULL,
    recipient_discord_name TEXT NOT NULL,
    recipient_role TEXT NOT NULL,

    -- Distribution amounts
    role_percentage NUMERIC(5, 2) NOT NULL CHECK (role_percentage > 0 AND role_percentage <= 100),
    base_amount NUMERIC(20, 2) NOT NULL CHECK (base_amount > 0),
    transaction_fee NUMERIC(20, 2) NOT NULL CHECK (transaction_fee >= 0),
    final_amount NUMERIC(20, 2) NOT NULL CHECK (final_amount >= 0),

    -- Award eligibility tracking
    event_participant_count INTEGER DEFAULT 0,
    party_up_count INTEGER DEFAULT 0,
    eligibility_reason TEXT,

    -- Distribution status
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'cancelled')),

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ DEFAULT NULL,

    FOREIGN KEY (recipient_discord_id) REFERENCES citizens(discord_user_id) ON DELETE CASCADE,
    UNIQUE (distribution_date, recipient_discord_id, status)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_bank_distributions_date ON bank_distributions (distribution_date);
CREATE INDEX IF NOT EXISTS idx_bank_distributions_recipient ON bank_distributions (recipient_discord_id);
CREATE INDEX IF NOT EXISTS idx_bank_distributions_status ON bank_distributions (status);
CREATE INDEX IF NOT EXISTS idx_bank_distributions_date_status ON bank_distributions (distribution_date, status);
CREATE INDEX IF NOT EXISTS idx_bank_distributions_deleted_at ON bank_distributions (deleted_at) WHERE deleted_at IS NULL;
