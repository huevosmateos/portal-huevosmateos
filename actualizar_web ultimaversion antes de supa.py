# -*- coding: utf-8 -*-
# ============================================================================
#  ACTUALIZAR WEB  -  HUEVOS MATEOS, S.L.
#  Refresca SOLO los datos (articulos, precios, descripciones, familias), las
#  imagenes de los productos y las CATEGORIAS del pie de pagina.
#
#  NO toca: colores, tipografias, textos, ni la estructura de la web.
#  (Conserva intactos el diseno de tienda.html: maquetacion fija de cabecera/
#   buscador/menu, el grid de 4 columnas y la busqueda con resultados seguidos.)
#  Modifica unicamente:
#     - en tienda.html y tiendaconprecio.html: la lista de productos (var PRODUCTOS=...),
#       el orden de familias (var ORDEN_FAM=...) y el menu lateral (<ul id="fam-list">)
#     - en index.html, tienda.html y contacto.html: la lista de categorias
#       del pie (<ul class="pie-cats">), para que coincida con las familias reales
#     - copia/actualiza las fotos en la carpeta img
#
#  Requisitos:  pip install pypyodbc   (ya lo tienes para el PDF)
# ============================================================================

import os
import re
import json
import html
import shutil
import unicodedata
from urllib.parse import quote

# ----------------------------------------------------------------------------
#  CONFIGURACION  (igual que generar_web_db.py)
# ----------------------------------------------------------------------------
DB_PATH    = r"F:\RICARDO\BASE DATOS.mdb"
FOTOS_PATH = r"F:\IMAGENES DE PRODUCTOS"
WEB_DIR    = r"C:\bot_whatsapp\webhuevosmateos"     # carpeta donde esta la web ya maquetada
CONSULTA   = "CONSULTA ARTICULOS POR FAMILIAS"
# Fuentes para los clientes del login. Se prueban EN ORDEN hasta encontrar
# clientes con email + PIN. Pueden ser consultas o tablas.
FUENTES_CLIENTES = [
    "CONSULTA CLIENTES EMAIL FACTURAS",   # tu consulta (si incluye ContraseñaLogicNet)
    "CLIENTES", "Clientes", "clientes",   # la tabla de clientes (por si la consulta no trae el PIN)
]
MAX_VARIANTES = 2   # fotos adicionales por producto, ademas de la principal

# ----------------------------------------------------------------------------
#  UTILIDADES (mismas que el generador, para que los datos salgan identicos)
# ----------------------------------------------------------------------------
_MIN = {"y", "de", "del", "la", "el", "los", "las", "con", "sin", "en", "a", "al", "para", "e", "o"}

def titlecase_es(s):
    s = (s or "").strip()
    if not s:
        return s
    out = []
    for i, w in enumerate(s.split()):
        wl = w.lower()
        out.append(wl if (i > 0 and wl in _MIN) else (wl[:1].upper() + wl[1:]))
    return " ".join(out)

def precio_es(v):
    try:
        return ("%.2f" % float(v)).replace(".", ",")
    except Exception:
        return ""

def _clave(s):
    s = (s or "").replace(" ", "").lower()
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

def get(row, *names):
    objetivos = [_clave(n) for n in names]
    for obj in objetivos:
        for k in row:
            if _clave(k) == obj:
                return row[k]
    return ""

# ----------------------------------------------------------------------------
#  LECTURA DESDE ACCESS
# ----------------------------------------------------------------------------
def leer_db():
    try:
        import pypyodbc
    except ImportError:
        print("[ERROR] Falta pypyodbc.  Ejecuta:  pip install pypyodbc")
        return None
    if not os.path.exists(DB_PATH):
        print("[ERROR] No se encuentra la base de datos:", DB_PATH)
        return None
    print("Conectando a Access...")
    conn_str = r'DRIVER={Microsoft Access Driver (*.mdb)};DBQ=' + DB_PATH + ';'
    try:
        conn = pypyodbc.connect(conn_str)
    except Exception as e:
        print("[ERROR] No se pudo conectar:", e)
        return None
    cur = conn.cursor()
    try:
        cur.execute('SELECT * FROM [%s]' % CONSULTA)
    except Exception as e:
        print("[ERROR] No se pudo leer la consulta '%s': %s" % (CONSULTA, e))
        conn.close()
        return None
    cols = [d[0] for d in cur.description]
    filas = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    print("[OK] Filas leidas de la consulta:", len(filas))
    return filas

