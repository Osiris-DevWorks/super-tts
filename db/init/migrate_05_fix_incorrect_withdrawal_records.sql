-- Migration: Fix incorrect withdrawal records
-- Soft-delete (mark as deleted) bank_items records that were incorrectly stored as deposits
-- when they should have been withdrawals
--
-- This addresses the bug where withdrawal requests were being routed to ItemDepositModal
-- instead of ItemWithdrawModal, causing them to be inserted with transaction_type='deposit'
-- instead of 'withdrawal'
--
-- These records are safely soft-deleted so they won't appear in pending requests,
-- and the user can resubmit them with the correct transaction type.

UPDATE bank_items
SET deleted_at = CURRENT_TIMESTAMP
WHERE status = 'pending'
  AND deleted_at IS NULL
  AND transaction_type = 'deposit'
  AND (submitted_by_discord_name ILIKE '%osiris%' OR item_name = 'AbsoluteZero');
