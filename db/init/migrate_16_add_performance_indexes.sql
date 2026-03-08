-- Performance optimization: Add indexes for frequently filtered columns
-- This migration improves query performance for org and incident management

-- Incidents table indexes
CREATE INDEX IF NOT EXISTS idx_incidents_predator_org_id
  ON incidents(predator_org_id)
  WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_incidents_victim_org_id
  ON incidents(victim_org_id)
  WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_incidents_deleted_at
  ON incidents(deleted_at);

-- Organizations table indexes
CREATE INDEX IF NOT EXISTS idx_organizations_disposition
  ON organizations(disposition)
  WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_organizations_deleted_at
  ON organizations(deleted_at);

-- Citizens table indexes (for RSI handle lookups)
CREATE INDEX IF NOT EXISTS idx_citizens_rsi_handle
  ON citizens(rsi_handle);

CREATE INDEX IF NOT EXISTS idx_citizens_rsi_org_id
  ON citizens(rsi_org_id);

-- Combined indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_incidents_predator_org_deleted
  ON incidents(predator_org_id, deleted_at);

CREATE INDEX IF NOT EXISTS idx_organizations_name_deleted
  ON organizations(rsi_org_name, deleted_at);