# ----------------------------------------------------------------------------
#  CONSTRUCCION DE PRODUCTOS (sin duplicados de subfamilia) + copia de imagenes
# ----------------------------------------------------------------------------
def construir_productos(filas, img_dir):
    productos = []
    fam_nombre = {}
    vistos = set()
    copiadas = 0

    # PASO 1: nombre de cada FAMILIA tomado de la fila de nivel familia.
    # Esa fila tiene CodigoSubfamilia con asteriscos (no numerico) y su Descripcion
    # va en MAYUSCULAS. Las filas con subfamilia numerica (030, 540...) llevan la
    # descripcion de la SUBFAMILIA, que NO queremos.
    for r in filas:
        fc  = str(get(r, "CodigoFamilia")).strip()
        sub = str(get(r, "CodigoSubfamilia")).strip()
        desc = str(get(r, "Descripcion")).strip()
        if fc and desc and not sub.isdigit() and fc not in fam_nombre:
            fam_nombre[fc] = titlecase_es(desc)

    # PASO 2: productos (sin duplicados por subfamilia)
    for r in filas:
        cod = str(get(r, "CodigoArticulo")).strip()
        if not cod or cod in vistos:
            continue
        vistos.add(cod)
        cod4 = cod.zfill(4)
        fam_cod = str(get(r, "CodigoFamilia")).strip()
        # respaldo: si una familia no tuviera fila de nivel familia, usar su Descripcion
        if fam_cod and fam_cod not in fam_nombre:
            d = str(get(r, "Descripcion")).strip()
            if d:
                fam_nombre[fam_cod] = titlecase_es(d)

        imgs = []
        candidatos = [cod4 + ".jpg"] + [cod4 + "_%d.jpg" % i for i in range(1, MAX_VARIANTES + 3)]
        for nombre_img in candidatos:
            origen = os.path.join(FOTOS_PATH, nombre_img)
            if os.path.isfile(origen):
                try:
                    shutil.copy(origen, os.path.join(img_dir, nombre_img))
                    imgs.append("img/" + nombre_img)
                    copiadas += 1
                except Exception:
                    pass
            if len(imgs) >= (1 + MAX_VARIANTES):
                break

        productos.append({
            "codigo":  cod4,
            "nombre":  str(get(r, "DescripcionArticulo")).strip(),
            "envase":  str(get(r, "Descripcion2Articulo")).strip(),
            "marca":   str(get(r, "MarcaProducto")).strip(),
            "precio":  precio_es(get(r, "PrecioVentasinIVA1", "PrecioVentasInIVA1")),
            "p1":      precio_es(get(r, "PrecioVentasinIVA1", "PrecioVentasInIVA1")),
            "p2":      precio_es(get(r, "PrecioVentasinIVA2", "PrecioVentasInIVA2")),
            "p3":      precio_es(get(r, "PrecioVentasinIVA3", "PrecioVentasInIVA3")),
            "p0":      precio_es(get(r, "PrecioVenta")),
            "unidad":  str(get(r, "UnidadMedida2", "UnidadMedida2_")).strip(),
            "fam_cod": fam_cod,
            "familia": fam_nombre.get(fam_cod, "Otros"),
            "imgs":    imgs,
        })

    for p in productos:
        p["familia"] = fam_nombre.get(p["fam_cod"], p["familia"])

    def fkey(fc):
        try:
            return (0, int(fc))
        except Exception:
            return (1, fc)
    familias = []
    for fc in sorted(fam_nombre, key=fkey):
        nom = fam_nombre[fc]
        if nom not in familias:   # evita familias repetidas si comparten descripcion
            familias.append(nom)
    return productos, familias, copiadas

