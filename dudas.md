# Dudas de la migración de datos

Registro de los casos dudosos encontrados al volcar cada página del sistema antiguo (`http://10.114.10.166/IPs/`) a IP Taula, con la decisión tomada. Pensado para enseñárselo al responsable del área afectada, por si hubiera que corregir algo en el futuro.

## IPs_10_114_159.htm → grupo "Sistema Virtual" (Bilbo/Gestioa)

1. **IP duplicada `10.114.159.253`**: el documento original tiene dos nombres para la misma IP, `Plantilla win2003-64` y `Plantilla win2008-64`. Se cargó `Plantilla win2003-64` como nombre principal y se anotó `Plantilla win2008-64` en Oharrak. **Pendiente de confirmar cuál de las dos plantillas sigue en uso, o si hay que moverla a otra IP.**

2. **Equipos que solo tenían IP en la red de contenidos (10.124.159.x), sin pareja en la red de gestión (10.114.159.x)**: `Cabina MTOE IS-5000-A`, `Cabina MTOE IS-5000-B`, `Vcentersupport`, `Vmware io-analizer`, `MTM-WIN10-148`, `Frogak-iker`, `NginxDalet2 (nginx2re.bio.etb)`. Se creó un rango nuevo `10.124.159.0/24` ("Edukien sarea") dentro de "Sistema Virtual" y se cargaron ahí con su IP real.

   - **Caso aparte, sin cargar todavía**: `NAKIVO Transp ETB dedupl`. En el documento original su IP aparece como `10.114.159.110?` — con una interrogación literal, es decir, el propio autor del documento ya no estaba seguro del número. No tiene tampoco IP de contenidos. **No se ha cargado en ningún sitio; hace falta que alguien confirme la IP real de este equipo.**

3. **IP duplicada `10.114.159.231`**: tres nombres distintos para la misma IP: `MTM-WIN10.229` (se cargó como nombre principal, encajaba con el patrón de numeración +2 del resto de la serie MTM-WIN10.22x), `Mtoebiltegia` (tenía IP de contenidos `10.124.159.230`) y `Mtoe_samba_plantilla` (sin IP de contenidos). Se anotó en Oharrak la existencia de los otros dos nombres y la IP de contenidos de `Mtoebiltegia`. **Pendiente de asignar IPs reales y distintas a estos dos si siguen en uso.**

4. **Nombre `Suse_html5-i?igo`**: la interrogación era casi con toda seguridad una "ñ" mal guardada en el documento original. Se cambió a `Suse_html5-iñigo`.

5. **Bloque de IPs `10.126.159.13x`** (filas de `UBUNTUFLICKR`, `Managermir`, `Sles12`, `WS2003-64mir`, `Mammirrepvirt`, `OLWEBLOGIC`): se cargaron como `10.114.159.13x` por encajar en la secuencia consecutiva de IPs de esa zona del documento, pero **esto se aplicó sin confirmación explícita** — si alguno de estos equipos realmente vive en una red `10.126.159.x` real, habría que corregirlo.
