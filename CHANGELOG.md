# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/). Este proyecto usa versionado semántico.

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
