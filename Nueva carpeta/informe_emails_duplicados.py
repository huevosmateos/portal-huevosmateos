# -*- coding: utf-8 -*-
"""
informe_emails_duplicados.py
----------------------------
Saca de Access los clientes cuyo email se repite, ordenado por email.
Genera salida por pantalla y un CSV: emails_duplicados.csv
"""
import os
import sys
import csv

DB_PATH = r"F:\RICARDO\BASE DATOS.mdb"
SALIDA  = "emails_duplicados.csv"

# Posibles consultas/tablas con email (probamos en orden hasta encontrar una)
FUENTES = [
    ("CONSULTA CLIENTES EMAIL FACTURAS", "EMail1"),
    ("Clientes",                          "EMail1"),
]

def main():
    try:
        import pypyodbc
    except ImportError:
        print("[ERROR] Falta pypyodbc.  Ejecuta:  py -m pip install pypyodbc")
        sys.exit(1)

    if not os.path.exists(DB_PATH):
        print("[ERROR] No se encuentra la base de datos:", DB_PATH)
        sys.exit(1)

    conn = pypyodbc.connect(
        r'DRIVER={Microsoft Access Driver (*.mdb)};DBQ=' + DB_PATH + ';'
    )
    cur = conn.cursor()

    # Leer codigo cliente y email desde la consulta que sabemos que lo tiene
    filas = []
    for fuente, campo_email in FUENTES:
        try:
            cur.execute(f"SELECT CodigoCliente, {campo_email} FROM [{fuente}]")
            for row in cur.fetchall():
                cod = str(row[0]).strip().zfill(4)
                em  = (str(row[1]) if row[1] is not None else "").strip().lower()
                if cod and em and "@" in em:
                    filas.append((cod, em))
            print(f"[OK] Leidos {len(filas)} (cliente, email) de '{fuente}'")
            break
        except Exception as e:
            print(f"[AVISO] No se pudo leer '{fuente}':", e)

    if not filas:
        print("[ERROR] No se obtuvo ningun email.")
        conn.close()
        sys.exit(1)

    # Leer nombre de cliente (RazonSocial) desde la tabla Clientes
    nombres = {}
    try:
        cur.execute("SELECT CodigoCliente, RazonSocial FROM Clientes")
        for row in cur.fetchall():
            cod = str(row[0]).strip().zfill(4)
            nombre = (str(row[1]) if row[1] is not None else "").strip()
            nombres[cod] = nombre
    except Exception as e:
        print("[AVISO] No se pudo leer RazonSocial:", e)

    conn.close()

    # Agrupar por email para encontrar duplicados
    por_email = {}
    for cod, em in filas:
        por_email.setdefault(em, []).append(cod)

    duplicados = {em: cods for em, cods in por_email.items() if len(cods) > 1}

    if not duplicados:
        print("\n[OK] No hay emails duplicados en el ERP.")
        return

    # Salida por pantalla
    print(f"\n=== {len(duplicados)} EMAILS DUPLICADOS ===\n")
    print(f"{'EMAIL':40s}  {'COD.':5s}  NOMBRE")
    print("-" * 80)

    # Y a CSV
    with open(SALIDA, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Email", "CodigoCliente", "Nombre"])
        for em in sorted(duplicados.keys()):
            for cod in sorted(duplicados[em]):
                nombre = nombres.get(cod, "")
                print(f"{em:40s}  {cod}  {nombre}")
                w.writerow([em, cod, nombre])
            print()  # linea en blanco entre grupos

    print(f"\n[OK] Informe guardado en:  {SALIDA}")
    print("    Abrelo con Excel (formato CSV con ; como separador)")

if __name__ == "__main__":
    main()
