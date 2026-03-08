-- Award Type Conversion Migration
-- Converts specific award types to consolidated types while preserving history
-- Only converts active awards (status != 'revoked')
-- Appends conversion note to reason field
--
-- Target award types:
-- - red-dead (target for: kill-shot, kill-assist, roach-killer, solo-kill)
-- - vip-kill (target for: enemy-kill)

BEGIN;

-- Convert kill-shot to red-dead
UPDATE awards_assigned
SET award_type = 'red-dead',
    reason = CASE
      WHEN reason IS NULL THEN '(converted from kill-shot)'
      ELSE reason || ' (converted from kill-shot)'
    END
WHERE award_type = 'kill-shot'
  AND status != 'revoked';

-- Convert kill-assist to red-dead
UPDATE awards_assigned
SET award_type = 'red-dead',
    reason = CASE
      WHEN reason IS NULL THEN '(converted from kill-assist)'
      ELSE reason || ' (converted from kill-assist)'
    END
WHERE award_type = 'kill-assist'
  AND status != 'revoked';

-- Convert roach-killer to red-dead
UPDATE awards_assigned
SET award_type = 'red-dead',
    reason = CASE
      WHEN reason IS NULL THEN '(converted from roach-killer)'
      ELSE reason || ' (converted from roach-killer)'
    END
WHERE award_type = 'roach-killer'
  AND status != 'revoked';

-- Convert solo-kill to red-dead
UPDATE awards_assigned
SET award_type = 'red-dead',
    reason = CASE
      WHEN reason IS NULL THEN '(converted from solo-kill)'
      ELSE reason || ' (converted from solo-kill)'
    END
WHERE award_type = 'solo-kill'
  AND status != 'revoked';

-- Convert enemy-kill to vip-kill
UPDATE awards_assigned
SET award_type = 'vip-kill',
    reason = CASE
      WHEN reason IS NULL THEN '(converted from enemy-kill)'
      ELSE reason || ' (converted from enemy-kill)'
    END
WHERE award_type = 'enemy-kill'
  AND status != 'revoked';

COMMIT;

-- ============ VERIFICATION QUERIES (run after migration) ============
--
-- Check conversions to red-dead
-- SELECT 'kill-shot' as source, COUNT(*) as converted_count
-- FROM awards_assigned
-- WHERE award_type = 'red-dead' AND reason LIKE '%(converted from kill-shot)%';
--
-- SELECT 'kill-assist' as source, COUNT(*) as converted_count
-- FROM awards_assigned
-- WHERE award_type = 'red-dead' AND reason LIKE '%(converted from kill-assist)%';
--
-- SELECT 'roach-killer' as source, COUNT(*) as converted_count
-- FROM awards_assigned
-- WHERE award_type = 'red-dead' AND reason LIKE '%(converted from roach-killer)%';
--
-- SELECT 'solo-kill' as source, COUNT(*) as converted_count
-- FROM awards_assigned
-- WHERE award_type = 'red-dead' AND reason LIKE '%(converted from solo-kill)%';
--
-- Check conversions to vip-kill
-- SELECT 'enemy-kill' as source, COUNT(*) as converted_count
-- FROM awards_assigned
-- WHERE award_type = 'vip-kill' AND reason LIKE '%(converted from enemy-kill)%';
--
-- Summary of all conversions
-- SELECT COUNT(*) as total_converted
-- FROM awards_assigned
-- WHERE reason LIKE '%(converted from%' AND status != 'revoked';
