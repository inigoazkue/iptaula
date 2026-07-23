# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/). Este proyecto usa versionado semántico.

## [1.1.0] - 2026-07-23

### Añadido

- Reordenar y mover agrupaciones/rangos arrastrando y soltando (en vez de solo al crearlos), incluyendo soltar directamente sobre una agrupación colapsada y un resaltado visual de la zona de destino (antes/después/dentro).
- Deshacer/rehacer (hasta 4 pasos) para altas, cambios, borrados y movimientos de la estructura y de los valores de IP, con dos botones en la página principal y en el modal de edición de rango.
- Botón de ping por IP en el modal de edición: verde si responde, naranja mientras lo intenta (hasta 6 intentos), rojo si no llega.

### Cambiado

- La vista previa de cada rango en la matriz general ya no muestra una mini-tabla de IPs; solo nombre, descripción y CIDR, para que las tarjetas ocupen menos espacio.

## [1.0.0] - 2026-07-24

Primera versión estable. Sustituye por completo al sistema anterior de tablas en Word exportadas a HTML.

### Añadido

- Matriz de sedes × tipos de red, ambas dimensiones configurables (alta/baja desde el menú de gestión), como página de entrada.
- Modelo de rangos y agrupaciones anidables sin límite dentro de cada celda de la matriz.
- Rangos con CIDR validado, nombre y descripción opcional.
- Catálogo global de columnas de IP (hostname, MAC, o cualquier otra que se necesite), activables por rango.
- Tabla de IPs por rango que enumera automáticamente todo el CIDR (sin alta manual de direcciones), editable celda a celda con guardado automático; filas libres y ocupadas diferenciadas visualmente.
- Buscador general (IP, nombre, descripción, valores de columna) que despliega y resalta las coincidencias en la matriz.
- Autenticación con dos roles: **admin** (control total) y **user** (solo puede añadir/editar valores de IP en rangos existentes, sin permiso para crear, renombrar o borrar estructura).
- Gestión de usuarios, cambio de contraseña, y modo de solo lectura para quien no ha iniciado sesión.
- Modo claro/oscuro con selector manual, respetando la preferencia del sistema por defecto.
- Interfaz completa en euskera.
- Despliegue en un único contenedor Docker (FastAPI + SQLite embebida), sin base de datos ni servicios auxiliares aparte.

### Cambiado

- Arquitectura sustituida de NetBox (evaluado inicialmente) a una aplicación a medida: para el volumen de datos real, NetBox suponía más aparato operativo (5 contenedores) del que aportaba valor, y no encajaba con la estructura de matriz personalizada que se necesitaba.