# ----------------------------------------------------------------------------
#  ACTUALIZACION QUIRURGICA DE tienda.html  (solo datos)
# ----------------------------------------------------------------------------
def actualizar_tienda(productos, familias, nombre="tienda.html"):
    ruta = os.path.join(WEB_DIR, nombre)
    if not os.path.isfile(ruta):
        print("[ERROR] No se encuentra:", ruta)
        return False

    with open(ruta, "r", encoding="utf-8") as f:
        contenido = f.read()

    # --- 1) datos de productos y orden de familias ---
    data = json.dumps(productos, ensure_ascii=False)
    fams = json.dumps(familias, ensure_ascii=False)
    nuevo_datos = "var PRODUCTOS=%s, ORDEN_FAM=%s, IMG={};" % (data, fams)

    contenido, n1 = re.subn(r"var PRODUCTOS=.*?IMG=\{\};",
                            lambda m: nuevo_datos, contenido, count=1, flags=re.S)
    if n1 == 0:
        print("[AVISO] No encontre el bloque 'var PRODUCTOS=...' en tienda.html. No se han tocado los datos.")
        return False

    # --- 2) menu lateral de familias ---
    items = "".join('<li><a href="#" data-fam="%s">%s <span>%d</span></a></li>'
                    % (html.escape(f, quote=True), html.escape(f),
                       sum(1 for p in productos if p["familia"] == f)) for f in familias)
    nuevo_ul = '<ul id="fam-list"><li><a href="#" data-fam="" class="activo">Todas</a></li>' + items + '</ul>'
    contenido, n2 = re.subn(r'<ul id="fam-list">.*?</ul>',
                            lambda m: nuevo_ul, contenido, count=1, flags=re.S)
    if n2 == 0:
        print("[AVISO] No encontre el menu '<ul id=\"fam-list\">'. Se actualizaron los datos pero no el menu lateral.")

    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    return True

# ----------------------------------------------------------------------------
#  ACTUALIZACION DE LAS CATEGORIAS DEL PIE  (index, tienda y contacto)
#  Solo reemplaza el contenido de <ul class="pie-cats">...</ul>.
#  Cada categoria es un enlace que abre la tienda filtrada por esa familia.
# ----------------------------------------------------------------------------
def actualizar_categorias_pie(familias):
    actualizados = 0
    for nombre in ("index.html", "tienda.html", "contacto.html", "tiendaconprecio.html"):
        ruta = os.path.join(WEB_DIR, nombre)
        if not os.path.isfile(ruta):
            # tiendaconprecio.html puede no existir todavia: no es un error
            if nombre != "tiendaconprecio.html":
                print("[AVISO] No se encuentra:", nombre, "-> no se actualiza su pie.")
            continue
        # en la pagina con precios las categorias navegan dentro de ella misma
        destino = "tiendaconprecio.html" if nombre == "tiendaconprecio.html" else "tienda.html"
        cats = "".join('<li><a href="%s?fam=%s">%s</a></li>'
                       % (destino, quote(f, safe=''), html.escape(f)) for f in familias)
        nuevo_ul = '<ul class="pie-cats">' + cats + '</ul>'
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()
        contenido, n = re.subn(r'<ul class="pie-cats">.*?</ul>',
                               lambda m: nuevo_ul, contenido, count=1, flags=re.S)
        if n == 0:
            print("[AVISO] No encontre '<ul class=\"pie-cats\">' en", nombre, "-> pie sin cambios.")
            continue
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        actualizados += 1
    return actualizados

# ----------------------------------------------------------------------------
#  CLIENTES PARA EL LOGIN  (email + PIN)  ->  se cargan en tienda.html
#  email = campo Domicilio2 (domicilioenvio2) ; PIN = campo ContrasenaLogicNet
# ----------------------------------------------------------------------------
def _leer_tabla(nombre):
    """Lee SELECT * FROM [nombre]; devuelve lista de filas (dicts) o None si falla."""
    try:
        import pypyodbc
    except ImportError:
        return None
    conn_str = r'DRIVER={Microsoft Access Driver (*.mdb)};DBQ=' + DB_PATH + ';'
    conn = None
    try:
        conn = pypyodbc.connect(conn_str)
        cur = conn.cursor()
        cur.execute('SELECT * FROM [%s]' % nombre)
        cols = [d[0] for d in cur.description]
        filas = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.close()
        return filas
    except Exception:
        if conn:
            try: conn.close()
            except Exception: pass
        return None

def cargar_clientes_login():
    """Prueba las fuentes de FUENTES_CLIENTES hasta encontrar clientes con
    email (domicilioenvio2) + PIN (ContrasenaLogicNet) y los escribe en el login
    de tienda.html. Devuelve (numero_de_clientes, fuente_usada)."""
    if not os.path.exists(DB_PATH):
        print("[ERROR] No se encuentra la base de datos:", DB_PATH)
        return 0, None
    for fuente in FUENTES_CLIENTES:
        filas = _leer_tabla(fuente)
        if not filas:
            continue
        clientes = construir_clientes(filas)
        if clientes:
            n = actualizar_clientes_login(clientes)
            return n, fuente
    return 0, None

