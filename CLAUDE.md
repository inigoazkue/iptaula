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

Una columna del catálogo puede marcarse como `is_ip` o `is_hostname` (booleanos en `columns_catalog`, elegidos al crearla). No cambian cómo se guarda el valor (sigue siendo texto libre en `ip_values`); solo controlan qué botón de diagnóstico pinta el frontend junto a esa celda: `is_ip` añade un botón de ping que pinga el propio valor de la celda (no la IP de la fila); `is_hostname` añade un botón de resolución DNS inversa que, si encuentra nombre, lo escribe en la misma celda y lo guarda como si lo hubiera tecleado el usuario. Además, junto al ping de la IP principal de cada fila hay siempre un botón de resolución de hostname (ese no depende de ninguna columna, pinga/resuelve la IP de la fila directamente).

### Orden de los nodos y cómo se mueven

Cada nodo tiene una `position` (entero) que ordena a sus hermanos (mismos `parent_id`/`site`/`role`); `get_tree()` ordena por `position, id`. `POST /api/nodes/{id}/move` es el único endpoint para reordenar y para reparentar/cambiar de sede-rol a la vez:
- con `before_id`: inserta el nodo justo delante de ese hermano en el destino (reordenar sin cambiar de sitio, o cambiar de sitio insertándolo en un punto concreto);
- sin `before_id`: lo añade al final del destino (soltar en hueco vacío).
- Si el nodo movido es una `agrupacion`, su `site`/`role` — y los de **todos sus descendientes** — se actualizan para que coincidan con el nuevo destino (`get_descendant_ids()` + `UPDATE ... WHERE id IN (...)`). Se rechaza mover un nodo dentro de sí mismo o de uno de sus propios descendientes (comprobado con la misma función).

### Desegin/berregin: argazkis completos, no un log de comandos

`undo_stack`/`redo_stack` guardan hasta `UNDO_DEPTH` (4) argazkis JSON completos de `nodes`+`range_columns`+`ip_entries`+`ip_values` (no del catálogo de sedes/roles/columnas, que queda fuera de este mecanismo). `push_undo(conn)` toma un argazki **antes** de la mutación y se llama al principio de cada endpoint que cambia estructura o valores de IP (`create_node`, `update_node`, `delete_node`, `move_node`, `add_range_column`, `remove_range_column`, `set_ip_value`) — si añades un endpoint mutador nuevo sobre esas tablas, añade la llamada correspondiente o quedará fuera del undo. Se eligió argazki completo en vez de un log de comandos con su inversa porque recrear un nodo borrado con `INSERT` le habría dado un `id` nuevo (rompiendo cualquier referencia); restaurando el argazki entero (borrar todo de esas 4 tablas e insertar de vuelta indicando el `id` explícito, con `PRAGMA foreign_keys = OFF` durante el proceso para no depender del orden padre-antes-que-hijo) los ids sobreviven intactos a un undo+redo.

`POST /api/undo`/`POST /api/redo` mueven un argazki entre las dos pilas (además apilan el estado actual en la pila contraria, para poder deshacer el deshacer); cualquier acción mutadora nueva vacía `redo_stack` por completo (la rama "futuro" queda invalidada, como en cualquier editor). Disponible para `require_auth` (no solo admin): un usuario con rol `user` también puede deshacer sus propias ediciones de IP. El frontend refleja esto con dos botones (arriba a la derecha y dentro del modal de rango) cuyo estado habilitado/deshabilitado viene de `GET /api/history-status`.

### Ping por IP: diagnóstico desde el contenedor, no desde el navegador

`GET /api/ping/{ip}` hace de proxy a un `ping -c 6 -W 1 <ip>` real ejecutado en el propio contenedor (el navegador no tiene forma de emitir ICMP). Requiere `iputils-ping` instalado en la imagen (ver `Dockerfile`) y que el contenedor conserve `NET_RAW` (el set de capabilities por defecto de Docker lo incluye; no lo quites en `docker-compose.yml`). Devuelve `ok_count` (cuántas de las 6 respondieron) en vez de un simple booleano, para que el frontend pinte el botón en tramos (`pingTierClass()` en `index.html`): 0 = rojo, 1 = azul, 2-5 = naranja, 6 = verde. También distingue, aparte del conteo, si el propio `ping` vio un ICMP "Destination (Host/Net/Port) Unreachable" explícito de un router intermedio (`rejected: true`, significa que el paquete no llegó al destino) frente a un simple silencio/timeout (`rejected: false`) — este último caso es **ambiguo por diseño del propio ICMP**: no hay forma de distinguir "no llegó" de "llegó pero la respuesta se perdió" cuando no hay ningún mensaje de error de vuelta, así que solo se usa como detalle en el tooltip, no como un tramo de color aparte.

