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

Esta versao usa persistencia hibrida:

- PostgreSQL quando `DATABASE_URL` estiver configurada;
- JSON local em `data/store.json` quando `DATABASE_URL` nao estiver configurada.

Schema SQL:

```text
migrations/001_app_store_postgresql.sql
```
