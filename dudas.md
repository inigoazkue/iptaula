# Dudas de la migración de datos

Registro de los casos dudosos encontrados al volcar cada página del sistema antiguo (`http://10.114.10.166/IPs/`) a IP Taula, con la decisión tomada. Pensado para enseñárselo al responsable del área afectada, por si hubiera que corregir algo en el futuro.

## IPs_10_114_159.htm → grupo "Sistema Virtual" (Bilbo/Gestioa)

1. **IP duplicada `10.114.159.253`**: el documento original tiene dos nombres para la misma IP, `Plantilla win2003-64` y `Plantilla win2008-64`. Se cargó `Plantilla win2003-64` como nombre principal y se anotó `Plantilla win2008-64` en Oharrak. **Pendiente de confirmar cuál de las dos plantillas sigue en uso, o si hay que moverla a otra IP.**

2. **Equipos que solo tenían IP en la red de contenidos (10.124.159.x), sin pareja en la red de gestión (10.114.159.x)**: `Cabina MTOE IS-5000-A`, `Cabina MTOE IS-5000-B`, `Vcentersupport`, `Vmware io-analizer`, `MTM-WIN10-148`, `Frogak-iker`, `NginxDalet2 (nginx2re.bio.etb)`. Se creó un rango nuevo `10.124.159.0/24` ("Edukien sarea") dentro de "Sistema Virtual" y se cargaron ahí con su IP real.

   - **Caso aparte, sin cargar todavía**: `NAKIVO Transp ETB dedupl`. En el documento original su IP aparece como `10.114.159.110?` — con una interrogación literal, es decir, el propio autor del documento ya no estaba seguro del número. No tiene tampoco IP de contenidos. **No se ha cargado en ningún sitio; hace falta que alguien confirme la IP real de este equipo.**

3. **IP duplicada `10.114.159.231`**: tres nombres distintos para la misma IP: `MTM-WIN10.229` (se cargó como nombre principal, encajaba con el patrón de numeración +2 del resto de la serie MTM-WIN10.22x), `Mtoebiltegia` (tenía IP de contenidos `10.124.159.230`) y `Mtoe_samba_plantilla` (sin IP de contenidos). Se anotó en Oharrak la existencia de los otros dos nombres y la IP de contenidos de `Mtoebiltegia`. **Pendiente de asignar IPs reales y distintas a estos dos si siguen en uso.**

4. **Nombre `Suse_html5-i?igo`**: la interrogación era casi con toda seguridad una "ñ" mal guardada en el documento original. Se cambió a `Suse_html5-iñigo`.

5. **Bloque de IPs `10.126.159.13x`** (filas de `UBUNTUFLICKR`, `Managermir`, `Sles12`, `WS2003-64mir`, `Mammirrepvirt`, `OLWEBLOGIC`): se cargaron como `10.114.159.13x` por encajar en la secuencia consecutiva de IPs de esa zona del documento, pero **esto se aplicó sin confirmación explícita** — si alguno de estos equipos realmente vive en una red `10.126.159.x` real, habría que corregirlo.

## bilbao_10_114.htm → grupo "Bilbao Automatización" (Bilbo/Gestioa)

Página muy grande (685 filas, ~19 subredes distintas dentro de un único documento). Resumen de lo dudoso:

1. **Grafismo (10.114.106.0/24), fila con celda fusionada**: el documento original mezclaba en una sola celda cuatro pares IP/nombre: `10.114.106.121 ENGINE5-E04`, `10.114.106.150 VIZTRACKING-HUB`, `10.114.106.121 ENGINE-RA1` y `10.114.106.121 ENGINE-RA2` — es decir, tres nombres distintos para la misma IP `.121`, lo cual no puede ser cierto a la vez. Se cargó `ENGINE5-E04` en `.121` y `VIZTRACKING-HUB` en `.150`; **`ENGINE-RA1` y `ENGINE-RA2` NO se han cargado**, solo se anotó en Oharrak de `ENGINE5-E04` que el documento antiguo les daba la misma IP. **Hace falta que alguien confirme las IPs reales de ENGINE-RA1 y ENGINE-RA2.**

2. **ILO-CUTTER2**: en el documento original aparece como `10.124.158.111` (con una interrogación en el propio número, `10.124.158.111?`), nota "Konfiguratu gabe" (sin configurar). Está junto a `ILO-CUTTER1`, que sí vive en la red principal en `10.114.158.110`. **No se ha cargado en ningún sitio** — no está claro si su IP real es `10.114.158.111` (pareja de ILO-CUTTER1) o si de verdad vive en la red `10.124.158.x`. Hace falta confirmarlo.

3. **Erlojua - Radio Euskadi (10.111.0.220)**: aparece suelto en medio de la tabla de Bilbao, en una red (`10.111.0.x`) que no encaja con el resto de redes `10.114.x` de esta página. Se cargó igualmente, como rango independiente `10.111.0.0/24` en Bilbo/Gestioa (fuera de la agrupación "Bilbao Automatización"). **Pendiente de confirmar que este dispositivo pertenece realmente a Bilbao/Gestioa y no a otra sede o área.**

