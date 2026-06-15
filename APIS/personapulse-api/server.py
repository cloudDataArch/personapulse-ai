import json
import os
import html
import random
import re
import threading
import unicodedata
import urllib.error
import urllib.request
import uuid
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:
    psycopg = None


HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8088"))
BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
API_VERSION = "v20.0"
ASSETS_DIR = BASE_DIR / "assets"
APP_DIR = BASE_DIR / "static" / "personapulse"
STORE_KEY = "default"
MERCADO_LIVRE_ACCESS_TOKEN = (
    os.environ.get("MERCADO_LIVRE_ACCESS_TOKEN")
    or os.environ.get("MELI_ACCESS_TOKEN")
    or ""
).strip()
MERCADO_LIVRE_SEARCH_URL = "https://api.mercadolibre.com/sites/MLB/search"
MARKETPLACE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
POSTGRES_SCHEMA_LOCK = threading.Lock()
POSTGRES_SCHEMA_READY = False


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
        "powerbi_snapshot": {},
        "price_researches": [],
    }


CRM_DEMO_PRODUCTS = [
    ("Notebook Dell Inspiron", "eletronicos", 5299.90),
    ("Bicicleta MTB Carbon", "esporte", 14990.00),
    ("Carro de Bebe Travel System", "bebe", 3890.00),
    ("Perfume Amadeirado Premium", "beleza", 429.90),
    ("Smartphone Samsung Galaxy", "eletronicos", 3199.00),
    ("Cafeteira Espresso Automatica", "casa", 2499.00),
    ("Relogio Garmin Forerunner", "esporte", 2899.00),
    ("Bolsa Executiva Couro", "moda", 899.00),
]


PRICE_SOURCE_LABELS = {
    "mercadolivre.com.br": "Mercado Livre",
    "amazon.com.br": "Amazon",
    "shopee.com.br": "Shopee",
}

PRICE_SEARCH_DOMAINS = sorted(PRICE_SOURCE_LABELS)
ENTRY_EXCLUSION_TERMS = {
    "carbon", "carbono", "elite", "pro", "professional", "slx", "xt", "xtr",
    "sram", "rockshox", "sid", "full suspension", "full-suspension", "fs",
    "competition", "comp", "speed", "eletrica", "eletrica", "ebike", "e-bike",
}


def price_source_status():
    return [
        {
            "name": "Mercado Livre API",
            "status": "active" if MERCADO_LIVRE_ACCESS_TOKEN else "best_effort_public",
            "needsCredentials": not bool(MERCADO_LIVRE_ACCESS_TOKEN),
        },
        {"name": "Amazon busca publica", "status": "best_effort", "needsCredentials": False},
        {"name": "Shopee busca publica", "status": "best_effort", "needsCredentials": False},
    ]


def parse_brl_price(value, allow_plain_integer=False):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        price = float(value)
        return round(price, 2) if 10 <= price <= 500000 else None
    if isinstance(value, str):
        value = html.unescape(value)
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    pattern = r"(?:R\$\s*)?(\d{1,3}(?:\.\d{3})+,\d{2}|\d{1,6},\d{2}|\d{2,7}\.\d{2})"
    if allow_plain_integer:
        pattern = r"(?:R\$\s*)?(\d{1,3}(?:\.\d{3})+,\d{2}|\d{1,6},\d{2}|\d{2,7}\.\d{2}|\d{2,7})"
    match = re.search(pattern, text)
    if not match:
        return None
    raw = match.group(1)
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        price = float(raw)
    except ValueError:
        return None
    if price < 10 or price > 500000:
        return None
    return round(price, 2)


def normalize_position(position):
    normalized = normalize_text(position or "intermediario")
    if "lux" in normalized or "alto" in normalized or "custo" in normalized:
        return "alto_custo"
    if "prem" in normalized:
        return "premium"
    if "entrada" in normalized or "basico" in normalized:
        return "entrada"
    return "intermediario"


def normalize_text(value):
    normalized = unicodedata.normalize("NFKD", str(value or "").lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", normalized).strip()


def product_tokens(product):
    ignored = {"bicicleta", "bike", "mtb", "adulto", "adulta", "aro", "preco", "comprar", "basica", "basico"}
    tokens = re.findall(r"[a-z0-9]+", normalize_text(product))
    return [token for token in tokens if len(token) > 1 and token not in ignored]


def item_matches_product(item, product, position):
    text = normalize_text(" ".join([
        item.get("title") or "",
        item.get("snippet") or "",
        item.get("htmlSnippet") or "",
    ]))
    if not text:
        return False
    tokens = product_tokens(product)
    required_tokens = [token for token in tokens if token.isdigit() or len(token) >= 4]
    if required_tokens:
        matched = sum(1 for token in required_tokens if token in text)
        if matched < max(1, min(2, len(required_tokens))):
            return False
    if normalize_position(position) == "entrada":
        if any(term in text for term in ENTRY_EXCLUSION_TERMS):
            return False
    return True


def source_domain(item):
    for key in ("domain", "source_domain", "seller_domain", "displayLink"):
        value = item.get(key)
        if value:
            return str(value).lower().replace("www.", "")
    for key in ("url", "product_url", "link"):
        value = item.get(key)
        if value:
            hostname = urlparse(str(value)).hostname or ""
            return hostname.lower().replace("www.", "")
    source = str(item.get("source") or item.get("seller") or item.get("merchant") or "").lower()
    for domain, label in PRICE_SOURCE_LABELS.items():
        if domain in source or label.lower() in source:
            return domain
    return ""


def source_allowed(item, position):
    domain = source_domain(item)
    return any(domain == allowed or domain.endswith("." + allowed) for allowed in PRICE_SEARCH_DOMAINS)


def source_label(item):
    domain = source_domain(item)
    if domain:
        for allowed, label in PRICE_SOURCE_LABELS.items():
            if domain == allowed or domain.endswith("." + allowed):
                return label
    return item.get("source") or item.get("seller") or item.get("merchant") or item.get("displayLink") or "Google"


def price_search_keyword(product, position):
    product = str(product or "").strip()
    terms = [product, "preco", "comprar"]
    lower = product.lower()
    if "perfume" in lower and "marca" not in lower:
        terms.append("perfume")
    return " ".join(dict.fromkeys(term for term in terms if term))


def marketplace_price_queries(product, position):
    product = re.sub(r"\s+", " ", str(product or "")).strip()
    queries = [product]
    if normalize_position(position) == "entrada":
        queries.extend([
            f"{product} basica",
            f"{product} entrada",
            f"{product} barato",
        ])
    return list(dict.fromkeys(query for query in queries if query))


def marketplace_request(url, timeout=20):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": MARKETPLACE_USER_AGENT,
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        body = response.read().decode("utf-8", errors="ignore")
    if "application/json" in content_type:
        return json.loads(body)
    return body


def mercado_livre_item(result):
    price = parse_brl_price(result.get("price"), allow_plain_integer=True)
    if price is None:
        return None
    title = html.unescape(result.get("title") or "Produto")
    return {
        "marketplace": "Mercado Livre",
        "title": title,
        "price": price,
        "currency": result.get("currency_id") or "BRL",
        "url": result.get("permalink") or "",
        "domain": "mercadolivre.com.br",
        "snippet": " ".join(str(result.get(key) or "") for key in ("condition", "official_store_name", "seller_address")),
        "raw": result,
    }


def search_mercado_livre_prices(product, position):
    items = []
    errors = []
    for query in marketplace_price_queries(product, position):
        params = {"q": query, "limit": 50}
        url = MERCADO_LIVRE_SEARCH_URL + "?" + urlencode(params)
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "Accept-Language": "pt-BR,pt;q=0.9",
                    "User-Agent": MARKETPLACE_USER_AGENT,
                    **({"Authorization": f"Bearer {MERCADO_LIVRE_ACCESS_TOKEN}"} if MERCADO_LIVRE_ACCESS_TOKEN else {}),
                },
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8", errors="ignore"))
            for result in payload.get("results") or []:
                item = mercado_livre_item(result)
                if not item:
                    continue
                if item_matches_product(item, product, position):
                    items.append(item)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            errors.append({"source": "Mercado Livre API", "error": str(exc), "query": query})
    return dedupe_price_items(items), errors


def html_search_blocks(page, marker):
    parts = page.split(marker)
    return [marker + part for part in parts[1:]]


def strip_tags(value):
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def search_amazon_prices(product, position):
    items = []
    errors = []
    query = marketplace_price_queries(product, position)[0]
    url = "https://www.amazon.com.br/s?" + urlencode({"k": query})
    try:
        page = marketplace_request(url)
        blocks = html_search_blocks(page, 'data-component-type="s-search-result"')[:20]
        for block in blocks:
            title_match = re.search(r'<h2[^>]*>.*?<span[^>]*>(.*?)</span>.*?</h2>', block, flags=re.I | re.S)
            whole_match = re.search(r'<span class="a-price-whole">([^<]+)</span>', block, flags=re.I)
            frac_match = re.search(r'<span class="a-price-fraction">([^<]+)</span>', block, flags=re.I)
            link_match = re.search(r'<a[^>]+class="[^"]*a-link-normal[^"]*"[^>]+href="([^"]+)"', block, flags=re.I)
            if not (title_match and whole_match):
                continue
            title = strip_tags(title_match.group(1))
            raw_price = whole_match.group(1)
            if frac_match:
                raw_price = f"{raw_price},{frac_match.group(1)}"
            price = parse_brl_price(raw_price)
            if price is None:
                continue
            path = html.unescape(link_match.group(1)) if link_match else ""
            item = {
                "marketplace": "Amazon",
                "title": title,
                "price": price,
                "currency": "BRL",
                "url": "https://www.amazon.com.br" + path if path.startswith("/") else path,
                "domain": "amazon.com.br",
                "snippet": strip_tags(block[:1000]),
                "raw": {},
            }
            if item_matches_product(item, product, position):
                items.append(item)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        errors.append({"source": "Amazon busca publica", "error": str(exc), "query": query})
    return dedupe_price_items(items), errors


