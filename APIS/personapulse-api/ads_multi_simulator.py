import json
import random
import urllib.error
import urllib.request
from datetime import date, timedelta


BASE_URL = "http://127.0.0.1:8088"
random.seed(8821)


SOURCES = {
    "google": ("Google Ads", ["Notebook Dell Inspiron", "Bicicleta MTB Carbon", "Smartphone Samsung Galaxy"]),
    "microsoft": ("Microsoft Ads", ["Notebook Dell Inspiron", "Cafeteira Espresso Automatica"]),
    "tiktok": ("TikTok Ads", ["Perfume Amadeirado Premium", "Smartphone Samsung Galaxy"]),
    "linkedin": ("LinkedIn Ads", ["Consultoria de Dados", "Notebook Dell Inspiron"]),
    "pinterest": ("Pinterest Ads", ["Carro de Bebe Travel System", "Perfume Amadeirado Premium"]),
    "snapchat": ("Snapchat Ads", ["Smartphone Samsung Galaxy", "Perfume Amadeirado Premium"]),
    "amazon": ("Amazon Ads", ["Cafeteira Espresso Automatica", "Notebook Dell Inspiron"]),
    "mercadolivre": ("Mercado Livre Ads", ["Bicicleta MTB Carbon", "Carro de Bebe Travel System"]),
}

PRICES = {
    "Notebook Dell Inspiron": 5200,
    "Bicicleta MTB Carbon": 16600,
    "Smartphone Samsung Galaxy": 3100,
    "Cafeteira Espresso Automatica": 2800,
    "Perfume Amadeirado Premium": 420,
    "Carro de Bebe Travel System": 4700,
    "Consultoria de Dados": 8500,
}

FIRST_NAMES = ["Ana", "Bruno", "Carla", "Diego", "Elaine", "Fabio", "Gabriela", "Henrique", "Isabela", "Joao"]
LAST_NAMES = ["Silva", "Santos", "Oliveira", "Souza", "Lima", "Costa", "Pereira", "Ferreira"]


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


def campaign_payload(source, label, index, product):
    start = date.today() - timedelta(days=random.randint(1, 20))
    return {
        "campaign_id": f"{source}_cmp_{index:03d}",
        "campaign_name": f"{label} - {product}",
        "product_name": product,
        "objective": random.choice(["SALES", "LEADS", "TRAFFIC"]),
        "status": random.choice(["ACTIVE", "ACTIVE", "PAUSED"]),
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=random.randint(7, 25))).isoformat(),
    }


def insight_payload(campaign):
    product = campaign["product_name"]
    price = PRICES[product]
    impressions = random.randint(25000, 210000)
    clicks = int(impressions * random.uniform(0.009, 0.052))
    conversions = max(1, int(clicks * random.uniform(0.01, 0.06)))
    spend = round(clicks * random.uniform(0.55, 3.2), 2)
    revenue = round(conversions * price * random.uniform(0.65, 1.2), 2)
    return {
        "campaign_id": campaign["campaign_id"],
        "campaign_name": campaign["campaign_name"],
        "product_name": product,
        "impressions": impressions,
        "reach": int(impressions * random.uniform(0.45, 0.82)),
        "clicks": clicks,
        "conversions": conversions,
        "spend": spend,
        "purchase_value": revenue,
        "date_start": campaign["start_date"],
        "date_stop": campaign["end_date"],
    }


def lead_payload(source, campaign, index):
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    product = campaign["product_name"]
    score = random.randint(58, 98)
    return {
        "lead_id": f"{source}_lead_{campaign['campaign_id']}_{index:03d}",
        "campaign_id": campaign["campaign_id"],
        "campaign_name": campaign["campaign_name"],
        "name": f"{first} {last}",
        "email": f"{first.lower()}.{last.lower()}.{source}{index}@lead-demo.com",
        "product_name": product,
        "store": campaign["campaign_name"].split(" - ")[0],
        "estimated_value": round(PRICES[product] * random.uniform(0.72, 1.15), 2),
        "captured_at": (date.today() - timedelta(days=random.randint(0, 18))).isoformat(),
        "score": score,
        "status": "cliente premium" if score >= 88 else "alta intencao",
        "consent_marketing": random.random() < 0.9,
    }


def main():
    print("PersonaPulse Multi Ads Simulator")
    print(request("GET", "/health")["status"])
    totals = {"campaigns": 0, "insights": 0, "leads": 0}

    for source, (label, products) in SOURCES.items():
        print(f"Sincronizando {label}...")
        for index, product in enumerate(products, start=1):
            campaign = campaign_payload(source, label, index, product)
            insight = insight_payload(campaign)
            request("POST", f"/api/ads/{source}/campaigns", campaign)
            request("POST", f"/api/ads/{source}/insights", insight)
            lead_count = max(5, min(22, int(insight["conversions"] * 0.25)))
            for lead_index in range(1, lead_count + 1):
                request("POST", f"/api/ads/{source}/leads", lead_payload(source, campaign, lead_index))
            totals["campaigns"] += 1
            totals["insights"] += 1
            totals["leads"] += lead_count

    print("")
    print("Resumo")
    print(f"- Campanhas: {totals['campaigns']}")
    print(f"- Insights: {totals['insights']}")
    print(f"- Leads/clientes atribuídos: {totals['leads']}")
    print("Teste concluido com sucesso.")


if __name__ == "__main__":
    main()
