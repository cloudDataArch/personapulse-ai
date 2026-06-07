-- Banco: PersonaPulse Banco
-- Arquivo: DDL consolidado para PostgreSQL
-- Observacao: nao contem credenciais, senhas ou URLs privadas.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ===== 001_app_store_postgresql.sql =====
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

-- ===== 002_relational_model.sql =====
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

-- ===== 003_price_researches.sql =====
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

-- ===== 004_dba_portuguese_views.sql =====
CREATE SCHEMA IF NOT EXISTS dba;

DROP VIEW IF EXISTS dba.resumo_banco;
DROP VIEW IF EXISTS dba.contatos_clientes;
DROP VIEW IF EXISTS dba.metricas_campanhas;
DROP VIEW IF EXISTS dba.recomendacoes;
DROP VIEW IF EXISTS dba.pesquisas_precos;
DROP VIEW IF EXISTS dba.pedidos;
DROP VIEW IF EXISTS dba.eventos;
DROP VIEW IF EXISTS dba.campanhas;
DROP VIEW IF EXISTS dba.clientes CASCADE;

CREATE OR REPLACE VIEW dba.clientes AS
SELECT
    (ROW_NUMBER() OVER (ORDER BY c.created_at, c.id) - 1)::BIGINT AS id_cliente,
    c.external_id AS id_origem_cliente,
    c.source AS origem_dados,
    c.name AS nome,
    c.email,
    c.phone AS telefone,
    c.city AS cidade,
    c.state AS estado,
    c.country AS pais,
    c.consent_marketing AS consentimento_marketing,
    c.consent_source AS origem_consentimento,
    c.behavioral_segment AS segmento_comportamental,
    c.intent_score AS score_intencao,
    c.status,
    c.created_at AS criado_em,
    c.updated_at AS atualizado_em
FROM app.customers c;

CREATE OR REPLACE VIEW dba.pedidos AS
SELECT
    (ROW_NUMBER() OVER (ORDER BY o.created_at, o.id) - 1)::BIGINT AS id_pedido,
    dc.id_cliente,
    o.external_order_id AS id_origem_pedido,
    o.external_customer_id AS id_origem_cliente,
    o.source AS origem_dados,
    o.product_name AS produto,
    o.category AS categoria,
    o.store_name AS loja,
    o.channel AS canal,
    o.value AS valor,
    o.purchased_at AS comprado_em,
    o.created_at AS criado_em
FROM app.orders o
LEFT JOIN dba.clientes dc ON dc.id_origem_cliente = o.external_customer_id
    AND dc.origem_dados = o.source;

CREATE OR REPLACE VIEW dba.eventos AS
SELECT
    (ROW_NUMBER() OVER (ORDER BY e.created_at, e.id) - 1)::BIGINT AS id_evento,
    dc.id_cliente,
    e.external_event_id AS id_origem_evento,
    e.external_customer_id AS id_origem_cliente,
    e.source AS origem_dados,
    CASE e.event_type
        WHEN 'abandoned_cart' THEN 'carrinho_abandonado'
        WHEN 'product_view' THEN 'visualizacao_produto'
        WHEN 'lead' THEN 'lead'
        WHEN 'purchase' THEN 'compra'
        ELSE e.event_type
    END AS tipo_evento,
    e.product_name AS produto,
    e.channel AS canal,
    e.occurred_at AS ocorrido_em,
    e.created_at AS criado_em
FROM app.events e
LEFT JOIN dba.clientes dc ON dc.id_origem_cliente = e.external_customer_id
    AND dc.origem_dados = e.source;

CREATE OR REPLACE VIEW dba.campanhas AS
SELECT
    (ROW_NUMBER() OVER (ORDER BY c.created_at, c.id) - 1)::BIGINT AS id_campanha,
    c.external_campaign_id AS id_origem_campanha,
    c.source AS origem_dados,
    c.name AS nome,
    c.status,
    c.channel AS canal,
    c.segment AS segmento,
    c.product_name AS produto,
    c.tone AS tom,
    c.creative_text AS texto_criativo,
    c.start_date AS data_inicio,
    c.end_date AS data_fim,
    c.created_at AS criado_em,
    c.updated_at AS atualizado_em
