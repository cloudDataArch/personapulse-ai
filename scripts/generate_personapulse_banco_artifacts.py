from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_BASE = "https://personapulse-ai.onrender.com"
TARGET_DIR = ROOT / "BANCO" / "PersonaPulse Banco"
MIGRATIONS_DIR = ROOT / "APIS" / "personapulse-api" / "migrations"


def fetch_json(path: str) -> dict:
    with urllib.request.urlopen(f"{API_BASE}{path}", timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def sql_text(value) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def sql_bool(value) -> str:
    return "TRUE" if bool(value) else "FALSE"


def sql_num(value) -> str:
    if value in (None, ""):
        return "0"
    try:
        return str(float(value))
    except (TypeError, ValueError):
        return "0"


def sql_json(value) -> str:
    return sql_text(json.dumps(value or {}, ensure_ascii=False, sort_keys=True)) + "::jsonb"


def only_digits(value: str) -> str:
    return re.sub(r"\D+", "", value or "")


def contact_payload(customer: dict, index: int) -> dict:
    phone_digits = only_digits(customer.get("phone") or customer.get("telefone") or "")
    whatsapp = customer.get("whatsapp") or (f"+{phone_digits}" if phone_digits else None)
    email_prefix = (customer.get("email") or f"cliente{index}@demo.local").split("@", 1)[0]
    slug = re.sub(r"[^a-z0-9_]+", "", email_prefix.lower().replace(".", "_"))
    return {
        "whatsapp": whatsapp,
        "instagram": customer.get("instagram") or f"@{slug}",
        "tiktok": customer.get("tiktok") or f"@{slug}",
        "linkedin": customer.get("linkedin") or f"https://www.linkedin.com/in/{slug}",
        "facebook": customer.get("facebook") or f"https://www.facebook.com/{slug}",
        "preferred_contact_channel": customer.get("preferred_contact_channel")
        or customer.get("canal_preferido_contato")
        or "whatsapp",
    }


def read_schema() -> str:
    files = [
        "001_app_store_postgresql.sql",
        "002_relational_model.sql",
        "003_price_researches.sql",
        "004_dba_portuguese_views.sql",
        "005_customer_contact_channels.sql",
    ]
    sections = [
        "-- Banco: PersonaPulse Banco",
        "-- Arquivo: DDL consolidado para PostgreSQL",
        "-- Observacao: nao contem credenciais, senhas ou URLs privadas.",
        "",
        "CREATE EXTENSION IF NOT EXISTS pgcrypto;",
        "",
    ]
    for filename in files:
        path = MIGRATIONS_DIR / filename
        sections.append(f"-- ===== {filename} =====")
        sections.append(path.read_text(encoding="utf-8").strip())
        sections.append("")
    return "\n".join(sections).strip() + "\n"


def build_seed(customers: list[dict], orders: list[dict], events: list[dict], campaigns: list[dict]) -> str:
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "-- Banco: PersonaPulse Banco",
        "-- Arquivo: carga demonstrativa DML",
        f"-- Gerado em: {now}",
        "-- Dados: CRM demonstrativo e campanhas cadastradas pelo PersonaPulse.",
        "-- Observacao: nao contem credenciais, senhas ou URLs privadas.",
        "",
        "BEGIN;",
        "",
        "TRUNCATE TABLE",
        "    app.campaign_metrics,",
        "    app.recommendations,",
        "    app.campaigns,",
        "    app.events,",
        "    app.orders,",
        "    app.customers",
        "CASCADE;",
        "",
    ]

    for index, customer in enumerate(customers, start=1):
        contacts = contact_payload(customer, index)
        raw_payload = {**customer, **contacts}
        fields = [
            "external_id",
            "source",
            "name",
            "email",
            "phone",
            "whatsapp",
            "instagram",
            "tiktok",
            "linkedin",
            "facebook",
            "preferred_contact_channel",
            "city",
            "state",
            "country",
            "consent_marketing",
            "consent_source",
            "behavioral_segment",
            "intent_score",
            "status",
            "raw_payload",
        ]
        values = [
            sql_text(customer.get("external_id") or f"crm_demo_{index:04d}"),
            sql_text(customer.get("source") or "crm"),
            sql_text(customer.get("name") or f"Cliente {index}"),
            sql_text(customer.get("email")),
            sql_text(customer.get("phone")),
            sql_text(contacts["whatsapp"]),
            sql_text(contacts["instagram"]),
            sql_text(contacts["tiktok"]),
            sql_text(contacts["linkedin"]),
            sql_text(contacts["facebook"]),
            sql_text(contacts["preferred_contact_channel"]),
            sql_text(customer.get("city")),
            sql_text(customer.get("state")),
            sql_text(customer.get("country") or "BR"),
            sql_bool(customer.get("consent_marketing")),
            sql_text(customer.get("consent_source") or "crm_demo"),
            sql_text(customer.get("behavioral_segment") or customer.get("status")),
            sql_num(customer.get("intent_score")),
            sql_text(customer.get("status")),
            sql_json(raw_payload),
        ]
        lines.append(
            f"INSERT INTO app.customers ({', '.join(fields)}) VALUES ({', '.join(values)}) "
            "ON CONFLICT (source, external_id) DO UPDATE SET "
            "name = EXCLUDED.name, email = EXCLUDED.email, phone = EXCLUDED.phone, "
            "whatsapp = EXCLUDED.whatsapp, instagram = EXCLUDED.instagram, tiktok = EXCLUDED.tiktok, "
            "linkedin = EXCLUDED.linkedin, facebook = EXCLUDED.facebook, "
            "preferred_contact_channel = EXCLUDED.preferred_contact_channel, "
            "city = EXCLUDED.city, state = EXCLUDED.state, country = EXCLUDED.country, "
            "consent_marketing = EXCLUDED.consent_marketing, raw_payload = EXCLUDED.raw_payload, "
            "updated_at = NOW();"
        )

    lines.append("")
    for index, order in enumerate(orders, start=1):
        source = order.get("source") or "crm"
        external_customer_id = order.get("external_customer_id")
        fields = [
            "external_order_id",
            "customer_id",
            "external_customer_id",
            "source",
            "product_name",
            "category",
            "store_name",
            "channel",
            "value",
            "purchased_at",
            "raw_payload",
        ]
        values = [
            sql_text(order.get("order_id") or order.get("external_order_id") or f"PED-DEMO-{index:05d}"),
            f"(SELECT id FROM app.customers WHERE source = {sql_text(source)} AND external_id = {sql_text(external_customer_id)} LIMIT 1)",
            sql_text(external_customer_id),
            sql_text(source),
            sql_text(order.get("product_name") or "Produto nao informado"),
            sql_text(order.get("category")),
            sql_text(order.get("store") or order.get("store_name")),
            sql_text(order.get("channel")),
            sql_num(order.get("value")),
            sql_text(order.get("purchased_at")),
            sql_json(order),
        ]
        lines.append(f"INSERT INTO app.orders ({', '.join(fields)}) VALUES ({', '.join(values)});")

    lines.append("")
    for index, event in enumerate(events, start=1):
        source = event.get("source") or "crm"
        external_customer_id = event.get("external_customer_id")
        fields = [
            "external_event_id",
            "customer_id",
            "external_customer_id",
            "source",
            "event_type",
            "product_name",
            "channel",
            "occurred_at",
            "raw_payload",
        ]
        values = [
            sql_text(event.get("event_id") or event.get("external_event_id") or f"EVT-DEMO-{index:05d}"),
            f"(SELECT id FROM app.customers WHERE source = {sql_text(source)} AND external_id = {sql_text(external_customer_id)} LIMIT 1)",
            sql_text(external_customer_id),
            sql_text(source),
            sql_text(event.get("event_type") or "evento"),
            sql_text(event.get("product_name")),
            sql_text(event.get("channel")),
            sql_text(event.get("occurred_at")),
            sql_json(event),
        ]
        lines.append(f"INSERT INTO app.events ({', '.join(fields)}) VALUES ({', '.join(values)});")

    lines.extend([
        "",
        "INSERT INTO integrations.data_sources (source_key, source_name, source_type, status)",
        "VALUES",
        "    ('csv', 'CSV', 'file', 'active'),",
        "    ('crm', 'CRM', 'crm', 'active'),",
        "    ('meta_ads', 'Meta Ads', 'ads', 'planned'),",
        "    ('google_ads', 'Google Ads', 'ads', 'planned'),",
        "    ('powerbi', 'Power BI', 'bi', 'active'),",
        "    ('marketplace_prices', 'Mercado Livre + Amazon + Shopee', 'price_research', 'active')",
        "ON CONFLICT (source_key) DO UPDATE SET",
        "    source_name = EXCLUDED.source_name,",
        "    source_type = EXCLUDED.source_type,",
        "    status = EXCLUDED.status,",
        "    updated_at = NOW();",
        "",
        "COMMIT;",
        "",
        "-- Conferencia rapida:",
        "SELECT * FROM dba.resumo_banco;",
    ])
    return "\n".join(lines) + "\n"


