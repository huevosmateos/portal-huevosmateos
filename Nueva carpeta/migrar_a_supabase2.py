# -*- coding: utf-8 -*-
"""
migrar_a_supabase.py
--------------------
Vuelca los datos del ERP (Access) a las tablas de Supabase.

Tablas que rellena:
  - articulos   <- CONSULTA ARTICULOS POR FAMILIAS (+ campos del ERP)
  - clientes    <- Clientes + EMail1 de CONSULTA CLIENTES EMAIL FACTURAS
  - ofertas     <- ArticuloCliente filtrando Automatico = 0

Variables de entorno requeridas (ya las tienes puestas como permanentes):
  - SUPABASE_URL
  - SUPABASE_SERVICE_KEY   (clave secreta, NUNCA en la web)

USO:
   py migrar_a_supabase.py prueba    # solo 5 articulos / 3 clientes / 3 ofertas
   py migrar_a_supabase.py completo  # todo el catalogo
   py migrar_a_supabase.py contar    # solo mostrar cuantos hay sin escribir nada
"""

import os
import sys

# ---- Configuracion (la misma que tu actualizar_web.py) ----------------------
DB_PATH = r"F:\RICARDO\BASE DATOS.mdb"

# Consultas/tablas del ERP
CONSULTA_ARTICULOS = "CONSULTA ARTICULOS POR FAMILIAS"
CONSULTA_EMAILS    = "CONSULTA CLIENTES EMAIL FACTURAS"
TABLA_CLIENTES     = "Clientes"
TABLA_OFERTAS      = "ArticuloCliente"

# Limites para el modo 'prueba'
LIMITE_PRUEBA_ART = 5
LIMITE_PRUEBA_CLI = 3
LIMITE_PRUEBA_OFE = 3


# ---- Comprobaciones previas -------------------------------------------------
def comprobar_entorno():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("[ERROR] Faltan variables de entorno SUPABASE_URL o SUPABASE_SERVICE_KEY.")
        sys.exit(1)
    if not os.path.exists(DB_PATH):
        print("[ERROR] No se encuentra la base de datos:", DB_PATH)
        sys.exit(1)
    return url, key


# ---- Conexion a Access ------------------------------------------------------
def conectar_access():
    try:
        import pypyodbc
    except ImportError:
        print("[ERROR] Falta pypyodbc.  Ejecuta:  pip install pypyodbc")
        sys.exit(1)
    conn_str = r'DRIVER={Microsoft Access Driver (*.mdb)};DBQ=' + DB_PATH + ';'
    try:
        return pypyodbc.connect(conn_str)
    except Exception as e:
        print("[ERROR] No se pudo conectar a Access:", e)
        sys.exit(1)


def filas_dict(cursor):
    """Convierte el resultado del cursor en lista de dicts {columna: valor}."""
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in cursor.fetchall()]


def g(row, *nombres):
    """Lectura tolerante: prueba varios posibles nombres de columna."""
    for n in nombres:
        for k in row:
            if k.lower() == n.lower():
                return row[k]
    return None


def num(v, defecto=0):
    try:
        return float(v) if v is not None else defecto
    except Exception:
        return defecto


def texto(v):
    return "" if v is None else str(v).strip()


