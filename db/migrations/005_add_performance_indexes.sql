-- Performance indexes for frequently queried columns
-- Migration: 005_add_performance_indexes.sql

-- Citizens table indexes
CREATE INDEX IF NOT EXISTS idx_citizens_rsi_handle ON citizens(rsi_handle);
CREATE INDEX IF NOT EXISTS idx_citizens_discord_user_id ON citizens(discord_user_id);
CREATE INDEX IF NOT EXISTS idx_citizens_rsi_org_id ON citizens(rsi_org_id);
CREATE INDEX IF NOT EXISTS idx_citizens_deleted_at ON citizens(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_citizens_disposition ON citizens(disposition);

-- Organizations table indexes
CREATE INDEX IF NOT EXISTS idx_organizations_rsi_org_id ON organizations(rsi_org_id);
CREATE INDEX IF NOT EXISTS idx_organizations_deleted_at ON organizations(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_organizations_disposition ON organizations(disposition);
CREATE INDEX IF NOT EXISTS idx_organizations_rsi_org_name ON organizations(rsi_org_name);

-- Awards_assigned table indexes
CREATE INDEX IF NOT EXISTS idx_awards_assigned_discord_user_id ON awards_assigned(discord_user_id);
CREATE INDEX IF NOT EXISTS idx_awards_assigned_award_type ON awards_assigned(award_type);
CREATE INDEX IF NOT EXISTS idx_awards_assigned_status ON awards_assigned(status);
CREATE INDEX IF NOT EXISTS idx_awards_assigned_deleted_at ON awards_assigned(deleted_at) WHERE deleted_at IS NULL;

-- Award_types table indexes
CREATE INDEX IF NOT EXISTS idx_award_types_award_type ON award_types(award_type);
CREATE INDEX IF NOT EXISTS idx_award_types_deleted_at ON award_types(deleted_at) WHERE deleted_at IS NULL;

-- Incidents table indexes
CREATE INDEX IF NOT EXISTS idx_incidents_predator_rsi_handle ON incidents(predator_rsi_handle);
CREATE INDEX IF NOT EXISTS idx_incidents_victim_rsi_handle ON incidents(victim_rsi_handle);
CREATE INDEX IF NOT EXISTS idx_incidents_predator_org ON incidents(predator_org);
CREATE INDEX IF NOT EXISTS idx_incidents_victim_org ON incidents(victim_org);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_citizens_org_visibility ON citizens(rsi_org_id, visibility) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_awards_user_type_status ON awards_assigned(discord_user_id, award_type, status) WHERE deleted_at IS NULL;
