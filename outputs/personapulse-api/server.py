import json
import os
import urllib.request
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse


HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8088"))
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STORE_FILE = DATA_DIR / "store.json"
API_VERSION = "v20.0"


CONNECTOR_PROVIDERS = {
    "meta": {
        "auth_url": f"https://www.facebook.com/{API_VERSION}/dialog/oauth",
        "token_url": f"https://graph.facebook.com/{API_VERSION}/oauth/access_token",
        "default_scopes": "ads_read,business_management",
    },
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "default_scopes": "https://www.googleapis.com/auth/adwords",
    },
    "microsoft": {"default_scopes": "https://ads.microsoft.com/msads.manage"},
    "tiktok": {"default_scopes": "advertiser.read,report.read"},
    "linkedin": {"default_scopes": "r_ads,r_ads_reporting"},
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def empty_store():
    return {
        "customers": [],
        "orders": [],
        "events": [],
        "campaigns": [],
        "meta_ads_campaigns": [],
        "meta_ads_insights": [],
        "meta_ads_leads": [],
        "ads_campaigns": [],
        "ads_insights": [],
        "ads_leads": [],
        "connector_configs": {},
        "recommendations": [],
        "audit_logs": [],
    }


def load_store():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not STORE_FILE.exists():
        save_store(empty_store())
    with STORE_FILE.open("r", encoding="utf-8") as f:
        store = json.load(f)
    for key, value in empty_store().items():
        store.setdefault(key, value)
    return store


def save_store(store):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with STORE_FILE.open("w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def add_audit(store, action, details):
    store["audit_logs"].insert(0, {
        "id": str(uuid.uuid4()),
        "action": action,
        "details": details,
        "created_at": now_iso(),
    })


def read_json(handler):
    length = int(handler.headers.get("Content-Length", "0") or 0)
    if length == 0:
        return {}
    raw = handler.rfile.read(length).decode("utf-8")
    return json.loads(raw)


def public_connector_config(config):
    return {
        key: value for key, value in config.items()
        if key not in {"client_secret", "access_token", "refresh_token"}
    } | {
        "has_client_secret": bool(config.get("client_secret")),
        "has_access_token": bool(config.get("access_token")),
    }


def http_get_json(url, params):
    query = urlencode(params, doseq=True)
    with urllib.request.urlopen(f"{url}?{query}", timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def http_post_json(url, payload, headers=None):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})}, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def http_post_form_json(url, payload):
    data = urlencode(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"true", "1", "sim", "yes"}


def customer_score(customer, orders, events):
    customer_orders = [o for o in orders if o.get("external_customer_id") == customer.get("external_id")]
    customer_events = [e for e in events if e.get("external_customer_id") == customer.get("external_id")]
    total_value = sum(float(o.get("value") or 0) for o in customer_orders)
    score = 35
    score += min(30, len(customer_orders) * 6)
    score += min(20, int(total_value / 1000))
    score += min(15, len(customer_events) * 3)
    if as_bool(customer.get("consent_marketing")):
        score += 5
    return max(0, min(100, score))


def build_segments(store):
    customers = store["customers"]
    orders = store["orders"]
    events = store["events"]
    enriched = []
    for customer in customers:
        score = customer_score(customer, orders, events)
        total_value = sum(float(o.get("value") or 0) for o in orders if o.get("external_customer_id") == customer.get("external_id"))
        enriched.append({**customer, "score": score, "total_value": total_value})

    def count(predicate):
        return sum(1 for c in enriched if predicate(c))

    return [
        {
            "id": "premium",
            "name": "Clientes premium",
            "customers": count(lambda c: c["total_value"] >= 5000 or c["score"] >= 85),
            "rule": "total_value >= 5000 OR score >= 85",
        },
        {
            "id": "high_intent",
            "name": "Alta intenção",
            "customers": count(lambda c: c["score"] >= 80),
            "rule": "score >= 80",
        },
        {
            "id": "no_consent",
            "name": "Sem consentimento",
            "customers": count(lambda c: not as_bool(c.get("consent_marketing"))),
            "rule": "consent_marketing = false",
        },
        {
            "id": "new_customers",
            "name": "Novos clientes",
            "customers": count(lambda c: c["total_value"] == 0),
            "rule": "sem pedidos registrados",
        },
    ]


