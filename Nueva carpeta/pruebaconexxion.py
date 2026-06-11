"""
prueba_conexion.py
------------------
Script MINIMO para verificar que la conexion con Supabase funciona.
No inserta nada, no borra nada. Solo cuenta filas de las tablas (deben ser 0).

USO:
   1) Crear las variables de entorno SUPABASE_URL y SUPABASE_SERVICE_KEY
      (ver instrucciones de Claude). No escribir las claves dentro de este archivo.
   2) Ejecutar desde cmd:   py prueba_conexion.py
"""

import os
import sys

# Comprobacion previa: la libreria esta instalada
try:
    from supabase import create_client
except ImportError:
    print("ERROR: no esta instalada la libreria 'supabase'.")
    print("Instala con:   py -m pip install supabase")
    sys.exit(1)

# Leer URL y clave secreta desde variables de entorno.
# Asi la SERVICE_ROLE no queda escrita en el codigo.
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not URL or not KEY:
    print("ERROR: no encuentro las variables de entorno.")
    print("  SUPABASE_URL          =", "OK" if URL else "FALTA")
    print("  SUPABASE_SERVICE_KEY  =", "OK" if KEY else "FALTA")
    print()
    print("Cierra y vuelve a abrir el cmd despues de definirlas, o usa")
    print("el comando 'set' en la misma sesion antes de ejecutar.")
    sys.exit(1)

print("URL:", URL)
print("Clave: oculta (longitud=", len(KEY), ")")
print("Conectando con Supabase...")

# Crear cliente
sb = create_client(URL, KEY)

# Probar las 3 tablas: pedir un contador (count) sin traer datos.
for tabla in ("articulos", "clientes", "ofertas"):
    try:
        # head=True + count='exact' = solo cuenta, no descarga filas
        r = sb.table(tabla).select("*", count="exact", head=True).execute()
        print(f"  tabla {tabla:10s} -> {r.count} filas")
    except Exception as e:
        print(f"  tabla {tabla:10s} -> ERROR: {e}")

print()
print("OK - conexion verificada.")