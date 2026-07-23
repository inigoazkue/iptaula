"""
IP Taula - catálogo jerárquico de rangos de IP.

Modelo: una única tabla `nodes` autorreferenciada. Cada nodo es un "rango"
(hoja, con CIDR) o una "agrupacion" (contenedor de más rangos/agrupaciones).
Los nodos de primer nivel (parent_id NULL) fijan la celda de la matriz
(sede x rol) a la que pertenecen; los hijos heredan esa sede/rol del padre.
"""
from contextlib import asynccontextmanager, contextmanager
from ipaddress import ip_network
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


def validate_cidr(cidr):
    try:
        ip_network(cidr, strict=True)
    except ValueError as exc:
        raise HTTPException(400, f"Rango CIDR inválido: {exc}")


@app.get("/api/tree")
def get_tree():
    with get_db() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM nodes ORDER BY id")]

    by_parent = {}
    for row in rows:
        row["children"] = []
        by_parent.setdefault(row["parent_id"], []).append(row)

    nodes_by_id = {row["id"]: row for row in rows}
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


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
