# -*- coding: utf-8 -*-
"""
comprobar_escenarios.py
=======================

Verifica automáticamente que los escenarios de ``datos_prueba/`` producen el
resultado esperado con las funciones reales de la aplicación.

Para cada escenario:

1. Copia sus archivos a una carpeta temporal (nunca toca el escenario original).
2. Comprueba el estado del hash SHA-256.
3. Llama a ``cargar_indice()`` y, si corresponde, a ``leer_registro_aleatorio()``.
4. Compara los resultados con lo declarado en ``datos_prueba/manifest.json``.

Uso::

    python pruebas/comprobar_escenarios.py

Devuelve 0 si todos los escenarios se comportan como se espera y 1 si falla
alguno.
"""

import json
import os
import shutil
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "src")
for ruta in (BASE, SRC):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

from almacenamiento import gestor_archivos as gestor  # noqa: E402
from servicios import utilidades_sistema as utilidades  # noqa: E402

DATOS_PRUEBA = os.path.join(BASE, "datos_prueba")
MANIFIESTO = os.path.join(DATOS_PRUEBA, "manifest.json")
ARCHIVO_DAT = "contactos.dat"
ARCHIVO_INDICE = "indice.json"
ARCHIVO_HASH = "contactos.sha256"
ARCHIVOS = (ARCHIVO_DAT, ARCHIVO_INDICE, ARCHIVO_HASH)

FALLOS = []
PASADOS = 0


def check(nombre: str, condicion: bool, detalle: str = "") -> None:
    global PASADOS
    if condicion:
        PASADOS += 1
    else:
        FALLOS.append(nombre)
        print("    [FALLO] {}".format(nombre))
        if detalle:
            print("            {}".format(detalle))


def _copiar_escenario(carpeta_origen: str, destino: str) -> None:
    for nombre in ARCHIVOS:
        origen = os.path.join(carpeta_origen, nombre)
        if os.path.isfile(origen):
            shutil.copy2(origen, os.path.join(destino, nombre))


def _leer_indice(ruta: str) -> dict:
    with open(ruta, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def comprobar_escenario(escenario: dict) -> None:
    nombre = escenario["carpeta"]
    origen = os.path.join(DATOS_PRUEBA, nombre)
    esperado = escenario["esperado"]

    print("  {}".format(nombre))

    if not os.path.isdir(origen):
        check(
            "{}: existe la carpeta".format(nombre),
            False,
            "Ejecuta primero pruebas/generar_datos_prueba.py.",
        )
        return

    temporal = tempfile.mkdtemp(prefix="agenda_escenario_")
    anterior = os.getcwd()

    try:
        _copiar_escenario(origen, temporal)
        os.chdir(temporal)

        # 1) Integridad SHA-256 antes de cualquier reparación.
        resultado_hash = utilidades.verificar_integridad_sha256()
        check(
            "{}: integridad = {}".format(nombre, esperado["hash_integro"]),
            resultado_hash.get("integro") is esperado["hash_integro"],
            "obtenido: {!r}; mensaje: {}".format(
                resultado_hash.get("integro"),
                resultado_hash.get("mensaje"),
            ),
        )

        # 2) Carga del índice.
        indice = None
        error_carga = None
        try:
            indice = gestor.cargar_indice()
        except Exception as error:  # noqa: BLE001 - se compara el tipo esperado
            error_carga = error

        if esperado["cargar_indice"] == "error":
            tipo = esperado.get("excepcion") or "Exception"
            clase = getattr(gestor, tipo, Exception)
            check(
                "{}: cargar_indice lanza {}".format(nombre, tipo),
                isinstance(error_carga, clase),
                "obtenido: {}: {}".format(
                    type(error_carga).__name__ if error_carga else "ninguno",
                    error_carga,
                ),
            )
        else:
            check(
                "{}: cargar_indice no lanza excepción".format(nombre),
                error_carga is None,
                "obtenido: {}: {}".format(
                    type(error_carga).__name__ if error_carga else "ninguno",
                    error_carga,
                ),
            )

        # 3) Lecturas aleatorias y correspondencia ID <-> número de registro.
        if indice is not None:
            leidos = 0
            errores_lectura = 0

            for clave, numero_registro in indice.items():
                try:
                    contacto = gestor.leer_registro_aleatorio(numero_registro)
                except (FileNotFoundError, PermissionError, OSError, ValueError):
                    errores_lectura += 1
                    continue

                leidos += 1
                if str(contacto["id"]) != str(clave):
                    check(
                        "{}: el ID {} apunta al registro correcto".format(
                            nombre, clave
                        ),
                        False,
                        "se leyó el ID {} en el registro {}.".format(
                            contacto["id"], numero_registro
                        ),
                    )

            check(
                "{}: {} registro(s) legible(s)".format(
                    nombre, esperado["registros_leibles"]
                ),
                leidos == esperado["registros_leibles"],
                "obtenidos: {}.".format(leidos),
            )
            check(
                "{}: {} registro(s) con error".format(
                    nombre, esperado["registros_con_error"]
                ),
                errores_lectura == esperado["registros_con_error"],
                "obtenidos: {}.".format(errores_lectura),
            )

            esperados_en_indice = (
                esperado["registros_leibles"]
                + esperado["registros_con_error"]
            )
            check(
                "{}: índice con {} entrada(s)".format(
                    nombre, esperados_en_indice
                ),
                len(indice) == esperados_en_indice,
                "obtenidas: {}.".format(len(indice)),
            )

        # 4) Reparación automática del índice.
        if esperado["indice_reparado"] and indice is not None:
            try:
                reparado = _leer_indice(ARCHIVO_INDICE)
            except (OSError, ValueError, json.JSONDecodeError) as error:
                check(
                    "{}: índice reparado en disco".format(nombre),
                    False,
                    "no se pudo leer: {}".format(error),
                )
            else:
                check(
                    "{}: índice reparado con {} entrada(s)".format(
                        nombre, escenario["registros"]
                    ),
                    len(reparado) == escenario["registros"],
                    "obtenidas: {}.".format(len(reparado)),
                )

    finally:
        os.chdir(anterior)
        shutil.rmtree(temporal, ignore_errors=True)


def main() -> int:
    global PASADOS

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    print("Verificación de datos de prueba")
    print("=" * 60)

    if not os.path.isfile(MANIFIESTO):
        print(
            "ERROR: no existe '{}'. Ejecuta primero:\n"
            "  python pruebas/generar_datos_prueba.py".format(MANIFIESTO),
            file=sys.stderr,
        )
        return 1

    with open(MANIFIESTO, "r", encoding="utf-8") as archivo:
        manifiesto = json.load(archivo)

    escenarios = manifiesto.get("escenarios", [])
    if not escenarios:
        print("ERROR: el manifiesto no contiene escenarios.", file=sys.stderr)
        return 1

    for escenario in escenarios:
        try:
            comprobar_escenario(escenario)
        except Exception as error:  # noqa: BLE001 - reporte defensivo
            FALLOS.append(escenario.get("carpeta", "?"))
            print(
                "    [FALLO] excepción no controlada: {}: {}".format(
                    type(error).__name__, error
                )
            )

    print("")
    print("=" * 60)
    print("Comprobaciones superadas: {}".format(PASADOS))
    print("Comprobaciones fallidas:  {}".format(len(FALLOS)))

    if FALLOS:
        print("RESULTADO: HAY FALLOS")
        for fallo in FALLOS:
            print("  - {}".format(fallo))
        return 1

    print("RESULTADO: TODOS LOS ESCENARIOS PASARON")
    return 0


if __name__ == "__main__":
    sys.exit(main())
