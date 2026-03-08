-- Create the incidents table
CREATE TABLE IF NOT EXISTS incidents (
    id SERIAL PRIMARY KEY,                                  -- Auto-incrementing primary key
    victim_rsi_handle TEXT NOT NULL,                        -- RSI handle of the victim
    victim_org TEXT,                                        -- Organization of the victim
    victim_ship TEXT,                                       -- Ship used by the victim
    predator_rsi_handle TEXT NOT NULL,                      -- RSI handle of the predator
    predator_org TEXT,                                      -- Organization of the predator
    predator_ship TEXT,                                     -- Ship used by the predator
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Timestamp when the incident was created
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,        -- Timestamp when the incident was last updated
    deleted_at TIMESTAMPTZ DEFAULT NULL                   -- Timestamp when the incident was soft-deleted

);
