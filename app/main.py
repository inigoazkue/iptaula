"""
IP Taula - catálogo jerárquico de rangos de IP.

Modelo: una tabla `nodes` autorreferenciada. Cada nodo es un "rango" (hoja,
con CIDR) o una "agrupacion" (contenedor de más rangos/agrupaciones). Los
nodos de primer nivel (parent_id NULL) fijan la celda de la matriz (sede x
rol) a la que pertenecen, y ambas dimensiones son configurables (tablas
`sites`/`roles`, no listas fijas en código).

Dentro de un "rango" se pueden registrar IPs en uso (`ip_entries`), cada
una con valores para columnas dinámicas (`columns_catalog` + `range_columns`
+ `ip_values`) - las columnas se definen una vez en un catálogo global y
cada rango elige cuáles de ellas usar.

Autenticación: solo lectura/búsqueda sin sesión; todas las escrituras
requieren haber iniciado sesión (cookie de sesión simple, sin JWT ni
librerías externas - hash de contraseña con pbkdf2 de la librería estándar).
"""
import hashlib
import os
import re
import secrets
import sqlite3
import unicodedata
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Optional

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

DB_PATH = os.environ.get("DB_PATH", "/data/iptaula.db")
STATIC_DIR = Path(__file__).parent / "static"

DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASSWORD = "Digibat@1"
SESSION_COOKIE = "session"
SESSION_MAX_AGE_DAYS = 30

DEFAULT_SITES = [
    ("bilbo", "Bilbo"), ("miramon", "Miramon"), ("gasteiz", "Gasteiz"),
    ("irunea", "Iruñea"), ("besteak", "Besteak"),
]
DEFAULT_ROLES = [
    ("gestioa", "Gestioa"), ("edukiak", "Edukiak"), ("produkziorako_sareak", "Produkziorako sareak"),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER REFERENCES nodes(id) ON DELETE CASCADE,
    site TEXT NOT NULL,
    role TEXT NOT NULL,
    node_type TEXT NOT NULL CHECK (node_type IN ('rango', 'agrupacion')),
    name TEXT NOT NULL,
    description TEXT,
    cidr TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS columns_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS range_columns (
    node_id INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    column_id INTEGER NOT NULL REFERENCES columns_catalog(id) ON DELETE CASCADE,
    PRIMARY KEY (node_id, column_id)
);

CREATE TABLE IF NOT EXISTS ip_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    ip TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(node_id, ip)
);

CREATE TABLE IF NOT EXISTS ip_values (
    ip_entry_id INTEGER NOT NULL REFERENCES ip_entries(id) ON DELETE CASCADE,
    column_id INTEGER NOT NULL REFERENCES columns_catalog(id) ON DELETE CASCADE,
    value TEXT,
    PRIMARY KEY (ip_entry_id, column_id)
);

CREATE TABLE IF NOT EXISTS auth_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    username TEXT NOT NULL,
    salt TEXT NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


# --- utilidades de contraseña (pbkdf2 de la librería estándar, sin dependencias nuevas) ---

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()
    return salt, digest


def verify_password(password, salt, digest):
    _, check = hash_password(password, salt)
    return secrets.compare_digest(check, digest)


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text or "x"


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def seed_defaults(conn):
    if not conn.execute("SELECT 1 FROM sites LIMIT 1").fetchone():
        conn.executemany("INSERT INTO sites (slug, name) VALUES (?, ?)", DEFAULT_SITES)
    if not conn.execute("SELECT 1 FROM roles LIMIT 1").fetchone():
        conn.executemany("INSERT INTO roles (slug, name) VALUES (?, ?)", DEFAULT_ROLES)
    if not conn.execute("SELECT 1 FROM auth_config WHERE id=1").fetchone():
        salt, digest = hash_password(DEFAULT_ADMIN_PASSWORD)
        conn.execute(
            "INSERT INTO auth_config (id, username, salt, password_hash) VALUES (1, ?, ?, ?)",
            (DEFAULT_ADMIN_USER, salt, digest),
        )


