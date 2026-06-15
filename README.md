# PersonaPulse AI

Aplicacao PersonaPulse AI com dashboard, clientes, campanhas, pesquisa de precos, central de integracoes e endpoints para Power BI.

## Estrutura

- `APIS/personapulse-api/server.py`: API Python para CRM, Ads, OAuth, Power BI e sincronizacao.
- `APIS/personapulse-api/static/personapulse/index.html`: frontend publicado junto da API.
- `APIS/personapulse-api/README.md`: referencia de endpoints da API.
- `APIS/personapulse-api/RENDER_DEPLOY.md`: guia de deploy no Render.
- `interfaces.PNG/`: imagens de interface, previews e organograma.
- `CSV/`: bases demonstrativas de clientes.
- `DOCUMENTOS/`: arquivos DOCX de arquitetura, organograma, comparativo e roteiro.
- `scripts/`: scripts usados para gerar documentos, CSVs, imagens e utilitarios.
- `docs/DESENVOLVIMENTO_TECNICO.md`: documentacao tecnica de desenvolvimento.
- `docs/ORGANOGRAMA_PROJETO.md`: organograma visual e hierarquico do projeto.
- `docs/BANCO_POSTGRESQL.md`: guia de persistencia PostgreSQL.
- `render.yaml`: blueprint para deploy no Render.

## URLs publicas

Defina a URL publica conforme o servico publicado.

- Aplicacao: `<URL_PUBLICA_DA_API>/app`
- API/docs: `<URL_PUBLICA_DA_API>/docs`
- Health check: `<URL_PUBLICA_DA_API>/health`
- Power BI resumo: `<URL_PUBLICA_DA_API>/api/powerbi/executive-summary`
- Power BI clientes: `<URL_PUBLICA_DA_API>/api/powerbi/customers`
- Power BI campanhas: `<URL_PUBLICA_DA_API>/api/powerbi/campaigns`
- Power BI fontes: `<URL_PUBLICA_DA_API>/api/powerbi/sources`

## Rodar localmente

```powershell
cd APIS/personapulse-api
python server.py
```

API local:

```text
http://127.0.0.1:8088/docs
```

Frontend local:

```text
http://127.0.0.1:8088/app
```

## Deploy no Render

Use o blueprint `render.yaml` ou crie um Web Service manualmente:

- Root Directory: `APIS/personapulse-api`
- Build Command: `pip install -r requirements.txt`
- Start Command: `python server.py`
- Health Check Path: `/health`

## Proximo marco tecnico

Configurar `DATABASE_URL` no Render e validar a persistencia PostgreSQL com CRM, Ads e Power BI. Sem `DATABASE_URL`, a API nao grava dados em producao.
