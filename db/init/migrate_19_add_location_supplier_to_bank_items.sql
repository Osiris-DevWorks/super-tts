-- Migration 19: Add location and supplier tracking to bank_items
-- Enables tracking WHERE items are stored and WHO is supplying them
-- Applies to all item types: armor, weapons, vehicle-items, other

ALTER TABLE bank_items
ADD COLUMN IF NOT EXISTS location TEXT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS supplier_discord_id BIGINT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS supplier_discord_name VARCHAR DEFAULT NULL;

-- Index for querying items by location + supplier (for withdrawal UI)
-- Used to build LocationSupplierSelectView options
CREATE INDEX IF NOT EXISTS idx_bank_items_location_supplier
  ON bank_items(location, supplier_discord_id, transaction_type, status)
  WHERE deleted_at IS NULL AND status = 'approved';

-- Index for supplier notifications (quick lookup when approving)
-- Used to notify suppliers of withdrawal approvals
CREATE INDEX IF NOT EXISTS idx_bank_items_supplier_status
  ON bank_items(supplier_discord_id, transaction_type, status)
  WHERE deleted_at IS NULL;
