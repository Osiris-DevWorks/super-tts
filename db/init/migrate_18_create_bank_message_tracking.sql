-- Bank Message Tracking Table
-- Tracks Discord message IDs for pending bank requests (deposits/withdrawals)
-- Allows bot to re-attach views to messages after restarts
-- Auto-cleanup: Messages older than 7 days are removed

CREATE TABLE IF NOT EXISTS bank_pending_requests (
    id SERIAL PRIMARY KEY,
    message_id BIGINT NOT NULL UNIQUE,
    channel_id BIGINT NOT NULL,
    transaction_id INTEGER NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('transaction', 'item')),
    -- transaction_type: 'transaction' for monetary (aUEC/USD), 'item' for items
    request_type TEXT NOT NULL CHECK (request_type IN ('deposit', 'withdrawal')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'expired')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(transaction_id, transaction_type)
);

-- Index for quick cleanup of old messages
CREATE INDEX IF NOT EXISTS idx_bank_pending_created_at ON bank_pending_requests(created_at);

-- Index for looking up by message_id
CREATE INDEX IF NOT EXISTS idx_bank_pending_message_id ON bank_pending_requests(message_id);

-- Index for cleanup queries (status + created_at)
CREATE INDEX IF NOT EXISTS idx_bank_pending_status_created ON bank_pending_requests(status, created_at);
