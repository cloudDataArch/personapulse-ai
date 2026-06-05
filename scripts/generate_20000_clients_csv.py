import csv
import random
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "CSV" / "personapulse_clientes_20000_diversos.csv"
random.seed(4317)

first_names = [
    "Ana", "Bruno", "Carla", "Diego", "Elaine", "Fabio", "Gabriela", "Henrique", "Isabela", "Joao",
    "Karina", "Leonardo", "Marina", "Nicolas", "Olivia", "Paulo", "Renata", "Samuel", "Tatiana", "Victor",
    "Amanda", "Caio", "Daniela", "Eduardo", "Fernanda", "Gustavo", "Helena", "Igor", "Juliana", "Lucas",
]
last_names = [
    "Silva", "Santos", "Oliveira", "Souza", "Lima", "Costa", "Pereira", "Ferreira", "Almeida", "Ribeiro",
    "Martins", "Barbosa", "Rocha", "Moura", "Araujo", "Cardoso", "Nunes", "Castro", "Mendes", "Teixeira",
]
cities = [
    "Sao Paulo", "Rio de Janeiro", "Belo Horizonte", "Curitiba", "Porto Alegre", "Brasilia", "Salvador",
    "Recife", "Fortaleza", "Goiania", "Campinas", "Florianopolis", "Vitoria", "Manaus", "Belem",
]
origins = ["site", "loja online", "instagram", "google ads", "newsletter", "whatsapp", "indicacao", "marketplace"]
stores = [
    "E-commerce proprio", "Loja Shopping Morumbi", "Marketplace", "WhatsApp Vendas", "Loja Centro",
    "App Mobile", "Instagram Shop", "Google Shopping", "Loja Barra", "Loja Campinas",
]
channels = ["WhatsApp", "E-mail", "Meta Ads", "Google Ads", "SMS"]

catalog = [
    ("Notebook Dell Inspiron", "eletronicos", 2800, 7500),
    ("Smartphone Samsung Galaxy", "eletronicos", 1400, 8000),
    ("Celular Nokia", "eletronicos", 250, 1300),
    ("Bicicleta MTB Carbon", "esporte", 8000, 25000),
    ("Bicicleta Urbana Premium", "esporte", 2500, 7000),
    ("Carro de Bebe Travel System", "bebe", 2200, 7000),
    ("Cadeira Auto Isofix", "bebe", 800, 2500),
    ("Perfume Amadeirado Premium", "beleza", 250, 900),
    ("Kit Skincare Anti-idade", "beleza", 180, 900),
    ("Tenis Corrida Performance", "moda", 350, 1200),
    ("Jaqueta Couro Premium", "moda", 600, 2500),
    ("Mala Viagem Executiva", "viagem", 400, 1800),
    ("Pacote Resort Nordeste", "viagem", 3000, 12000),
    ("Cafeteira Espresso Automatica", "casa", 1200, 4500),
    ("Sofa Retratil Premium", "casa", 2500, 9000),
    ("Livro Devocional Luxo", "religioso", 60, 250),
    ("Instrumento Musical Teclado", "musica", 800, 5000),
    ("Curso Online Marketing", "educacao", 497, 2497),
]

statuses = [
    "cliente premium",
    "carrinho abandonado",
    "recompra provavel",
    "sensivel a desconto",
    "inativo",
    "comprador recorrente",
    "novo lead",
    "alta intencao",
]
status_weights = [0.12, 0.14, 0.16, 0.18, 0.12, 0.13, 0.08, 0.07]

lifestyles = [
    "premium urbano", "familia com bebe", "aventureiro esportivo", "tecnologia e produtividade",
    "beleza e autocuidado", "viagens e experiencias", "casa e conforto", "religioso e comunidade",
    "sensivel a preco", "comprador recorrente"
]


def weighted_status():
    return random.choices(statuses, weights=status_weights, k=1)[0]


def build_row(i):
    first = random.choice(first_names)
    last = random.choice(last_names)
    name = f"{first} {last}"
    product, category, price_min, price_max = random.choice(catalog)
    status = weighted_status()
    lifestyle = random.choice(lifestyles)
    city = random.choice(cities)
    origin = random.choice(origins)
    channel = random.choice(channels)
    store = random.choice(stores)

    purchases = random.randint(1, 12)
    position = random.random()
    if status == "cliente premium":
        position = random.uniform(0.62, 0.98)
        score = random.randint(82, 96)
    elif status == "carrinho abandonado":
        position = random.uniform(0.45, 0.85)
        score = random.randint(76, 92)
    elif status == "inativo":
        position = random.uniform(0.18, 0.58)
        score = random.randint(34, 58)
    elif status == "sensivel a desconto":
        position = random.uniform(0.12, 0.50)
        score = random.randint(58, 78)
    elif status == "alta intencao":
        position = random.uniform(0.50, 0.90)
        score = random.randint(84, 98)
    else:
        position = random.uniform(0.25, 0.75)
        score = random.randint(60, 84)

    ticket = round(price_min + (price_max - price_min) * position, 2)
    last_purchase = date(2026, 5, 31) - timedelta(days=random.randint(0, 365))
    purchase_value = round(ticket * random.uniform(0.97, 1.03), 2)
    consent = "sim" if random.random() < 0.86 else "nao"
    cart = "sim" if status == "carrinho abandonado" or random.random() < 0.08 else "nao"
    discount = "sim" if status == "sensivel a desconto" or random.random() < 0.22 else "nao"
    affinity = "alta" if status == "cliente premium" or ticket >= 3500 else ("media" if ticket >= 800 else "baixa")
    source_consent = random.choice(["checkout", "newsletter", "cadastro site", "whatsapp", "programa fidelidade"])

    return {
        "cliente_id": f"CLI-{i:05d}",
        "nome": name,
        "email": f"{first.lower()}.{last.lower()}{i}@emaildemo.com",
        "cidade": city,
        "origem": origin,
        "estilo_comportamental": lifestyle,
        "produto_ultimo_interesse": product,
        "produto_comprado": product,
        "categoria_preferida": category,
        "local_compra": store,
        "valor_compra": f"{purchase_value:.2f}",
        "data_compra": last_purchase.isoformat(),
        "ticket_medio": f"{ticket:.2f}",
        "compras_12_meses": purchases,
        "ultima_compra": last_purchase.isoformat(),
        "status_comportamental": status,
        "score_intencao": score,
        "carrinho_abandonado": cart,
        "sensivel_desconto": discount,
        "afinidade_premium": affinity,
        "canal_preferido": channel,
        "consentimento_marketing": consent,
        "origem_consentimento": source_consent,
        "acao_recomendada": action_for(status, channel),
    }


def action_for(status, channel):
    actions = {
        "cliente premium": f"Lancamento exclusivo por {channel}",
        "carrinho abandonado": f"Recuperar carrinho por {channel}",
        "recompra provavel": f"Oferta de recompra por {channel}",
        "sensivel a desconto": f"Cupom limitado por {channel}",
        "inativo": f"Reativacao por {channel}",
        "comprador recorrente": f"Curadoria personalizada por {channel}",
        "novo lead": f"Nutrir lead por {channel}",
        "alta intencao": f"Campanha de conversao por {channel}",
    }
    return actions[status]


def main():
    rows = [build_row(i) for i in range(1, 20001)]
    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(OUTPUT)


if __name__ == "__main__":
    main()