def build_queries() -> str:
    return """-- Banco: PersonaPulse Banco
-- Consultas iniciais para DBA, BI e validacao funcional.

SELECT * FROM dba.resumo_banco ORDER BY tabela;

SELECT
    id_cliente,
    nome,
    email,
    whatsapp,
    instagram,
    tiktok,
    linkedin,
    facebook,
    canal_preferido_contato,
    origem_dados
FROM dba.contatos_clientes
ORDER BY id_cliente
LIMIT 50;

SELECT
    id_cliente,
    nome,
    segmento_comportamental,
    score_intencao,
    consentimento_marketing,
    origem_dados
FROM dba.clientes
ORDER BY id_cliente
LIMIT 50;

SELECT
    p.id_pedido,
    p.id_cliente,
    c.nome,
    p.produto,
    p.loja,
    p.canal,
    p.valor,
    p.comprado_em
FROM dba.pedidos p
LEFT JOIN dba.clientes c ON c.id_cliente = p.id_cliente
ORDER BY p.id_pedido
LIMIT 50;

SELECT
    id_pesquisa_preco,
    produto,
    posicionamento,
    origem_dados,
    ticket_medio,
    preco_competitivo,
    preco_recomendado,
    preco_premium,
    itens_observados
FROM dba.pesquisas_precos
ORDER BY criado_em DESC
LIMIT 25;
"""


