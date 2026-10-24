# -*- coding: utf-8 -*-
"""
generar_salidas.py
==================

Genera los artefactos de entrega a partir de los datos activos de la raíz:

* JSON exportado con todos los contactos.
* Reporte PDF con la tabla de contactos y la fecha de generación.
* Respaldo ZIP con ``contactos.dat`` e ``indice.json``.

Los archivos se escriben en ``salidas/`` para no mezclarlos con el código ni
con los datos de prueba. La aplicación gráfica sigue generándolos en la raíz
cuando se usan sus opciones de menú; este script sirve para preparar la
entrega de forma reproducible.

Uso::

    python pruebas/generar_salidas.py

Antes de ejecutarlo, carga el escenario que quieras exportar::

    python pruebas/cargar_escenario.py 01_agenda_normal
    python pruebas/generar_salidas.py
"""

import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "src")
for ruta in (BASE, SRC):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

from servicios import exportador  # noqa: E402
from servicios import utilidades_sistema  # noqa: E402

SALIDAS = os.path.join(BASE, "salidas")
ARCHIVO_JSON = os.path.join(SALIDAS, "contactos_exportados.json")
ARCHIVO_PDF = os.path.join(SALIDAS, "reporte_contactos.pdf")
ARCHIVO_ZIP = os.path.join(SALIDAS, "respaldo_agenda.zip")


def _imprimir_resultado(nombre: str, resultado: dict) -> bool:
    if resultado.get("ok"):
        print("  [OK] {}".format(nombre))
        return True

    print("  [FALLO] {}: {}".format(nombre, resultado.get("error")))
    return False


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    os.chdir(BASE)
    os.makedirs(SALIDAS, exist_ok=True)

    print("Generando salidas en '{}'".format(SALIDAS))
    print("")

    resultados = []

    resultado_json = exportador.exportar_contactos_json(ARCHIVO_JSON)
    resultados.append(
        _imprimir_resultado(
            "JSON ({} contactos)".format(resultado_json.get("cantidad", 0)),
            resultado_json,
        )
    )

    resultado_pdf = exportador.generar_reporte_pdf(ARCHIVO_JSON, ARCHIVO_PDF)
    if resultado_pdf.get("ok"):
        resultados.append(
            _imprimir_resultado(
                "PDF ({} bytes)".format(resultado_pdf.get("tamano_pdf", 0)),
                resultado_pdf,
            )
        )
    else:
        resultados.append(_imprimir_resultado("PDF", resultado_pdf))

    resultado_zip = utilidades_sistema.crear_respaldo_zip(ARCHIVO_ZIP)
    if resultado_zip.get("ok"):
        resultados.append(
            _imprimir_resultado(
                "ZIP ({} bytes, {}% de ahorro)".format(
                    resultado_zip.get("tamano_zip", 0),
                    resultado_zip.get("porcentaje_compresion", 0),
                ),
                resultado_zip,
            )
        )
        print(
            "       original: {} bytes; comprimido: {} bytes".format(
                resultado_zip.get("tamano_original", 0),
                resultado_zip.get("tamano_zip", 0),
            )
        )
    else:
        resultados.append(_imprimir_resultado("ZIP", resultado_zip))

    print("")
    if not all(resultados):
        print("RESULTADO: hubo errores al generar las salidas.")
        return 1

    print("RESULTADO: salidas generadas correctamente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
