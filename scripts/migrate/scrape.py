"""
Descarga todas las páginas del manifiesto (y las que descubre por el camino
en las páginas "índice de subredes"), extrae filas de IP de forma genérica
y vuelca todo a data/parsed_ips.json para revisión antes de cargarlo a NetBox.

Enfoque de extracción: en vez de intentar adivinar qué columna es
"hostname" y cuál es "notas" (los nombres cambian en cada página: EQUIPO,
Hostname, EKIPOA, OHARRAK, Descripción...), cada fila se reduce a sus
celdas no vacías y se separan por tipo: las que tienen forma de IP
(cuatro octetos numéricos) van a ip_1/ip_2, el resto se concatena tal cual
en "label". Es menos "bonito" pero es robusto frente al HTML exportado
de Word, que es muy inconsistente entre páginas.

Una página se trata como "índice de subredes" (no como datos) cuando
ninguna fila produce una IP completa pero sí contiene enlaces a más
páginas .htm/.html - típico de las columnas SUBRED/ZONA/LINK.

Uso:
    python scrape.py
"""
import html
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

from manifest import BASE_URL, PAGES

OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "parsed_ips.json"

IP_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)
HREF_RE = re.compile(r'href\s*=\s*"([^"]+)"', re.IGNORECASE)
MAX_DEPTH = 4


def cell_text(cell_html):
    text = re.sub(r"<[^>]+>", " ", cell_html)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def fetch(path):
    url = urljoin(BASE_URL, path)
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return url, resp.text


def find_sub_links(row_html, current_url):
    links = []
    for href in HREF_RE.findall(row_html):
        if href.lower().startswith(("javascript:", "mailto:")):
            continue
        if not re.search(r"\.html?$", href, re.IGNORECASE):
            continue
        resolved = urljoin(current_url, href)
        if resolved.lower().startswith(BASE_URL.lower()):
            links.append(resolved[len(BASE_URL):])
    return links


def parse_page(path, current_url, body_html):
    """Devuelve (records, sub_links) para una página ya descargada."""
    records = []
    sub_links = []
    for row_match in ROW_RE.finditer(body_html):
        row_html = row_match.group(1)
        cells = [cell_text(c) for c in CELL_RE.findall(row_html)]
        non_empty = [c for c in cells if c]
        ips = [c for c in non_empty if IP_RE.match(c)]
        labels = [c for c in non_empty if not IP_RE.match(c)]
        # Las tablas originales pre-listan TODAS las IPs posibles del rango
        # (plantilla completa de /24), estén o no asignadas. Sin texto
        # descriptivo no hay forma de distinguir "asignada sin anotar" de
        # "libre", así que solo se conserva la fila si hay algo escrito.
        if ips and labels:
            records.append({
                "ip_1": ips[0],
                "ip_2": ips[1] if len(ips) > 1 else None,
                "label": " / ".join(labels),
            })
        sub_links.extend(find_sub_links(row_html, current_url))
    return records, sub_links


def run():
    visited = set()
    all_records = []
    processed_pages = []
    skipped_pages = []
    errors = []

    queue = [(entry["path"], entry, 0) for entry in PAGES]

    while queue:
        path, entry, depth = queue.pop(0)
        key = path.lower()
        if key in visited or depth > MAX_DEPTH:
            continue
        visited.add(key)

        if entry.get("skip_records"):
            skipped_pages.append({"path": path, "reason": entry.get("review", "marcada para revisión manual")})
            continue

        try:
            current_url, body = fetch(path)
        except requests.RequestException as exc:
            errors.append({"path": path, "error": str(exc)})
            continue

        records, sub_links = parse_page(path, current_url, body)

        if records:
            for rec in records:
                rec.update({
                    "source_page": path,
                    "site": entry.get("site"),
                    "role": entry.get("role"),
                    "vrf": entry.get("vrf"),
                    "needs_review": bool(entry.get("review")),
                    "review_note": entry.get("review"),
                })
            all_records.extend(records)
            processed_pages.append({"path": path, "records": len(records)})
        elif entry.get("index") or sub_links:
            processed_pages.append({"path": path, "records": 0, "expanded_as_index": True})
        else:
            processed_pages.append({"path": path, "records": 0})

        for link in sub_links:
            if link.lower() not in visited:
                queue.append((link, entry, depth + 1))

    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "base_url": BASE_URL,
            "total_records": len(all_records),
            "records": all_records,
            "processed_pages": processed_pages,
            "skipped_pages": skipped_pages,
            "errors": errors,
        }, f, ensure_ascii=False, indent=2)

    print(f"Registros extraidos: {len(all_records)}")
    print(f"Paginas procesadas: {len(processed_pages)}")
    print(f"Paginas omitidas (revision manual): {len(skipped_pages)}")
    print(f"Errores: {len(errors)}")
    print(f"Salida: {OUTPUT_FILE}")


if __name__ == "__main__":
    run()
