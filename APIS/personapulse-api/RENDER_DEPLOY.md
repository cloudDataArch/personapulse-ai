# Deploy no Render

## Servico

- Tipo: Web Service
- Nome sugerido: `personapulse-api`
- Runtime: Python
- Build Command: `pip install -r requirements.txt`
- Start Command: `python server.py`
- Health Check: `/health`

## URL gerada

Depois do deploy, o Render vai gerar uma URL parecida com:

```txt
https://personapulse-api.onrender.com
```

Use essa URL no PersonaPulse, no campo:

```txt
URL da API PersonaPulse
```

## Redirect OAuth

No Meta Developers e no Google Cloud, cadastre:

```txt
https://personapulse-api.onrender.com/api/oauth/callback
```

Troque `personapulse-api.onrender.com` pela URL real que o Render gerar.

## Observacao importante

No plano gratuito, o servico pode dormir apos inatividade. A primeira chamada depois de um tempo parado pode demorar alguns segundos.