def build_readme(customers_count: int, orders_count: int, events_count: int, campaigns_count: int) -> str:
    return f"""# PersonaPulse Banco

Pacote versionado do banco de dados do PersonaPulse AI.

Este diretorio guarda os artefatos iniciais do banco, sem credenciais e sem URLs privadas:

- `00_personapulse_banco_schema.sql`: DDL consolidado do PostgreSQL.
- `01_personapulse_banco_seed_demo.sql`: DML com carga demonstrativa do CRM.
- `02_consultas_dba.sql`: consultas em portugues para validacao e analise.

## Base demonstrativa incluida

- Clientes: {customers_count}
- Pedidos: {orders_count}
- Eventos: {events_count}
- Campanhas: {campaigns_count}

## Como usar

1. Crie ou selecione um banco PostgreSQL.
2. Execute `00_personapulse_banco_schema.sql`.
3. Execute `01_personapulse_banco_seed_demo.sql`.
4. Valide com `02_consultas_dba.sql`.

## Padrao adotado

As tabelas internas usam UUID para proteger integracoes entre CSV, CRM, Ads e Power BI.
Para leitura humana, as views `dba.*` exibem IDs sequenciais iniciando em zero, nomes de colunas em portugues e campos de contato como WhatsApp, e-mail, Instagram, TikTok, LinkedIn e Facebook.

Proxima evolucao prevista: separar DDL, DML, funcoes, procedures, indices e documentacao operacional em arquivos proprios.
"""


def main() -> None:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    customers = fetch_json("/api/crm/customers").get("customers", [])
    orders = fetch_json("/api/crm/orders").get("orders", [])
    events = fetch_json("/api/crm/events").get("events", [])
    campaigns = fetch_json("/api/campaigns").get("campaigns", [])

    (TARGET_DIR / "README.md").write_text(
        build_readme(len(customers), len(orders), len(events), len(campaigns)),
        encoding="utf-8",
    )
    (TARGET_DIR / "00_personapulse_banco_schema.sql").write_text(read_schema(), encoding="utf-8")
    (TARGET_DIR / "01_personapulse_banco_seed_demo.sql").write_text(
        build_seed(customers, orders, events, campaigns),
        encoding="utf-8",
    )
    (TARGET_DIR / "02_consultas_dba.sql").write_text(build_queries(), encoding="utf-8")
    print(f"Banco artifacts generated at {TARGET_DIR}")
    print(f"customers={len(customers)} orders={len(orders)} events={len(events)} campaigns={len(campaigns)}")


if __name__ == "__main__":
    main()
