# PersonaPulse AI

Prototipo navegavel do PersonaPulse AI com dashboard, clientes, campanhas, pesquisa de precos, central de integracoes e endpoints para Power BI.

## Estrutura

- `outputs/personapulse-prototype/index.html`: frontend navegavel do MVP.
- `outputs/personapulse-api/static/personapulse/index.html`: frontend publicado junto da API.
- `outputs/personapulse-api/server.py`: API Python para CRM, Ads, OAuth, Power BI e sincronizacao.
- `outputs/personapulse-api/README.md`: referencia de endpoints da API.
- `outputs/personapulse-api/RENDER_DEPLOY.md`: guia de deploy no Render.
- `docs/DESENVOLVIMENTO_TECNICO.md`: documentacao tecnica de desenvolvimento.
- `docs/ORGANOGRAMA_PROJETO.md`: organograma visual e hierarquico do projeto.
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
cd outputs/personapulse-api
python server.py
```

API local:

```text
http://127.0.0.1:8088/docs
```

Frontend local:

```text
outputs/personapulse-prototype/index.html
```

## Deploy no Render

Use o blueprint `render.yaml` ou crie um Web Service manualmente:

- Root Directory: `outputs/personapulse-api`
- Build Command: `pip install -r requirements.txt`
- Start Command: `python server.py`
- Health Check Path: `/health`

## Proximo marco tecnico

Migrar a persistencia atual em JSON para PostgreSQL, mantendo compatibilidade com o frontend, CRM, Ads e Power BI.
