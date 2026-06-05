CREATE TABLE IF NOT EXISTS app_store (
    key TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app_audit (
    id UUID PRIMARY KEY,
    action TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_app_audit_created_at
    ON app_audit (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_app_audit_action
    ON app_audit (action);