def construir_clientes(filas):
    clientes = {}
    for r in filas:
        email = str(get(r, "Domicilio2", "domicilioenvio2", "DomicilioEnvio2", "email", "correo")).strip().lower()
        pin   = str(get(r, "ContrasenaLogicNet", "ContraseñaLogicNet")).strip()
        if email and pin and "@" in email:
            clientes[email] = pin
    return clientes

def actualizar_clientes_login(clientes):
    # Carga la lista de clientes en el login de TODAS las paginas que lo tengan
    nuevo = "var CLIENTES=%s;" % json.dumps(clientes, ensure_ascii=False)
    paginas = ("tienda.html",)  # solo tienda.html gestiona el login; tiendaconprecio no lo necesita
    escritas = 0
    for nombre in paginas:
        ruta = os.path.join(WEB_DIR, nombre)
        if not os.path.isfile(ruta):
            continue
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()
        contenido, n = re.subn(r"var CLIENTES=\{.*?\};", lambda m: nuevo, contenido, count=1, flags=re.S)
        if n:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(contenido)
            escritas += 1
    if escritas == 0:
        print("[AVISO] No encontre 'var CLIENTES={...}' en ninguna pagina -> login sin cambios.")
        return 0
    return len(clientes)

# ----------------------------------------------------------------------------
#  PRODUCTOS HABITUALES  (ArticuloCliente, ultimos 3 meses)
#  Genera en tiendaconprecio.html las variables:
#    CLIENTES_COD  : { email -> CodigoCliente }
#    HABITUALES    : { CodigoCliente -> [lista de CodigoArticulo] }
# ----------------------------------------------------------------------------
def cargar_habituales():
    """Lee ArticuloCliente filtrando FechaUltimoAlbaran >= hace 3 meses,
    cruza con CONSULTA CLIENTES EMAIL FACTURAS para obtener el email,
    y escribe CLIENTES_COD y HABITUALES en tiendaconprecio.html."""
    if not os.path.exists(DB_PATH):
        print("[ERROR] No se encuentra la base de datos:", DB_PATH)
        return 0
    ruta = os.path.join(WEB_DIR, "tiendaconprecio.html")
    if not os.path.isfile(ruta):
        print("[AVISO] tiendaconprecio.html no existe, no se escriben habituales.")
        return 0

    try:
        import pypyodbc
        from datetime import datetime, timedelta
    except ImportError:
        print("[ERROR] Falta pypyodbc.")
        return 0

    conn_str = r'DRIVER={Microsoft Access Driver (*.mdb)};DBQ=' + DB_PATH + ';'
    try:
        conn = pypyodbc.connect(conn_str)
    except Exception as e:
        print("[ERROR] No se pudo conectar para habituales:", e)
        return 0

    cur = conn.cursor()
    hace3meses = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

    # --- 1) ArticuloCliente: CodigoCliente -> set de CodigoArticulo ---
    habituales = {}
    try:
        cur.execute(
            "SELECT CodigoCliente, CodigoArticulo FROM ArticuloCliente "
            "WHERE FechaUltimoAlbaran >= #%s#" % hace3meses
        )
        for row in cur.fetchall():
            cli  = str(row[0]).strip().zfill(4)
            art  = str(row[1]).strip().zfill(4)
            if cli not in habituales:
                habituales[cli] = []
            if art not in habituales[cli]:
                habituales[cli].append(art)
    except Exception as e:
        print("[AVISO] No se pudo leer ArticuloCliente:", e)

    # --- 2) CONSULTA CLIENTES EMAIL FACTURAS: email -> CodigoCliente ---
    clientes_cod = {}
    try:
        cur.execute("SELECT CodigoCliente, EMail1 FROM [CONSULTA CLIENTES EMAIL FACTURAS]")
        for row in cur.fetchall():
            cli   = str(row[0]).strip().zfill(4)
            email = str(row[1] or '').strip().lower()
            if email and '@' in email:
                clientes_cod[email] = cli
    except Exception as e:
        print("[AVISO] No se pudo leer CONSULTA CLIENTES EMAIL FACTURAS:", e)

    # --- 3) Tabla Clientes: CodigoCliente -> TarifaPrecio ---
    tarifas = {}
    try:
        cur.execute("SELECT CodigoCliente, TarifaPrecio FROM Clientes")
        for row in cur.fetchall():
            cli    = str(row[0]).strip().zfill(4)
            tarifa = str(row[1]).strip() if row[1] is not None else "1"
            tarifas[cli] = tarifa
    except Exception as e:
        print("[AVISO] No se pudo leer TarifaPrecio de Clientes:", e)

    conn.close()

    if not habituales and not clientes_cod:
        print("[AVISO] No se obtuvieron datos de habituales.")
        return 0

    # --- 4) Escribir en tiendaconprecio.html ---
    nuevo_cod  = "var CLIENTES_COD=%s;" % json.dumps(clientes_cod, ensure_ascii=False)
    nuevo_hab  = "var HABITUALES=%s;"   % json.dumps(habituales,   ensure_ascii=False)
    nuevo_tar  = "var TARIFAS=%s;"      % json.dumps(tarifas,      ensure_ascii=False)

    with open(ruta, "r", encoding="utf-8") as f:
        contenido = f.read()

    contenido, n1 = re.subn(r"var CLIENTES_COD=\{.*?\};", lambda m: nuevo_cod, contenido, count=1, flags=re.S)
    contenido, n2 = re.subn(r"var HABITUALES=\{.*?\};",   lambda m: nuevo_hab, contenido, count=1, flags=re.S)
    contenido, n3 = re.subn(r"var TARIFAS=\{.*?\};",      lambda m: nuevo_tar, contenido, count=1, flags=re.S)

    if n1 == 0:
        print("[AVISO] No se encontro 'var CLIENTES_COD={};' en tiendaconprecio.html -> no actualizado.")
    if n2 == 0:
        print("[AVISO] No se encontro 'var HABITUALES={};' en tiendaconprecio.html -> no actualizado.")
    if n3 == 0:
        print("[AVISO] No se encontro 'var TARIFAS={};' en tiendaconprecio.html -> no actualizado.")

    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)

    print("Clientes con email vinculado:", len(clientes_cod))
    print("Clientes con habituales (3 meses):", len(habituales))
    return len(habituales)


