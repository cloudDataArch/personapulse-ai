# PersonaPulse AI

Protótipo navegável do PersonaPulse AI com dashboard, campanhas, clientes, pesquisa de preços e central de integrações.

## Estrutura

- `outputs/personapulse-prototype/index.html`: frontend navegável do MVP.
- `outputs/personapulse-api/server.py`: API Python para CRM, Ads, OAuth e sincronização.
- `render.yaml`: blueprint para deploy da API no Render.

## Rodar localmente

```powershell
cd outputs/personapulse-api
python server.py
```

API local:

```txt
http://127.0.0.1:8088/docs
```

Frontend:

```txt
outputs/personapulse-prototype/index.html
```

## Deploy no Render

Use o blueprint `render.yaml` ou crie um Web Service manualmente:

- Root Directory: `outputs/personapulse-api`
- Build Command: `pip install -r requirements.txt`
- Start Command: `python server.py`
- Health Check Path: `/health`

Depois do deploy, use a URL gerada pelo Render no campo `URL da API PersonaPulse` dentro da tela de Integrações.
