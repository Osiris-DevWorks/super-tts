-- Migration: Add currency_type column to bank tables
-- Allows tracking of both aUEC (in-game) and USD (real money) transactions

-- Add currency_type column to bank_treasury (if it doesn't exist)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'bank_treasury' AND column_name = 'currency_type'
  ) THEN
    -- Add the column with default value
    ALTER TABLE bank_treasury
    ADD COLUMN currency_type TEXT NOT NULL DEFAULT 'aUEC'
    CHECK (currency_type IN ('aUEC', 'USD'));

    -- Consolidate multiple aUEC rows into one (keep highest balance)
    -- Delete duplicate aUEC rows, keeping only the one with the highest balance
    DELETE FROM bank_treasury
    WHERE id NOT IN (
      SELECT id FROM bank_treasury
      WHERE currency_type = 'aUEC'
      ORDER BY balance DESC, id ASC
      LIMIT 1
    ) AND currency_type = 'aUEC';

    -- Create unique constraint so there's only one row per currency type
    ALTER TABLE bank_treasury
    ADD CONSTRAINT unique_currency_type UNIQUE (currency_type);
  END IF;
END
$$;

-- Add currency_type column to bank_transactions (if it doesn't exist)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'bank_transactions' AND column_name = 'currency_type'
  ) THEN
    ALTER TABLE bank_transactions
    ADD COLUMN currency_type TEXT NOT NULL DEFAULT 'aUEC'
    CHECK (currency_type IN ('aUEC', 'USD'));
  END IF;
END
$$;

-- Create index for efficient querying by currency type
CREATE INDEX IF NOT EXISTS idx_bank_transactions_currency_type
ON bank_transactions (currency_type);

-- Create index for querying by currency and status
CREATE INDEX IF NOT EXISTS idx_bank_transactions_currency_status
ON bank_transactions (currency_type, status);

-- Initialize a USD treasury row (singleton)
-- The aUEC row should already exist from the create script
INSERT INTO bank_treasury (balance, currency_type)
VALUES (0.00, 'USD')
ON CONFLICT (currency_type) DO NOTHING;