def search_shopee_prices(product, position):
    items = []
    errors = []
    query = marketplace_price_queries(product, position)[0]
    url = "https://shopee.com.br/search?" + urlencode({"keyword": query})
    try:
        page = marketplace_request(url)
        for match in re.finditer(r'"name"\s*:\s*"([^"]{8,180})".{0,800}?"price"\s*:\s*(\d+)', page, flags=re.I | re.S):
            title = html.unescape(match.group(1)).encode("utf-8").decode("unicode_escape", errors="ignore")
            raw_price = float(match.group(2))
            price = raw_price / 100000 if raw_price > 1000000 else raw_price
            item = {
                "marketplace": "Shopee",
                "title": title,
                "price": round(price, 2),
                "currency": "BRL",
                "url": url,
                "domain": "shopee.com.br",
                "snippet": title,
                "raw": {},
            }
            if item_matches_product(item, product, position):
                items.append(item)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        errors.append({"source": "Shopee busca publica", "error": str(exc), "query": query})
    return dedupe_price_items(items), errors


def dedupe_price_items(items):
    deduped = []
    seen = set()
    for item in sorted(items, key=lambda entry: (entry.get("url", ""), entry.get("price", 0))):
        key = (item.get("url"), round(item.get("price", 0), 2))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def search_marketplace_prices(product, position):
    items = []
    errors = []
    for search_fn in (search_mercado_livre_prices, search_amazon_prices, search_shopee_prices):
        found, source_errors = search_fn(product, position)
        items.extend(found)
        errors.extend(source_errors)
    return dedupe_price_items(items), errors


def percentile_value(prices, percentile):
    prices = sorted(prices)
    if not prices:
        return 0
    if len(prices) == 1:
        return prices[0]
    index = (len(prices) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(prices) - 1)
    weight = index - lower
    return prices[lower] * (1 - weight) + prices[upper] * weight


def price_bucket(prices, low_percentile, high_percentile, min_items=1):
    low = percentile_value(prices, low_percentile)
    high = percentile_value(prices, high_percentile)
    bucket_prices = [price for price in prices if low <= price <= high]
    if len(bucket_prices) < min_items:
        center = (low_percentile + high_percentile) / 2
        ranked = sorted(prices, key=lambda price: abs(price - percentile_value(prices, center)))
        bucket_prices = sorted(ranked[:min(min_items, len(prices))])
    if not bucket_prices:
        bucket_prices = [percentile_value(prices, (low_percentile + high_percentile) / 2)]
    avg = sum(bucket_prices) / len(bucket_prices)
    return {"low": round(min(bucket_prices)), "avg": round(avg), "high": round(max(bucket_prices)), "items": len(bucket_prices)}


def price_buckets(prices):
    basic_min_items = min(2, len(prices))
    return {
        "basico": price_bucket(prices, 0.00, 0.40, min_items=basic_min_items),
        "intermediario": price_bucket(prices, 0.25, 0.70, min_items=min(2, len(prices))),
        "premium": price_bucket(prices, 0.55, 0.90, min_items=min(2, len(prices))),
        "alto_custo": price_bucket(prices, 0.75, 1.00, min_items=min(2, len(prices))),
    }


def selected_bucket_key(position):
    normalized = normalize_position(position)
    if normalized == "entrada":
        return "basico"
    if normalized == "premium":
        return "premium"
    if normalized == "alto_custo":
        return "alto_custo"
    return "intermediario"


def build_pricing_result(product, position, items, source, errors=None):
    filtered = sorted(remove_price_outliers(items), key=lambda item: item["price"])
    prices = sorted(item["price"] for item in filtered)
    if len(prices) < 3:
        return insufficient_pricing_result(
            product,
            position,
            (errors or []) + [{"source": source, "error": "Menos de 3 precos confiaveis foram encontrados nos marketplaces permitidos."}],
            observed_items=len(prices),
        )
    buckets = price_buckets(prices)
    target = buckets[selected_bucket_key(position)]["avg"]
    return {
        "id": str(uuid.uuid4()),
        "created_at": now_iso(),
        "product": product,
        "position": position,
        "source": source,
        "sourceStatus": price_source_status(),
        "ticketMedio": target,
        "priceSuggestions": [
            {"label": "Basico", "value": buckets["basico"]["avg"], "reason": f"Faixa de entrada observada nos marketplaces: R$ {buckets['basico']['low']} a R$ {buckets['basico']['high']}."},
            {"label": "Intermediario", "value": buckets["intermediario"]["avg"], "reason": f"Faixa central de mercado: R$ {buckets['intermediario']['low']} a R$ {buckets['intermediario']['high']}."},
            {"label": "Premium", "value": buckets["premium"]["avg"], "reason": f"Faixa superior com maior valor percebido: R$ {buckets['premium']['low']} a R$ {buckets['premium']['high']}."},
            {"label": "Alto custo", "value": buckets["alto_custo"]["avg"], "reason": f"Topo da distribuicao encontrada: R$ {buckets['alto_custo']['low']} a R$ {buckets['alto_custo']['high']}."},
        ],
        "range": {"low": round(min(prices)), "high": round(max(prices))},
        "priceBuckets": buckets,
        "attrs": [
            "precos encontrados em marketplaces permitidos",
            "fontes limitadas a Mercado Livre, Amazon e Shopee",
            "resultados incompatíveis com o produto foram descartados",
            "outliers removidos antes do calculo",
            "ticket medio escolhido pela faixa de posicionamento",
        ],
        "sources": [
            {
                "title": f"{item['marketplace']}: {item['title']}",
                "price": item["price"],
                "url": item["url"],
                "domain": item.get("domain") or item.get("marketplace", ""),
            }
            for item in filtered[:8]
        ],
        "observedItems": len(filtered),
        "errors": errors or [],
    }


def marketplace_pricing(product, position):
    items, errors = search_marketplace_prices(product, position)
    if not items:
        errors.append({"source": "Marketplaces permitidos", "error": "Nenhum preco foi encontrado em Mercado Livre, Amazon ou Shopee."})
        return None, errors
    return build_pricing_result(
        product,
        position,
        items,
        "Mercado Livre + Amazon + Shopee",
        errors,
    ), errors


def insufficient_pricing_result(product, position, errors, observed_items=0):
    return {
        "id": str(uuid.uuid4()),
        "created_at": now_iso(),
        "product": product,
        "position": position,
        "source": "Mercado Livre + Amazon + Shopee. Dados insuficientes para calcular ticket medio confiavel.",
        "sourceStatus": price_source_status(),
        "ticketMedio": 0,
        "priceSuggestions": [
            {"label": "Basico", "value": 0, "reason": "Aguardando pelo menos 3 precos reais observados nos marketplaces permitidos."},
            {"label": "Intermediario", "value": 0, "reason": "Sem calculo automatico para evitar ticket medio falso."},
            {"label": "Premium", "value": 0, "reason": "Informe produto, marca e modelo para melhorar a busca."},
            {"label": "Alto custo", "value": 0, "reason": "Sem referencias suficientes para topo de mercado."},
        ],
        "range": {"low": 0, "high": 0},
        "priceBuckets": {
            "basico": {"low": 0, "avg": 0, "high": 0, "items": 0},
            "intermediario": {"low": 0, "avg": 0, "high": 0, "items": 0},
            "premium": {"low": 0, "avg": 0, "high": 0, "items": 0},
            "alto_custo": {"low": 0, "avg": 0, "high": 0, "items": 0},
        },
        "attrs": [
            "sem estimativa inventada",
            "calculo bloqueado por falta de precos reais suficientes",
            "use produto, marca e modelo para melhorar a busca",
        ],
        "sources": [],
        "observedItems": observed_items,
        "errors": errors,
    }


def pricing_reference(product, position):
    marketplace_result, errors = marketplace_pricing(product, position)
    if marketplace_result:
        return marketplace_result
    return insufficient_pricing_result(product, position, errors)


def remove_price_outliers(items):
    prices = sorted(item["price"] for item in items if item.get("price"))
    if len(prices) < 8:
        return items
    low_limit = percentile_value(prices, 0.05) * 0.7
    high_limit = percentile_value(prices, 0.95) * 1.3
    return [item for item in items if low_limit <= item["price"] <= high_limit]


