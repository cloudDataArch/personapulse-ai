import json
import os
import random
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta


BASE_URL = os.environ.get("PERSONAPULSE_API_BASE_URL", "http://127.0.0.1:8088").rstrip("/")
random.seed(9126)


FIRST_NAMES = ["Ana", "Bruno", "Carla", "Diego", "Elaine", "Fabio", "Gabriela", "Henrique", "Isabela", "Joao"]
LAST_NAMES = ["Silva", "Santos", "Oliveira", "Souza", "Lima", "Costa", "Pereira", "Ferreira", "Almeida", "Ribeiro"]
CITIES = ["Sao Paulo", "Rio de Janeiro", "Belo Horizonte", "Curitiba", "Campinas", "Brasilia", "Salvador"]
PRODUCTS = [
    ("Notebook Dell Inspiron", "eletronicos", 5200),
    ("Bicicleta MTB Carbon", "esporte", 16600),
    ("Carro de Bebe Travel System", "bebe", 4700),
    ("Perfume Amadeirado Premium", "beleza", 420),
    ("Smartphone Samsung Galaxy", "eletronicos", 3100),
    ("Cafeteira Espresso Automatica", "casa", 2800),
]
CHANNELS = ["WhatsApp", "E-mail", "Meta Ads", "Google Ads"]
EVENT_TYPES = ["product_view", "cart_add", "checkout_start", "email_click", "ad_click"]


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


def make_customer(i):
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    return {
        "external_id": f"crm_sim_{i:04d}",
        "name": f"{first} {last}",
        "email": f"{first.lower()}.{last.lower()}.{i}@crm-demo.com",
        "phone": f"+55119{random.randint(10000000, 99999999)}",
        "city": random.choice(CITIES),
        "consent_marketing": random.random() < 0.88,
        "source": random.choice(["hubspot", "rd_station", "pipedrive", "salesforce", "crm_demo"]),
    }


def make_order(customer_id, order_index):
    product, category, avg_price = random.choice(PRODUCTS)
    value = round(avg_price * random.uniform(0.82, 1.18), 2)
    purchased_at = date.today() - timedelta(days=random.randint(0, 180))
    return {
        "external_customer_id": customer_id,
        "order_id": f"SIM-PED-{order_index:05d}",
        "product_name": product,
        "category": category,
        "store": random.choice(["E-commerce proprio", "Marketplace", "WhatsApp Vendas", "Loja fisica"]),
        "value": value,
        "purchased_at": purchased_at.isoformat(),
    }


def make_event(customer_id):
    product, _, _ = random.choice(PRODUCTS)
    occurred_at = datetime.now() - timedelta(hours=random.randint(0, 720))
    return {
        "external_customer_id": customer_id,
        "event_type": random.choice(EVENT_TYPES),
        "product_name": product,
        "occurred_at": occurred_at.isoformat(timespec="seconds"),
    }


def main():
    print("PersonaPulse CRM Simulator")
    print(f"API: {BASE_URL}")
    health = request("GET", "/health")
    print(f"Health: {health['status']}")

    customer_count = 100
    order_count = 0
    event_count = 0
    customers = []

    print(f"Criando {customer_count} clientes...")
    for i in range(1, customer_count + 1):
        customer = make_customer(i)
        customers.append(customer)
        request("POST", "/api/crm/customers", customer)

    print("Enviando pedidos...")
    for customer in customers:
        for _ in range(random.randint(0, 4)):
            order_count += 1
            request("POST", "/api/crm/orders", make_order(customer["external_id"], order_count))

    print("Enviando eventos comportamentais...")
    for customer in customers:
        for _ in range(random.randint(1, 6)):
            event_count += 1
            request("POST", "/api/crm/events", make_event(customer["external_id"]))

    print("Consultando segmentos...")
    segments = request("GET", "/api/segments")["segments"]
    for segment in segments:
        print(f"- {segment['name']}: {segment['customers']} clientes")

    best_segment = max(segments, key=lambda item: item["customers"])
    print(f"Gerando campanha para segmento: {best_segment['name']}")
    campaign_payload = {
        "segment_name": best_segment["name"],
        "product_name": "Notebook Dell Inspiron",
        "channel": random.choice(CHANNELS),
        "tone": "Sofisticado",
        "objective": "converter clientes do CRM em compradores",
    }
    campaign = request("POST", "/api/campaigns/generate", campaign_payload)["campaign"]
    print(f"Campanha criada: {campaign['title']}")

    push = request("POST", "/api/crm/recommendations/push", {"target_crm": "crm_demo"})
    print(f"Recomendacoes enviadas ao CRM: {push['count']}")

    print("")
    print("Resumo do teste")
    print(f"- Clientes enviados: {customer_count}")
    print(f"- Pedidos enviados: {order_count}")
    print(f"- Eventos enviados: {event_count}")
    print(f"- Segmentos retornados: {len(segments)}")
    print(f"- Campanha gerada: {campaign['id']}")
    print("Teste concluido com sucesso.")


if __name__ == "__main__":
    main()