def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        conn.executescript(SCHEMA)
        seed_defaults(conn)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="IP Taula", lifespan=lifespan)


def require_auth(session: Optional[str] = Cookie(None)):
    if not session:
        raise HTTPException(401, "No autenticado")
    with get_db() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE token=?", (session,)).fetchone()
    if not row:
        raise HTTPException(401, "Sesión no válida")
    created = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
    if datetime.utcnow() - created > timedelta(days=SESSION_MAX_AGE_DAYS):
        raise HTTPException(401, "Sesión caducada")


class NodeIn(BaseModel):
    parent_id: Optional[int] = None
    site: Optional[str] = None
    role: Optional[str] = None
    node_type: str
    name: str
    description: Optional[str] = None
    cidr: Optional[str] = None


class NodeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cidr: Optional[str] = None


class ColumnIn(BaseModel):
    name: str


class RangeColumnIn(BaseModel):
    column_id: int


class IpValueSet(BaseModel):
    ip: str
    column_id: int
    value: Optional[str] = None


class NamedIn(BaseModel):
    name: str


class LoginIn(BaseModel):
    username: str
    password: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


def validate_cidr(cidr):
    try:
        ip_network(cidr, strict=True)
    except ValueError as exc:
        raise HTTPException(400, f"Rango CIDR inválido: {exc}")


def validate_ip_in_cidr(ip_str, cidr):
    try:
        addr = ip_address(ip_str)
    except ValueError:
        raise HTTPException(400, f"IP inválida: {ip_str}")
    if addr not in ip_network(cidr, strict=True):
        raise HTTPException(400, f"La IP {ip_str} no pertenece al rango {cidr}")


def get_range_node(conn, node_id):
    row = conn.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Rango no encontrado")
    if row["node_type"] != "rango":
        raise HTTPException(400, "El nodo no es un rango")
    return row


def valid_site(conn, slug):
    return conn.execute("SELECT 1 FROM sites WHERE slug=?", (slug,)).fetchone() is not None


def valid_role(conn, slug):
    return conn.execute("SELECT 1 FROM roles WHERE slug=?", (slug,)).fetchone() is not None


# --- árbol completo (sedes, roles y nodos con sus IPs/columnas) ---

@app.get("/api/tree")
def get_tree():
    with get_db() as conn:
        sites = [dict(r) for r in conn.execute("SELECT * FROM sites ORDER BY id")]
        roles = [dict(r) for r in conn.execute("SELECT * FROM roles ORDER BY id")]
        rows = [dict(r) for r in conn.execute("SELECT * FROM nodes ORDER BY id")]

        columns_by_node = {}
        for rc in conn.execute(
            "SELECT rc.node_id AS node_id, c.id AS column_id, c.name AS name "
            "FROM range_columns rc JOIN columns_catalog c ON c.id = rc.column_id "
            "ORDER BY c.name"
        ):
            columns_by_node.setdefault(rc["node_id"], []).append(
                {"id": rc["column_id"], "name": rc["name"]}
            )

        values_by_entry = {}
        for v in conn.execute("SELECT * FROM ip_values"):
            values_by_entry.setdefault(v["ip_entry_id"], {})[str(v["column_id"])] = v["value"]

        entries_by_node = {}
        for e in conn.execute("SELECT * FROM ip_entries"):
            entries_by_node.setdefault(e["node_id"], []).append({
                "id": e["id"], "ip": e["ip"], "values": values_by_entry.get(e["id"], {}),
            })
        for node_id, entries in entries_by_node.items():
            entries.sort(key=lambda e: ip_address(e["ip"]))

    by_parent = {}
    for row in rows:
        row["children"] = []
        if row["node_type"] == "rango":
            row["columns"] = columns_by_node.get(row["id"], [])
            row["ip_entries"] = entries_by_node.get(row["id"], [])
        by_parent.setdefault(row["parent_id"], []).append(row)

    for row in rows:
        row["children"] = by_parent.get(row["id"], [])

    tree = {s["slug"]: {r["slug"]: [] for r in roles} for s in sites}
    for row in by_parent.get(None, []):
        if row["site"] in tree and row["role"] in tree[row["site"]]:
            tree[row["site"]][row["role"]].append(row)

    return {"sites": sites, "roles": roles, "tree": tree}


