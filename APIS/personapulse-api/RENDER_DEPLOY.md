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
<URL_PUBLICA_DA_API>
```

Use essa URL no PersonaPulse, no campo:

```txt
URL da API PersonaPulse
```

## Redirect OAuth

No Meta Developers e no Google Cloud, cadastre:

```txt
<URL_PUBLICA_DA_API>/api/oauth/callback
```

Troque `<URL_PUBLICA_DA_API_SEM_PROTOCOLO>` pela URL real que o Render gerar.

## Observacao importante

No plano gratuito, o servico pode dormir apos inatividade. A primeira chamada depois de um tempo parado pode demorar alguns segundos.
