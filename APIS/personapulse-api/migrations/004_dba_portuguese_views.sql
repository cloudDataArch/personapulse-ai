CREATE SCHEMA IF NOT EXISTS dba;

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