def generate_campaign(payload):
    segment = payload.get("segment_name") or payload.get("segment_id") or "Clientes com alta intenção"
    product = payload.get("product_name") or "produto foco"
    channel = payload.get("channel") or "WhatsApp"
    tone = payload.get("tone") or "Sofisticado"
    objective = payload.get("objective") or "converter interessados em compradores"
    return {
        "id": str(uuid.uuid4()),
        "segment": segment,
        "product_name": product,
        "channel": channel,
        "tone": tone,
        "objective": objective,
        "title": f"{product}: uma escolha feita para quem exige mais",
        "body": (
            f"Apresente {product} com uma mensagem {tone.lower()} para {segment}. "
            f"A campanha deve vender desejo, confiança e urgência, conduzindo o cliente a {objective}."
        ),
        "cta": "Conhecer a oferta",
        "created_at": now_iso(),
    }


def upsert_by_id(items, payload, id_key):
    item_id = payload.get(id_key) or str(uuid.uuid4())
    payload[id_key] = item_id
    payload["updated_at"] = now_iso()
    existing = next((item for item in items if item.get(id_key) == item_id), None)
    if existing:
        existing.update(payload)
        return "updated", existing
    payload["created_at"] = now_iso()
    items.append(payload)
    return "created", payload


def filter_by_source(items, source):
    return [item for item in items if item.get("source") == source]


def extract_action_value(items, contains):
    for item in items or []:
        action_type = str(item.get("action_type", ""))
        if contains in action_type:
            try:
                return float(item.get("value") or 0)
            except (TypeError, ValueError):
                return 0
    return 0


def sync_meta_ads(store, config):
    account_id = config.get("account_id", "").strip()
    token = config.get("access_token", "").strip()
    if not account_id or not token:
        raise ValueError("Meta Ads precisa de account_id e access_token. Conecte via OAuth primeiro.")
    if not account_id.startswith("act_"):
        account_id = f"act_{account_id}"

    campaigns_payload = http_get_json(
        f"https://graph.facebook.com/{API_VERSION}/{account_id}/campaigns",
        {
            "access_token": token,
            "fields": "id,name,status,objective,start_time,stop_time",
            "limit": 100,
        },
    )
    insights_payload = http_get_json(
        f"https://graph.facebook.com/{API_VERSION}/{account_id}/insights",
        {
            "access_token": token,
            "level": "campaign",
            "date_preset": "last_30d",
            "fields": "campaign_id,campaign_name,impressions,reach,clicks,spend,actions,action_values,date_start,date_stop",
            "limit": 100,
        },
    )

    source = "meta"
    campaign_count = 0
    for campaign in campaigns_payload.get("data", []):
        payload = {
            "source": source,
            "campaign_id": campaign.get("id"),
            "campaign_name": campaign.get("name"),
            "objective": campaign.get("objective"),
            "status": campaign.get("status"),
            "start_date": campaign.get("start_time", "")[:10],
            "end_date": campaign.get("stop_time", "")[:10],
        }
        upsert_by_id(store["ads_campaigns"], payload, "campaign_id")
        campaign_count += 1

    insight_count = 0
    for insight in insights_payload.get("data", []):
        spend = float(insight.get("spend") or 0)
        conversions = extract_action_value(insight.get("actions"), "purchase") or extract_action_value(insight.get("actions"), "lead")
        revenue = extract_action_value(insight.get("action_values"), "purchase")
        payload = {
            "source": source,
            "id": str(uuid.uuid4()),
            "campaign_id": insight.get("campaign_id"),
            "campaign_name": insight.get("campaign_name"),
            "impressions": int(float(insight.get("impressions") or 0)),
            "reach": int(float(insight.get("reach") or 0)),
            "clicks": int(float(insight.get("clicks") or 0)),
            "conversions": conversions,
            "spend": spend,
            "purchase_value": revenue,
            "date_start": insight.get("date_start"),
            "date_stop": insight.get("date_stop"),
            "created_at": now_iso(),
        }
        store["ads_insights"].insert(0, payload)
        insight_count += 1

    config["last_sync_at"] = now_iso()
    config["status"] = "synced"
    return {"campaigns": campaign_count, "insights": insight_count}