def powerbi_summary_defaults():
    return {
        "updated_at": now_iso(),
        "clientes_analisados": 0,
        "campanhas": 0,
        "conversoes": 0,
        "receita_atribuida": 0,
        "gasto_real": 0,
        "roi_real_percentual": 0,
        "conformidade_lgpd_percentual": 0,
        "ticket_medio": 0,
        "produto_mais_recorrente": "",
        "canal_mais_recorrente": "",
        "fontes": {
            "csv_clientes": 0,
            "crm_clientes": 0,
            "meta_ads_clientes": 0,
            "meta_ads_leads": 0,
            "outros_ads_clientes": 0,
            "outros_ads_leads": 0,
            "crm_pedidos": 0,
            "meta_ads_campanhas": 0,
            "outros_ads_campanhas": 0,
        },
    }


def executive_summary(store):
    snapshot = store.get("powerbi_snapshot") or {}
    summary = snapshot.get("summary") or {}
    if summary:
        defaults = powerbi_summary_defaults()
        fontes = {**defaults["fontes"], **(summary.get("fontes") or {})}
        return {
            **defaults,
            **summary,
            "fontes": fontes,
            "updated_at": snapshot.get("updated_at") or summary.get("updated_at") or now_iso(),
        }

    customers = store["customers"] + store["meta_ads_leads"] + store["ads_leads"]
    campaigns = store["campaigns"] + store["meta_ads_campaigns"] + store["ads_campaigns"]
    orders_revenue = sum(float(order.get("value") or 0) for order in store["orders"])
    media_revenue = sum(
        float(item.get("purchase_value") or item.get("revenue") or item.get("conversion_value") or 0)
        for item in store["meta_ads_insights"] + store["ads_insights"]
    )
    spend = sum(
        float(item.get("spend") or item.get("cost") or item.get("cost_micros") or 0)
        for item in store["meta_ads_insights"] + store["ads_insights"]
    )
    if spend > 100000:
        spend = spend / 1000000
    revenue = orders_revenue + media_revenue
    ticket_medio = round(orders_revenue / len(store["orders"]), 2) if store["orders"] else 0
    conversions = sum(
        int(float(item.get("conversions") or item.get("purchases") or item.get("leads") or 0))
        for item in store["meta_ads_insights"] + store["ads_insights"]
    )
    consent = sum(1 for customer in customers if as_bool(customer.get("consent_marketing")))
    roi = round(((revenue - spend) / spend) * 100, 2) if spend else 0
    summary = powerbi_summary_defaults()
    summary.update({
        "clientes_analisados": len(customers),
        "campanhas": len(campaigns),
        "conversoes": conversions,
        "receita_atribuida": round(revenue, 2),
        "gasto_real": round(spend, 2),
        "roi_real_percentual": roi,
        "conformidade_lgpd_percentual": round((consent / len(customers)) * 100, 2) if customers else 0,
        "ticket_medio": ticket_medio,
        "fontes": {
            **summary["fontes"],
            "crm_clientes": len(store["customers"]),
            "meta_ads_leads": len(store["meta_ads_leads"]),
            "outros_ads_leads": len(store["ads_leads"]),
            "crm_pedidos": len(store["orders"]),
            "meta_ads_campanhas": len(store["meta_ads_campaigns"]),
            "outros_ads_campanhas": len(store["ads_campaigns"]),
        },
    })
    return summary


def powerbi_customers(store):
    snapshot = store.get("powerbi_snapshot") or {}
    customers = snapshot.get("customers")
    if isinstance(customers, list):
        return customers
    rows = []
    orders_by_customer = {}
    for order in store["orders"]:
        orders_by_customer.setdefault(order.get("external_customer_id"), []).append(order)
    for customer in store["customers"]:
        customer_orders = orders_by_customer.get(customer.get("external_id"), [])
        last_order = customer_orders[-1] if customer_orders else {}
        rows.append({
            "cliente_id": customer.get("external_id"),
            "nome": customer.get("name"),
            "email": customer.get("email"),
            "telefone": customer.get("phone"),
            "cidade": customer.get("city"),
            "origem": customer.get("source", "CRM"),
            "consentimento_marketing": as_bool(customer.get("consent_marketing")),
            "produto": last_order.get("product_name", ""),
            "valor": float(last_order.get("value") or 0),
            "data_compra": last_order.get("purchased_at", ""),
        })
    return rows


def powerbi_campaigns(store):
    snapshot = store.get("powerbi_snapshot") or {}
    campaigns = snapshot.get("campaigns")
    if isinstance(campaigns, list):
        return campaigns
    rows = []
    for campaign in store["campaigns"] + store["meta_ads_campaigns"] + store["ads_campaigns"]:
        rows.append({
            "campanha_id": campaign.get("id") or campaign.get("campaign_id"),
            "campanha": campaign.get("name") or campaign.get("campaign_name") or campaign.get("title"),
            "fonte": campaign.get("source") or ("Meta Ads" if campaign in store["meta_ads_campaigns"] else "PersonaPulse"),
            "status": campaign.get("status", ""),
            "canal": campaign.get("channel", ""),
            "data_inicio": campaign.get("start_date") or campaign.get("date_start") or "",
            "data_fim": campaign.get("end_date") or campaign.get("date_stop") or "",
        })
    return rows


def powerbi_sources(store):
    snapshot = store.get("powerbi_snapshot") or {}
    sources = snapshot.get("sources")
    if isinstance(sources, list):
        return sources
    summary = executive_summary(store)
    fontes = summary.get("fontes", {})
    return [{"fonte": key, "quantidade": value} for key, value in fontes.items()]


