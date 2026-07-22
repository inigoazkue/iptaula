"""
Mapa de página -> (sede, rol, VRF) deducido de la cuadrícula de default.aspx
y del menú (menu.aspx) del sistema actual. Es la única fuente de esa
información: no se puede reconstruir leyendo solo la página de detalle.

site: slug de Site en NetBox, o None si es infraestructura compartida
      entre sedes (backbone) y hay que confirmar con el equipo de redes.
role: slug de Role en NetBox (gestion/contenidos/privada/radios).
vrf:  nombre del VRF en NetBox, o None si es red corporativa (va a la
      tabla global, sin VRF, porque todas las sedes están enrutadas entre sí).
index: True si es una página "índice de subredes" (columnas SUBRED/ZONA/LINK)
       que hay que expandir seleccionando sus enlaces internos.
skip_records: True si la página no debe convertirse en registros IP
       automáticamente (frameset roto, o tabla de rango completo generada
       en vez de asignaciones reales) — requiere revisión manual.
review: nota para revisar a mano antes de dar el dato por bueno.
"""

BASE_URL = "http://10.114.10.166/IPs/"

PAGES = [
    # --- GEST / BILBAO ---
    {"path": "IPs_10_217_157.htm", "site": "bilbao", "role": "gestion", "vrf": None},
    {"path": "IPs_10_214_154.htm", "site": "bilbao", "role": "gestion", "vrf": None},
    {"path": "IPs_10_114_159.htm", "site": "bilbao", "role": "gestion", "vrf": None},
    {"path": "bilbao_10_114.htm", "site": "bilbao", "role": "gestion", "vrf": None},
    {"path": "bilbao_10_114_11.htm", "site": "bilbao", "role": "gestion", "vrf": None},
    {"path": "bilbao_10_114_12.htm", "site": "bilbao", "role": "gestion", "vrf": None},
    {"path": "dmz_192_168.htm", "site": "bilbao", "role": "gestion", "vrf": "DMZ-BIO"},

    # --- GEST / MIRAMON ---
    {"path": "IPs_10_3_x.htm", "site": "miramon", "role": "gestion", "vrf": None, "index": True},
    {"path": "IPs_10_132_2.htm", "site": "miramon", "role": "gestion", "vrf": None},
    {"path": "IPs_10_114_15.htm", "site": "miramon", "role": "gestion", "vrf": None},

    # --- GEST / OTRAS (backbone compartido, sede sin confirmar) ---
    {"path": "IPs_10_132_x.htm", "site": None, "role": "gestion", "vrf": None, "index": True, "review": "backbone compartido, confirmar sede"},
    {"path": "IPs_10_112_x.htm", "site": None, "role": "gestion", "vrf": None, "index": True, "review": "backbone compartido, confirmar sede"},
    {"path": "IPs_10_119_x.htm", "site": None, "role": "gestion", "vrf": None, "index": True, "review": "backbone compartido, confirmar sede"},
    {"path": "172.18.x.htm", "site": None, "role": "gestion", "vrf": None, "review": "cabecera Cires21 compartida, confirmar sede"},
    {"path": "10.115.x.html", "site": None, "role": "gestion", "vrf": None, "review": "gestion streaming compartida, confirmar sede"},

    # --- GEST / RADIOS ---
    {"path": "IPs_10_113_x.htm", "site": None, "role": "radios", "vrf": None, "index": True, "review": "Radio Euskadi, confirmar sede"},
    {"path": "IPs_10_123_x.htm", "site": "gasteiz", "role": "radios", "vrf": None, "index": True, "review": "Radio Vitoria: asumido Gasteiz, confirmar"},
    {"path": "IPs_10_133_x.htm", "site": None, "role": "radios", "vrf": None, "index": True, "review": "Euskadi Irratia, confirmar sede"},
    {"path": "IPs_10_173_x.htm", "site": "iruna", "role": "radios", "vrf": None, "index": True, "review": "Irunea Erradioa: asumido Iruna, confirmar"},

    # --- CONT / BILBAO ---
    {"path": "IPs_10_124_54.htm", "site": "bilbao", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_79.htm", "site": "bilbao", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_62.htm", "site": "bilbao", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_11.htm", "site": "bilbao", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_10.htm", "site": "bilbao", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_30.htm", "site": "bilbao", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_150.htm", "site": "bilbao", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_158.htm", "site": "bilbao", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_9.htm", "site": "bilbao", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_16.htm", "site": "bilbao", "role": "contenidos", "vrf": None},
    {"path": "IPs_WBIEDRI.htm", "site": "bilbao", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_61.htm", "site": "bilbao", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_63.htm", "site": "bilbao", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_64.htm", "site": "bilbao", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_56.htm", "site": "bilbao", "role": "contenidos", "vrf": None},
    {"path": "IPs_WBIEDAR.htm", "site": "bilbao", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_60.htm", "site": "bilbao", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_59.htm", "site": "bilbao", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_17.htm", "site": "bilbao", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_20.htm", "site": "bilbao", "role": "contenidos", "vrf": None},

    # --- CONT / MIRAMON ---
    {"path": "IPs_10_124_12.htm", "site": "miramon", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_14.htm", "site": "miramon", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_55.htm", "site": "miramon", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_58.htm", "site": "miramon", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_57.htm", "site": "miramon", "role": "contenidos", "vrf": None, "skip_records": True, "review": "pagina rota (frameset JS antiguo, no es una tabla), sustituir a mano"},
    {"path": "IPs_10_124_70.htm", "site": "miramon", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_157.htm", "site": "miramon", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_125_x.htm", "site": "miramon", "role": "contenidos", "vrf": None},
    {"path": "IPs_10_124_18.htm", "site": "iruna", "role": "contenidos", "vrf": None},

    # --- CONT / OTRAS ---
    {"path": "IPs_192_168_100.htm", "site": None, "role": "contenidos", "vrf": None, "review": "confirmar sede"},
    {"path": "IPs_10_124_15.htm", "site": "gasteiz", "role": "contenidos", "vrf": None},
    {"path": "IPs_Madrid.htm", "site": "madrid", "role": "contenidos", "vrf": None},
    {"path": "WBIEDRI_korresponsalia.htm", "site": None, "role": "contenidos", "vrf": None, "review": "corresponsalia, confirmar sede"},

    # --- PRIV ---
    {"path": "mir_192.168.X_X.htm", "site": "miramon", "role": "privada", "vrf": "PRIV-MIR", "index": True},
    {"path": "irr_192.168.X_X.htm", "site": None, "role": "privada", "vrf": "PRIV-RADIOS", "index": True, "review": "confirmar sede"},

    # --- IRRATIA - CALREC (AoIP) ---
    {"path": "irratia_calrec/subnet_ips.html", "site": "bilbao", "role": "radios", "vrf": "AOIP-CALREC"},
    {"path": "irratia_calrec/core.html", "site": "bilbao", "role": "radios", "vrf": "AOIP-CALREC"},
    {"path": "irratia_calrec/surface_panels.html", "site": "bilbao", "role": "radios", "vrf": "AOIP-CALREC"},
    {"path": "irratia_calrec/aoip_networks_ifs.html", "site": "bilbao", "role": "radios", "vrf": "AOIP-CALREC"},
    {"path": "irratia_calrec/sistema_hi.html", "site": "bilbao", "role": "radios", "vrf": "AOIP-CALREC"},
    {"path": "irratia_calrec/glue.html", "site": "bilbao", "role": "radios", "vrf": "AOIP-CALREC"},
    {"path": "irratia_calrec/red_calrec_mixer_surface.html", "site": "bilbao", "role": "radios", "vrf": "AOIP-CALREC",
     "skip_records": True, "review": "tabla de ~2325 filas: parece el rango completo generado, no asignaciones reales. Revisar con el equipo de radio antes de decidir cómo importarla"},
    {"path": "irratia_calrec/red_calrec_external_control.html", "site": "bilbao", "role": "radios", "vrf": "AOIP-CALREC",
     "skip_records": True, "review": "idem: ~2325 filas generadas, revisar antes de importar"},
    {"path": "irratia_calrec/red_hi_glue.html", "site": "bilbao", "role": "radios", "vrf": "AOIP-CALREC"},
    {"path": "irratia_calrec/red_calrec_management.html", "site": "bilbao", "role": "radios", "vrf": "AOIP-CALREC",
     "skip_records": True, "review": "idem: ~2068 filas generadas, revisar antes de importar"},
    {"path": "irratia_calrec/red_aoip.html", "site": "bilbao", "role": "radios", "vrf": "AOIP-CALREC"},

    # --- huérfanas (no enlazadas desde default.aspx, encontradas vía menu.aspx) ---
    {"path": "IPs_10_126_157.htm", "site": "bilbao", "role": "contenidos", "vrf": None, "review": "pagina huerfana, no referenciada desde el indice principal"},
]
