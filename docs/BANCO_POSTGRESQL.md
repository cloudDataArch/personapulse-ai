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

O MVP salva o estado consolidado em JSONB para evitar quebrar os contratos atuais da aplicacao.

Tabelas:

- `app_store`: guarda o estado consolidado do produto;
- `app_audit`: guarda trilha de auditoria das principais acoes.

Arquivo SQL:

```text
APIS/personapulse-api/migrations/001_app_store_postgresql.sql
```

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

A API cria as tabelas automaticamente se elas ainda nao existirem.

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

Depois do MVP estabilizar, normalizar os dados em tabelas relacionais:

- `customers`
- `orders`
- `events`
- `campaigns`
- `campaign_metrics`
- `data_sources`
- `recommendations`
- `connector_configs`
- `powerbi_snapshots`