def seed_crm_demo(store, reset=False, customer_count=120):
    if reset:
        store["customers"] = []
        store["orders"] = []
        store["events"] = []
    if store["customers"] or store["orders"] or store["events"]:
        return {
            "status": "preserved",
            "customers": len(store["customers"]),
            "orders": len(store["orders"]),
            "events": len(store["events"]),
        }

    rng = random.Random(9126)
    first_names = ["Ana", "Bruno", "Carla", "Diego", "Elaine", "Fabio", "Gabriela", "Henrique", "Isabela", "Joao", "Larissa", "Marcos"]
    last_names = ["Silva", "Santos", "Oliveira", "Souza", "Lima", "Costa", "Pereira", "Ferreira", "Almeida", "Ribeiro"]
    cities = ["Sao Paulo", "Rio de Janeiro", "Belo Horizonte", "Curitiba", "Campinas", "Brasilia", "Salvador", "Recife"]
    sources = ["hubspot", "rd_station", "pipedrive", "salesforce", "crm_demo"]
    event_types = ["product_view", "cart_add", "checkout_start", "email_click", "ad_click"]
    channels = ["E-commerce proprio", "Marketplace", "WhatsApp Vendas", "Loja fisica"]
    contact_channels = ["E-mail", "WhatsApp", "Instagram", "TikTok", "LinkedIn", "Facebook"]
    today = date.today()

    order_count = 0
    event_count = 0
    for index in range(1, customer_count + 1):
        first = rng.choice(first_names)
        last = rng.choice(last_names)
        external_id = f"crm_demo_{index:04d}"
        customer = {
            "external_id": external_id,
            "name": f"{first} {last}",
            "email": f"{first.lower()}.{last.lower()}.{index}@crm-demo.com",
            "phone": f"+55119{rng.randint(10000000, 99999999)}",
            "whatsapp": f"+55119{rng.randint(10000000, 99999999)}",
            "instagram": f"@{first.lower()}.{last.lower()}.{index}",
            "tiktok": f"@{first.lower()}{last.lower()}{index}",
            "linkedin": f"https://www.linkedin.com/in/{first.lower()}-{last.lower()}-{index}",
            "facebook": f"https://www.facebook.com/{first.lower()}.{last.lower()}.{index}",
            "preferred_contact_channel": rng.choice(contact_channels),
            "city": rng.choice(cities),
            "consent_marketing": rng.random() < 0.9,
            "source": rng.choice(sources),
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        store["customers"].append(customer)

        for _ in range(rng.randint(1, 4)):
            product, category, avg_price = rng.choice(CRM_DEMO_PRODUCTS)
            order_count += 1
            value = round(avg_price * rng.uniform(0.84, 1.16), 2)
            store["orders"].append({
                "id": str(uuid.uuid4()),
                "external_customer_id": external_id,
                "order_id": f"CRM-PED-{order_count:05d}",
                "product_name": product,
                "category": category,
                "store": rng.choice(channels),
                "value": value,
                "purchased_at": (today - timedelta(days=rng.randint(0, 180))).isoformat(),
                "created_at": now_iso(),
            })

        for _ in range(rng.randint(2, 7)):
            product, _, _ = rng.choice(CRM_DEMO_PRODUCTS)
            event_count += 1
            store["events"].append({
                "id": str(uuid.uuid4()),
                "external_customer_id": external_id,
                "event_type": rng.choice(event_types),
                "product_name": product,
                "occurred_at": (datetime.now() - timedelta(hours=rng.randint(0, 720))).isoformat(timespec="seconds"),
                "created_at": now_iso(),
            })

    add_audit(store, "crm_demo_seeded", {
        "customers": len(store["customers"]),
        "orders": len(store["orders"]),
        "events": len(store["events"]),
    })
    return {
        "status": "seeded",
        "customers": len(store["customers"]),
        "orders": len(store["orders"]),
        "events": len(store["events"]),
    }


def using_postgres():
    return bool(DATABASE_URL)


def persistence_status():
    if using_postgres():
        return "postgresql"
    return "database_missing"


def postgres_connection():
    if psycopg is None:
        raise RuntimeError("DATABASE_URL foi configurado, mas psycopg[binary] nao esta instalado.")
    return psycopg.connect(DATABASE_URL)


def ensure_postgres_schema():
    global POSTGRES_SCHEMA_READY
    if POSTGRES_SCHEMA_READY:
        return
    with POSTGRES_SCHEMA_LOCK:
        if POSTGRES_SCHEMA_READY:
            return
        _ensure_postgres_schema_unlocked()
        POSTGRES_SCHEMA_READY = True


def _ensure_postgres_schema_unlocked():
    with postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS app_store (
                    key TEXT PRIMARY KEY,
                    payload JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS app_audit (
                    id UUID PRIMARY KEY,
                    action TEXT NOT NULL,
                    details JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            for migration in sorted((BASE_DIR / "migrations").glob("*.sql")):
                cur.execute(migration.read_text(encoding="utf-8"))
        conn.commit()


def load_store_from_postgres():
    ensure_postgres_schema()
    with postgres_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT payload FROM app_store WHERE key = %s", (STORE_KEY,))
            row = cur.fetchone()
            if not row:
                store = empty_store()
                save_store_to_postgres(store)
                return store
            store = row["payload"]
    for key, value in empty_store().items():
        store.setdefault(key, value)
    return store


def save_store_to_postgres(store):
    ensure_postgres_schema()
    with postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app_store (key, payload, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (key)
                DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW()
                """,
                (STORE_KEY, Jsonb(store)),
            )
            sync_relational_store(cur, store)
        conn.commit()


def item_source(item, default):
    return str(item.get("source") or item.get("origem") or item.get("origem_dados") or default)


def item_text(item, keys, default=""):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def item_float(item, keys, default=0):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            try:
                number = float(value)
                if key == "cost_micros" or number > 1000000 and "cost" in key:
                    return number / 1000000
                return number
            except (TypeError, ValueError):
                continue
    return default


def parse_money_value(value):
    if value in (None, ""):
        return 0
    text = str(value)
    cleaned = "".join(char for char in text if char.isdigit() or char in ",.-")
    if "." in cleaned and "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except (TypeError, ValueError):
        return 0


def item_int(item, keys, default=0):
    return int(item_float(item, keys, default))


def item_date(item, keys):
    value = item_text(item, keys)
    return value[:10] if value else None


def item_timestamp(value):
    if value in (None, ""):
        return None
    return str(value)


def sync_relational_store(cur, store):
    cur.execute("""
        TRUNCATE
            app.campaign_metrics,
            app.recommendations,
            app.events,
            app.orders,
            app.campaigns,
            app.customers,
            app.price_researches,
            bi.powerbi_snapshots,
            audit.audit_logs
        RESTART IDENTITY CASCADE
    """)

    for source_key, config in store.get("connector_configs", {}).items():
        public_config = public_connector_config(config)
        cur.execute(
            """
            INSERT INTO integrations.data_sources (
                source_key, source_name, source_type, status, last_sync_at,
                config_public, updated_at
            )
            VALUES (%s, %s, %s, %s, %s::timestamptz, %s, NOW())
            ON CONFLICT (source_key)
            DO UPDATE SET
                status = EXCLUDED.status,
                last_sync_at = EXCLUDED.last_sync_at,
                config_public = EXCLUDED.config_public,
                updated_at = NOW()
            """,
            (
                source_key,
                item_text(config, ["name", "source_name"], source_key.replace("_", " ").title()),
                item_text(config, ["source_type", "type"], "ads" if "ads" in source_key else source_key),
                item_text(config, ["status"], "configured"),
                item_timestamp(config.get("last_sync_at") or config.get("updated_at")),
                Jsonb(public_config),
            ),
        )
        cur.execute(
            """
            INSERT INTO integrations.connector_configs (
                source_key, client_id, account_id, scopes, status,
                secret_ref, token_ref, raw_payload, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (source_key)
            DO UPDATE SET
                client_id = EXCLUDED.client_id,
                account_id = EXCLUDED.account_id,
                scopes = EXCLUDED.scopes,
                status = EXCLUDED.status,
                secret_ref = EXCLUDED.secret_ref,
                token_ref = EXCLUDED.token_ref,
                raw_payload = EXCLUDED.raw_payload,
                updated_at = NOW()
            """,
            (
                source_key,
                item_text(config, ["client_id", "app_id"]),
                item_text(config, ["account_id", "ad_account_id", "customer_id"]),
                ",".join(config.get("scopes") or []) if isinstance(config.get("scopes"), list) else item_text(config, ["scopes"]),
                item_text(config, ["status"], "configured"),
                "stored_in_app_store" if config.get("client_secret") else None,
                "stored_in_app_store" if config.get("access_token") or config.get("refresh_token") else None,
                Jsonb(public_config),
            ),
        )

    customer_map = {}
    customer_rows = []
    for customer in store.get("customers", []):
        customer_rows.append((customer, item_source(customer, "crm")))
    for lead in store.get("meta_ads_leads", []):
        customer_rows.append((lead, "meta_ads"))
    for lead in store.get("ads_leads", []):
        customer_rows.append((lead, item_source(lead, "ads")))

    for customer, source in customer_rows:
        external_id = item_text(customer, ["external_id", "lead_id", "id", "email"], str(uuid.uuid4()))
        cur.execute(
            """
            INSERT INTO app.customers (
                external_id, source, name, email, phone, city, state, country,
                whatsapp, instagram, tiktok, linkedin, facebook, preferred_contact_channel,
                consent_marketing, consent_source, behavioral_segment,
                intent_score, status, raw_payload, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s::timestamptz, NOW()), COALESCE(%s::timestamptz, NOW()))
            ON CONFLICT (source, external_id)
            DO UPDATE SET
                name = EXCLUDED.name,
                email = EXCLUDED.email,
                phone = EXCLUDED.phone,
                city = EXCLUDED.city,
                state = EXCLUDED.state,
                country = EXCLUDED.country,
                whatsapp = EXCLUDED.whatsapp,
                instagram = EXCLUDED.instagram,
                tiktok = EXCLUDED.tiktok,
                linkedin = EXCLUDED.linkedin,
                facebook = EXCLUDED.facebook,
                preferred_contact_channel = EXCLUDED.preferred_contact_channel,
                consent_marketing = EXCLUDED.consent_marketing,
                consent_source = EXCLUDED.consent_source,
                behavioral_segment = EXCLUDED.behavioral_segment,
                intent_score = EXCLUDED.intent_score,
                status = EXCLUDED.status,
                raw_payload = EXCLUDED.raw_payload,
                updated_at = NOW()
            RETURNING id
            """,
            (
                external_id,
                source,
                item_text(customer, ["name", "nome", "full_name"], "Cliente sem nome"),
                item_text(customer, ["email"]),
                item_text(customer, ["phone", "telefone"]),
                item_text(customer, ["city", "cidade"]),
                item_text(customer, ["state", "estado"]),
                item_text(customer, ["country", "pais"], "BR"),
                item_text(customer, ["whatsapp", "telefone_whatsapp", "celular"]),
                item_text(customer, ["instagram", "perfil_instagram", "insta"]),
                item_text(customer, ["tiktok", "perfil_tiktok"]),
                item_text(customer, ["linkedin", "perfil_linkedin"]),
                item_text(customer, ["facebook", "perfil_facebook"]),
                item_text(customer, ["preferred_contact_channel", "canal_preferido_contato", "canal_preferido", "canal"]),
                as_bool(customer.get("consent_marketing") if "consent_marketing" in customer else customer.get("consentimento_marketing")),
                item_text(customer, ["consent_source", "origem_consentimento"]),
                item_text(customer, ["behavioral_segment", "segmento", "status"]),
                item_float(customer, ["intent_score", "score_intencao", "score"]),
                item_text(customer, ["status"]),
                Jsonb(customer),
                item_timestamp(customer.get("created_at")),
                item_timestamp(customer.get("updated_at") or customer.get("created_at")),
            ),
        )
        customer_id = cur.fetchone()[0]
        customer_map[external_id] = customer_id
        if customer.get("email"):
            customer_map[str(customer.get("email"))] = customer_id

    for order in store.get("orders", []):
        external_customer_id = item_text(order, ["external_customer_id", "customer_external_id", "cliente_id"])
        cur.execute(
            """
            INSERT INTO app.orders (
                external_order_id, customer_id, external_customer_id, source,
                product_name, category, store_name, channel, value, purchased_at,
                raw_payload, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::timestamptz, %s, COALESCE(%s::timestamptz, NOW()))
            """,
            (
                item_text(order, ["order_id", "external_order_id", "id"], str(uuid.uuid4())),
                customer_map.get(external_customer_id),
                external_customer_id,
                item_source(order, "crm"),
                item_text(order, ["product_name", "produto"], "Produto nao informado"),
                item_text(order, ["category", "categoria"]),
                item_text(order, ["store", "store_name", "onde"]),
                item_text(order, ["channel", "canal", "store"]),
                item_float(order, ["value", "valor"]),
                item_timestamp(order.get("purchased_at") or order.get("data_compra")),
                Jsonb(order),
                item_timestamp(order.get("created_at")),
            ),
        )

    for event in store.get("events", []):
        external_customer_id = item_text(event, ["external_customer_id", "customer_external_id", "cliente_id"])
        cur.execute(
            """
            INSERT INTO app.events (
                external_event_id, customer_id, external_customer_id, source,
                event_type, product_name, channel, occurred_at, raw_payload, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::timestamptz, %s, COALESCE(%s::timestamptz, NOW()))
            """,
            (
                item_text(event, ["event_id", "external_event_id", "id"], str(uuid.uuid4())),
                customer_map.get(external_customer_id),
                external_customer_id,
                item_source(event, "crm"),
                item_text(event, ["event_type", "tipo"], "event"),
                item_text(event, ["product_name", "produto"]),
                item_text(event, ["channel", "canal"]),
                item_timestamp(event.get("occurred_at") or event.get("created_at")),
                Jsonb(event),
                item_timestamp(event.get("created_at")),
            ),
        )

    campaign_map = {}

    def insert_campaign(campaign, default_source):
        source = item_source(campaign, default_source)
        external_id = item_text(campaign, ["campaign_id", "external_campaign_id", "id"], str(uuid.uuid4()))
        cur.execute(
            """
            INSERT INTO app.campaigns (
                external_campaign_id, source, name, status, channel, segment,
                product_name, tone, creative_text, start_date, end_date,
                raw_payload, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::date, %s::date, %s, COALESCE(%s::timestamptz, NOW()), COALESCE(%s::timestamptz, NOW()))
            ON CONFLICT (source, external_campaign_id)
            DO UPDATE SET
                name = EXCLUDED.name,
                status = EXCLUDED.status,
                channel = EXCLUDED.channel,
                segment = EXCLUDED.segment,
                product_name = EXCLUDED.product_name,
                tone = EXCLUDED.tone,
                creative_text = EXCLUDED.creative_text,
                start_date = EXCLUDED.start_date,
                end_date = EXCLUDED.end_date,
                raw_payload = EXCLUDED.raw_payload,
                updated_at = NOW()
            RETURNING id
            """,
            (
                external_id,
                source,
                item_text(campaign, ["name", "campaign_name", "title"], "Campanha sem nome"),
                item_text(campaign, ["status"], "draft"),
                item_text(campaign, ["channel", "canal"]),
                item_text(campaign, ["segment", "segmento", "segment_name"]),
                item_text(campaign, ["product_name", "produto"]),
                item_text(campaign, ["tone", "tom"]),
                item_text(campaign, ["body", "creative_text", "texto"]),
                item_date(campaign, ["start_date", "date_start", "start_time"]),
                item_date(campaign, ["end_date", "date_stop", "stop_time"]),
                Jsonb(campaign),
                item_timestamp(campaign.get("created_at")),
                item_timestamp(campaign.get("updated_at") or campaign.get("created_at")),
            ),
        )
        campaign_id = cur.fetchone()[0]
        campaign_map[(source, external_id)] = campaign_id
        campaign_map[external_id] = campaign_id
        return campaign_id

    for campaign in store.get("campaigns", []):
        insert_campaign(campaign, "personapulse")
    for campaign in store.get("meta_ads_campaigns", []):
        insert_campaign(campaign, "meta_ads")
    for campaign in store.get("ads_campaigns", []):
        insert_campaign(campaign, item_source(campaign, "ads"))

    for insight in store.get("meta_ads_insights", []) + store.get("ads_insights", []):
        source = item_source(insight, "meta_ads" if insight in store.get("meta_ads_insights", []) else "ads")
        external_id = item_text(insight, ["campaign_id", "external_campaign_id", "id"], str(uuid.uuid4()))
        campaign_id = campaign_map.get((source, external_id)) or campaign_map.get(external_id)
        if not campaign_id:
            campaign_id = insert_campaign({
                "campaign_id": external_id,
                "source": source,
                "name": item_text(insight, ["campaign_name", "name"], f"Campanha {external_id}"),
                "status": "active",
            }, source)
        cur.execute(
            """
            INSERT INTO app.campaign_metrics (
                campaign_id, external_campaign_id, source, metric_date,
                impressions, clicks, conversions, leads, spend, revenue,
                raw_payload, created_at
            )
            VALUES (%s, %s, %s, COALESCE(%s::date, CURRENT_DATE), %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (source, external_campaign_id, metric_date)
            DO UPDATE SET
                impressions = EXCLUDED.impressions,
                clicks = EXCLUDED.clicks,
                conversions = EXCLUDED.conversions,
                leads = EXCLUDED.leads,
                spend = EXCLUDED.spend,
                revenue = EXCLUDED.revenue,
                raw_payload = EXCLUDED.raw_payload
            """,
            (
                campaign_id,
                external_id,
                source,
                item_date(insight, ["date", "metric_date", "date_start", "created_at"]),
                item_int(insight, ["impressions"]),
                item_int(insight, ["clicks"]),
                item_int(insight, ["conversions", "purchases"]),
                item_int(insight, ["leads"]),
                item_float(insight, ["spend", "cost", "cost_micros"]),
                item_float(insight, ["purchase_value", "revenue", "conversion_value"]),
                Jsonb(insight),
            ),
        )

    for recommendation in store.get("recommendations", []):
        cur.execute(
            """
            INSERT INTO app.recommendations (
                recommendation_type, title, description, priority, status, raw_payload, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, COALESCE(%s::timestamptz, NOW()))
            """,
            (
                item_text(recommendation, ["type", "recommendation_type"], "general"),
                item_text(recommendation, ["title"], "Recomendacao"),
                item_text(recommendation, ["description", "body"]),
                item_int(recommendation, ["priority"]),
                item_text(recommendation, ["status"], "open"),
                Jsonb(recommendation),
                item_timestamp(recommendation.get("created_at")),
            ),
        )

    for research in store.get("price_researches", []):
        suggestions = research.get("priceSuggestions") or []
        suggestion_by_label = {item.get("label", ""): item for item in suggestions}
        def suggestion_value(*labels):
            for label in labels:
                value = item_float(suggestion_by_label.get(label, {}), ["value"])
                if value:
                    return value
            return 0

        cur.execute(
            """
            INSERT INTO app.price_researches (
                id, product_name, positioning, source, ticket_medio,
                price_competitive, price_recommended, price_premium,
                range_low, range_high, observed_items, sources, raw_payload, created_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                COALESCE(%s::timestamptz, NOW())
            )
            ON CONFLICT (id) DO NOTHING
            """,
            (
                research.get("id") or str(uuid.uuid4()),
                item_text(research, ["product", "product_name"], "Produto"),
                item_text(research, ["position", "positioning"]),
                item_text(research, ["source"], "Google Shopping"),
                item_float(research, ["ticketMedio", "ticket_medio"]),
                suggestion_value("Preco minimo observado", "Preco competitivo"),
                suggestion_value("Ticket medio sugerido", "Preco recomendado"),
                suggestion_value("Preco alto observado", "Preco premium"),
                item_float(research.get("range") or {}, ["low"]),
                item_float(research.get("range") or {}, ["high"]),
                item_int(research, ["observedItems", "observed_items"]),
                Jsonb(research.get("sources") or []),
                Jsonb(research),
                item_timestamp(research.get("created_at")),
            ),
        )

    snapshot = store.get("powerbi_snapshot") or {}
    if snapshot:
        cur.execute(
            """
            INSERT INTO bi.powerbi_snapshots (
                snapshot_key, summary, customers, campaigns, sources, created_at
            )
            VALUES (%s, %s, %s, %s, %s, COALESCE(%s::timestamptz, NOW()))
            """,
            (
                STORE_KEY,
                Jsonb(snapshot.get("summary") or {}),
                Jsonb(snapshot.get("customers") or []),
                Jsonb(snapshot.get("campaigns") or []),
                Jsonb(snapshot.get("sources") or []),
                item_timestamp(snapshot.get("updated_at")),
            ),
        )

    for entry in store.get("audit_logs", []):
        cur.execute(
            """
            INSERT INTO audit.audit_logs (id, action, entity_type, entity_id, details, created_at)
            VALUES (%s, %s, %s, %s, %s, COALESCE(%s::timestamptz, NOW()))
            ON CONFLICT (id) DO NOTHING
            """,
            (
                entry.get("id") or str(uuid.uuid4()),
                item_text(entry, ["action"], "event"),
                item_text(entry, ["entity_type"]),
                item_text(entry, ["entity_id"]),
                Jsonb(entry.get("details") or {}),
                item_timestamp(entry.get("created_at")),
            ),
        )


STORE_COUNT_KEYS = {
    "customers": "customers",
    "orders": "orders",
    "events": "events",
    "campaigns": "campaigns",
    "meta_ads_campaigns": "meta_ads_campaigns",
    "meta_ads_insights": "meta_ads_insights",
    "meta_ads_leads": "meta_ads_leads",
    "ads_campaigns": "ads_campaigns",
    "ads_insights": "ads_insights",
    "ads_leads": "ads_leads",
    "price_researches": "price_researches",
}


RELATIONAL_COUNT_TABLES = [
    "app.customers",
    "app.orders",
    "app.events",
    "app.campaigns",
    "app.campaign_metrics",
    "app.price_researches",
    "app.recommendations",
    "integrations.data_sources",
    "integrations.connector_configs",
    "bi.powerbi_snapshots",
    "audit.audit_logs",
    "dba.clientes",
    "dba.contatos_clientes",
    "dba.pedidos",
    "dba.eventos",
    "dba.campanhas",
    "dba.metricas_campanhas",
    "dba.recomendacoes",
    "dba.pesquisas_precos",
]


def store_counts(store):
    return {label: len(store.get(key, [])) for label, key in STORE_COUNT_KEYS.items()}


def relational_counts():
    if not using_postgres():
        return {}
    ensure_postgres_schema()
    counts = {}
    with postgres_connection() as conn:
        with conn.cursor() as cur:
            for table_name in RELATIONAL_COUNT_TABLES:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                    counts[table_name] = cur.fetchone()[0]
                except Exception as exc:
                    counts[table_name] = {"error": str(exc)}
                    conn.rollback()
    return counts


def database_status_payload(store):
    payload = {
        "status": "ok",
        "service": "personapulse-api",
        "persistence": persistence_status(),
        "database_url_configured": using_postgres(),
        "store_counts": store_counts(store),
        "relational_counts": {},
        "time": now_iso(),
    }
    if using_postgres():
        try:
            payload["relational_counts"] = relational_counts()
        except Exception as exc:
            payload["status"] = "partial"
            payload["relational_error"] = str(exc)
    return payload


def source_status_entry(key, name, source_type, records, campaigns=0, config=None):
    config = config or {}
    has_credentials = bool(
        config.get("access_token")
        or config.get("refresh_token")
        or config.get("client_id")
        or config.get("account_id")
    )
    if records or campaigns:
        status = "active"
    elif config.get("status") in {"synced", "configured"} or has_credentials:
        status = "configured"
    elif key in {"csv", "crm"}:
        status = "empty"
    else:
        status = "planned"
    if config.get("status") == "error":
        status = "error"
    return {
        "key": key,
        "name": name,
        "type": source_type,
        "status": status,
        "records": records,
        "campaigns": campaigns,
        "last_sync_at": config.get("last_sync_at") or config.get("updated_at") or "",
        "has_credentials": has_credentials,
        "message": config.get("last_error") or "",
    }


def customer_source_count(store, source_keys):
    source_keys = {key.lower() for key in source_keys}
    return sum(
        1 for customer in store.get("customers", [])
        if str(customer.get("source") or customer.get("origem") or "").lower() in source_keys
    )


def source_statuses(store):
    configs = store.get("connector_configs", {})
    csv_count = customer_source_count(store, {"csv"})
    crm_count = len(store.get("customers", [])) - csv_count
    return [
        source_status_entry("csv", "CSV", "file", csv_count),
        source_status_entry("crm", "CRM", "crm", crm_count, config=configs.get("crm", {})),
        source_status_entry(
            "meta",
            "Meta Ads",
            "ads",
            len(store.get("meta_ads_leads", [])),
            len(store.get("meta_ads_campaigns", [])),
            configs.get("meta", {}),
        ),
        source_status_entry(
            "google",
            "Google Ads",
            "ads",
            0,
            len([item for item in store.get("ads_campaigns", []) if item.get("source") == "google"]),
            configs.get("google", {}),
        ),
        source_status_entry(
            "other_ads",
            "Outros Ads",
            "ads",
            len(store.get("ads_leads", [])),
            len(store.get("ads_campaigns", [])),
        ),
        source_status_entry("powerbi", "Power BI", "bi", 1 if store.get("powerbi_snapshot") else 0),
    ]


def system_status_payload(store):
    summary = executive_summary(store)
    sources = source_statuses(store)
    active_sources = sum(1 for source in sources if source["status"] == "active")
    warnings = []
    if not active_sources:
        warnings.append("Nenhuma fonte com dados reais carregados.")
    if summary.get("clientes_analisados", 0) == 0:
        warnings.append("Base de clientes vazia.")
    if summary.get("campanhas", 0) == 0:
        warnings.append("Nenhuma campanha carregada.")
    return {
        "status": "ok" if not warnings else "attention",
        "service": "personapulse-api",
        "time": now_iso(),
        "database": {
            "persistence": persistence_status(),
            "database_url_configured": using_postgres(),
            "connected": True,
        },
        "summary": summary,
        "sources": sources,
        "store_counts": store_counts(store),
        "warnings": warnings,
    }


def normalize_imported_customer(row, index, file_name):
    external_id = item_text(row, ["external_id", "cliente_id", "customer_id", "id", "email"], f"csv_{index + 1:06d}")
    name = item_text(row, ["nome", "name", "cliente", "full_name"], "Cliente CSV")
    email = item_text(row, ["email"])
    phone = item_text(row, ["telefone", "phone", "whatsapp"])
    city = item_text(row, ["cidade", "city"])
    state = item_text(row, ["estado", "state"])
    consent_value = row.get("consentimento_marketing") if "consentimento_marketing" in row else row.get("consent_marketing")
    customer = {
        **row,
        "external_id": external_id,
        "source": "csv",
        "name": name,
        "email": email,
        "phone": phone,
        "whatsapp": item_text(row, ["whatsapp", "telefone_whatsapp", "celular", "telefone", "phone"]),
        "instagram": item_text(row, ["instagram", "perfil_instagram", "insta"]),
        "tiktok": item_text(row, ["tiktok", "perfil_tiktok"]),
        "linkedin": item_text(row, ["linkedin", "perfil_linkedin"]),
        "facebook": item_text(row, ["facebook", "perfil_facebook"]),
        "preferred_contact_channel": item_text(row, ["canal_preferido_contato", "canal_preferido", "canal"]),
        "city": city,
        "state": state,
        "country": item_text(row, ["pais", "country"], "BR"),
        "consent_marketing": as_bool(consent_value),
        "consent_source": item_text(row, ["origem_consentimento", "consent_source"], "csv"),
        "behavioral_segment": item_text(row, ["estilo_comportamental", "status_comportamental", "segmento", "status"]),
        "intent_score": item_float(row, ["score_intencao", "intent_score", "score"]),
        "status": item_text(row, ["status_comportamental", "status"]),
        "origem_dados": "CSV",
        "origem_arquivo": file_name,
        "updated_at": now_iso(),
    }
    product = item_text(row, ["produto_comprado", "produto_ultimo_interesse", "produto", "product_name"])
    value = parse_money_value(item_text(row, ["valor_compra", "valor", "value", "ticket_medio", "ticket"], "0"))
    order = None
    if product or value:
        purchased_at = item_text(row, ["data_compra", "ultima_compra", "purchased_at", "created_at"])
        order = {
            **row,
            "id": str(uuid.uuid4()),
            "order_id": item_text(row, ["order_id", "external_order_id"], f"csv_{external_id}_{index + 1}"),
            "external_customer_id": external_id,
            "source": "csv",
            "product_name": product or "Produto nao informado",
            "category": item_text(row, ["categoria_preferida", "categoria", "category"]),
            "store": item_text(row, ["onde_comprou", "local_compra", "loja", "origem", "canal_preferido"], "CSV"),
            "channel": item_text(row, ["canal_preferido", "canal"], "CSV"),
            "value": value,
            "purchased_at": purchased_at or now_iso(),
            "created_at": now_iso(),
        }
    events = []
    if as_bool(row.get("carrinho_abandonado")):
        events.append({
            "id": str(uuid.uuid4()),
            "event_id": f"csv_cart_{external_id}_{index + 1}",
            "external_customer_id": external_id,
            "source": "csv",
            "event_type": "abandoned_cart",
            "product_name": product,
            "channel": item_text(row, ["canal_preferido", "canal"], "CSV"),
            "occurred_at": now_iso(),
            "created_at": now_iso(),
        })
    return customer, order, events


def import_csv_customers(store, rows, file_name="arquivo.csv", replace_source=True):
    if replace_source:
        store["customers"] = [item for item in store.get("customers", []) if item_source(item, "").lower() != "csv"]
        store["orders"] = [item for item in store.get("orders", []) if item_source(item, "").lower() != "csv"]
        store["events"] = [item for item in store.get("events", []) if item_source(item, "").lower() != "csv"]
    customers = []
    orders = []
    events = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        customer, order, customer_events = normalize_imported_customer(row, index, file_name)
        customers.append(customer)
        if order:
            orders.append(order)
        events.extend(customer_events)
    store["customers"].extend(customers)
    store["orders"].extend(orders)
    store["events"].extend(events)
    add_audit(store, "csv_customers_imported", {
        "file_name": file_name,
        "customers": len(customers),
        "orders": len(orders),
        "events": len(events),
        "replace_source": replace_source,
    })
    return {"customers": len(customers), "orders": len(orders), "events": len(events)}


def load_store():
    if using_postgres():
        return load_store_from_postgres()
    raise RuntimeError("DATABASE_URL nao configurada. Configure o PostgreSQL no Render para habilitar persistencia.")


def save_store(store):
    if using_postgres():
        return save_store_to_postgres(store)
    raise RuntimeError("DATABASE_URL nao configurada. Dados nao foram gravados.")


def add_audit(store, action, details):
    entry = {
        "id": str(uuid.uuid4()),
        "action": action,
        "details": details,
        "created_at": now_iso(),
    }
    store["audit_logs"].insert(0, entry)
    if using_postgres():
        try:
            ensure_postgres_schema()
            with postgres_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO app_audit (id, action, details, created_at)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (entry["id"], action, Jsonb(details), entry["created_at"]),
                    )
                conn.commit()
        except Exception:
            pass


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
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        detail = body
        try:
            error_payload = json.loads(body)
            if isinstance(error_payload, dict):
                error_value = error_payload.get("error")
                if isinstance(error_value, dict):
                    detail = error_value.get("message") or error_value.get("status") or body
                else:
                    detail = error_payload.get("error_description") or error_payload.get("message") or body
            elif isinstance(error_payload, list):
                detail = json.dumps(error_payload[:2], ensure_ascii=False)
        except json.JSONDecodeError:
            pass
        raise RuntimeError(f"HTTP {exc.code} {exc.reason}: {detail}") from exc


def http_post_form_json(url, payload):
    data = urlencode(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def oauth_error_html(title, detail):
    safe_title = html.escape(str(title))
    safe_detail = html.escape(str(detail))
    return f"""
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=AW-18204384285"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'AW-18204384285');
  </script>
  <title>{safe_title}</title>
  <style>
    body {{ font-family: Arial, sans-serif; background:#f6f8fb; color:#07142f; padding:40px; }}
    main {{ max-width:720px; margin:auto; background:white; border:1px solid #d8e0ee; border-radius:12px; padding:28px; }}
    h1 {{ margin-top:0; }}
    pre {{ white-space:pre-wrap; background:#111827; color:#f8fafc; padding:16px; border-radius:8px; }}
  </style>
</head>
<body>
  <main>
    <h1>{safe_title}</h1>
    <p>O PersonaPulse recebeu o retorno do provedor, mas não conseguiu concluir a autorização.</p>
    <pre>{safe_detail}</pre>
    <p>Volte ao PersonaPulse, revise as credenciais e abra o OAuth novamente.</p>
  </main>
</body>
</html>
"""


def readable_http_error(exc):
    try:
        body = exc.read().decode("utf-8")
    except Exception:
        body = ""
    return f"HTTP {getattr(exc, 'code', '')} {getattr(exc, 'reason', '')}\n{body}".strip()


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


def google_ads_headers(access_token, developer_token, login_customer_id=""):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": developer_token,
    }
    login_customer_id = str(login_customer_id or "").replace("-", "").strip()
    if login_customer_id:
        headers["login-customer-id"] = login_customer_id
    return headers


def google_ads_search_stream(customer_id, query, access_token, developer_token, login_customer_id=""):
    customer_id = str(customer_id).replace("-", "").replace("customers/", "").strip()
    return http_post_json(
        f"https://googleads.googleapis.com/v22/customers/{customer_id}/googleAds:searchStream",
        {"query": query},
        google_ads_headers(access_token, developer_token, login_customer_id),
    )


def google_ads_client_accounts(manager_id, access_token, developer_token):
    query = """
      SELECT
        customer_client.client_customer,
        customer_client.descriptive_name,
        customer_client.manager,
        customer_client.status
      FROM customer_client
      WHERE customer_client.manager = false
    """
    payload = google_ads_search_stream(manager_id, query, access_token, developer_token, manager_id)
    clients = []
    for batch in payload if isinstance(payload, list) else []:
        for row in batch.get("results", []):
            client = row.get("customerClient", {})
            client_customer = str(client.get("clientCustomer", "")).replace("customers/", "").strip()
            if client_customer:
                clients.append({
                    "customer_id": client_customer,
                    "name": client.get("descriptiveName") or client_customer,
                    "status": client.get("status"),
                })
    return clients


def google_ads_is_manager_metrics_error(error):
    return "REQUESTED_METRICS_FOR_MANAGER" in str(error)


def import_google_ads_payload(store, payload, source="google"):
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
    return campaign_count, insight_count


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
    login_customer_id = str(config.get("login_customer_id", "")).replace("-", "").strip()
    campaign_count = 0
    insight_count = 0
    synced_customers = []

    try:
        payload = google_ads_search_stream(customer_id, query, access_token, developer_token, login_customer_id)
        campaigns, insights = import_google_ads_payload(store, payload)
        campaign_count += campaigns
        insight_count += insights
        synced_customers.append(customer_id)
    except RuntimeError as exc:
        if not google_ads_is_manager_metrics_error(exc):
            raise
        clients = google_ads_client_accounts(customer_id, access_token, developer_token)
        if not clients:
            raise RuntimeError("A conta informada e uma MCC, mas nenhuma conta cliente foi encontrada abaixo dela.") from exc
        for client in clients:
            payload = google_ads_search_stream(client["customer_id"], query, access_token, developer_token, customer_id)
            campaigns, insights = import_google_ads_payload(store, payload)
            campaign_count += campaigns
            insight_count += insights
            synced_customers.append(client["customer_id"])

    config["last_sync_at"] = now_iso()
    config["status"] = "synced"
    return {"campaigns": campaign_count, "insights": insight_count, "customers": synced_customers}


DOCS_HTML = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=AW-18204384285"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'AW-18204384285');
  </script>
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
  <section><span class="method">GET</span> <code>/api/db/status</code><p>Diagnostico do PostgreSQL: contagens do store consolidado e das tabelas relacionais.</p></section>
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
  <section><span class="method">POST</span> <code>/api/import/customers</code><p>Importa uma lista de clientes vindos de CSV/XLS convertido no front. Preserva CRM e substitui a origem CSV anterior.</p>
<pre>{
  "file_name": "clientes.csv",
  "customers": [
    {
      "cliente_id": "CLI-0001",
      "nome": "Ana Silva",
      "email": "ana@email.com",
      "produto_comprado": "Notebook Dell Inspiron",
      "valor_compra": "5299.90",
      "consentimento_marketing": "sim"
    }
  ]
}</pre></section>
  <section><span class="method">GET</span> <code>/api/segments</code><p>Retorna segmentos calculados.</p></section>
  <section><span class="method">GET</span> <code>/api/powerbi/executive-summary</code><p>Resumo executivo em JSON para Power BI, com clientes, campanhas, receita, gasto, ROI real e fontes.</p></section>
  <section><span class="method">GET</span> <code>/api/powerbi/customers</code><p>Tabela de clientes analisados para Power BI.</p></section>
  <section><span class="method">GET</span> <code>/api/powerbi/campaigns</code><p>Tabela de campanhas e métricas para Power BI.</p></section>
  <section><span class="method">GET</span> <code>/api/powerbi/sources</code><p>Tabela de fontes de dados para Power BI.</p></section>
  <section><span class="method">POST</span> <code>/api/powerbi/snapshot</code><p>Recebe a fotografia consolidada do front para alimentar o dashboard executivo.</p></section>
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

LEGAL_PAGE_STYLE = """
  <style>
    body{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f6f8fb;color:#172033;line-height:1.55}
    main{max-width:880px;margin:0 auto;padding:40px 24px}
    header{border-bottom:1px solid #d8dee8;margin-bottom:24px;padding-bottom:18px}
    h1{margin:0 0 8px;font-size:32px}
    h2{margin:28px 0 8px;font-size:20px}
    p,li{color:#42526b}
    a{color:#0f8b8d;text-decoration:none;font-weight:600}
    .meta{color:#667085;font-size:14px}
    .card{background:white;border:1px solid #d8dee8;border-radius:8px;padding:20px;margin:18px 0}
    footer{margin-top:28px;color:#667085;font-size:14px}
  </style>
"""


TERMS_HTML = f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PersonaPulse AI - Terms of Service</title>
  {LEGAL_PAGE_STYLE}
</head>
<body>
<main>
  <header>
    <h1>PersonaPulse AI Terms of Service</h1>
    <p class="meta">Last updated: June 6, 2026</p>
    <p>These terms apply to PersonaPulse AI, a business analytics and marketing intelligence prototype operated by COBWEB ARQUITETURA E CONSULTORIA DADOS.</p>
  </header>

  <section class="card">
    <h2>1. Purpose of the service</h2>
    <p>PersonaPulse AI helps authorized business users consolidate customer, CRM, campaign, price research, and advertising performance data in order to generate dashboards, recommendations, campaign drafts, and executive reports.</p>
  </section>

  <section class="card">
    <h2>2. Authorized use</h2>
    <p>You may use PersonaPulse AI only with accounts, data sources, advertising accounts, CRM records, and customer data that you are legally authorized to access and process. You are responsible for respecting applicable privacy, advertising, and data protection rules.</p>
  </section>

  <section class="card">
    <h2>3. Google Ads API use</h2>
    <p>When connected to Google Ads, PersonaPulse AI uses OAuth authorization to request permitted campaign, reporting, and account data. The tool is designed for reporting, campaign analysis, and marketing workflow support. It does not sell Google user data, and it does not share Google Ads data with unauthorized third parties.</p>
  </section>

  <section class="card">
    <h2>4. User responsibilities</h2>
    <ul>
      <li>Provide accurate credentials, account IDs, and business information.</li>
      <li>Use only consented and lawful customer data.</li>
      <li>Review campaign suggestions before publishing or using them.</li>
      <li>Keep API credentials, tokens, and passwords confidential.</li>
    </ul>
  </section>

  <section class="card">
    <h2>5. Limitations</h2>
    <p>PersonaPulse AI is provided as an MVP/prototype and may contain incomplete features, simulated data flows, or integration limits while the product is under development. Recommendations and generated content are decision-support outputs and should be reviewed by a qualified user before commercial use.</p>
  </section>

  <section class="card">
    <h2>6. Security and access</h2>
    <p>Access to integrations may require OAuth credentials, API keys, or database credentials. Production credentials are expected to be stored in backend environment variables and not in the browser.</p>
  </section>

  <section class="card">
    <h2>7. Termination and data deletion</h2>
    <p>You may request removal of stored business data or disconnect integrations by contacting the operator. Access may be suspended if the service is used in violation of these terms or applicable law.</p>
  </section>

  <footer>
    <p>Contact: cloud.datascience.arch@gmail.com</p>
    <p><a href="/privacy">Privacy Policy</a> | <a href="/app">Open PersonaPulse AI</a></p>
  </footer>
</main>
</body>
</html>
"""


PRIVACY_HTML = f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PersonaPulse AI - Privacy Policy</title>
  {LEGAL_PAGE_STYLE}
</head>
<body>
<main>
  <header>
    <h1>PersonaPulse AI Privacy Policy</h1>
    <p class="meta">Last updated: June 6, 2026</p>
    <p>This policy explains how PersonaPulse AI handles information used for dashboards, CRM synchronization, price research, campaign analytics, and advertising integrations.</p>
  </header>

  <section class="card">
    <h2>1. Information we process</h2>
    <p>Depending on the integrations enabled by the user, PersonaPulse AI may process customer records, CRM events, purchases, campaign names, campaign metrics, advertising costs, conversions, attributed revenue, price research results, OAuth tokens, API configuration metadata, and technical logs.</p>
  </section>

  <section class="card">
    <h2>2. How information is used</h2>
    <p>Information is used to calculate dashboards, customer segments, campaign performance, ROI, recommendations, price positioning, and reports for authorized business users.</p>
  </section>

  <section class="card">
    <h2>3. Google user data and Google Ads data</h2>
    <p>Google OAuth data and Google Ads API data are used only to connect the authorized account, retrieve permitted advertising information, and display analytics inside PersonaPulse AI. PersonaPulse AI does not sell Google user data and does not use Google data for unauthorized advertising, profiling, or transfer to unrelated parties.</p>
  </section>

  <section class="card">
    <h2>4. Sharing and subprocessors</h2>
    <p>Data may be processed by infrastructure and integration providers required to operate the service, such as hosting, database, analytics, advertising APIs, and reporting tools selected by the user. PersonaPulse AI does not sell customer data.</p>
  </section>

  <section class="card">
    <h2>5. Retention and deletion</h2>
    <p>Data is retained only as needed for the MVP operation, auditability, reporting, and integration testing. Users may request deletion or disconnection of stored data and credentials by contacting the operator.</p>
  </section>

  <section class="card">
    <h2>6. Security</h2>
    <p>The service is designed to store sensitive integration credentials on the backend through environment variables or protected database records. Access to production systems should be restricted to authorized operators.</p>
  </section>

  <section class="card">
    <h2>7. Your rights</h2>
    <p>Where applicable, users and data subjects may request access, correction, portability, or deletion of personal data, subject to legal and operational requirements.</p>
  </section>

  <footer>
    <p>Contact: cloud.datascience.arch@gmail.com</p>
    <p><a href="/terms">Terms of Service</a> | <a href="/app">Open PersonaPulse AI</a></p>
  </footer>
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

    def redirect(self, location):
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def send_file(self, file_path, content_type):
        if not file_path.exists() or not file_path.is_file():
            return self.send_json(404, {"error": "not_found"})
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
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
        if path == "/":
            return self.redirect("/app")
        if path in {"/app", "/app/"}:
            return self.send_file(APP_DIR / "index.html", "text/html; charset=utf-8")
        if path == "/docs":
            return self.send_html(DOCS_HTML)
        if path in {"/terms", "/terms-of-service"}:
            return self.send_html(TERMS_HTML)
        if path in {"/privacy", "/privacy-policy"}:
            return self.send_html(PRIVACY_HTML)
        if path == "/health":
            persistence = persistence_status()
            payload = {
                "status": "ok" if persistence != "database_missing" else "configuration_required",
                "service": "personapulse-api",
                "persistence": persistence,
                "database_url_configured": using_postgres(),
                "time": now_iso(),
            }
            status_code = 200 if persistence != "database_missing" else 503
            if using_postgres():
                try:
                    with postgres_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("SELECT 1")
                    payload["database_connected"] = True
                except Exception as exc:
                    payload["status"] = "database_error"
                    payload["database_connected"] = False
                    payload["detail"] = str(exc)
                    status_code = 503
            return self.send_json(status_code, payload)
        if path == "/api/price-research":
            return self.send_json(410, {
                "error": "price_research_removed",
                "service": "personapulse-api",
                "message": "O precificador foi removido do PersonaPulse AI.",
                "time": now_iso(),
            })
        try:
            store = load_store()
        except Exception as exc:
            return self.send_json(503, {
                "error": "database_load_failed",
                "service": "personapulse-api",
                "persistence": persistence_status(),
                "database_url_configured": using_postgres(),
                "detail": str(exc),
                "time": now_iso(),
            })
        if path == "/api/powerbi/executive-summary":
            return self.send_json(200, executive_summary(store))
        if path == "/api/powerbi/customers":
            rows = powerbi_customers(store)
            return self.send_json(200, {"customers": rows, "count": len(rows), "updated_at": (store.get("powerbi_snapshot") or {}).get("updated_at")})
        if path == "/api/powerbi/campaigns":
            rows = powerbi_campaigns(store)
            return self.send_json(200, {"campaigns": rows, "count": len(rows), "updated_at": (store.get("powerbi_snapshot") or {}).get("updated_at")})
        if path == "/api/powerbi/sources":
            rows = powerbi_sources(store)
            return self.send_json(200, {"sources": rows, "count": len(rows), "updated_at": (store.get("powerbi_snapshot") or {}).get("updated_at")})
        if path == "/api/db/status":
            try:
                return self.send_json(200, database_status_payload(store))
            except Exception as exc:
                return self.send_json(503, {
                    "status": "database_error",
                    "service": "personapulse-api",
                    "persistence": persistence_status(),
                    "database_url_configured": using_postgres(),
                    "store_counts": store_counts(store),
                    "detail": str(exc),
                    "time": now_iso(),
                })
        if path == "/api/system/status":
            return self.send_json(200, system_status_payload(store))
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
            try:
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
            except urllib.error.HTTPError as exc:
                detail = readable_http_error(exc)
                add_audit(store, "connector_oauth_error", {"source": source, "detail": detail})
                save_store(store)
                return self.send_html(oauth_error_html("OAuth nao concluido", detail))
            except Exception as exc:
                detail = str(exc)
                add_audit(store, "connector_oauth_error", {"source": source, "detail": detail})
                save_store(store)
                return self.send_html(oauth_error_html("OAuth nao concluido", detail))
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
        try:
            store = load_store()
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

            if path == "/api/crm/demo-seed":
                result = seed_crm_demo(store, reset=as_bool(payload.get("reset", False)))
                save_store(store)
                return self.send_json(200, {
                    **result,
                    "customers_data": store["customers"],
                    "orders_data": store["orders"],
                    "events_data": store["events"],
                })

            if path == "/api/powerbi/snapshot":
                snapshot = {
                    "updated_at": now_iso(),
                    "summary": payload.get("summary") or {},
                    "customers": payload.get("customers") or [],
                    "campaigns": payload.get("campaigns") or [],
                    "sources": payload.get("sources") or [],
                }
                store["powerbi_snapshot"] = snapshot
                add_audit(store, "powerbi_snapshot_received", {
                    "customers": len(snapshot["customers"]),
                    "campaigns": len(snapshot["campaigns"]),
                    "sources": len(snapshot["sources"]),
                })
                save_store(store)
                return self.send_json(200, {
                    "status": "saved",
                    "updated_at": snapshot["updated_at"],
                    "customers": len(snapshot["customers"]),
                    "campaigns": len(snapshot["campaigns"]),
                    "sources": len(snapshot["sources"]),
                })

            if path == "/api/import/customers":
                rows = payload.get("customers") or payload.get("rows") or []
                if not isinstance(rows, list):
                    return self.send_json(400, {"error": "invalid_payload", "detail": "Envie customers ou rows como lista."})
                result = import_csv_customers(
                    store,
                    rows,
                    file_name=payload.get("file_name") or payload.get("filename") or "arquivo.csv",
                    replace_source=not (payload.get("append") is True),
                )
                save_store(store)
                return self.send_json(200, {"status": "imported", **result, "store_counts": store_counts(store)})

            if path == "/api/db/rebuild-relational":
                save_store(store)
                return self.send_json(200, {**database_status_payload(store), "rebuild_status": "rebuilt"})

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
        except RuntimeError as exc:
            self.send_json(503, {"error": "database_not_configured", "detail": str(exc)})
        except Exception as exc:
            self.send_json(400, {"error": "bad_request", "detail": str(exc)})

    def do_DELETE(self):
        path = urlparse(self.path).path
        try:
            store = load_store()
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
        except RuntimeError as exc:
            self.send_json(503, {"error": "database_not_configured", "detail": str(exc)})
        except Exception as exc:
            self.send_json(400, {"error": "bad_request", "detail": str(exc)})


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"PersonaPulse API running at http://{HOST}:{PORT}/docs")
    server.serve_forever()