@app.post("/api/nodes")
def create_node(node: NodeIn, _auth=Depends(require_auth)):
    if node.node_type not in ("rango", "agrupacion"):
        raise HTTPException(400, "node_type debe ser 'rango' o 'agrupacion'")
    if not node.name.strip():
        raise HTTPException(400, "El nombre es obligatorio")

    with get_db() as conn:
        if node.parent_id is None:
            if not node.site or not valid_site(conn, node.site) or not node.role or not valid_role(conn, node.role):
                raise HTTPException(400, "site/role inválidos para un nodo de primer nivel")
            site, role = node.site, node.role
        else:
            parent = conn.execute("SELECT * FROM nodes WHERE id=?", (node.parent_id,)).fetchone()
            if not parent:
                raise HTTPException(404, "Nodo padre no encontrado")
            if parent["node_type"] != "agrupacion":
                raise HTTPException(400, "Solo se puede añadir dentro de una agrupación")
            site, role = parent["site"], parent["role"]

        cidr = None
        if node.node_type == "rango":
            if not node.cidr:
                raise HTTPException(400, "El rango (CIDR) es obligatorio en un 'rango'")
            validate_cidr(node.cidr)
            cidr = node.cidr

        cur = conn.execute(
            "INSERT INTO nodes (parent_id, site, role, node_type, name, description, cidr) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (node.parent_id, site, role, node.node_type, node.name.strip(), node.description, cidr),
        )
        return {"id": cur.lastrowid}


@app.patch("/api/nodes/{node_id}")
def update_node(node_id: int, patch: NodeUpdate, _auth=Depends(require_auth)):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
        if not row:
            raise HTTPException(404, "No encontrado")

        name = patch.name.strip() if patch.name is not None else row["name"]
        if not name:
            raise HTTPException(400, "El nombre es obligatorio")
        description = patch.description if patch.description is not None else row["description"]
        cidr = row["cidr"]
        if row["node_type"] == "rango" and patch.cidr is not None:
            validate_cidr(patch.cidr)
            cidr = patch.cidr

        conn.execute(
            "UPDATE nodes SET name=?, description=?, cidr=? WHERE id=?",
            (name, description, cidr, node_id),
        )
    return {"ok": True}


@app.delete("/api/nodes/{node_id}")
def delete_node(node_id: int, _auth=Depends(require_auth)):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM nodes WHERE id=?", (node_id,)).fetchone()
        if not row:
            raise HTTPException(404, "No encontrado")
        conn.execute("DELETE FROM nodes WHERE id=?", (node_id,))
    return {"ok": True}


# --- sedes y roles (filas/columnas generales de la matriz) ---

def _list_named(table):
    with get_db() as conn:
        return [dict(r) for r in conn.execute(f"SELECT * FROM {table} ORDER BY id")]


def _create_named(table, name, _auth):
    name = name.strip()
    if not name:
        raise HTTPException(400, "El nombre es obligatorio")
    slug = slugify(name)
    with get_db() as conn:
        if conn.execute(f"SELECT 1 FROM {table} WHERE slug=?", (slug,)).fetchone():
            raise HTTPException(409, "Ya existe uno con ese nombre")
        cur = conn.execute(f"INSERT INTO {table} (slug, name) VALUES (?, ?)", (slug, name))
        return {"id": cur.lastrowid, "slug": slug, "name": name}


