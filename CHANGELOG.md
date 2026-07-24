# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/). Este proyecto usa versionado semántico.

## [1.2.0] - 2026-07-24

### Añadido

- Resolución de hostname sin registro DNS: cuando falla la resolución DNS inversa, se intenta por NetBIOS (nbtscan) y, si tampoco responde, por SMB (nmap smb-os-discovery negociando una sesión real sobre el puerto 445) — cubre equipos con el servicio de nombres NetBIOS clásico desactivado o bloqueado por firewall.
- Las cabeceras de la tabla de IPs se quedan fijas al hacer scroll hacia abajo en el modal de edición.
- Botón para lanzar ping u resolución de hostname sobre todas las IPs del rango a la vez, junto a los títulos "Ping"/"Host.Res.".
- Las columnas de datos de la tabla de IPs se pueden reordenar arrastrándolas (no aplica a la columna de IP ni a la de diagnóstico).
- Las columnas de la tabla de IPs se pueden ensanchar arrastrando su borde; al hacerlo, el modal se ensancha en la misma medida (y se estrecha de vuelta sin bajar de su tamaño inicial).

### Cambiado

- Ping y resolución de hostname ya no requieren haber iniciado sesión.
- Reescrita la tabla de IPs con `<colgroup>` para que el ancho de cada columna sea fiable con cabeceras agrupadas (antes "IP honen diagnostikoa" impedía calcular bien el ancho de Ping/Host.Res. por separado).

### Corregido

- Las celdas con botón de ping/resolución (que habían perdido el centrado vertical al forzar `display:flex` directamente en la celda) vuelven a centrarse correctamente.
- `remove_range_column` ya no deja entradas de IP huérfanas sin ningún valor al quitar una columna de un rango.
- Texto de ayuda para usuarios sin sesión: decía "laranja = erabilita" (naranja) cuando el color real de fila usada es azul.

## [1.1.0] - 2026-07-23

### Añadido

- Reordenar y mover agrupaciones/rangos arrastrando y soltando (en vez de solo al crearlos), incluyendo soltar directamente sobre una agrupación colapsada y un resaltado visual de la zona de destino (antes/después/dentro).
- Deshacer/rehacer (hasta 4 pasos) para altas, cambios, borrados y movimientos de la estructura y de los valores de IP, con dos botones en la página principal y en el modal de edición de rango.
- Botón de ping por IP en el modal de edición, con colores por tramos según cuántas de las 6 respuestas llegan: rojo (0), azul (1), naranja (2-5), verde (6).
- Columnas del catálogo marcables como **IP** (ping directo sobre su valor) o **Hostname** (botón de resolución DNS inversa que rellena y guarda la celda); además, un botón de resolución de hostname siempre presente junto al ping principal de cada IP.
- Las IPs libres consecutivas (3 o más seguidas) se agrupan en una fila plegada; filtro para mostrar solo las ocupadas, solo las libres o todas.
- Botón para mostrar/ocultar columnas en la tabla de IPs, y botón para vaciar una fila entera (liberar la IP) de un clic.
- Modo de borrado: los botones de borrar de las tarjetas están ocultos hasta activarlos con un botón candado junto al selector de tema; empieza siempre desactivado.
- Los resultados de una búsqueda que coinciden con una IP o un valor de columna se muestran directamente en la tarjeta del rango, sin necesidad de abrir el modal; botón para vaciar el buscador.
- Diseño adaptado a pantallas pequeñas, cierre de los modales al clicar fuera, y favicon propio.

### Cambiado

- La vista previa de cada rango en la matriz general ya no muestra una mini-tabla de IPs; solo nombre, descripción y CIDR, para que las tarjetas ocupen menos espacio.
- En el modal de edición de rango, los datos del tramo y las columnas activas se muestran en dos columnas lado a lado (con título y separador) en vez de apiladas, para que la tabla de IPs empiece más arriba.
- Las IPs ocupadas se resaltan en azul cielo en vez de naranja.
- Textos del menú de ajustes: "Matrizea kudeatu" → "Taula orokorra kudeatu", "Zutabeak kudeatu" → "IP taulen zutabeak kudeatu".

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
