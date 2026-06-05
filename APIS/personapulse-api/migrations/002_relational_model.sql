CREATE SCHEMA IF NOT EXISTS app;
CREATE SCHEMA IF NOT EXISTS integrations;
CREATE SCHEMA IF NOT EXISTS bi;
CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE IF NOT EXISTS app.customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual',
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    city TEXT,
    state TEXT,
    country TEXT DEFAULT 'BR',
    consent_marketing BOOLEAN NOT NULL DEFAULT FALSE,
    consent_source TEXT,
    behavioral_segment TEXT,
    intent_score NUMERIC(5,2) DEFAULT 0,
    status TEXT,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source, external_id)
);

CREATE TABLE IF NOT EXISTS app.orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_order_id TEXT,
    customer_id UUID REFERENCES app.customers(id) ON DELETE SET NULL,
    external_customer_id TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    product_name TEXT NOT NULL,
    category TEXT,
    store_name TEXT,
    channel TEXT,
    value NUMERIC(14,2) NOT NULL DEFAULT 0,
    purchased_at TIMESTAMPTZ,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_event_id TEXT,
    customer_id UUID REFERENCES app.customers(id) ON DELETE SET NULL,
    external_customer_id TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    event_type TEXT NOT NULL,
    product_name TEXT,
    channel TEXT,
    occurred_at TIMESTAMPTZ,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_campaign_id TEXT,
    source TEXT NOT NULL DEFAULT 'personapulse',
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    channel TEXT,
    segment TEXT,
    product_name TEXT,
    tone TEXT,
    creative_text TEXT,
    start_date DATE,
    end_date DATE,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source, external_campaign_id)
);

CREATE TABLE IF NOT EXISTS app.campaign_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES app.campaigns(id) ON DELETE CASCADE,
    external_campaign_id TEXT,
    source TEXT NOT NULL DEFAULT 'personapulse',
    metric_date DATE NOT NULL DEFAULT CURRENT_DATE,
    impressions INTEGER NOT NULL DEFAULT 0,
    clicks INTEGER NOT NULL DEFAULT 0,
    conversions INTEGER NOT NULL DEFAULT 0,
    leads INTEGER NOT NULL DEFAULT 0,
    spend NUMERIC(14,2) NOT NULL DEFAULT 0,
    revenue NUMERIC(14,2) NOT NULL DEFAULT 0,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source, external_campaign_id, metric_date)
);

CREATE TABLE IF NOT EXISTS integrations.data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_key TEXT NOT NULL UNIQUE,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned',
    last_sync_at TIMESTAMPTZ,
    config_public JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS integrations.connector_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_key TEXT NOT NULL UNIQUE REFERENCES integrations.data_sources(source_key) ON DELETE CASCADE,
    client_id TEXT,
    account_id TEXT,
    scopes TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    secret_ref TEXT,
    token_ref TEXT,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'open',
    related_customer_id UUID REFERENCES app.customers(id) ON DELETE SET NULL,
    related_campaign_id UUID REFERENCES app.campaigns(id) ON DELETE SET NULL,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS bi.powerbi_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_key TEXT NOT NULL DEFAULT 'default',
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    customers JSONB NOT NULL DEFAULT '[]'::jsonb,
    campaigns JSONB NOT NULL DEFAULT '[]'::jsonb,
    sources JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customers_email ON app.customers (email);