`GET /api/resolve/{ip}` hace una resolución DNS inversa (`socket.gethostbyaddr`, con `socket.setdefaulttimeout(5)` para no bloquear indefinidamente) desde el propio contenedor. Comparte estética con el ping (mismas clases CSS `ping-green`/`ping-red`/`pinging`) pero es binario: encontrado o no, sin tramos intermedios. Muchos equipos Windows de la red interna no tienen registro DNS inverso configurado; si la resolución DNS falla, se hace un segundo intento con `nbtscan` (`resolve_via_nbtscan()`), que pregunta el nombre NetBIOS directamente al host por UDP 137 — funciona para bastantes equipos Windows aunque el DNS no tenga nada. Si eso también falla (algunos equipos tienen NetBIOS Name Service desactivado o bloqueado por firewall aunque el resto de configuración parezca idéntica a la de otro equipo que sí resuelve), hay un tercer intento con `nmap --script smb-os-discovery` sobre el puerto 445 (`resolve_via_smb()`): negocia una sesión SMB real y le pregunta el nombre de equipo directamente, lo cual funciona en bastantes casos donde el 137 no responde porque el servicio SMB (compartición de ficheros) sigue accesible aunque el Name Service clásico esté apagado. Verificado empíricamente contra IPs reales de producción donde los otros dos métodos fallaban. La respuesta indica `source: "dns"`, `"netbios"` o `"smb"` para que el frontend pueda anotarlo en el tooltip. Requiere el paquete `nmap` en la imagen además de `nbtscan` (ver `Dockerfile`), igual que `iputils-ping` para el ping.

### Modo de borrado: los botones de borrar empiezan ocultos

`deleteModeEnabled` (variable JS, siempre `false` al cargar la página) controla si se renderiza el botón "ezabatu" de cada tarjeta (`canDelete()` = `isAdmin() && deleteModeEnabled`, en vez de solo `isAdmin()`). Se activa/desactiva con un botón candado junto al selector de tema; **si añades un botón de borrado nuevo en algún otro sitio, decide explícitamente si debe respetar `canDelete()` o si `isAdmin()` a secas es correcto ahí** — mezclar los dos (renderizar con uno y enganchar el evento con el otro) ya causó un bug real (el listener intentaba engancharse a un botón que no se había renderizado).

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
- Mover nodos es arrastrar y soltar (solo admin, `draggable=true` en cada tarjeta `.node`; el estado del arrastre en curso es la variable global `draggingNode`, no `dataTransfer.getData()`, para no depender de su soporte irregular durante `dragover`). Hay tres tipos de zona de soltado, cada uno con su propio `dragover`/`drop` con `stopPropagation()` para que no se disparen varios a la vez al estar anidados en el DOM: soltar sobre otra tarjeta (`move` con `before_id`), soltar en el hueco vacío de una celda `<td>` (`move` con `site`/`role`, a primer nivel) y soltar en el hueco vacío del área desplegada de una agrupación (`move` con `parent_id`, al final). `collectDescendantIds()` bloquea en el cliente soltar un grupo sobre uno de sus propios descendientes antes de llamar a la API (que también lo rechazaría, pero así se evita el viaje de ida y vuelta).

### Detalles del despliegue

La red corporativa exige pasar por un proxy con inspección (Zscaler) para cualquier salida HTTPS, incluido el `pip install` durante el build de Docker — el `Dockerfile` recibe `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` como build args (con valor por defecto en `docker-compose.yml` apuntando al proxy corporativo conocido, ya que `sudo` en el host de despliegue no propaga las variables de entorno del usuario) e instala el certificado raíz de Zscaler (`certs/ZscalerRootCertificate-2048-SHA256.crt`) en el almacén de confianza de la imagen de build para que `pip` pueda verificar el TLS a través del proxy que inspecciona el tráfico.

El servidor de producción (`ingprod@10.3.159.73` / `MIR-IPTAULA`) no tiene GitHub Actions ni ningún CI: desplegar es `git pull && sudo docker compose up -d --build` a mano (o por SSH). Dos detalles si se automatiza esto:
- `sudo` ahí necesita `-S` con la contraseña por stdin cuando se ejecuta sin pty (p.ej. `echo '<pass>' | sudo -S docker compose ...`), porque no propaga terminal interactiva por SSH en modo batch.
- El repo tiene dos remotos: `origin` (`http://gitlab149.bio.etb/ip_taula/ip_taula.git`, el interno de EITB, el que hay que mantener al día) y `github` (espejo público en `github.com/inigoazkue/iptaula`, secundario). Un `git push` a secas ya va a `origin`.
