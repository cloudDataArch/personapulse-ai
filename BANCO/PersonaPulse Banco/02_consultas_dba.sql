-- Banco: PersonaPulse Banco
-- Consultas iniciais para DBA, BI e validacao funcional.

SELECT * FROM dba.resumo_banco ORDER BY tabela;

SELECT
    id_cliente,
    nome,
    email,
    whatsapp,
    instagram,
    tiktok,
    linkedin,
    facebook,
    canal_preferido_contato,
    origem_dados
FROM dba.contatos_clientes
ORDER BY id_cliente
LIMIT 50;

SELECT
    id_cliente,
    nome,
    segmento_comportamental,
    score_intencao,
    consentimento_marketing,
    origem_dados
FROM dba.clientes
ORDER BY id_cliente
LIMIT 50;

SELECT
    p.id_pedido,
    p.id_cliente,
    c.nome,
    p.produto,
    p.loja,
    p.canal,
    p.valor,
    p.comprado_em
FROM dba.pedidos p
LEFT JOIN dba.clientes c ON c.id_cliente = p.id_cliente
ORDER BY p.id_pedido
LIMIT 50;

SELECT
    id_pesquisa_preco,
    produto,
    posicionamento,
    origem_dados,
    ticket_medio,
    preco_competitivo,
    preco_recomendado,
    preco_premium,
    itens_observados
FROM dba.pesquisas_precos
ORDER BY criado_em DESC
LIMIT 25;