4. **IPs duplicadas dentro de la misma subred, resueltas sin preguntar por ser repeticiones sin conflicto real de contenido** (mismo dispositivo listado dos o más veces con texto casi idéntico, se dejó solo una entrada): `10.114.157.191`/`.192` (ACSLS1/ACSLS2, repetidos en mayúsculas y minúsculas), `10.114.158.92` (`ILO HOST92` repetido como simple `ILO`), `10.114.158.195` (`MTM-NEAR1` repetido 4 veces con la misma nota `LTO7`).

5. **`10.114.158.70` — conflicto real**: dos nombres distintos para la misma IP, `VHAIPM` y `VMWARE ARIA`. Se cargó `VHAIPM` como nombre principal y se anotó en Oharrak que `VMWARE ARIA` comparte la misma IP. **Pendiente de confirmar cuál de los dos sigue en uso o si hay que reasignar una IP.**

6. **Subredes cargadas vacías (reservadas, sin ningún dispositivo en el documento original)**: `ELIKA-FORTA` (10.114.55.x), `POST PO` (10.114.56.x), `Subred reservado para editores` (10.114.57.x), `Subred reservado para editores Edius` (10.114.63.x). Se crearon igualmente como rangos vacíos para dejar constancia de la reserva, a decisión del usuario.

7. **Nombres sin subred declarada explícitamente en el documento** (se les puso un nombre descriptivo propio, a falta de uno mejor — se pueden renombrar libremente desde la interfaz si no encajan): `10.114.10.x`, `Isilon` (10.114.9.x), `Birtualizazioa (OLVM/oVirt)` (10.114.155.x), `Esplotazioa` (10.114.154.x), `Garapena eta DMZ` (10.114.150.x), `Ekoizpen nagusia` (10.114.157.x), `Biltegiratzea eta DMZ` (10.114.158.x), `ESRS Dell EMC` (10.114.70.x, un único dispositivo).

8. **Nota huérfana sin IP**: al final del documento aparece una fila suelta con el texto "IBM 3550 m3" sin ninguna IP asociada. No se ha cargado en ningún sitio por no poder relacionarla con un host concreto.

## bilbao_10_114_11.htm → rango "Switch-ak / sareko ekipamendua" (dentro de "Sistema Virtual", Bilbo/Gestioa)

Página sencilla, una sola subred (10.114.11.0/24, 113 entradas cargadas). A petición del usuario, la columna "Ping" del documento original no se cargó (no se sabía qué representaba).

1. **IP duplicada `10.114.11.118`**: dos nombres distintos, `HOUSE MONITORING` (con nota "FLOW 3") y `MAM`. Se cargó `HOUSE MONITORING` como nombre principal y se anotó en Oharrak que `MAM` comparte la misma IP. **Pendiente de confirmar cuál de los dos sigue en uso.**

## bilbao_10_114_12.htm → rango independiente "10.114.12.x" (Bilbo/Gestioa, fuera de cualquier agrupación)

Página con varios equipos que en el documento original no tenían una IP explícita asignada (solo el nombre, en filas sueltas después de un equipo con IP conocida). Instrucción del usuario: reconstruir la IP por la secuencia, y en esas filas concretas dejar el campo Hostname vacío y poner el nombre original en Oharrak (para poder distinguir a simple vista qué entradas tienen IP confirmada en el documento y cuáles se han deducido).

1. **`EDKMIRLF2.1`, `EDKMIRLF3.1`, `EDKMIRLF4.1`**: sin IP en el original, justo después de `10.114.12.52` (`EDKMIRLF1.1`). Se les asignaron `.53`, `.54` y `.55` por ser las siguientes tres libres de la secuencia.

2. **`EDKMIRLF1.2`, `EDKMIRLF2.2`, `EDKMIRLF3.2`, `EDKMIRLF4.2`**: sin IP en el original, después de `10.114.12.61` (`EDKMIRSP2`). Aquí había **4** filas sin IP, no 3 como en el bloque anterior — se lo comenté al usuario (por simetría con el bloque `.51`/`.52`, donde `LF1.1` se quedaba con su propia IP inmediatamente después de la del switch principal) y confirmó asignar las 4 seguidas: `.62`, `.63`, `.64` y `.65`.

3. **`PRUEBAS ONLINE`**: la última fila del documento original decía literalmente "10.114.12.100-120" (un rango, no una IP única). Se cargó en cada una de las 21 IPs de `.100` a `.120`, con Oharrak="PRUEBAS ONLINE" y Hostname vacío.

4. **`HUALogs DC_MIR_Insight` — sin cargar, IP desconocida**: aparece en el documento original justo después de `10.114.12.70` (`iMaster3/3 DC_MIR`), sin ninguna IP propia ni forma clara de deducirla por secuencia (el hueco entre `.70` y el rango final `.100-120` es demasiado amplio para asumir nada). **Viene de la tabla de `bilbao_10_114_12.htm`, fila siguiente a `10.114.12.70`. Pendiente de averiguar su IP real.**
