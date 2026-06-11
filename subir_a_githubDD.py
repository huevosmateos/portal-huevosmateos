# -*- coding: utf-8 -*-
"""
subir_a_github.py
-----------------
Sube la carpeta de la web a GitHub Pages.
Hace git add + commit + push desde la carpeta local de la tienda.

USO: doble clic o  py subir_a_github.py
"""

import os
import sys
import subprocess

# ---- Configuracion ----------------------------------------------------------
WEB_DIR = r"C:\bot_whatsapp\webhuevosmateos"


def ejecutar(cmd, cwd=None):
    """Ejecuta un comando y devuelve (codigo_retorno, salida)."""
    try:
        r = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            encoding="utf-8", errors="replace"
        )
        salida = (r.stdout or "") + (r.stderr or "")
        return r.returncode, salida.strip()
    except Exception as e:
        return -1, str(e)


def main():
    print("=" * 62)
    print("SUBIR A GITHUB - HUEVOS MATEOS")
    print("=" * 62)

    # Comprobar carpeta
    if not os.path.isdir(WEB_DIR):
        print("[ERROR] No se encuentra la carpeta:", WEB_DIR)
        input("\nPresiona ENTER para salir...")
        return

    # Comprobar que es un repo git
    if not os.path.isdir(os.path.join(WEB_DIR, ".git")):
        print("[ERROR] La carpeta no es un repositorio git:", WEB_DIR)
        input("\nPresiona ENTER para salir...")
        return

    # Comprobar que git esta disponible
    ret, out = ejecutar(["git", "--version"])
    if ret != 0:
        print("[ERROR] Git no esta instalado o no esta en el PATH.")
        input("\nPresiona ENTER para salir...")
        return
    print("  " + out)

    # Mostrar estado
    print("\nComprobando cambios...")
    ret, status = ejecutar(["git", "status", "--short"], cwd=WEB_DIR)
    if not status:
        print("\n  No hay cambios. La web esta al dia con GitHub.")
        input("\nPresiona ENTER para salir...")
        return

    # Contar ficheros modificados
    lineas = [l for l in status.split("\n") if l.strip()]
    print(f"\n  {len(lineas)} ficheros con cambios:\n")
    for l in lineas[:30]:
        print("    " + l)
    if len(lineas) > 30:
        print(f"    ... y {len(lineas) - 30} mas")

    # Pedir confirmacion
    print()
    resp = input("Subir estos cambios a GitHub? (s/n): ").strip().lower()
    if resp not in ("s", "si", "y", "yes"):
        print("\nCancelado.")
        input("\nPresiona ENTER para salir...")
        return

    # Pedir mensaje de commit (o usar uno por defecto)
    msg = input("Mensaje del commit (ENTER para usar el predeterminado): ").strip()
    if not msg:
        msg = "Actualizar tienda"

    # git add .
    print("\n1/3  git add ...")
    ret, out = ejecutar(["git", "add", "."], cwd=WEB_DIR)
    if ret != 0:
        print("[ERROR] git add fallo:", out)
        input("\nPresiona ENTER para salir...")
        return
    print("     OK")

    # git commit
    print("2/3  git commit ...")
    ret, out = ejecutar(["git", "commit", "-m", msg], cwd=WEB_DIR)
    if ret != 0 and "nothing to commit" not in out:
        print("[ERROR] git commit fallo:", out)
        input("\nPresiona ENTER para salir...")
        return
    print("     OK -", msg)

    # git push
    print("3/3  git push ...")
    ret, out = ejecutar(["git", "push"], cwd=WEB_DIR)
    if ret != 0:
        print("[ERROR] git push fallo:")
        print(out)
        input("\nPresiona ENTER para salir...")
        return
    print("     OK")

    print("\n" + "=" * 62)
    print("[OK] Web subida a GitHub.")
    print("     En 1-2 minutos estara disponible en:")
    print("     https://huevosmateos.github.io/portal-huevosmateos/")
    print("=" * 62)
    input("\nPresiona ENTER para salir...")


if __name__ == "__main__":
    main()
