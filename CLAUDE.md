# CLAUDE.md

Este fichero da contexto a Claude Code (claude.ai/code) para trabajar en este repositorio.

## Qué es esto

IP Taula es el catálogo de rangos de IP interno de EITB. Sustituye a un sistema antiguo de documentos Word editados a mano y exportados a HTML estático. Toda la aplicación son dos ficheros: `app/main.py` (backend FastAPI) y `app/static/index.html` (una única página autocontenida — sin build, sin framework, sin npm). SQLite es el único almacén de datos.

## Cómo ejecutarlo

En local, sin Docker (el ciclo más rápido mientras se edita):
```bash
pip install fastapi "uvicorn[standard]"
DB_PATH=./data/iptaula.db python -m uvicorn main:app --app-dir app --reload --port 8000
```

Con Docker Compose (igual que en producción):
```bash
docker compose up -d --build
```
El fichero SQLite vive en `./data/iptaula.db` en el host (bind-mount), así que sobrevive a reconstrucciones del contenedor.

No hay suite de tests ni linter configurados. Así se ha validado el código hasta ahora:
- Python: `python -c "import ast; ast.parse(open('app/main.py', encoding='utf-8').read())"` como chequeo de sintaxis barato, más probar los endpoints directamente con `curl` (flujos de alta/lectura/edición/borrado, flujos de autenticación) contra un `DB_PATH` desechable antes de dar un cambio por bueno.
- JS del frontend: extraer el bloque `<script>` de `index.html` y pasarle `node --check`, ya que no hay bundler que detecte errores de sintaxis de otra forma.

## Arquitectura

### Modelo de datos: un único árbol autorreferenciado

Todo vive en una tabla `nodes` (ver `SCHEMA` en `app/main.py`). Un nodo es:
- un **`rango`** (hoja): tiene un CIDR, opcionalmente una descripción, y puede llevar datos por IP (ver más abajo).
- una **`agrupacion`** (contenedor): agrupa más `rango`/`agrupacion` hijos vía `parent_id`.

Los nodos de primer nivel (`parent_id IS NULL`) declaran una `site` y un `role`, que los sitúa en una celda de la matriz que pinta el frontend (sedes = columnas, tipos de red = filas). Ambas dimensiones están en tablas propias (`sites`, `roles`), no fijas en código — un admin puede añadir/quitar sedes o tipos en caliente vía `/api/sites` y `/api/roles`. Los hijos heredan la `site`/`role` del padre; solo hace falta indicarlas al crear un nodo de primer nivel.

### Los datos por IP son de esquema dinámico, no un conjunto fijo de columnas

Un `rango` no tiene campos fijos tipo "hostname" o "MAC". En su lugar:
- `columns_catalog` es un catálogo global de nombres de columna posibles (p.ej. "Hostname", "MAC"), gestionado por un admin.
- `range_columns` dice cuáles de esas columnas están activas en un rango concreto.
- `ip_entries` + `ip_values` guardan los valores reales por IP (una fila de `ip_entries` por cada IP con *algún* dato; `ip_values` es una fila por cada (entrada, columna)).

No existe un paso de "añadir IP". El frontend enumera en el cliente todas las direcciones de host del CIDR del rango (`hostsOf()` en `index.html`) y pinta una fila por dirección, tenga o no datos todavía. Editar una celda llama a `PUT /api/nodes/{id}/ip-values`, un único endpoint idempotente que crea la fila de `ip_entries` en la primera escritura y **la borra de nuevo si se queda sin ningún valor no vacío** — una IP sin nada registrado es indistinguible de una libre, así que no se persiste nada para ella. Si tocas ese endpoint, conserva este invariante: no reintroduzcas un flujo separado de crear/borrar IP.

### Autenticación: dos roles, sesión por cookie, sin dependencias externas

- Las contraseñas se hashean con `hashlib.pbkdf2_hmac` de la librería estándar (sin bcrypt/passlib, a propósito, para no añadir instalaciones de pip detrás del proxy corporativo — ver más abajo).
- Las sesiones son un token aleatorio en una cookie httponly, buscado en una tabla `sessions` (`get_current_user` en `app/main.py`). Sin JWT.
- Dos roles: `admin` (todo) y `user` (solo puede leer/buscar y editar valores de IP ya existentes vía `PUT .../ip-values`; no puede crear/renombrar/borrar nodos, gestionar el catálogo de columnas, ni gestionar sedes/roles/usuarios). Se aplica con dos dependencias de FastAPI, `require_auth` (cualquier usuario con sesión) y `require_admin` (solo admin) — al añadir un endpoint de escritura nuevo, decide cuál de las dos necesita en vez de usar `require_auth` por defecto.
- Todos los endpoints de lectura (`GET /api/tree`, `/api/columns`, `/api/sites`, `/api/roles`) son públicos/sin autenticar a propósito — navegar y buscar funciona sin iniciar sesión.

### Los cambios de esquema requieren migración manual

No hay framework de migraciones — `SCHEMA` en `app/main.py` se aplica con `executescript()` en cada arranque, y `CREATE TABLE IF NOT EXISTS` **no hace nada a una tabla que ya existe** con una forma antigua. Esto ya causó un bug en producción: `sessions` ganó una columna `user_id`, pero las bases de datos ya desplegadas se quedaron con la forma vieja hasta que se añadió `migrate_schema()` para detectarlo explícitamente y hacer `DROP TABLE`/recrearla. Si cambias la forma de una tabla que ya esté en producción, añade un paso equivalente explícito en `migrate_schema()` (se llama desde `init_db()` antes de `executescript`) en vez de asumir que el `CREATE TABLE IF NOT EXISTS` se encargará.

### Estructura del frontend

`app/static/index.html` es un único fichero: `<style>` inline (variables CSS para el tema, claro/oscuro vía `prefers-color-scheme` y un `data-theme` que el usuario puede forzar) y `<script>` inline (JS puro, sin imports). Piezas clave:
- `loadAll()`/`refresh()` piden `/api/tree`, `/api/columns` y `/api/session` y repintan todo desde esa foto fija; no hay sincronización de estado más fina que esa.
- `renderGrid()` construye la tabla matriz sede×rol; `renderNode()` pinta un nodo y sus hijos recursivamente.
- Varios `<dialog>` (modales nativos de HTML) hacen de ventana modal: detalle/edición de rango, catálogo de columnas, gestión de matriz (sedes/roles), gestión de usuarios, login, cambio de contraseña.
- El texto de la interfaz está íntegramente en euskera, incluidos los mensajes de error que genera el backend (`HTTPException`). Mantén en euskera cualquier texto nuevo de cara al usuario, por coherencia.
- Los controles de edición se muestran u ocultan según `isAuthenticated`/`isAdmin()` calculado en el cliente a partir de `/api/session` — pero la autoridad real es el backend (cada endpoint de escritura vuelve a comprobar con `require_auth`/`require_admin`), así que el filtrado del frontend es solo para no mostrar controles que el usuario no podría usar, no una barrera de seguridad.

### Detalles del despliegue

La red corporativa exige pasar por un proxy con inspección (Zscaler) para cualquier salida HTTPS, incluido el `pip install` durante el build de Docker — el `Dockerfile` recibe `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` como build args (con valor por defecto en `docker-compose.yml` apuntando al proxy corporativo conocido, ya que `sudo` en el host de despliegue no propaga las variables de entorno del usuario) e instala el certificado raíz de Zscaler (`certs/ZscalerRootCertificate-2048-SHA256.crt`) en el almacén de confianza de la imagen de build para que `pip` pueda verificar el TLS a través del proxy que inspecciona el tráfico.
