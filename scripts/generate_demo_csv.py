import csv
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "CSV" / "personapulse_clientes_demo.csv"

first_names = [
    "Ana", "Carlos", "Mariana", "Joao", "Beatriz", "Rafael", "Camila", "Lucas", "Juliana", "Felipe",
    "Larissa", "Gustavo", "Patricia", "Eduardo", "Renata", "Bruno", "Fernanda", "Diego", "Aline", "Thiago",
]
last_names = [
    "Silva", "Lima", "Oliveira", "Santos", "Costa", "Almeida", "Pereira", "Moura", "Ferreira", "Barbosa",
    "Ribeiro", "Gomes", "Martins", "Cardoso", "Rocha", "Nunes", "Teixeira", "Araujo", "Castro", "Mendes",
]

products = [
    ("Perfume Premium Amadeirado", "amadeirado", 349.00),
    ("Perfume Floral Elegance", "floral", 289.00),
    ("Perfume Citrico Fresh", "citrico", 219.00),
    ("Perfume Oriental Night", "oriental", 399.00),
    ("Kit Presente Essenza Prime", "presente", 459.00),
    ("Perfume Oud Signature", "luxo", 649.00),
    ("Body Splash Soft", "leve", 119.00),
    ("Vela Aromatica Premium", "casa", 159.00),
]

channels = ["WhatsApp", "E-mail", "Meta Ads", "Google Ads"]
cities = ["Sao Paulo", "Rio de Janeiro", "Belo Horizonte", "Curitiba", "Campinas", "Brasilia", "Salvador", "Recife"]
origins = ["site", "loja online", "instagram", "google ads", "newsletter", "whatsapp"]
statuses = ["comprador recorrente", "cliente premium", "carrinho abandonado", "inativo", "recompra provavel", "sensivel a desconto"]


def row_for(i):
    first = first_names[i % len(first_names)]
    last = last_names[(i * 3) % len(last_names)]
    name = f"{first} {last}"
    email = f"{first.lower()}.{last.lower()}{i+1}@emaildemo.com"
    product, category, base_price = products[(i * 5) % len(products)]
    status = statuses[(i * 7) % len(statuses)]
    channel = channels[(i * 2 + 1) % len(channels)]
    city = cities[(i * 4 + 2) % len(cities)]
    origin = origins[(i * 5 + 3) % len(origins)]

    purchases = 1 + (i % 6)
    if status == "cliente premium":
        ticket = base_price + 180 + (i % 5) * 35
        intent = 88 + (i % 7)
    elif status == "carrinho abandonado":
        ticket = base_price + 40
        intent = 80 + (i % 9)
    elif status == "inativo":
        ticket = max(119, base_price - 60)
        intent = 45 + (i % 12)
    elif status == "recompra provavel":
        ticket = base_price + 25
        intent = 72 + (i % 10)
    elif status == "sensivel a desconto":
        ticket = max(99, base_price - 90)
        intent = 62 + (i % 11)
    else:
        ticket = base_price + (i % 4) * 20
        intent = 68 + (i % 12)

    last_purchase = date(2026, 5, 31) - timedelta(days=(i * 3) % 180)
    cart_abandoned = "sim" if status == "carrinho abandonado" or i % 13 == 0 else "nao"
    consent = "sim" if i % 10 != 0 else "nao"
    lgpd_source = "checkout" if i % 3 == 0 else ("newsletter" if i % 3 == 1 else "cadastro site")
    discount_sensitive = "sim" if status == "sensivel a desconto" or i % 8 == 0 else "nao"
    premium_affinity = "alta" if status == "cliente premium" or category in ["luxo", "oriental"] else ("media" if ticket > 280 else "baixa")

    return {
        "cliente_id": f"CLI-{i+1:04d}",
        "nome": name,
        "email": email,
        "cidade": city,
        "origem": origin,
        "produto_ultimo_interesse": product,
        "categoria_preferida": category,
        "ticket_medio": f"{ticket:.2f}",
        "compras_12_meses": purchases,
        "ultima_compra": last_purchase.isoformat(),
        "status_comportamental": status,
        "score_intencao": intent,
        "carrinho_abandonado": cart_abandoned,
        "sensivel_desconto": discount_sensitive,
        "afinidade_premium": premium_affinity,
        "canal_preferido": channel,
        "consentimento_marketing": consent,
        "origem_consentimento": lgpd_source,
        "acao_recomendada": recommended_action(status, channel),
    }


def recommended_action(status, channel):
    mapping = {
        "comprador recorrente": f"Enviar curadoria por {channel}",
        "cliente premium": f"Oferecer lancamento exclusivo por {channel}",
        "carrinho abandonado": f"Recuperar carrinho por {channel}",
        "inativo": f"Sequencia de reativacao por {channel}",
        "recompra provavel": f"Sugerir recompra com kit por {channel}",
        "sensivel a desconto": f"Enviar cupom limitado por {channel}",
    }
    return mapping[status]


def main():
    rows = [row_for(i) for i in range(100)]
    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(OUTPUT)


if __name__ == "__main__":
    main()
