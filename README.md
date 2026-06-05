# PersonaPulse AI

Prototipo navegavel do PersonaPulse AI com dashboard, clientes, campanhas, pesquisa de precos, central de integracoes e endpoints para Power BI.

## Estrutura

- `APIS/personapulse-api/server.py`: API Python para CRM, Ads, OAuth, Power BI e sincronizacao.
- `APIS/personapulse-api/static/personapulse/index.html`: frontend publicado junto da API.
- `APIS/personapulse-api/README.md`: referencia de endpoints da API.
- `APIS/personapulse-api/RENDER_DEPLOY.md`: guia de deploy no Render.
- `interfaces.HTML/personapulse-prototype/index.html`: frontend navegavel do MVP.
- `interfaces.PNG/`: imagens de interface, previews, organograma e campanha.
- `JSON/`: exemplos de payloads JSON para API.
- `CSV/`: bases demonstrativas de clientes.
- `DOCUMENTOS/`: arquivos DOCX de arquitetura, organograma, comparativo e roteiro.
- `scripts/`: scripts usados para gerar documentos, CSVs, imagens e utilitarios.
- `docs/DESENVOLVIMENTO_TECNICO.md`: documentacao tecnica de desenvolvimento.
- `docs/ORGANOGRAMA_PROJETO.md`: organograma visual e hierarquico do projeto.
- `docs/BANCO_POSTGRESQL.md`: guia de persistencia PostgreSQL.
- `render.yaml`: blueprint para deploy no Render.

## URLs publicas

- Aplicacao: `https://personapulse-ai.onrender.com/app`
- API/docs: `https://personapulse-ai.onrender.com/docs`
- Health check: `https://personapulse-ai.onrender.com/health`
- Power BI resumo: `https://personapulse-ai.onrender.com/api/powerbi/executive-summary`
- Power BI clientes: `https://personapulse-ai.onrender.com/api/powerbi/customers`
- Power BI campanhas: `https://personapulse-ai.onrender.com/api/powerbi/campaigns`
- Power BI fontes: `https://personapulse-ai.onrender.com/api/powerbi/sources`

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
interfaces.HTML/personapulse-prototype/index.html
```

## Deploy no Render

Use o blueprint `render.yaml` ou crie um Web Service manualmente:

- Root Directory: `APIS/personapulse-api`
- Build Command: `pip install -r requirements.txt`
- Start Command: `python server.py`
- Health Check Path: `/health`

## Proximo marco tecnico

Configurar `DATABASE_URL` no Render e validar a persistencia PostgreSQL com CRM, Ads e Power BI.
