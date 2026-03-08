-- Track when members are promoted to Aspirant role
ALTER TABLE citizens
ADD COLUMN IF NOT EXISTS promoted_to_aspirant_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_citizens_promoted_to_aspirant ON citizens(promoted_to_aspirant_at);
