-- Migration: Add 'other' item category to banking system
-- Purpose: Add support for miscellaneous items category using /api/v2/items endpoint
-- Date: 2025-12-30

-- Update bank_items table CHECK constraint
ALTER TABLE bank_items
DROP CONSTRAINT bank_items_item_category_check;

ALTER TABLE bank_items
ADD CONSTRAINT bank_items_item_category_check
CHECK (item_category IN ('armor', 'weapons', 'vehicle-items', 'other'));

-- Update bank_item_cache table CHECK constraint
ALTER TABLE bank_item_cache
DROP CONSTRAINT bank_item_cache_category_check;

ALTER TABLE bank_item_cache
ADD CONSTRAINT bank_item_cache_category_check
CHECK (category IN ('armor', 'weapons', 'vehicle-items', 'other'));

-- Verify constraints were updated
SELECT constraint_name, table_name FROM information_schema.table_constraints
WHERE constraint_type = 'CHECK'
  AND table_name IN ('bank_items', 'bank_item_cache')
ORDER BY table_name, constraint_name;