# ---- Lecturas del ERP -------------------------------------------------------
def leer_articulos(conn, limite=None):
    """Devuelve lista de dicts listos para la tabla 'articulos' de Supabase.
    Lee directamente de la TABLA Articulos (no de la consulta de familias)
    porque la consulta no trae todos los campos que necesitamos."""
    cur = conn.cursor()

    # 1) Nombre de cada familia desde la consulta de familias (las filas con
    #    CodigoSubfamilia no numerico tienen la descripcion de la FAMILIA).
    fam_nombre = {}
    try:
        cur.execute("SELECT * FROM [%s]" % CONSULTA_ARTICULOS)
        for r in filas_dict(cur):
            fc  = texto(g(r, "CodigoFamilia"))
            sub = texto(g(r, "CodigoSubfamilia"))
            desc = texto(g(r, "Descripcion"))
            if fc and desc and not sub.isdigit() and fc not in fam_nombre:
                fam_nombre[fc] = desc
    except Exception as e:
        print("[AVISO] No se pudo leer la consulta de familias:", e)

    # 2) Leer la tabla Articulos (tiene TODOS los campos)
    cur.execute("SELECT * FROM Articulos")
    filas = filas_dict(cur)

    salida = []
    descartados_bloqueados = 0
    for r in filas:
        cod = texto(g(r, "CodigoArticulo")).zfill(4)
        if not cod:
            continue

        # FILTRO: solo subir VENDIBLES (BloqueoAlbaranVenta = 0)
        bloqueado = int(num(g(r, "BloqueoAlbaranVenta"))) != 0
        if bloqueado:
            descartados_bloqueados += 1
            continue

        familia_codigo = texto(g(r, "CodigoFamilia"))

        salida.append({
            "codigo":                cod,
            "descripcion":           texto(g(r, "DescripcionArticulo")),
            "precio_t0":             num(g(r, "PrecioVenta")),
            "precio_t1":             num(g(r, "PrecioVentasinIVA1")),
            "precio_t2":             num(g(r, "PrecioVentasinIVA2")),
            "precio_t3":             num(g(r, "PrecioVentasinIVA3")),
            "unidad_monetaria":      texto(g(r, "UnidadMedida2_")) or None,
            "formato_defecto":       texto(g(r, "UnidadMedidaAlternativa_")) or None,
            "desc_formato":          texto(g(r, "Descripcion2Articulo")) or None,
            "uds_por_caja_fija":     num(g(r, "CDunidxcaja")),
            "uds_caja_fraccionable": num(g(r, "StockMinimo")),
            "min_fraccion":          num(g(r, "PuntoPedido")),
            "desc_fraccion":         texto(g(r, "UnidadMedidaDefecto_")) or None,
            "peso_medio_caja":       num(g(r, "StockMaximo")),
            "grupo_iva":             int(num(g(r, "GrupoIva"), 1)),
            "familia_codigo":        familia_codigo or None,
            "familia":               fam_nombre.get(familia_codigo) or None,
            "marca":                 texto(g(r, "MarcaProducto")) or None,
            "publicar_web":          int(num(g(r, "PublicarInternet"))) == 0,
            "vendible":              True,   # solo vendibles llegan aqui
        })

    if descartados_bloqueados:
        print(f"  [info] {descartados_bloqueados} articulos descartados por estar BLOQUEADOS para venta")

    if limite:
        salida = salida[:limite]
    return salida


def detectar_emails_duplicados(clientes):
    """Recorre la lista y agrupa por email para detectar duplicados.
    Devuelve dict {email: [codigos]} solo con los repetidos.
    AVISA por pantalla y deja vacio el email en todos menos el primero
    para evitar el error de clave unica."""
    por_email = {}
    for c in clientes:
        em = c.get("email")
        if em:
            por_email.setdefault(em, []).append(c["codigo"])

    duplicados = {em: cods for em, cods in por_email.items() if len(cods) > 1}

    if duplicados:
        print()
        print("  *** AVISO: emails duplicados en el ERP ***")
        print("  Los siguientes emails estan en varios clientes. Solo el PRIMERO")
        print("  mantendra el email; los demas se subiran SIN email para no romper.")
        print("  Corrige esto en el ERP cuando puedas:")
        for em, cods in duplicados.items():
            print(f"    {em} -> clientes: {', '.join(cods)}")
        # Vaciar email en los duplicados (menos el primero de cada grupo)
        ya_visto = set()
        for c in clientes:
            em = c.get("email")
            if em in duplicados:
                if em in ya_visto:
                    c["email"] = None
                else:
                    ya_visto.add(em)
        print()


def leer_clientes(conn, limite=None):
    """Devuelve clientes con codigo, nombre, email, tarifa y descuento.
    Cruza tabla Clientes con CONSULTA CLIENTES EMAIL FACTURAS para los emails."""
    cur = conn.cursor()

    # 1) email por codigo de cliente
    emails = {}
    try:
        cur.execute("SELECT CodigoCliente, EMail1 FROM [%s]" % CONSULTA_EMAILS)
        for row in cur.fetchall():
            cli = texto(row[0]).zfill(4)
            em  = texto(row[1]).lower()
            if cli and em and "@" in em:
                emails[cli] = em
    except Exception as e:
        print("[AVISO] No se pudo leer emails:", e)

    # 2) tabla Clientes
    salida = []
    try:
        cur.execute(
            "SELECT CodigoCliente, RazonSocial, TarifaPrecio, [%%Descuento] "
            "FROM %s" % TABLA_CLIENTES
        )
    except Exception:
        # Fallback con * si no acierta con los nombres exactos
        cur.execute("SELECT * FROM %s" % TABLA_CLIENTES)

    filas = filas_dict(cur)
    for r in filas:
        cod = texto(g(r, "CodigoCliente")).zfill(4)
        if not cod:
            continue
        tarifa = int(num(g(r, "TarifaPrecio"), 0))
        if tarifa < 0 or tarifa > 3:
            tarifa = 0
        salida.append({
            "codigo":    cod,
            "nombre":    texto(g(r, "RazonSocial", "Nombre")) or None,
            "email":     emails.get(cod) or None,
            "tarifa":    tarifa,
            "descuento": num(g(r, "%Descuento", "PorcentajeDescuento")),
        })

    if limite:
        salida = salida[:limite]
    return salida


