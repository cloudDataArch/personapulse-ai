import json
import random
import urllib.error
import urllib.request
from datetime import date, timedelta


BASE_URL = "http://127.0.0.1:8088"
random.seed(4871)


PRODUCTS = [
    ("Notebook Dell Inspiron", "Conversao Notebook Dell", 5200),
    ("Bicicleta MTB Carbon", "Lancamento MTB Premium", 16600),
    ("Carro de Bebe Travel System", "Carrinho bebe premium", 4700),
    ("Perfume Amadeirado Premium", "Perfume premium dia especial", 420),
    ("Smartphone Samsung Galaxy", "Smartphone alto interesse", 3100),
    ("Cafeteira Espresso Automatica", "Cafeteira espresso casa premium", 2800),
]
OBJECTIVES = ["SALES", "LEADS", "TRAFFIC"]
STATUSES = ["ACTIVE", "ACTIVE", "ACTIVE", "PAUSED"]
FIRST_NAMES = ["Ana", "Bruno", "Carla", "Diego", "Elaine", "Fabio", "Gabriela", "Henrique", "Isabela", "Joao", "Marina", "Rafael"]
LAST_NAMES = ["Silva", "Santos", "Oliveira", "Souza", "Lima", "Costa", "Pereira", "Ferreira", "Almeida", "Ribeiro"]
CITIES = ["Sao Paulo", "Rio de Janeiro", "Belo Horizonte", "Curitiba", "Campinas", "Brasilia", "Salvador"]
CHANNELS = ["Instagram Lead Ads", "Facebook Lead Ads", "Instagram Shopping", "Meta Pixel"]


def request(method, path, payload=None):
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "ignore")
        raise RuntimeError(f"{method} {path} failed: {exc.code} {detail}") from exc


def make_campaign(index):
    product, name, _ = PRODUCTS[index % len(PRODUCTS)]
    start = date.today() - timedelta(days=random.randint(1, 18))
    end = start + timedelta(days=random.randint(6, 21))
    return {
        "campaign_id": f"meta_cmp_{index + 1:03d}",
        "name": name,
        "product_name": product,
        "objective": random.choice(OBJECTIVES),
        "status": random.choice(STATUSES),
        "buying_type": "AUCTION",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "source": "meta_ads_simulator",
    }


def make_insight(campaign):
    product = campaign["product_name"]
    avg_price = next(price for item, _, price in PRODUCTS if item == product)
    impressions = random.randint(45000, 280000)
    reach = int(impressions * random.uniform(0.55, 0.82))
    ctr = random.uniform(0.012, 0.045)
    clicks = int(impressions * ctr)
    conversion_rate = random.uniform(0.012, 0.055)
    conversions = max(1, int(clicks * conversion_rate))
    spend = round(clicks * random.uniform(0.65, 2.85), 2)
    purchase_value = round(conversions * avg_price * random.uniform(0.74, 1.22), 2)
    return {
        "campaign_id": campaign["campaign_id"],
        "campaign_name": campaign["name"],
        "product_name": product,
        "spend": spend,
        "impressions": impressions,
        "reach": reach,
        "clicks": clicks,
        "ctr": round((clicks / impressions) * 100, 2),
        "cpc": round(spend / max(1, clicks), 2),
        "cpm": round((spend / impressions) * 1000, 2),
        "conversions": conversions,
        "purchase_value": purchase_value,
        "roas": round(purchase_value / max(1, spend), 2),
        "date_start": campaign["start_date"],
        "date_stop": campaign["end_date"],
    }


def make_lead(campaign, index):
    product = campaign["product_name"]
    avg_price = next(price for item, _, price in PRODUCTS if item == product)
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    value = round(avg_price * random.uniform(0.72, 1.18), 2)
    score = random.randint(62, 98)
    captured_at = date.today() - timedelta(days=random.randint(0, 21))
    return {
        "lead_id": f"meta_lead_{campaign['campaign_id']}_{index:04d}",
        "campaign_id": campaign["campaign_id"],
        "campaign_name": campaign["name"],
        "name": f"{first} {last}",
        "email": f"{first.lower()}.{last.lower()}.meta{index}@lead-demo.com",
        "phone": f"+55119{random.randint(10000000, 99999999)}",
        "city": random.choice(CITIES),
        "product_name": product,
        "store": random.choice(CHANNELS),
        "estimated_value": value,
        "captured_at": captured_at.isoformat(),
        "score": score,
        "status": random.choice(["alta intencao", "cliente premium", "carrinho abandonado", "novo lead"]),
        "consent_marketing": random.random() < 0.92,
        "source": "meta_ads_lead_ads",
    }


def main():
    print("PersonaPulse Meta Ads Simulator")
    health = request("GET", "/health")
    print(f"Health: {health['status']}")

    campaign_count = 8
    campaigns = [make_campaign(i) for i in range(campaign_count)]

    print(f"Enviando {campaign_count} campanhas do Meta Ads...")
    for campaign in campaigns:
        request("POST", "/api/meta-ads/campaigns", campaign)
        insight = make_insight(campaign)
        request("POST", "/api/meta-ads/insights", insight)
        lead_count = max(8, min(40, int(insight["conversions"] * 0.35)))
        for lead_index in range(1, lead_count + 1):
            request("POST", "/api/meta-ads/leads", make_lead(campaign, lead_index))

    synced_campaigns = request("GET", "/api/meta-ads/campaigns")
    synced_insights = request("GET", "/api/meta-ads/insights")
    synced_leads = request("GET", "/api/meta-ads/leads")
    total_spend = sum(float(item.get("spend") or 0) for item in synced_insights["insights"])
    total_revenue = sum(float(item.get("purchase_value") or 0) for item in synced_insights["insights"])

    print("")
    print("Resumo Meta Ads")
    print(f"- Campanhas sincronizadas: {synced_campaigns['count']}")
    print(f"- Insights recebidos: {synced_insights['count']}")
    print(f"- Leads/clientes atribuídos: {synced_leads['count']}")
    print(f"- Gasto total simulado: R$ {total_spend:,.2f}")
    print(f"- Receita atribuida simulada: R$ {total_revenue:,.2f}")
    print("Teste concluido com sucesso.")


if __name__ == "__main__":
    main()
