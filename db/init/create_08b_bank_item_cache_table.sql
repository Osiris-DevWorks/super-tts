-- Bank Item Cache Table
-- Caches items from Star Citizen Wiki API for fast autocomplete lookups
-- Cache invalidates when game version changes (detected from API response)

CREATE TABLE IF NOT EXISTS bank_item_cache (
    id SERIAL PRIMARY KEY,

    -- Category of item
    category TEXT NOT NULL CHECK (category IN ('armor', 'weapons', 'vehicle-items', 'other')),

    -- Item details from API
    item_uuid TEXT NOT NULL,
    item_name TEXT NOT NULL,
    item_type TEXT NOT NULL,
    item_sub_type TEXT,

    -- Manufacturer information
    manufacturer_name TEXT,
    manufacturer_code TEXT,

    -- Component-specific metadata
    grade TEXT,
    class TEXT,

    -- Cache versioning
    game_version TEXT NOT NULL,
    cached_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Unique constraint to prevent duplicate cache entries
CREATE UNIQUE INDEX IF NOT EXISTS idx_bank_item_cache_unique ON bank_item_cache (category, item_uuid);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_bank_item_cache_category ON bank_item_cache (category);
CREATE INDEX IF NOT EXISTS idx_bank_item_cache_name ON bank_item_cache (item_name);
CREATE INDEX IF NOT EXISTS idx_bank_item_cache_version ON bank_item_cache (game_version);
CREATE INDEX IF NOT EXISTS idx_bank_item_cache_cached_at ON bank_item_cache (cached_at);