def leer_ofertas(conn, codigos_clientes, codigos_articulos, limite=None):
    """Lee ArticuloCliente con Automatico=0 (precio especial activo).
    Solo devuelve filas cuyo cliente y articulo existan en Supabase."""
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT CodigoCliente, CodigoArticulo, PrecioOferta "
            "FROM %s WHERE Automatico = 0" % TABLA_OFERTAS
        )
    except Exception as e:
        print("[ERROR] No se pudo leer ArticuloCliente:", e)
        return []

    salida = []
    descartados = 0
    for row in cur.fetchall():
        cli = texto(row[0]).zfill(4)
        art = texto(row[1]).zfill(4)
        precio = num(row[2])
        if not cli or not art:
            continue
        # No incluimos ofertas de clientes/articulos que no estan en Supabase
        if cli not in codigos_clientes or art not in codigos_articulos:
            descartados += 1
            continue
        salida.append({
            "cliente_codigo":  cli,
            "articulo_codigo": art,
            "precio_oferta":   precio,
        })

    if descartados:
        print(f"  [info] {descartados} ofertas descartadas (cliente o articulo no en Supabase)")

    if limite:
        salida = salida[:limite]
    return salida


# ---- Escritura a Supabase ---------------------------------------------------
def conectar_supabase(url, key):
    try:
        from supabase import create_client
    except ImportError:
        print("[ERROR] Falta libreria 'supabase'.  py -m pip install supabase")
        sys.exit(1)
    return create_client(url, key)


def subir(sb, tabla, datos, lote=100):
    """Sube por lotes con upsert. Si un lote falla, reintenta fila a fila
    para que un solo fallo no detenga el resto. Avisa de las que no se suben.
    Asi el script se puede ejecutar varias veces sin duplicar."""
    if not datos:
        print(f"  [{tabla}] nada que subir")
        return 0
    total_ok = 0
    fallos = []
    for i in range(0, len(datos), lote):
        bloque = datos[i:i+lote]
        try:
            sb.table(tabla).upsert(bloque).execute()
            total_ok += len(bloque)
            print(f"  [{tabla}] subidas {total_ok}/{len(datos)}")
        except Exception:
            # El lote ha fallado; probamos fila a fila para identificar la mala
            print(f"  [{tabla}] lote {i}-{i+len(bloque)} fallo; reintentando fila a fila...")
            for fila in bloque:
                try:
                    sb.table(tabla).upsert(fila).execute()
                    total_ok += 1
                except Exception as e2:
                    fallos.append((fila, str(e2)))
            print(f"  [{tabla}] tras reintento: {total_ok}/{len(datos)} OK, {len(fallos)} fallos")

    if fallos:
        print(f"  [{tabla}] *** {len(fallos)} filas NO subidas (primeras 5): ***")
        for fila, err in fallos[:5]:
            cod = fila.get("codigo") or fila.get("cliente_codigo") or "?"
            # mensaje resumido del error
            msg = err.split("\n")[0][:120]
            print(f"    {cod}: {msg}")
    return total_ok


def borrar_obsoletos(sb, tabla, clave, codigos_actuales):
    """Borra de Supabase las filas cuya 'clave' NO esta en el conjunto
    de codigos actuales. Es decir, los que ya no vienen en el ERP (o han
    cambiado a bloqueado). En cascada se borraran tambien sus ofertas si
    es la tabla 'articulos'."""
    if not codigos_actuales:
        return 0
    try:
        # Leer todos los codigos que hay ahora en Supabase
        r = sb.table(tabla).select(clave).execute()
        en_supabase = {fila[clave] for fila in (r.data or [])}
        obsoletos = list(en_supabase - codigos_actuales)
        if not obsoletos:
            print(f"  [{tabla}] nada obsoleto que borrar")
            return 0
        # Borrar por lotes (Supabase tiene limites en URL si la lista es muy larga)
        total = 0
        for i in range(0, len(obsoletos), 100):
            lote = obsoletos[i:i+100]
            sb.table(tabla).delete().in_(clave, lote).execute()
            total += len(lote)
        print(f"  [{tabla}] BORRADOS {total} obsoletos: {obsoletos[:5]}{'...' if len(obsoletos)>5 else ''}")
        return total
    except Exception as e:
        print(f"  [{tabla}] ERROR al limpiar obsoletos: {e}")
        return 0


