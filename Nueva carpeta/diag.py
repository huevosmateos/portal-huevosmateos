"""
diag.py - diagnostico de variables de entorno
Solo muestra lo que Python ve, sin conectar a Supabase.
"""
import os

url = os.environ.get("SUPABASE_URL", "")
key = os.environ.get("SUPABASE_SERVICE_KEY", "")

print("--- URL ---")
print(f"  longitud   : {len(url)}")
print(f"  contenido  : {url!r}")
print()
print("--- CLAVE ---")
print(f"  longitud      : {len(key)}")
if key:
    print(f"  primeros 15   : {key[:15]!r}")
    print(f"  ultimos 15    : {key[-15:]!r}")
    print(f"  empieza por sb_secret_ : {key.startswith('sb_secret_')}")
    print(f"  empieza por eyJ        : {key.startswith('eyJ')}")
    # caracteres no imprimibles
    raros = [c for c in key if not (c.isalnum() or c in '_-.')]
    if raros:
        print(f"  AVISO: hay caracteres raros: {raros[:10]}")
    else:
        print(f"  caracteres : OK (solo alfanumericos y _-.)")
