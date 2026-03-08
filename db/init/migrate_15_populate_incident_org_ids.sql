-- Populate org IDs from existing org name strings
-- This backfills the new victim_org_id and predator_org_id columns
-- by joining with the organizations table based on organization names

-- Populate victim_org_id by joining with organizations table
UPDATE incidents i
SET victim_org_id = o.rsi_org_id
FROM organizations o
WHERE i.victim_org = o.rsi_org_name
AND i.victim_org_id IS NULL
AND o.deleted_at IS NULL;

-- Populate predator_org_id by joining with organizations table
UPDATE incidents i
SET predator_org_id = o.rsi_org_id
FROM organizations o
WHERE i.predator_org = o.rsi_org_name
AND i.predator_org_id IS NULL
AND o.deleted_at IS NULL;

-- Set incident_date to created_at for existing incidents (they reported it when it happened)
UPDATE incidents
SET incident_date = created_at
WHERE incident_date IS NULL;
