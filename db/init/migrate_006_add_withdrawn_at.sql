-- Track when deposits are marked as withdrawn
-- A deposit with withdrawn_at IS NULL is still available for future withdrawals

ALTER TABLE bank_items
ADD COLUMN IF NOT EXISTS withdrawn_at TIMESTAMP;

-- Create index for efficient queries on withdrawn deposits
CREATE INDEX IF NOT EXISTS idx_bank_items_withdrawn_at
    ON bank_items(withdrawn_at, transaction_type, item_uuid);
