"""
IP Taula - catálogo jerárquico de rangos de IP.

Modelo: una tabla `nodes` autorreferenciada. Cada nodo es un "rango" (hoja,
con CIDR) o una "agrupacion" (contenedor de más rangos/agrupaciones). Los
nodos de primer nivel (parent_id NULL) fijan la celda de la matriz (sede x
rol) a la que pertenecen; los hijos heredan esa sede/rol del padre.

Dentro de un "rango" se pueden registrar IPs en uso (`ip_entries`), cada
una con valores para columnas dinámicas (`columns_catalog` + `range_columns`
+ `ip_values`) - las columnas se definen una vez en un catálogo global y
cada rango elige cuáles de ellas usar.
"""
from contextlib import asynccontextmanager, contextmanager
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Optional
import os
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

DB_PATH = os.environ.get("DB_PATH", "/data/iptaula.db")
STATIC_DIR = Path(__file__).parent / "static"

SITES = ["bilbo", "miramon", "gasteiz", "irunea", "besteak"]
ROLES = ["gestioa", "edukiak", "produkziorako_sareak"]

SCHEMA = """
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
"""


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


def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        conn.executescript(SCHEMA)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="IP Taula", lifespan=lifespan)


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


@app.get("/api/tree")
def get_tree():
    with get_db() as conn:
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

    tree = {site: {role: [] for role in ROLES} for site in SITES}
    for row in by_parent.get(None, []):
        tree[row["site"]][row["role"]].append(row)
    return tree


@app.post("/api/nodes")
def create_node(node: NodeIn):
    if node.node_type not in ("rango", "agrupacion"):
        raise HTTPException(400, "node_type debe ser 'rango' o 'agrupacion'")
    if not node.name.strip():
        raise HTTPException(400, "El nombre es obligatorio")

    with get_db() as conn:
        if node.parent_id is None:
            if node.site not in SITES or node.role not in ROLES:
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
def update_node(node_id: int, patch: NodeUpdate):
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
def delete_node(node_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM nodes WHERE id=?", (node_id,)).fetchone()
        if not row:
            raise HTTPException(404, "No encontrado")
        conn.execute("DELETE FROM nodes WHERE id=?", (node_id,))
    return {"ok": True}


# --- catálogo global de columnas (menú aparte) ---

@app.get("/api/columns")
def list_columns():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM columns_catalog ORDER BY name").fetchall()
    return [dict(r) for r in rows]


@app.post("/api/columns")
def create_column(col: ColumnIn):
    name = col.name.strip()
    if not name:
        raise HTTPException(400, "El nombre de columna es obligatorio")
    with get_db() as conn:
        if conn.execute("SELECT id FROM columns_catalog WHERE name=?", (name,)).fetchone():
            raise HTTPException(409, "Ya existe una columna con ese nombre")
        cur = conn.execute("INSERT INTO columns_catalog (name) VALUES (?)", (name,))
        return {"id": cur.lastrowid, "name": name}


@app.delete("/api/columns/{column_id}")
def delete_column(column_id: int):
    with get_db() as conn:
        if not conn.execute("SELECT id FROM columns_catalog WHERE id=?", (column_id,)).fetchone():
            raise HTTPException(404, "No encontrada")
        conn.execute("DELETE FROM columns_catalog WHERE id=?", (column_id,))
    return {"ok": True}


# --- columnas activas de un rango concreto ---

@app.post("/api/nodes/{node_id}/columns")
def add_range_column(node_id: int, body: RangeColumnIn):
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
def remove_range_column(node_id: int, column_id: int):
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
def set_ip_value(node_id: int, body: IpValueSet):
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


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
