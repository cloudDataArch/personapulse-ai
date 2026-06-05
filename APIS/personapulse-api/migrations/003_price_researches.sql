CREATE TABLE IF NOT EXISTS app.price_researches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_name TEXT NOT NULL,
    positioning TEXT,
    source TEXT NOT NULL,
    ticket_medio NUMERIC(14,2) NOT NULL DEFAULT 0,
    price_competitive NUMERIC(14,2) NOT NULL DEFAULT 0,
    price_recommended NUMERIC(14,2) NOT NULL DEFAULT 0,
    price_premium NUMERIC(14,2) NOT NULL DEFAULT 0,
    range_low NUMERIC(14,2) NOT NULL DEFAULT 0,
    range_high NUMERIC(14,2) NOT NULL DEFAULT 0,
    observed_items INTEGER NOT NULL DEFAULT 0,
    sources JSONB NOT NULL DEFAULT '[]'::jsonb,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_price_researches_product
    ON app.price_researches (product_name);

CREATE INDEX IF NOT EXISTS idx_price_researches_created_at
    ON app.price_researches (created_at DESC);

CREATE OR REPLACE VIEW bi.vw_price_researches AS
SELECT
    id,
    product_name,
    positioning,
    source,
    ticket_medio,
    price_competitive,
    price_recommended,
    price_premium,
    range_low,
    range_high,
    observed_items,
    created_at
FROM app.price_researches;
