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