FROM app.campaigns c;

CREATE OR REPLACE VIEW dba.metricas_campanhas AS
SELECT
    (ROW_NUMBER() OVER (ORDER BY m.metric_date, m.created_at, m.id) - 1)::BIGINT AS id_metrica,
    dc.id_campanha,
    m.external_campaign_id AS id_origem_campanha,
    m.source AS origem_dados,
    m.metric_date AS data_metrica,
    m.impressions AS impressoes,
    m.clicks AS cliques,
    m.conversions AS conversoes,
    m.leads,
    m.spend AS gasto,
    m.revenue AS receita,
    CASE
        WHEN m.spend = 0 THEN 0
        ELSE ROUND(((m.revenue - m.spend) / NULLIF(m.spend, 0)) * 100, 2)
    END AS roi_percentual,
    m.created_at AS criado_em
FROM app.campaign_metrics m
LEFT JOIN dba.campanhas dc ON dc.id_origem_campanha = m.external_campaign_id
    AND dc.origem_dados = m.source;

CREATE OR REPLACE VIEW dba.recomendacoes AS
SELECT
    (ROW_NUMBER() OVER (ORDER BY r.created_at, r.id) - 1)::BIGINT AS id_recomendacao,
    CASE r.recommendation_type
        WHEN 'campaign' THEN 'campanha'
        WHEN 'general' THEN 'geral'
        ELSE r.recommendation_type
    END AS tipo_recomendacao,
    r.title AS titulo,
    r.description AS descricao,
    r.priority AS prioridade,
    r.status,
    r.created_at AS criado_em,
    r.resolved_at AS resolvido_em
FROM app.recommendations r;

CREATE OR REPLACE VIEW dba.pesquisas_precos AS
SELECT
    (ROW_NUMBER() OVER (ORDER BY p.created_at, p.id) - 1)::BIGINT AS id_pesquisa_preco,
    p.product_name AS produto,
    p.positioning AS posicionamento,
    p.source AS origem_dados,
    p.ticket_medio,
    p.price_competitive AS preco_competitivo,
    p.price_recommended AS preco_recomendado,
    p.price_premium AS preco_premium,
    p.range_low AS faixa_minima,
    p.range_high AS faixa_maxima,
    p.observed_items AS itens_observados,
    p.created_at AS criado_em
FROM app.price_researches p;

CREATE OR REPLACE VIEW dba.resumo_banco AS
SELECT 'clientes' AS tabela, COUNT(*)::BIGINT AS registros FROM app.customers
UNION ALL SELECT 'pedidos', COUNT(*)::BIGINT FROM app.orders
UNION ALL SELECT 'eventos', COUNT(*)::BIGINT FROM app.events
UNION ALL SELECT 'campanhas', COUNT(*)::BIGINT FROM app.campaigns
UNION ALL SELECT 'metricas_campanhas', COUNT(*)::BIGINT FROM app.campaign_metrics
UNION ALL SELECT 'recomendacoes', COUNT(*)::BIGINT FROM app.recommendations
UNION ALL SELECT 'pesquisas_precos', COUNT(*)::BIGINT FROM app.price_researches;

-- ===== 005_customer_contact_channels.sql =====
ALTER TABLE app.customers
    ADD COLUMN IF NOT EXISTS whatsapp TEXT,
    ADD COLUMN IF NOT EXISTS instagram TEXT,
    ADD COLUMN IF NOT EXISTS tiktok TEXT,
    ADD COLUMN IF NOT EXISTS linkedin TEXT,
    ADD COLUMN IF NOT EXISTS facebook TEXT,
    ADD COLUMN IF NOT EXISTS preferred_contact_channel TEXT;

CREATE INDEX IF NOT EXISTS idx_customers_whatsapp ON app.customers (whatsapp);
CREATE INDEX IF NOT EXISTS idx_customers_preferred_contact_channel ON app.customers (preferred_contact_channel);

