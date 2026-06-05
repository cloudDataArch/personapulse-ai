# PersonaPulse AI - Pesquisa de precos com DataForSEO

## Objetivo

Usar a DataForSEO Merchant API como fonte estruturada de precos para o MVP do PersonaPulse AI.

Fluxo:

1. Usuario informa o produto e o posicionamento.
2. PersonaPulse chama a DataForSEO Merchant API para Google Shopping Brasil.
3. A API filtra fontes permitidas, remove outliers e calcula ticket medio.
4. O sistema gera tres sugestoes de preco: competitivo, recomendado e premium.
5. O resultado e salvo no PostgreSQL em `app.price_researches`.

## Variaveis de ambiente

No Render, configure:

- `DATAFORSEO_LOGIN`
- `DATAFORSEO_PASSWORD`

Esses valores nao devem ser salvos no Git.

## Endpoint usado

O backend usa o fluxo de tarefas da DataForSEO:

- `POST /v3/merchant/google/products/task_post`
- `GET /v3/merchant/google/products/task_get/advanced/{task_id}`

Parametros principais:

- `keyword`: produto pesquisado
- `location_code`: `2076` para Brasil
- `language_code`: `pt`
- `se_domain`: `google.com.br`
- `depth`: `30`

## Fontes aceitas

Por padrao, o PersonaPulse aceita resultados cujo marketplace/fonte contenha:

- Amazon
- Mercado Livre
- Magalu / Magazine Luiza
- Shopee
- TikTok Shop
- Casas Bahia

Resultados fora dessa lista sao descartados antes do calculo.

## Persistencia

Cada pesquisa e salva em:

- `app.price_researches`
- `bi.vw_price_researches`

Campos principais:

- `product_name`
- `positioning`
- `source`
- `ticket_medio`
- `price_competitive`
- `price_recommended`
- `price_premium`
- `range_low`
- `range_high`
- `observed_items`
- `sources`
- `raw_payload`

## Comportamento sem credenciais

Se as credenciais DataForSEO nao estiverem configuradas, a tela ainda funciona com uma estimativa temporaria, mas informa claramente que a fonte real esta aguardando credenciais.
