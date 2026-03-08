-- Migration 20: Populate supplier fields from submitted_by for existing deposits
-- For deposits that don't have a supplier set, use the submitter as the supplier
-- Only populates if supplier_discord_id is NULL and submitted_by exists
-- This ensures backward compatibility with existing items

UPDATE bank_items
SET
    supplier_discord_id = submitted_by_discord_id,
    supplier_discord_name = submitted_by_discord_name
WHERE
    transaction_type = 'deposit'
    AND status = 'approved'
    AND supplier_discord_id IS NULL
    AND submitted_by_discord_id IS NOT NULL
    AND deleted_at IS NULL;
