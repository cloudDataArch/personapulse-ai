# PersonaPulse AI - API

API para integrar o PersonaPulse AI com CRM, fontes de Ads, gerador de campanhas e Power BI.

## Rodar localmente

```powershell
python .\server.py
```

Abra:

```text
http://127.0.0.1:8088/docs
```

## Endpoints

### Base

- `GET /health`
- `GET /docs`
- `GET /api/system/status`
- `GET /api/db/status`
- `POST /api/db/resync-relational`

### CRM

- `POST /api/crm/customers`
- `GET /api/crm/customers`
- `POST /api/crm/orders`
- `GET /api/crm/orders`
- `POST /api/crm/events`
- `GET /api/crm/events`

### Segmentos, campanhas e recomendacoes

- `GET /api/segments`
- `GET /api/campaigns`
- `POST /api/campaigns/generate`
- `GET /api/recommendations`
- `POST /api/crm/recommendations/push`

### Precificador removido

O precificador foi removido do PersonaPulse AI porque as fontes publicas bloqueavam consulta automatica e o produto nao deve exibir ticket medio vazio ou inventado.

O endpoint legado:

```http
GET /api/price-research
```

retorna `410 Gone` com `price_research_removed`.

### Meta Ads

- `POST /api/meta-ads/campaigns`
- `GET /api/meta-ads/campaigns`
- `POST /api/meta-ads/insights`
- `GET /api/meta-ads/insights`
- `POST /api/meta-ads/leads`
- `GET /api/meta-ads/leads`

### Outros Ads

- `POST /api/ads/{source}/campaigns`
- `GET /api/ads/{source}/campaigns`
- `POST /api/ads/{source}/insights`
- `GET /api/ads/{source}/insights`
- `POST /api/ads/{source}/leads`
- `GET /api/ads/{source}/leads`

### Conectores

- `POST /api/connectors/{source}/config`
- `GET /api/audit-logs`

### Power BI

- `GET /api/powerbi/executive-summary`
- `GET /api/powerbi/customers`
- `GET /api/powerbi/campaigns`
- `GET /api/powerbi/sources`
- `POST /api/powerbi/snapshot`

## Testes locais legados

Os scripts abaixo existem apenas para desenvolvimento local. A etapa atual do produto deve usar credenciais reais via conectores OAuth/API.

```powershell
python .\crm_simulator.py
python .\meta_ads_simulator.py
python .\ads_multi_simulator.py
```

## Persistencia

Esta versao usa PostgreSQL como persistencia oficial.

- Configure `DATABASE_URL` em producao.
- Sem `DATABASE_URL`, a API retorna erro de configuracao e nao grava dados.
- O `app_store` e a fonte consolidada. As tabelas relacionais `app.*`, `dba.*`, `bi.*`, `integrations.*` e `audit.*` podem ser reconstruidas com `POST /api/db/resync-relational`.
- O endpoint `GET /api/db/status` mostra contagens esperadas, contagens relacionais e divergencias de sincronizacao.

Na VPS atual, o servico systemd usa `/opt/personapulse/start.sh`, que deve apontar para:

```text
DATABASE_URL=postgresql://personapulse_user:<senha>@127.0.0.1:5433/personapulse_ai
```

O script tambem deve iniciar a API pela virtualenv:

```text
/opt/personapulse/APIS/personapulse-api/.venv/bin/python server.py
```

Schema SQL:

```text
migrations/001_app_store_postgresql.sql
```
