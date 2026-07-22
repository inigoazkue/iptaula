"""
Crea en NetBox el modelo inicial deducido del sistema antiguo de tablas IP:
- Sites: una por sede
- VRFs: solo para las redes privadas aisladas que reutilizan rangos RFC1918
  (las redes corporativas NO llevan VRF: viven en la tabla "global", ya que
  todas las sedes están enrutadas entre sí y no debe haber solapes entre ellas)
- Roles de prefijo: equivalentes a las filas "tipo de red" de la tabla original

Uso:
    NETBOX_URL=http://<host>:8080 NETBOX_TOKEN=<SUPERUSER_API_TOKEN> python bootstrap_netbox.py
"""
import os
import sys

import requests

NETBOX_URL = os.environ.get("NETBOX_URL", "http://localhost:8080").rstrip("/")
NETBOX_TOKEN = os.environ.get("NETBOX_TOKEN")

if not NETBOX_TOKEN:
    sys.exit("Falta la variable de entorno NETBOX_TOKEN (usa SUPERUSER_API_TOKEN del .env)")

SESSION = requests.Session()
SESSION.headers.update({
    "Authorization": f"Token {NETBOX_TOKEN}",
    "Content-Type": "application/json",
})

SITES = [
    {"name": "Bilbao", "slug": "bilbao"},
    {"name": "Miramon", "slug": "miramon"},
    {"name": "Gasteiz", "slug": "gasteiz"},
    {"name": "Madrid", "slug": "madrid"},
    {"name": "Iruna", "slug": "iruna"},
]

# Cada una es una isla de direccionamiento aislada que puede solapar rangos
# RFC1918 con cualquier otra sin conflicto (ver conversación: 192.168.x.x
# repetido entre DMZ Bilbao, privadas Miramón y privadas Radios).
VRFS = [
    {"name": "DMZ-BIO", "description": "DMZ de Bilbao, aislada de la red corporativa"},
    {"name": "PRIV-MIR", "description": "Red privada de Miramón, aislada"},
    {"name": "PRIV-RADIOS", "description": "Red privada de Radios, aislada"},
    {"name": "AOIP-CALREC", "description": "Redes AoIP del sistema Calrec (irratia_calrec), a confirmar si requiere más de un VRF"},
]

# Equivalen a las filas "tipo de red" de la tabla original (GEST/CONT/PRIV/RADIOS)
ROLES = [
    {"name": "Gestion", "slug": "gestion", "description": "Redes de gestión de infraestructura (fila GEST)"},
    {"name": "Contenidos", "slug": "contenidos", "description": "Redes de producción/contenidos audiovisuales (fila CONT)"},
    {"name": "Privada", "slug": "privada", "description": "Redes privadas aisladas (fila PRIV)"},
    {"name": "Radios", "slug": "radios", "description": "Redes de radio (fila RADIOS)"},
]


def get_existing(endpoint, key="name"):
    resp = SESSION.get(f"{NETBOX_URL}/api/{endpoint}/", params={"limit": 0})
    resp.raise_for_status()
    return {item[key] for item in resp.json()["results"]}


def create_missing(endpoint, items, key="name"):
    existing = get_existing(endpoint, key)
    for item in items:
        if item[key] in existing:
            print(f"  ya existe: {item[key]}")
            continue
        resp = SESSION.post(f"{NETBOX_URL}/api/{endpoint}/", json=item)
        if resp.status_code >= 300:
            print(f"  ERROR creando {item[key]}: {resp.status_code} {resp.text}")
        else:
            print(f"  creado: {item[key]}")


print("Sites:")
create_missing("dcim/sites", SITES)

print("VRFs:")
create_missing("ipam/vrfs", VRFS)

print("Roles de prefijo:")
create_missing("ipam/roles", ROLES)

print("\nListo. Siguiente paso: migrar los prefijos/IPs reales de las tablas HTML/Word a estos Sites/VRFs/Roles.")