def _delete_named(table, node_column, item_id):
    with get_db() as conn:
        row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (item_id,)).fetchone()
        if not row:
            raise HTTPException(404, "No encontrado")
        in_use = conn.execute(
            f"SELECT COUNT(*) AS n FROM nodes WHERE {node_column}=?", (row["slug"],)
        ).fetchone()["n"]
        if in_use:
            raise HTTPException(409, f"No se puede borrar: {in_use} elemento(s) lo usan todavía")
        conn.execute(f"DELETE FROM {table} WHERE id=?", (item_id,))
    return {"ok": True}


@app.get("/api/sites")
def list_sites():
    return _list_named("sites")


@app.post("/api/sites")
def create_site(body: NamedIn, _auth=Depends(require_auth)):
    return _create_named("sites", body.name, _auth)


@app.delete("/api/sites/{site_id}")
def delete_site(site_id: int, _auth=Depends(require_auth)):
    return _delete_named("sites", "site", site_id)


@app.get("/api/roles")
def list_roles():
    return _list_named("roles")


@app.post("/api/roles")
def create_role(body: NamedIn, _auth=Depends(require_auth)):
    return _create_named("roles", body.name, _auth)


@app.delete("/api/roles/{role_id}")
def delete_role(role_id: int, _auth=Depends(require_auth)):
    return _delete_named("roles", "role", role_id)


# --- catálogo global de columnas de IP (menú aparte) ---

@app.get("/api/columns")
def list_columns():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM columns_catalog ORDER BY name").fetchall()
    return [dict(r) for r in rows]


@app.post("/api/columns")
def create_column(col: ColumnIn, _auth=Depends(require_auth)):
    name = col.name.strip()
    if not name:
        raise HTTPException(400, "El nombre de columna es obligatorio")
    with get_db() as conn:
        if conn.execute("SELECT id FROM columns_catalog WHERE name=?", (name,)).fetchone():
            raise HTTPException(409, "Ya existe una columna con ese nombre")
        cur = conn.execute("INSERT INTO columns_catalog (name) VALUES (?)", (name,))
        return {"id": cur.lastrowid, "name": name}


@app.delete("/api/columns/{column_id}")
def delete_column(column_id: int, _auth=Depends(require_auth)):
    with get_db() as conn:
        if not conn.execute("SELECT id FROM columns_catalog WHERE id=?", (column_id,)).fetchone():
            raise HTTPException(404, "No encontrada")
        conn.execute("DELETE FROM columns_catalog WHERE id=?", (column_id,))
    return {"ok": True}


# --- columnas activas de un rango concreto ---

@app.post("/api/nodes/{node_id}/columns")
def add_range_column(node_id: int, body: RangeColumnIn, _auth=Depends(require_auth)):
    with get_db() as conn:
        get_range_node(conn, node_id)
        if not conn.execute("SELECT id FROM columns_catalog WHERE id=?", (body.column_id,)).fetchone():
            raise HTTPException(404, "Columna no encontrada")
        conn.execute(
            "INSERT OR IGNORE INTO range_columns (node_id, column_id) VALUES (?, ?)",
            (node_id, body.column_id),
        )
    return {"ok": True}


@app.delete("/api/nodes/{node_id}/columns/{column_id}")
def remove_range_column(node_id: int, column_id: int, _auth=Depends(require_auth)):
    with get_db() as conn:
        get_range_node(conn, node_id)
        conn.execute(
            "DELETE FROM range_columns WHERE node_id=? AND column_id=?", (node_id, column_id)
        )
        conn.execute(
            "DELETE FROM ip_values WHERE column_id=? AND ip_entry_id IN "
            "(SELECT id FROM ip_entries WHERE node_id=?)",
            (column_id, node_id),
        )
    return {"ok": True}