def main():
    print("=" * 62)
    print("ACTUALIZAR WEB - HUEVOS MATEOS  (datos, imagenes y categorias del pie)")
    print("=" * 62)

    if not os.path.isdir(WEB_DIR):
        print("[ERROR] No existe la carpeta de la web:", WEB_DIR)
        input("\nPresiona ENTER para salir...")
        return

    filas = leer_db()
    if filas is None:
        input("\nPresiona ENTER para salir...")
        return

    img_dir = os.path.join(WEB_DIR, "img")
    os.makedirs(img_dir, exist_ok=True)

    productos, familias, copiadas = construir_productos(filas, img_dir)
    ok = actualizar_tienda(productos, familias, "tienda.html")
    if os.path.isfile(os.path.join(WEB_DIR, "tiendaconprecio.html")):
        actualizar_tienda(productos, familias, "tiendaconprecio.html")
    pies = actualizar_categorias_pie(familias)

    n_cli, fuente_cli = cargar_clientes_login()
    n_hab = cargar_habituales()

    print("-" * 62)
    print("Productos actualizados:", len(productos))
    print("Familias:", len(familias))
    print("Imagenes copiadas (principal + variantes):", copiadas)
    if ok:
        print("OK -> tienda.html: productos y menu lateral actualizados.")
    print("Categorias del pie actualizadas en %d paginas." % pies)
    if n_cli > 0:
        print("Clientes cargados en el login (tienda.html):", n_cli, "(desde '%s')" % fuente_cli)
    else:
        print("[AVISO] No se cargo ningun cliente. Revisa el email (domicilioenvio2) y el")
        print("        PIN (ContrasenaLogicNet) en tu consulta/tabla de clientes.")
    if n_hab > 0:
        print("Habituales escritos en tiendaconprecio.html: %d clientes con articulos." % n_hab)
    print("Diseno, colores y textos: NO modificados.")
    print("=" * 62)
    input("\nPresiona ENTER para salir...")

if __name__ == "__main__":
    main()
