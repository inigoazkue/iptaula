# IP Taula

Catálogo interno de rangos de IP de EITB. Sustituye al sistema antiguo de tablas en Word exportadas a HTML estático por una aplicación web propia: una matriz de sedes × tipos de red, con rangos organizables en agrupaciones, y el detalle de las IPs de cada rango con columnas configurables (hostname, MAC, lo que haga falta).

Interfaz en euskera. Aplicación mínima a propósito: un backend en Python (FastAPI) y una única página HTML sin dependencias de frontend, con SQLite como base de datos.

## Puesta en marcha

Requiere Docker y Docker Compose.

```bash
git clone <url-del-repo>
cd iptaula
docker compose up -d --build
```

La aplicación queda escuchando en el puerto `8000`. Los datos se guardan en `./data/iptaula.db` (SQLite, montado desde el host), así que sobreviven a reconstrucciones del contenedor.

En el primer arranque se crea un usuario administrador por defecto:

```
usuario:    admin
contraseña: Digibat@1
```

**Cambia esa contraseña en cuanto entres** (menú de engranaje, abajo a la derecha → "Pasahitza aldatu").

### Desarrollo local sin Docker

```bash
pip install fastapi "uvicorn[standard]"
DB_PATH=./data/iptaula.db python -m uvicorn main:app --app-dir app --reload --port 8000
```

## Cómo funciona

- **Matriz**: las columnas son las sedes y las filas los tipos de red; ambas dimensiones se pueden añadir/quitar desde el menú de engranaje ("Taula orokorra kudeatu"), no están fijas en el código.
- **Rangos y agrupaciones**: dentro de cada celda se pueden crear rangos (con su CIDR) o agrupaciones que contienen más rangos/agrupaciones, anidables sin límite. Se pueden mover y reordenar arrastrando y soltando.
- **Columnas por IP**: cada rango puede activar las columnas que necesite de un catálogo global (menú de engranaje → "IP taulen zutabeak kudeatu"); una columna se puede marcar como IP (botón de ping sobre su valor) o como Hostname (botón de resolución DNS inversa). Al abrir un rango se ve una tabla con todas las IPs del CIDR, lista para rellenar directamente (se guarda sola al salir del campo); las IPs libres consecutivas se agrupan para no ocupar espacio, y hay un botón para vaciar una fila entera de golpe.
- **Diagnóstico por IP**: botón de ping (colores según cuántas de 6 respuestas llegan) y botón de resolución de hostname, ambos ejecutados desde el propio servidor.
- **Deshacer/rehacer**: hasta 4 pasos atrás para altas, cambios, borrados y movimientos.
- **Búsqueda**: el buscador de arriba busca por IP, nombre, descripción o cualquier valor de columna, resalta y despliega las coincidencias en la matriz, y muestra el detalle coincidente directamente en la tarjeta.
- **Modo de borrado**: los botones de borrar de las tarjetas están ocultos hasta activarlos con el candado junto al selector de tema, para evitar borrados accidentales.
- **Roles de usuario**:
  - **admin**: control total (crear/renombrar/borrar rangos y agrupaciones, gestionar columnas, sedes, tipos de red y usuarios).
  - **user**: puede navegar, buscar, y añadir/editar los valores de IP de los rangos ya existentes, pero no crear ni borrar rangos ni tocar la estructura.
  - Sin sesión iniciada solo se puede navegar y buscar (modo de solo lectura).

Más detalle de la arquitectura y los invariantes del modelo de datos en [CLAUDE.md](CLAUDE.md).

## Estructura del repositorio

```
app/
  main.py          backend FastAPI (API + esquema SQLite)
  static/
    index.html     todo el frontend (HTML + CSS + JS, sin build)
certs/             certificado raíz del proxy corporativo, para el build de Docker
Dockerfile
docker-compose.yml
requirements.txt
```

## Notas de despliegue

El build de Docker necesita salir a Internet (para `pip install`) a través del proxy corporativo (Zscaler), que inspecciona el TLS. El `Dockerfile` y `docker-compose.yml` ya vienen preparados para eso (ver la sección correspondiente en [CLAUDE.md](CLAUDE.md)); si se despliega fuera de esa red, esas variables de proxy son inocuas de más.
