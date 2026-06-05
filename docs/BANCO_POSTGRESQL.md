# PersonaPulse AI - PostgreSQL

## Objetivo

Migrar a persistencia do PersonaPulse AI de arquivo JSON local para PostgreSQL, mantendo compatibilidade com:

- frontend do PersonaPulse;
- CRM;
- APIs de Ads;
- endpoints Power BI.

## Estrategia do MVP

Nesta etapa, o backend usa uma camada hibrida:

- se `DATABASE_URL` existir, a API usa PostgreSQL;
- se `DATABASE_URL` nao existir, a API usa o arquivo local `data/store.json`.

Isso permite desenvolver localmente sem banco e usar PostgreSQL em producao.

## Modelo atual

O MVP salva o estado consolidado em JSONB para evitar quebrar os contratos atuais da aplicacao. Alem disso, o banco ja possui o primeiro modelo relacional para a proxima etapa.

Tabelas:

- `app_store`: guarda o estado consolidado do produto;
- `app_audit`: guarda trilha de auditoria das principais acoes.

Arquivo SQL:

```text
APIS/personapulse-api/migrations/001_app_store_postgresql.sql
```

Modelo relacional:

```text
APIS/personapulse-api/migrations/002_relational_model.sql
```

Schemas criados:

- `app`
- `integrations`
- `bi`
- `audit`

Tabelas relacionais principais:

- `app.customers`
- `app.orders`
- `app.events`
- `app.campaigns`
- `app.campaign_metrics`
- `app.recommendations`
- `integrations.data_sources`
- `integrations.connector_configs`
- `bi.powerbi_snapshots`
- `audit.audit_logs`

Views executivas:

- `bi.vw_executive_summary`
- `bi.vw_campaign_performance`
- `bi.vw_customer_profile`

## Variavel de ambiente

Configure no Render ou no ambiente local:

```text
DATABASE_URL=postgresql://usuario:senha@host:porta/banco
```

Exemplo local:

```text
DATABASE_URL=postgresql://postgres:1346@localhost:5432/postgres
```

## Como rodar localmente com PostgreSQL

```powershell
cd APIS/personapulse-api
$env:DATABASE_URL="postgresql://postgres:1346@localhost:5432/postgres"
python server.py
```

A API cria automaticamente as tabelas do store JSONB (`app_store` e `app_audit`). A migração relacional `002` deve ser executada no banco antes de migrarmos os endpoints para as tabelas normalizadas.

## Compatibilidade

Os endpoints continuam iguais:

- `/api/crm/customers`
- `/api/crm/orders`
- `/api/crm/events`
- `/api/campaigns`
- `/api/meta-ads/*`
- `/api/ads/*`
- `/api/powerbi/*`

O frontend nao precisa mudar para usar PostgreSQL.

## Proximo passo recomendado

Depois do MVP estabilizar, conectar os endpoints da API nas tabelas relacionais ja criadas:

- `customers`
- `orders`
- `events`
- `campaigns`
- `campaign_metrics`
- `data_sources`
- `recommendations`
- `connector_configs`
- `powerbi_snapshots`