CREATE INDEX IF NOT EXISTS idx_customers_source ON app.customers (source);
CREATE INDEX IF NOT EXISTS idx_customers_status ON app.customers (status);
CREATE INDEX IF NOT EXISTS idx_customers_segment ON app.customers (behavioral_segment);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON app.orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_purchased_at ON app.orders (purchased_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_customer_id ON app.events (customer_id);
CREATE INDEX IF NOT EXISTS idx_events_type_date ON app.events (event_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON app.campaigns (status);
CREATE INDEX IF NOT EXISTS idx_campaign_metrics_campaign_id ON app.campaign_metrics (campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_metrics_date ON app.campaign_metrics (metric_date DESC);
CREATE INDEX IF NOT EXISTS idx_powerbi_snapshots_key_date ON bi.powerbi_snapshots (snapshot_key, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action_date ON audit.audit_logs (action, created_at DESC);

CREATE OR REPLACE VIEW bi.vw_executive_summary AS
SELECT
    COUNT(DISTINCT c.id) AS clientes_analisados,
    COUNT(DISTINCT ca.id) AS campanhas,
    COALESCE(SUM(cm.conversions), 0) AS conversoes,
    COALESCE(SUM(cm.revenue), 0)::NUMERIC(14,2) AS receita_atribuida,
    COALESCE(SUM(cm.spend), 0)::NUMERIC(14,2) AS gasto_real,
    CASE
        WHEN COALESCE(SUM(cm.spend), 0) = 0 THEN 0
        ELSE ROUND(((SUM(cm.revenue) - SUM(cm.spend)) / NULLIF(SUM(cm.spend), 0)) * 100, 2)
    END AS roi_real_percentual,
    CASE
        WHEN COUNT(c.id) = 0 THEN 0
        ELSE ROUND((COUNT(c.id) FILTER (WHERE c.consent_marketing) * 100.0) / COUNT(c.id), 2)
    END AS conformidade_lgpd_percentual
FROM app.customers c
FULL OUTER JOIN app.campaigns ca ON TRUE
LEFT JOIN app.campaign_metrics cm ON cm.campaign_id = ca.id;

CREATE OR REPLACE VIEW bi.vw_campaign_performance AS
SELECT
    ca.id AS campaign_id,
    ca.name AS campanha,
    ca.source AS fonte,
    ca.status,
    ca.channel AS canal,
    ca.segment AS segmento,
    COALESCE(SUM(cm.impressions), 0) AS impressoes,
    COALESCE(SUM(cm.clicks), 0) AS cliques,
    COALESCE(SUM(cm.conversions), 0) AS conversoes,
    COALESCE(SUM(cm.spend), 0)::NUMERIC(14,2) AS gasto_real,
    COALESCE(SUM(cm.revenue), 0)::NUMERIC(14,2) AS receita_atribuida,
    CASE
        WHEN COALESCE(SUM(cm.spend), 0) = 0 THEN 0
        ELSE ROUND(((SUM(cm.revenue) - SUM(cm.spend)) / NULLIF(SUM(cm.spend), 0)) * 100, 2)
    END AS roi_real_percentual
FROM app.campaigns ca
LEFT JOIN app.campaign_metrics cm ON cm.campaign_id = ca.id
GROUP BY ca.id, ca.name, ca.source, ca.status, ca.channel, ca.segment;

CREATE OR REPLACE VIEW bi.vw_customer_profile AS
SELECT
    c.id AS customer_id,
    c.external_id,
    c.source,
    c.name,
    c.email,
    c.phone,
    c.city,
    c.behavioral_segment,
    c.intent_score,
    c.status,
    c.consent_marketing,
    COUNT(o.id) AS total_pedidos,
    COALESCE(SUM(o.value), 0)::NUMERIC(14,2) AS valor_total_compras,
    MAX(o.purchased_at) AS ultima_compra
FROM app.customers c
LEFT JOIN app.orders o ON o.customer_id = c.id
GROUP BY c.id, c.external_id, c.source, c.name, c.email, c.phone, c.city,
         c.behavioral_segment, c.intent_score, c.status, c.consent_marketing;

INSERT INTO integrations.data_sources (source_key, source_name, source_type, status)
VALUES
    ('csv', 'CSV', 'file', 'active'),
    ('crm', 'CRM', 'crm', 'active'),
    ('meta_ads', 'Meta Ads', 'ads', 'planned'),
    ('google_ads', 'Google Ads', 'ads', 'planned'),
    ('powerbi', 'Power BI', 'bi', 'active')
ON CONFLICT (source_key) DO NOTHING;