def refresh_google_token(config):
    refresh_token = config.get("refresh_token")
    if not refresh_token:
        return config.get("access_token", "")
    payload = http_post_form_json(CONNECTOR_PROVIDERS["google"]["token_url"], {
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })
    config["access_token"] = payload.get("access_token")
    config["token_type"] = payload.get("token_type", "Bearer")
    return config["access_token"]


def sync_google_ads(store, config):
    customer_id = str(config.get("account_id", "")).replace("-", "").strip()
    developer_token = config.get("developer_token", "").strip()
    access_token = refresh_google_token(config)
    if not customer_id or not developer_token or not access_token:
        raise ValueError("Google Ads precisa de customer_id, developer_token e OAuth autorizado.")

    query = """
      SELECT
        campaign.id,
        campaign.name,
        campaign.status,
        campaign.advertising_channel_type,
        metrics.impressions,
        metrics.clicks,
        metrics.cost_micros,
        metrics.conversions,
        metrics.conversions_value
      FROM campaign
      WHERE segments.date DURING LAST_30_DAYS
      LIMIT 100
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": developer_token,
    }
    login_customer_id = str(config.get("login_customer_id", "")).replace("-", "").strip()
    if login_customer_id:
        headers["login-customer-id"] = login_customer_id

    payload = http_post_json(
        f"https://googleads.googleapis.com/v22/customers/{customer_id}/googleAds:searchStream",
        {"query": query},
        headers,
    )

    source = "google"
    campaign_count = 0
    insight_count = 0
    for batch in payload if isinstance(payload, list) else []:
        for row in batch.get("results", []):
            campaign = row.get("campaign", {})
            metrics = row.get("metrics", {})
            campaign_id = str(campaign.get("id", ""))
            campaign_payload = {
                "source": source,
                "campaign_id": campaign_id,
                "campaign_name": campaign.get("name"),
                "objective": campaign.get("advertisingChannelType"),
                "status": campaign.get("status"),
                "start_date": "",
                "end_date": "",
            }
            upsert_by_id(store["ads_campaigns"], campaign_payload, "campaign_id")
            campaign_count += 1
            insight_payload = {
                "source": source,
                "id": str(uuid.uuid4()),
                "campaign_id": campaign_id,
                "campaign_name": campaign.get("name"),
                "impressions": int(metrics.get("impressions") or 0),
                "reach": int(metrics.get("impressions") or 0),
                "clicks": int(metrics.get("clicks") or 0),
                "conversions": float(metrics.get("conversions") or 0),
                "spend": float(metrics.get("costMicros") or 0) / 1_000_000,
                "purchase_value": float(metrics.get("conversionsValue") or 0),
                "date_start": "LAST_30_DAYS",
                "date_stop": "LAST_30_DAYS",
                "created_at": now_iso(),
            }
            store["ads_insights"].insert(0, insight_payload)
            insight_count += 1

    config["last_sync_at"] = now_iso()
    config["status"] = "synced"
    return {"campaigns": campaign_count, "insights": insight_count}


DOCS_HTML = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PersonaPulse API Docs</title>
  <style>
    body{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f6f8fb;color:#172033}
    main{max-width:1040px;margin:0 auto;padding:32px}
    h1{margin:0 0 8px;font-size:28px}
    p{color:#667085}
    section{background:white;border:1px solid #d8dee8;border-radius:8px;padding:18px;margin:16px 0}
    code,pre{background:#111827;color:#e5e7eb;border-radius:8px}
    code{padding:2px 6px}
    pre{padding:14px;overflow:auto}
    .method{font-weight:700;color:#0f8b8d}
  </style>
</head>
<body>
<main>
  <h1>PersonaPulse AI - CRM Integration API</h1>
  <p>API local para receber clientes, pedidos e eventos de um CRM e devolver segmentos, campanhas e recomendações.</p>

  <section><span class="method">GET</span> <code>/health</code><p>Status da API.</p></section>
  <section><span class="method">POST</span> <code>/api/crm/customers</code><p>Cria ou atualiza cliente vindo do CRM.</p>
<pre>{
  "external_id": "crm_123",
  "name": "Ana Silva",
  "email": "ana@email.com",
  "phone": "+5511999999999",
  "city": "Sao Paulo",
  "consent_marketing": true,
  "source": "hubspot"
}</pre></section>
  <section><span class="method">GET</span> <code>/api/crm/customers</code><p>Lista clientes.</p></section>
  <section><span class="method">POST</span> <code>/api/crm/orders</code><p>Recebe compra/pedido.</p>
<pre>{
  "external_customer_id": "crm_123",
  "order_id": "PED-991",
  "product_name": "Notebook Dell Inspiron",
  "category": "eletronicos",
  "store": "E-commerce proprio",
  "value": 5299.90,
  "purchased_at": "2026-05-31"
}</pre></section>
  <section><span class="method">POST</span> <code>/api/crm/events</code><p>Recebe evento comportamental.</p>
<pre>{
  "external_customer_id": "crm_123",
  "event_type": "product_view",
  "product_name": "Notebook Dell Inspiron",
  "occurred_at": "2026-05-31T15:00:00"
}</pre></section>
  <section><span class="method">GET</span> <code>/api/segments</code><p>Retorna segmentos calculados.</p></section>
  <section><span class="method">POST</span> <code>/api/campaigns/generate</code><p>Gera campanha para segmento/produto/canal.</p>
<pre>{
  "segment_name": "Clientes premium",
  "product_name": "Bicicleta MTB Carbon",
  "channel": "Google Ads",
  "tone": "Sofisticado",
  "objective": "vender lancamento premium"
}</pre></section>
  <section><span class="method">GET</span> <code>/api/recommendations</code><p>Lista recomendações geradas.</p></section>
  <section><span class="method">POST</span> <code>/api/crm/recommendations/push</code><p>Simula envio de recomendações de volta ao CRM.</p></section>
  <section><span class="method">POST</span> <code>/api/meta-ads/campaigns</code><p>Cria ou atualiza campanha vinda do Meta Ads.</p>
<pre>{
  "campaign_id": "meta_cmp_001",
  "name": "Conversao Notebook Dell",
  "objective": "SALES",
  "status": "ACTIVE",
  "start_date": "2026-06-01",
  "end_date": "2026-06-10"
}</pre></section>
  <section><span class="method">GET</span> <code>/api/meta-ads/campaigns</code><p>Lista campanhas sincronizadas do Meta Ads.</p></section>
  <section><span class="method">POST</span> <code>/api/meta-ads/insights</code><p>Recebe metricas simuladas de performance do Meta Ads.</p>
<pre>{
  "campaign_id": "meta_cmp_001",
  "campaign_name": "Conversao Notebook Dell",
  "spend": 2850.75,
  "impressions": 120000,
  "reach": 76000,
  "clicks": 3900,
  "conversions": 84,
  "purchase_value": 128900.50,
  "date_start": "2026-06-01",
  "date_stop": "2026-06-10"
}</pre></section>
  <section><span class="method">GET</span> <code>/api/meta-ads/insights</code><p>Lista insights sincronizados do Meta Ads.</p></section>
</main>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def send_json(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_html(self, html):
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key")
        self.end_headers()

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)
        store = load_store()
        if path in {"/", "/docs"}:
            return self.send_html(DOCS_HTML)
        if path == "/health":
            return self.send_json(200, {"status": "ok", "service": "personapulse-api", "time": now_iso()})
        if path == "/api/crm/customers":
            return self.send_json(200, {"customers": store["customers"], "count": len(store["customers"])})
        if path == "/api/crm/orders":
            return self.send_json(200, {"orders": store["orders"], "count": len(store["orders"])})
        if path == "/api/crm/events":
            return self.send_json(200, {"events": store["events"], "count": len(store["events"])})
        if path == "/api/segments":
            return self.send_json(200, {"segments": build_segments(store)})
        if path == "/api/campaigns":
            return self.send_json(200, {"campaigns": store["campaigns"], "count": len(store["campaigns"])})
        if path == "/api/meta-ads/campaigns":
            return self.send_json(200, {"campaigns": store["meta_ads_campaigns"], "count": len(store["meta_ads_campaigns"])})
        if path == "/api/meta-ads/insights":
            return self.send_json(200, {"insights": store["meta_ads_insights"], "count": len(store["meta_ads_insights"])})
        if path == "/api/meta-ads/leads":
            return self.send_json(200, {"leads": store["meta_ads_leads"], "count": len(store["meta_ads_leads"])})
        if path.startswith("/api/ads/"):
            parts = path.strip("/").split("/")
            if len(parts) == 4:
                source, collection = parts[2], parts[3]
                key = {"campaigns": "ads_campaigns", "insights": "ads_insights", "leads": "ads_leads"}.get(collection)
                if key:
                    items = filter_by_source(store[key], source)
                    return self.send_json(200, {collection: items, "count": len(items), "source": source})
        if path == "/api/connectors":
            return self.send_json(200, {"connectors": {key: public_connector_config(value) for key, value in store["connector_configs"].items()}})
        if path.startswith("/api/connectors/") and path.endswith("/authorize"):
            source = path.strip("/").split("/")[2]
            config = store["connector_configs"].get(source, {})
            provider = CONNECTOR_PROVIDERS.get(source, {})
            if source not in {"meta", "google"}:
                return self.send_json(400, {"error": "oauth_not_implemented", "detail": "OAuth real desta fonte sera ligado depois de Meta Ads e Google Ads."})
            if not config.get("client_id") or not config.get("redirect_uri"):
                return self.send_json(400, {"error": "missing_config", "detail": "Informe client_id e redirect_uri."})
            state = f"{source}:{uuid.uuid4()}"
            config["oauth_state"] = state
            store["connector_configs"][source] = config
            save_store(store)
            params = {
                "client_id": config["client_id"],
                "redirect_uri": config["redirect_uri"],
                "scope": config.get("scopes") or provider["default_scopes"],
                "state": state,
                "response_type": "code",
            }
            if source == "google":
                params["access_type"] = "offline"
                params["prompt"] = "consent"
            url = provider["auth_url"] + "?" + urlencode(params)
            return self.send_json(200, {"authorize_url": url, "source": source})
        if path == "/api/oauth/callback":
            state = (query.get("state") or [""])[0]
            code = (query.get("code") or [""])[0]
            source = state.split(":", 1)[0]
            config = store["connector_configs"].get(source, {})
            if not code or not source or state != config.get("oauth_state"):
                return self.send_html("<h1>OAuth inválido</h1><p>State ou code ausente.</p>")
            if source == "meta":
                token_payload = http_get_json(CONNECTOR_PROVIDERS[source]["token_url"], {
                    "client_id": config["client_id"],
                    "redirect_uri": config["redirect_uri"],
                    "client_secret": config["client_secret"],
                    "code": code,
                })
            elif source == "google":
                token_payload = http_post_form_json(CONNECTOR_PROVIDERS[source]["token_url"], {
                    "client_id": config["client_id"],
                    "redirect_uri": config["redirect_uri"],
                    "client_secret": config["client_secret"],
                    "code": code,
                    "grant_type": "authorization_code",
                })
            else:
                return self.send_html("<h1>OAuth recebido</h1><p>Conector ainda não implementado.</p>")
            config["access_token"] = token_payload.get("access_token")
            if token_payload.get("refresh_token"):
                config["refresh_token"] = token_payload.get("refresh_token")
            config["token_type"] = token_payload.get("token_type", "bearer")
            config["status"] = "authorized"
            config["authorized_at"] = now_iso()
            store["connector_configs"][source] = config
            add_audit(store, "connector_oauth_authorized", {"source": source})
            save_store(store)
            return self.send_html(f"<h1>{source.title()} conectado</h1><p>Você já pode voltar ao PersonaPulse e sincronizar a API real.</p>")
        if path == "/api/recommendations":
            return self.send_json(200, {"recommendations": store["recommendations"], "count": len(store["recommendations"])})
        if path == "/api/audit-logs":
            return self.send_json(200, {"audit_logs": store["audit_logs"][:100]})
        self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        path = urlparse(self.path).path
        store = load_store()
        try:
            payload = read_json(self)
            if path == "/api/crm/customers":
                external_id = payload.get("external_id") or str(uuid.uuid4())
                payload["external_id"] = external_id
                payload["consent_marketing"] = as_bool(payload.get("consent_marketing"))
                payload["updated_at"] = now_iso()
                existing = next((c for c in store["customers"] if c.get("external_id") == external_id), None)
                if existing:
                    existing.update(payload)
                    status = "updated"
                else:
                    payload["created_at"] = now_iso()
                    store["customers"].append(payload)
                    status = "created"
                add_audit(store, "crm_customer_upsert", {"external_id": external_id, "status": status})
                save_store(store)
                return self.send_json(200, {"status": status, "customer": payload})

            if path == "/api/crm/orders":
                payload["id"] = payload.get("id") or str(uuid.uuid4())
                payload["created_at"] = now_iso()
                store["orders"].append(payload)
                add_audit(store, "crm_order_received", {"order_id": payload.get("order_id"), "customer": payload.get("external_customer_id")})
                save_store(store)
                return self.send_json(201, {"status": "created", "order": payload})

            if path == "/api/crm/events":
                payload["id"] = payload.get("id") or str(uuid.uuid4())
                payload["created_at"] = now_iso()
                store["events"].append(payload)
                add_audit(store, "crm_event_received", {"event_type": payload.get("event_type"), "customer": payload.get("external_customer_id")})
                save_store(store)
                return self.send_json(201, {"status": "created", "event": payload})

            if path == "/api/campaigns/generate":
                campaign = generate_campaign(payload)
                store["campaigns"].insert(0, campaign)
                recommendation = {
                    "id": str(uuid.uuid4()),
                    "type": "campaign",
                    "title": f"Publicar campanha: {campaign['title']}",
                    "campaign_id": campaign["id"],
                    "created_at": now_iso(),
                }
                store["recommendations"].insert(0, recommendation)
                add_audit(store, "campaign_generated", {"campaign_id": campaign["id"], "product": campaign["product_name"]})
                save_store(store)
                return self.send_json(201, {"campaign": campaign, "recommendation": recommendation})

            if path == "/api/meta-ads/campaigns":
                status, campaign = upsert_by_id(store["meta_ads_campaigns"], payload, "campaign_id")
                add_audit(store, "meta_ads_campaign_upsert", {"campaign_id": campaign.get("campaign_id"), "status": status})
                save_store(store)
                return self.send_json(200, {"status": status, "campaign": campaign})

            if path == "/api/meta-ads/insights":
                payload["id"] = payload.get("id") or str(uuid.uuid4())
                payload["created_at"] = now_iso()
                store["meta_ads_insights"].insert(0, payload)
                add_audit(store, "meta_ads_insight_received", {
                    "campaign_id": payload.get("campaign_id"),
                    "spend": payload.get("spend"),
                    "conversions": payload.get("conversions"),
                })
                save_store(store)
                return self.send_json(201, {"status": "created", "insight": payload})

            if path == "/api/meta-ads/leads":
                lead_id = payload.get("lead_id") or str(uuid.uuid4())
                payload["lead_id"] = lead_id
                payload["consent_marketing"] = as_bool(payload.get("consent_marketing", True))
                payload["updated_at"] = now_iso()
                existing = next((lead for lead in store["meta_ads_leads"] if lead.get("lead_id") == lead_id), None)
                if existing:
                    existing.update(payload)
                    status = "updated"
                else:
                    payload["created_at"] = now_iso()
                    store["meta_ads_leads"].append(payload)
                    status = "created"
                add_audit(store, "meta_ads_lead_upsert", {"lead_id": lead_id, "status": status})
                save_store(store)
                return self.send_json(200, {"status": status, "lead": payload})

            if path.startswith("/api/connectors/") and path.endswith("/config"):
                source = path.strip("/").split("/")[2]
                sanitized = {
                    "source": source,
                    "client_id": payload.get("client_id", ""),
                    "client_secret": payload.get("client_secret", ""),
                    "account_id": payload.get("account_id", ""),
                    "developer_token": payload.get("developer_token", ""),
                    "login_customer_id": payload.get("login_customer_id", ""),
                    "redirect_uri": payload.get("redirect_uri") or "http://127.0.0.1:8088/api/oauth/callback",
                    "scopes": payload.get("scopes") or CONNECTOR_PROVIDERS.get(source, {}).get("default_scopes", ""),
                    "status": "configured" if payload.get("client_id") and payload.get("account_id") else "incomplete",
                    "updated_at": now_iso(),
                }
                store["connector_configs"][source] = sanitized
                add_audit(store, "connector_config_saved", {"source": source, "status": sanitized["status"]})
                save_store(store)
                return self.send_json(200, {"status": sanitized["status"], "connector": sanitized})

            if path.startswith("/api/connectors/") and path.endswith("/sync"):
                source = path.strip("/").split("/")[2]
                config = store["connector_configs"].get(source, {})
                if source == "meta":
                    result = sync_meta_ads(store, config)
                elif source == "google":
                    result = sync_google_ads(store, config)
                else:
                    return self.send_json(400, {"error": "sync_not_implemented", "detail": "Sincronização real disponível primeiro para Meta Ads e Google Ads."})
                store["connector_configs"][source] = config
                add_audit(store, "connector_real_sync", {"source": source, **result})
                save_store(store)
                return self.send_json(200, {"status": "synced", "source": source, **result})

            if path.startswith("/api/ads/"):
                parts = path.strip("/").split("/")
                if len(parts) == 4:
                    source, collection = parts[2], parts[3]
                    if collection == "campaigns":
                        payload["source"] = source
                        status, item = upsert_by_id(store["ads_campaigns"], payload, "campaign_id")
                        add_audit(store, "ads_campaign_upsert", {"source": source, "campaign_id": item.get("campaign_id"), "status": status})
                        save_store(store)
                        return self.send_json(200, {"status": status, "campaign": item})
                    if collection == "insights":
                        payload["source"] = source
                        payload["id"] = payload.get("id") or str(uuid.uuid4())
                        payload["created_at"] = now_iso()
                        store["ads_insights"].insert(0, payload)
                        add_audit(store, "ads_insight_received", {"source": source, "campaign_id": payload.get("campaign_id")})
                        save_store(store)
                        return self.send_json(201, {"status": "created", "insight": payload})
                    if collection == "leads":
                        payload["source"] = source
                        payload["lead_id"] = payload.get("lead_id") or str(uuid.uuid4())
                        payload["consent_marketing"] = as_bool(payload.get("consent_marketing", True))
                        status, item = upsert_by_id(store["ads_leads"], payload, "lead_id")
                        add_audit(store, "ads_lead_upsert", {"source": source, "lead_id": item.get("lead_id"), "status": status})
                        save_store(store)
                        return self.send_json(200, {"status": status, "lead": item})

            if path == "/api/crm/recommendations/push":
                add_audit(store, "crm_recommendations_push", {"count": len(store["recommendations"]), "target": payload.get("target_crm", "crm")})
                save_store(store)
                return self.send_json(200, {"status": "pushed", "count": len(store["recommendations"]), "target_crm": payload.get("target_crm", "crm")})

            self.send_json(404, {"error": "not_found"})
        except Exception as exc:
            self.send_json(400, {"error": "bad_request", "detail": str(exc)})

    def do_DELETE(self):
        path = urlparse(self.path).path
        store = load_store()
        try:
            if path == "/api/data-sources/crm":
                counts = {
                    "customers": len(store["customers"]),
                    "orders": len(store["orders"]),
                    "events": len(store["events"]),
                }
                store["customers"] = []
                store["orders"] = []
                store["events"] = []
                add_audit(store, "crm_data_deleted", counts)
                save_store(store)
                return self.send_json(200, {"status": "deleted", "source": "crm", "counts": counts})

            if path == "/api/data-sources/meta-ads":
                counts = {
                    "campaigns": len(store["meta_ads_campaigns"]),
                    "insights": len(store["meta_ads_insights"]),
                    "leads": len(store["meta_ads_leads"]),
                }
                store["meta_ads_campaigns"] = []
                store["meta_ads_insights"] = []
                store["meta_ads_leads"] = []
                add_audit(store, "meta_ads_data_deleted", counts)
                save_store(store)
                return self.send_json(200, {"status": "deleted", "source": "meta_ads", "counts": counts})

            if path == "/api/data-sources/all":
                counts = {
                    "customers": len(store["customers"]),
                    "orders": len(store["orders"]),
                    "events": len(store["events"]),
                    "campaigns": len(store["campaigns"]),
                    "meta_ads_campaigns": len(store["meta_ads_campaigns"]),
                    "meta_ads_insights": len(store["meta_ads_insights"]),
                    "meta_ads_leads": len(store["meta_ads_leads"]),
                    "recommendations": len(store["recommendations"]),
                }
                store["customers"] = []
                store["orders"] = []
                store["events"] = []
                store["campaigns"] = []
                store["meta_ads_campaigns"] = []
                store["meta_ads_insights"] = []
                store["meta_ads_leads"] = []
                store["recommendations"] = []
                add_audit(store, "all_data_deleted", counts)
                save_store(store)
                return self.send_json(200, {"status": "deleted", "source": "all", "counts": counts})

            if path.startswith("/api/data-sources/ads/"):
                source = path.strip("/").split("/")[-1]
                counts = {
                    "campaigns": len(filter_by_source(store["ads_campaigns"], source)),
                    "insights": len(filter_by_source(store["ads_insights"], source)),
                    "leads": len(filter_by_source(store["ads_leads"], source)),
                }
                store["ads_campaigns"] = [item for item in store["ads_campaigns"] if item.get("source") != source]
                store["ads_insights"] = [item for item in store["ads_insights"] if item.get("source") != source]
                store["ads_leads"] = [item for item in store["ads_leads"] if item.get("source") != source]
                add_audit(store, "ads_source_deleted", {"source": source, **counts})
                save_store(store)
                return self.send_json(200, {"status": "deleted", "source": source, "counts": counts})

            self.send_json(404, {"error": "not_found"})
        except Exception as exc:
            self.send_json(400, {"error": "bad_request", "detail": str(exc)})


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"PersonaPulse API running at http://{HOST}:{PORT}/docs")
    server.serve_forever()
