-- Migration: Update bank_distributions unique constraint to include status
-- This allows multiple distribution records per person per date (pending, approved, cancelled)
-- without violating the constraint, preserving the audit trail

DO $$
BEGIN
  -- Drop the old constraint if it exists
  IF EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_name = 'bank_distributions'
    AND constraint_name = 'bank_distributions_distribution_date_recipient_discord_id_key'
  ) THEN
    ALTER TABLE bank_distributions
    DROP CONSTRAINT bank_distributions_distribution_date_recipient_discord_id_key;
  END IF;

  -- Add the new constraint that includes status
  -- This prevents duplicate (distribution_date, recipient_discord_id, status) combinations
  -- but allows the same person to have pending, approved, and cancelled records
  ALTER TABLE bank_distributions
  ADD CONSTRAINT unique_distribution_per_person_per_status
  UNIQUE (distribution_date, recipient_discord_id, status);

  -- Create index for efficient lookups by status
  CREATE INDEX IF NOT EXISTS idx_bank_distributions_date_status
  ON bank_distributions (distribution_date, status);

EXCEPTION WHEN OTHERS THEN
  -- If constraint already exists, do nothing
  NULL;
END
$$;
