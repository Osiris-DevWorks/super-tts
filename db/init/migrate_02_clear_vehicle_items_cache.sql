-- Migration: Add size column to bank_item_cache and clear vehicle-items cache
-- The size field is needed for all categories but especially vehicle-items
-- After adding the column, clear vehicle-items cache to force rebuild with size metadata

-- Add size column if it doesn't exist, and clear vehicle-items cache only on first run
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'bank_item_cache' AND column_name = 'size') THEN
    ALTER TABLE bank_item_cache
    ADD COLUMN size INTEGER;

    CREATE INDEX idx_bank_item_cache_size ON bank_item_cache (size) WHERE size IS NOT NULL;

    -- Only clear vehicle-items cache on first migration run (when we're adding the column)
    DELETE FROM bank_item_cache WHERE category = 'vehicle-items';
  END IF;
END
$$;
