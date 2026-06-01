# PersonaPulse AI - CRM Integration API

API local para integrar o PersonaPulse AI com CRMs.

## Rodar

```powershell
& 'C:\Users\Celio\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\server.py
```

Abra:

```txt
http://127.0.0.1:8088/docs
```

## Endpoints

- `GET /health`
- `POST /api/crm/customers`
- `GET /api/crm/customers`
- `POST /api/crm/orders`
- `GET /api/crm/orders`
- `POST /api/crm/events`
- `GET /api/crm/events`
- `GET /api/segments`
- `GET /api/campaigns`
- `POST /api/campaigns/generate`
- `POST /api/meta-ads/campaigns`
- `GET /api/meta-ads/campaigns`
- `POST /api/meta-ads/insights`
- `GET /api/meta-ads/insights`
- `POST /api/meta-ads/leads`
- `GET /api/meta-ads/leads`
- `POST /api/ads/{source}/campaigns`
- `GET /api/ads/{source}/campaigns`
- `POST /api/ads/{source}/insights`
- `GET /api/ads/{source}/insights`
- `POST /api/ads/{source}/leads`
- `GET /api/ads/{source}/leads`
- `POST /api/connectors/{source}/config`
- `GET /api/recommendations`
- `POST /api/crm/recommendations/push`
- `GET /api/audit-logs`

## Testes locais legados

Os scripts abaixo existem apenas para desenvolvimento local. A etapa atual do produto deve usar credenciais reais via conectores OAuth/API.

```powershell
python .\crm_simulator.py
python .\meta_ads_simulator.py
python .\ads_multi_simulator.py
```

## Observação

Esta primeira versão salva os dados em `data/store.json`. Depois podemos trocar a persistência para PostgreSQL.