# ---- Programa principal -----------------------------------------------------
def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("prueba", "completo", "contar"):
        print(__doc__)
        sys.exit(1)
    modo = sys.argv[1]

    url, key = comprobar_entorno()
    print(f"Modo: {modo}")
    print("Conectando a Access...")
    conn = conectar_access()
    print("[OK] Conectado a Access")

    print("Leyendo articulos...")
    if modo == "prueba":
        articulos = leer_articulos(conn, LIMITE_PRUEBA_ART)
    else:
        articulos = leer_articulos(conn)
    print(f"  -> {len(articulos)} articulos preparados")

    print("Leyendo clientes...")
    if modo == "prueba":
        clientes = leer_clientes(conn, LIMITE_PRUEBA_CLI)
    else:
        clientes = leer_clientes(conn)
    detectar_emails_duplicados(clientes)
    print(f"  -> {len(clientes)} clientes preparados "
          f"({sum(1 for c in clientes if c['email'])} con email)")

    print("Leyendo ofertas (Automatico=0)...")
    cod_cli = {c["codigo"] for c in clientes}
    cod_art = {a["codigo"] for a in articulos}
    if modo == "prueba":
        ofertas = leer_ofertas(conn, cod_cli, cod_art, LIMITE_PRUEBA_OFE)
    else:
        ofertas = leer_ofertas(conn, cod_cli, cod_art)
    print(f"  -> {len(ofertas)} ofertas preparadas")

    conn.close()

    if modo == "contar":
        print("\n[Modo CONTAR] No se escribe nada a Supabase.")
        return

    print("\nConectando a Supabase...")
    sb = conectar_supabase(url, key)

    # Orden importante: primero las tablas a las que las ofertas hacen referencia
    print("\n--- Subiendo articulos ---")
    subir(sb, "articulos", articulos)

    print("\n--- Subiendo clientes ---")
    subir(sb, "clientes", clientes)

    print("\n--- Subiendo ofertas ---")
    subir(sb, "ofertas", ofertas)

    # Limpieza de obsoletos: solo en modo 'completo' (en 'prueba' no tiene sentido
    # porque solo hemos subido 5 articulos y borraria casi todo).
    if modo == "completo":
        print("\n--- Limpiando obsoletos en Supabase ---")
        cod_art = {a["codigo"] for a in articulos}
        cod_cli = {c["codigo"] for c in clientes}
        borrar_obsoletos(sb, "articulos", "codigo", cod_art)
        borrar_obsoletos(sb, "clientes",  "codigo", cod_cli)
        # Las ofertas se limpian solas en cascada al borrar articulos/clientes,
        # pero ademas removemos las que ya no esten en el ERP (Automatico volvio a -1).
        # Para eso necesitariamos identificarlas por (cliente, articulo). Hacemos:
        pares_ofertas = {(o["cliente_codigo"], o["articulo_codigo"]) for o in ofertas}
        try:
            r = sb.table("ofertas").select("cliente_codigo,articulo_codigo").execute()
            en_sb = {(f["cliente_codigo"], f["articulo_codigo"]) for f in (r.data or [])}
            obsoletas = list(en_sb - pares_ofertas)
            if obsoletas:
                # Borrar una a una (no hay 'in' compuesto sencillo)
                borradas = 0
                for cli, art in obsoletas[:500]:   # limite de seguridad
                    sb.table("ofertas").delete()\
                        .eq("cliente_codigo", cli)\
                        .eq("articulo_codigo", art).execute()
                    borradas += 1
                print(f"  [ofertas] BORRADAS {borradas} obsoletas (Automatico volvio a -1)")
            else:
                print("  [ofertas] nada obsoleto que borrar")
        except Exception as e:
            print(f"  [ofertas] ERROR al limpiar obsoletas: {e}")

    print("\n[OK] Migracion completada.")


if __name__ == "__main__":
    main()
