-- Track changes to Aspirant Eligible role for weekly reporting
CREATE TABLE IF NOT EXISTS aspirant_eligible_changes (
    id SERIAL PRIMARY KEY,
    discord_user_id BIGINT NOT NULL,
    change_type VARCHAR(10) NOT NULL CHECK (change_type IN ('added', 'removed')),
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_aspirant_eligible_changes_user ON aspirant_eligible_changes(discord_user_id);
CREATE INDEX IF NOT EXISTS idx_aspirant_eligible_changes_date ON aspirant_eligible_changes(changed_at);
