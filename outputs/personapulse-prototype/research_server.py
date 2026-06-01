import json
import math
import re
import urllib.parse
import urllib.request
from html import unescape
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


PORT = 4174


def br_category(product):
    lower = product.lower()
    if any(term in lower for term in ["carro de bebe", "carrinho", "bebê", "bebe"]):
        return {
            "low": 1200,
            "avg": 2800,
            "high": 5900,
            "attrs": [
                "travel system",
                "bebe conforto",
                "estrutura leve",
                "fechamento compacto",
                "certificacao de seguranca",
                "conforto para recem-nascido",
            ],
            "query": "carrinho de bebe premium travel system preco loja Brasil -carros -usados -webmotors -olx",
            "curated_sources": [
                {"title": "Travel System Trino Duo - Infanti Brasil", "url": "https://infanti.com.br/products/travel-system-trino-duo"},
                {"title": "Carrinho de Bebe Travel System Premium Baby Kansas - Droga Raia", "url": "https://www.drogaraia.com.br/carrinho-de-bebe-travel-system-premium-baby-kansas-prata-u-1302363.html"},
                {"title": "Carrinho Travel System Kansas Premium Baby - Minihug", "url": "https://www.minihug.com.br/products/carrinho-premium-baby-travel-system-kansas"},
            ],
        }
    if any(term in lower for term in ["bicicleta", "mtb", "bike"]):
        return {
            "low": 2500,
            "avg": 7200,
            "high": 15000,
            "attrs": [
                "quadro leve",
                "suspensao responsiva",
                "freios a disco hidraulicos",
                "transmissao Shimano ou SRAM",
                "pneus de alta aderencia",
            ],
            "query": f"{product} premium preco loja Brasil",
            "curated_sources": [],
        }
    if "perfume" in lower:
        return {
            "low": 180,
            "avg": 420,
            "high": 950,
            "attrs": ["fixacao", "familia olfativa", "frasco premium", "marca percebida", "exclusividade"],
            "query": f"{product} premium preco loja Brasil",
            "curated_sources": [],
        }
    if any(term in lower for term in ["notebook", "laptop", "dell", "macbook"]):
        return {
            "low": 2800,
            "avg": 5200,
            "high": 13500,
            "attrs": [
                "processador Intel Core i5/i7 ou Ryzen 5/7",
                "16 GB de memoria RAM",
                "SSD NVMe",
                "tela Full HD ou superior",
                "garantia e assistencia nacional",
                "acabamento premium",
            ],
            "query": f"{product} notebook preco Google Shopping Brasil loja",
            "curated_sources": [
                {"title": "Notebooks Dell - loja oficial", "url": "https://www.dell.com/pt-br/shop/notebooks-dell/sr/laptops"},
                {"title": "Notebook Dell em promocao - Magazine Luiza", "url": "https://www.magazineluiza.com.br/busca/notebook+dell/"},
                {"title": "Notebook Dell - Casas Bahia", "url": "https://www.casasbahia.com.br/notebook-dell/b"},
            ],
        }
    return {
        "low": 400,
        "avg": 850,
        "high": 1600,
        "attrs": ["acabamento superior", "garantia", "boa reputacao", "design diferenciado"],
        "query": f"{product} preco loja Brasil",
        "curated_sources": [],
    }


def position_multiplier(position):
    return {
        "Entrada": 0.75,
        "Intermediário": 1.0,
        "Intermediario": 1.0,
        "Premium": 1.35,
        "Luxo": 1.9,
    }.get(position, 1.35)


def fetch_sources(query):
    google_url = "https://www.google.com/search?q=" + urllib.parse.quote(query + " preco")
    try:
        req = urllib.request.Request(google_url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=8).read().decode("utf-8", "ignore")
        sources = []
        for match in re.finditer(r'<a href="/url\?q=([^"&]+)[^"]*".*?>(.*?)</a>', html, flags=re.S):
            url = urllib.parse.unquote(match.group(1))
            if "google." in url:
                continue
            title = re.sub(r"<.*?>", "", match.group(2))
            title = unescape(re.sub(r"\s+", " ", title)).strip()
            if title and url and not any(item["url"] == url for item in sources):
                sources.append({"title": title, "url": url})
            if len(sources) >= 5:
                return sources
    except Exception:
        pass

    url = "https://www.bing.com/search?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=8).read().decode("utf-8", "ignore")
    sources = []
    for match in re.finditer(r'<li class="b_algo".*?</li>', html, flags=re.S):
        block = match.group(0)
        title_match = re.search(r"<h2.*?<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>", block, flags=re.S)
        if not title_match:
            continue
        title = re.sub(r"<.*?>", "", title_match.group(2))
        title = unescape(re.sub(r"\s+", " ", title)).strip()
        url = unescape(title_match.group(1)).strip()
        if title and url and not any(item["url"] == url for item in sources):
            sources.append({"title": title, "url": url})
        if len(sources) >= 5:
            break
    return sources


def research(product, position):
    category = br_category(product)
    multiplier = position_multiplier(position)
    ticket = round(category["avg"] * multiplier)
    low = round(category["low"] * multiplier)
    high = round(category["high"] * multiplier)
    sources = []
    source_label = "Google + referencias online + estimativa por posicionamento"
    try:
        sources = category.get("curated_sources") or fetch_sources(category["query"])
    except Exception:
        source_label = "Estimativa local; busca online indisponivel"

    suggestions = [
        {
            "label": "Preco competitivo",
            "value": round(ticket * 0.88),
            "reason": "Bom para testar conversao sem perder o posicionamento.",
        },
        {
            "label": "Preco recomendado",
            "value": ticket,
            "reason": "Equilibra valor percebido, margem e atratividade.",
        },
        {
            "label": "Preco premium",
            "value": round(ticket * 1.18),
            "reason": "Aplicavel quando a oferta destaca atributos superiores e garantia.",
        },
    ]
    return {
        "product": product,
        "position": position,
        "source": source_label,
        "ticketMedio": ticket,
        "range": {"low": low, "high": high},
        "priceSuggestions": suggestions,
        "attrs": category["attrs"],
        "sources": sources,
    }


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/price-research":
            params = urllib.parse.parse_qs(parsed.query)
            product = params.get("product", ["Produto"])[0]
            position = params.get("position", ["Premium"])[0]
            data = json.dumps(research(product, position), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        super().do_GET()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"PersonaPulse prototype research server: http://127.0.0.1:{PORT}")
    server.serve_forever()
