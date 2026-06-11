# -*- coding: utf-8 -*-
"""
informe_duplicados_autorizados.py
---------------------------------
Detecta clientes en Access que tienen el MISMO email y ademas
estan AUTORIZADOS (ActivarLogicNet = -1) y NO bloqueados (BloqueoAlbaran = 0).

Salida:
  - Por pantalla: lista de duplicados (email + clientes afectados con nombre)
  - Archivo CSV: 'duplicados_autorizados.csv'

NO modifica nada en el ERP ni en Supabase. Solo lee y avisa.
"""
import os
import sys
import csv

DB_PATH = r"F:\RICARDO\BASE DATOS.mdb"
SALIDA  = "duplicados_autorizados.csv"

CONSULTA_EMAILS = "CONSULTA CLIENTES EMAIL FACTURAS"
TABLA_CLIENTES  = "Clientes"


def main():
    try:
        import pypyodbc
    except ImportError:
        print("[ERROR] Falta pypyodbc.  py -m pip install pypyodbc")
        sys.exit(1)

    if not os.path.exists(DB_PATH):
        print("[ERROR] No se encuentra la base de datos:", DB_PATH)
        sys.exit(1)

    conn = pypyodbc.connect(
        r'DRIVER={Microsoft Access Driver (*.mdb)};DBQ=' + DB_PATH + ';'
    )
    cur = conn.cursor()

    # 1) Emails por codigo cliente
    emails = {}
    try:
        cur.execute(f"SELECT CodigoCliente, EMail1 FROM [{CONSULTA_EMAILS}]")
        for row in cur.fetchall():
            cod = str(row[0]).strip().zfill(4) if row[0] is not None else ""
            em  = (str(row[1]) if row[1] is not None else "").strip().lower()
            if cod and em and "@" in em:
                emails[cod] = em
        print(f"[OK] Leidos {len(emails)} emails de '{CONSULTA_EMAILS}'")
    except Exception as e:
        print(f"[ERROR] Leyendo emails: {e}")
        sys.exit(1)

    # 2) Clientes activos y autorizados
    cur.execute(f"SELECT * FROM {TABLA_CLIENTES}")
    cols = [d[0] for d in cur.description]
    filas = cur.fetchall()

    def idx(nombre):
        n = nombre.lower()
        for i, c in enumerate(cols):
            if c.lower() == n:
                return i
        return None

    i_cod  = idx("CodigoCliente")
    i_nom  = idx("RazonSocial")
    i_blo  = idx("BloqueoAlbaran")
    i_act  = idx("ActivarLogicNet")

    if i_cod is None or i_act is None or i_blo is None:
        print("[ERROR] Falta alguna columna esperada.")
        print(f"        Encontradas: CodigoCliente={i_cod}  "
              f"BloqueoAlbaran={i_blo}  ActivarLogicNet={i_act}")
        sys.exit(1)

    # Diccionario: email -> [(codigo, nombre)]
    por_email = {}
    n_autorizados = 0
    n_autorizados_con_email = 0

    for r in filas:
        cod = str(r[i_cod]).strip().zfill(4) if r[i_cod] is not None else ""
        if not cod:
            continue

        # Filtros: NO bloqueado y AUTORIZADO
        try:
            bloqueado = int(r[i_blo]) != 0
        except Exception:
            bloqueado = False
        if bloqueado:
            continue

        try:
            autorizado = int(r[i_act]) != 0  # -1 = SI autorizado
        except Exception:
            autorizado = False
        if not autorizado:
            continue

        n_autorizados += 1
        em = emails.get(cod)
        if not em:
            continue
        n_autorizados_con_email += 1

        nombre = ""
        if i_nom is not None and r[i_nom] is not None:
            nombre = str(r[i_nom]).strip()

        por_email.setdefault(em, []).append((cod, nombre))

    conn.close()

    duplicados = {em: lista for em, lista in por_email.items() if len(lista) > 1}

    print()
    print(f"=== RESUMEN ===")
    print(f"  Clientes NO bloqueados y AUTORIZADOS: {n_autorizados}")
    print(f"  De ellos, con email asignado:         {n_autorizados_con_email}")
    print(f"  Emails unicos entre autorizados:      {len(por_email)}")
    print(f"  Emails DUPLICADOS:                    {len(duplicados)}")
    print()

    if not duplicados:
        print("[OK] NO hay emails duplicados entre clientes autorizados.")
        print("     Puedes lanzar la migracion con seguridad.")
        return

    # Listado y CSV
    n_filas = sum(len(l) for l in duplicados.values())
    print(f"=== {len(duplicados)} EMAILS DUPLICADOS afectan a {n_filas} clientes ===")
    print()
    print(f"{'EMAIL':40s}  {'COD.':5s}  NOMBRE")
    print("-" * 90)

    with open(SALIDA, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Email", "CodigoCliente", "Nombre"])
        for em in sorted(duplicados.keys()):
            for cod, nombre in sorted(duplicados[em]):
                print(f"{em:40s}  {cod}  {nombre}")
                w.writerow([em, cod, nombre])
            print()

    print(f"[OK] Detalle guardado en: {SALIDA}")
    print("     Abre con Excel (separador ;)")
    print()
    print("     Decide en el ERP cual cliente mantiene cada email y a")
    print("     cuales les cambias el email (o desactivas ActivarLogicNet).")
    print("     Despues vuelve a lanzar este informe para confirmar.")


if __name__ == "__main__":
    main()