DROP VIEW IF EXISTS dba.resumo_banco;
DROP VIEW IF EXISTS dba.contatos_clientes;
DROP VIEW IF EXISTS dba.clientes CASCADE;

CREATE OR REPLACE VIEW dba.clientes AS
SELECT
    (ROW_NUMBER() OVER (ORDER BY c.created_at, c.id) - 1)::BIGINT AS id_cliente,
    c.external_id AS id_origem_cliente,
    c.source AS origem_dados,
    c.name AS nome,
    c.email,
    c.phone AS telefone,
    c.whatsapp,
    c.instagram,
    c.tiktok,
    c.linkedin,
    c.facebook,
    c.preferred_contact_channel AS canal_preferido_contato,
    c.city AS cidade,
    c.state AS estado,
    c.country AS pais,
    c.consent_marketing AS consentimento_marketing,
    c.consent_source AS origem_consentimento,
    c.behavioral_segment AS segmento_comportamental,
    c.intent_score AS score_intencao,
    c.status,
    c.created_at AS criado_em,
    c.updated_at AS atualizado_em
FROM app.customers c;

CREATE OR REPLACE VIEW dba.pedidos AS
SELECT
    (ROW_NUMBER() OVER (ORDER BY o.created_at, o.id) - 1)::BIGINT AS id_pedido,
    dc.id_cliente,
    o.external_order_id AS id_origem_pedido,
    o.external_customer_id AS id_origem_cliente,
    o.source AS origem_dados,
    o.product_name AS produto,
    o.category AS categoria,
    o.store_name AS loja,
    o.channel AS canal,
    o.value AS valor,
    o.purchased_at AS comprado_em,
    o.created_at AS criado_em
FROM app.orders o
LEFT JOIN dba.clientes dc ON dc.id_origem_cliente = o.external_customer_id
    AND dc.origem_dados = o.source;

CREATE OR REPLACE VIEW dba.eventos AS
SELECT
    (ROW_NUMBER() OVER (ORDER BY e.created_at, e.id) - 1)::BIGINT AS id_evento,
    dc.id_cliente,
    e.external_event_id AS id_origem_evento,
    e.external_customer_id AS id_origem_cliente,
    e.source AS origem_dados,
    CASE e.event_type
        WHEN 'abandoned_cart' THEN 'carrinho_abandonado'
        WHEN 'product_view' THEN 'visualizacao_produto'
        WHEN 'lead' THEN 'lead'
        WHEN 'purchase' THEN 'compra'
        ELSE e.event_type
    END AS tipo_evento,
    e.product_name AS produto,
    e.channel AS canal,
    e.occurred_at AS ocorrido_em,
    e.created_at AS criado_em
FROM app.events e
LEFT JOIN dba.clientes dc ON dc.id_origem_cliente = e.external_customer_id
    AND dc.origem_dados = e.source;

CREATE OR REPLACE VIEW dba.contatos_clientes AS
SELECT
    id_cliente,
    id_origem_cliente,
    origem_dados,
    nome,
    email,
    telefone,
    whatsapp,
    instagram,
    tiktok,
    linkedin,
    facebook,
    canal_preferido_contato,
    consentimento_marketing,
    segmento_comportamental,
    score_intencao,
    status
FROM dba.clientes;

CREATE OR REPLACE VIEW dba.resumo_banco AS
SELECT 'clientes' AS tabela, COUNT(*)::BIGINT AS registros FROM app.customers
UNION ALL SELECT 'contatos_clientes', COUNT(*)::BIGINT FROM dba.contatos_clientes
UNION ALL SELECT 'pedidos', COUNT(*)::BIGINT FROM app.orders
UNION ALL SELECT 'eventos', COUNT(*)::BIGINT FROM app.events
UNION ALL SELECT 'campanhas', COUNT(*)::BIGINT FROM app.campaigns
UNION ALL SELECT 'metricas_campanhas', COUNT(*)::BIGINT FROM app.campaign_metrics
UNION ALL SELECT 'recomendacoes', COUNT(*)::BIGINT FROM app.recommendations
UNION ALL SELECT 'pesquisas_precos', COUNT(*)::BIGINT FROM app.price_researches;