# --- IPs dentro de un rango ---
# No hay "alta manual de IP": el frontend enumera todas las direcciones del
# CIDR y este único endpoint fija el valor de una columna para una de ellas,
# creando la fila si hacía falta y borrándola si se queda sin ningún valor
# (una IP sin datos no es distinta de una libre, no tiene sentido guardarla).

@app.put("/api/nodes/{node_id}/ip-values")
def set_ip_value(node_id: int, body: IpValueSet, _auth=Depends(require_auth)):
    with get_db() as conn:
        node = get_range_node(conn, node_id)
        validate_ip_in_cidr(body.ip, node["cidr"])
        if not conn.execute(
            "SELECT 1 FROM range_columns WHERE node_id=? AND column_id=?", (node_id, body.column_id)
        ).fetchone():
            raise HTTPException(400, "Esa columna no está activa en este rango")

        entry = conn.execute(
            "SELECT id FROM ip_entries WHERE node_id=? AND ip=?", (node_id, body.ip)
        ).fetchone()
        value = body.value or None

        if not entry:
            if value is None:
                return {"ok": True}
            entry_id = conn.execute(
                "INSERT INTO ip_entries (node_id, ip) VALUES (?, ?)", (node_id, body.ip)
            ).lastrowid
        else:
            entry_id = entry["id"]

        conn.execute(
            "INSERT INTO ip_values (ip_entry_id, column_id, value) VALUES (?, ?, ?) "
            "ON CONFLICT(ip_entry_id, column_id) DO UPDATE SET value=excluded.value",
            (entry_id, body.column_id, value),
        )

        remaining = conn.execute(
            "SELECT COUNT(*) AS n FROM ip_values WHERE ip_entry_id=? AND value IS NOT NULL AND value != ''",
            (entry_id,),
        ).fetchone()["n"]
        if remaining == 0:
            conn.execute("DELETE FROM ip_entries WHERE id=?", (entry_id,))

    return {"ok": True}


# --- autenticación ---

@app.get("/api/session")
def get_session(session: Optional[str] = Cookie(None)):
    if not session:
        return {"authenticated": False}
    with get_db() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE token=?", (session,)).fetchone()
        user = conn.execute("SELECT username FROM auth_config WHERE id=1").fetchone()
    if not row:
        return {"authenticated": False}
    created = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
    if datetime.utcnow() - created > timedelta(days=SESSION_MAX_AGE_DAYS):
        return {"authenticated": False}
    return {"authenticated": True, "username": user["username"] if user else None}


@app.post("/api/login")
def login(body: LoginIn, response: Response):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM auth_config WHERE id=1").fetchone()
    if not row or row["username"] != body.username or not verify_password(body.password, row["salt"], row["password_hash"]):
        raise HTTPException(401, "Usuario o contraseña incorrectos")
    token = secrets.token_hex(32)
    with get_db() as conn:
        conn.execute("INSERT INTO sessions (token) VALUES (?)", (token,))
    response.set_cookie(
        SESSION_COOKIE, token, httponly=True, samesite="lax",
        max_age=60 * 60 * 24 * SESSION_MAX_AGE_DAYS, path="/",
    )
    return {"ok": True}


@app.post("/api/logout")
def logout(response: Response, session: Optional[str] = Cookie(None)):
    if session:
        with get_db() as conn:
            conn.execute("DELETE FROM sessions WHERE token=?", (session,))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@app.post("/api/change-password")
def change_password(body: ChangePasswordIn, _auth=Depends(require_auth)):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM auth_config WHERE id=1").fetchone()
        if not verify_password(body.current_password, row["salt"], row["password_hash"]):
            raise HTTPException(400, "La contraseña actual no es correcta")
        if len(body.new_password) < 4:
            raise HTTPException(400, "La contraseña nueva es demasiado corta")
        salt, digest = hash_password(body.new_password)
        conn.execute("UPDATE auth_config SET password_hash=?, salt=? WHERE id=1", (digest, salt))
    return {"ok": True}


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
