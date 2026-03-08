-- Migration: Add status column to bank_distributions table
-- For existing distributions that were already processed, default to 'approved'
-- For new distributions created going forward, will be set to 'pending'

-- Add the status column with default 'approved' for existing records
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'bank_distributions' AND column_name = 'status') THEN
    ALTER TABLE bank_distributions
    ADD COLUMN status TEXT NOT NULL DEFAULT 'approved' CHECK (status IN ('pending', 'approved', 'cancelled'));

    -- Create index on status column
    CREATE INDEX idx_bank_distributions_status ON bank_distributions (status);
  END IF;
END
$$;
