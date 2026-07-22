"""
Lee data/parsed_ips.json (generado por scrape.py) y crea en NetBox:
- un Prefix por cada /24 distinta que aparece en los datos
- una IPAddress por cada registro con datos reales

Idempotente: si el prefix o la IP ya existen (mismo valor + mismo VRF), se
omiten en vez de duplicarse o sobreescribirse - así se puede re-ejecutar
sin miedo tras corregir el manifiesto o añadir páginas nuevas.

Uso:
    NETBOX_URL=http://<host>:8080 NETBOX_TOKEN=<token> python load_to_netbox.py
"""
import json
import os
import sys
from pathlib import Path

import requests

NETBOX_URL = os.environ.get("NETBOX_URL", "http://localhost:8080").rstrip("/")
NETBOX_TOKEN = os.environ.get("NETBOX_TOKEN")
DATA_FILE = Path(__file__).parent / "data" / "parsed_ips.json"

if not NETBOX_TOKEN:
    sys.exit("Falta la variable de entorno NETBOX_TOKEN")

SESSION = requests.Session()
SESSION.headers.update({
    "Authorization": f"Token {NETBOX_TOKEN}",
    "Content-Type": "application/json",
})

_site_cache = {}
_vrf_cache = {}
_role_cache = {}
_prefix_cache = {}  # (subnet, vrf_name) -> prefix id


def api_get(endpoint, params):
    resp = SESSION.get(f"{NETBOX_URL}/api/{endpoint}/", params=params)
    resp.raise_for_status()
    return resp.json()["results"]


def api_post(endpoint, payload):
    resp = SESSION.post(f"{NETBOX_URL}/api/{endpoint}/", json=payload)
    if resp.status_code >= 300:
        raise RuntimeError(f"POST {endpoint} -> {resp.status_code}: {resp.text}")
    return resp.json()


def site_id(slug):
    if slug is None:
        return None
    if slug not in _site_cache:
        results = api_get("dcim/sites", {"slug": slug})
        _site_cache[slug] = results[0]["id"] if results else None
    return _site_cache[slug]


def vrf_id(name):
    if name is None:
        return None
    if name not in _vrf_cache:
        results = api_get("ipam/vrfs", {"name": name})
        _vrf_cache[name] = results[0]["id"] if results else None
    return _vrf_cache[name]


def role_id(slug):
    if slug is None:
        return None
    if slug not in _role_cache:
        results = api_get("ipam/roles", {"slug": slug})
        _role_cache[slug] = results[0]["id"] if results else None
    return _role_cache[slug]


def subnet_24(ip):
    octets = ip.split(".")
    return f"{octets[0]}.{octets[1]}.{octets[2]}.0/24"


def ensure_prefix(subnet, vrf_name, site_slug, role_slug, description):
    cache_key = (subnet, vrf_name)
    if cache_key in _prefix_cache:
        return _prefix_cache[cache_key]

    vid = vrf_id(vrf_name)
    params = {"prefix": subnet}
    if vid:
        params["vrf_id"] = vid
    else:
        params["vrf_id"] = "null"
    existing = api_get("ipam/prefixes", params)
    if existing:
        _prefix_cache[cache_key] = existing[0]["id"]
        return existing[0]["id"]

    payload = {"prefix": subnet, "status": "active", "description": description[:200]}
    if vid:
        payload["vrf"] = vid
    sid = site_id(site_slug)
    if sid:
        payload["site"] = sid
    rid = role_id(role_slug)
    if rid:
        payload["role"] = rid

    created = api_post("ipam/prefixes", payload)
    print(f"  prefix creado: {subnet} (vrf={vrf_name})")
    _prefix_cache[cache_key] = created["id"]
    return created["id"]


def ip_exists(address, vrf_name):
    vid = vrf_id(vrf_name)
    params = {"address": address}
    params["vrf_id"] = vid if vid else "null"
    return bool(api_get("ipam/ip-addresses", params))


def looks_like_hostname(label):
    return bool(label) and " " not in label and "/" not in label and len(label) <= 63


def create_ip(ip, vrf_name, label, source_page):
    address = f"{ip}/24"
    if ip_exists(address, vrf_name):
        return "existing"
    payload = {
        "address": address,
        "status": "active",
        "description": f"{label} [origen: {source_page}]"[:200],
        "tags": [{"name": "migracion-legacy"}],
    }
    vid = vrf_id(vrf_name)
    if vid:
        payload["vrf"] = vid
    if looks_like_hostname(label):
        payload["dns_name"] = label
    api_post("ipam/ip-addresses", payload)
    return "created"


def run():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    records = data["records"]

    print(f"Registros a procesar: {len(records)}")
    stats = {"prefixes": 0, "ip_created": 0, "ip_existing": 0, "errors": 0}
    review_touched = set()

    for rec in records:
        try:
            for ip_key in ("ip_1", "ip_2"):
                ip = rec.get(ip_key)
                if not ip:
                    continue
                subnet = subnet_24(ip)
                before = len(_prefix_cache)
                ensure_prefix(subnet, rec["vrf"], rec["site"], rec["role"], rec["source_page"])
                if len(_prefix_cache) > before:
                    stats["prefixes"] += 1
                result = create_ip(ip, rec["vrf"], rec["label"], rec["source_page"])
                stats[f"ip_{result}"] += 1
            if rec.get("needs_review"):
                review_touched.add(rec["source_page"])
        except Exception as exc:
            stats["errors"] += 1
            print(f"  ERROR en {rec.get('source_page')} / {rec.get('ip_1')}: {exc}")

    print("\n--- resumen ---")
    print(stats)
    if review_touched:
        print(f"\n{len(review_touched)} paginas importadas con sede/VRF marcados 'a revisar':")
        for p in sorted(review_touched):
            print(f"  - {p}")
        print("Revisa esos Sites en NetBox una vez confirmados con el equipo de redes.")


if __name__ == "__main__":
    run()
