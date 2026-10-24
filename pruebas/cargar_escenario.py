# -*- coding: utf-8 -*-
"""
cargar_escenario.py
===================

Copia un escenario de ``datos_prueba/`` a la raíz del proyecto, que es donde
la aplicación busca ``contactos.dat``, ``indice.json`` y ``contactos.sha256``.

Antes de reemplazar el estado activo guarda una copia en
``datos_prueba/00_actual/``. Así se puede volver atrás o recuperar los datos
que se estaban usando.

Uso::

    python pruebas/cargar_escenario.py --listar
    python pruebas/cargar_escenario.py 01
    python pruebas/cargar_escenario.py 01_agenda_normal
    python pruebas/cargar_escenario.py agenda_normal
    python pruebas/cargar_escenario.py 00_actual

Cierra la aplicación antes de cargar un escenario. La opción
``--sin-respaldo`` evita guardar el estado activo en ``00_actual/``.
"""

import hashlib
import json
import os
import shutil
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS_PRUEBA = os.path.join(BASE, "datos_prueba")
CARPETA_RESPALDO = os.path.join(DATOS_PRUEBA, "00_actual")
MANIFIESTO = os.path.join(DATOS_PRUEBA, "manifest.json")

ARCHIVO_DAT = "contactos.dat"
ARCHIVO_INDICE = "indice.json"
ARCHIVO_HASH = "contactos.sha256"
ARCHIVOS_ACTIVOS = (ARCHIVO_DAT, ARCHIVO_INDICE, ARCHIVO_HASH)


# ---------------------------------------------------------------------------
# Lectura del manifiesto
# ---------------------------------------------------------------------------
def cargar_manifiesto() -> dict:
    if not os.path.isfile(MANIFIESTO):
        raise FileNotFoundError(
            "No existe '{}'. Ejecuta primero:\n"
            "  python pruebas/generar_datos_prueba.py".format(MANIFIESTO)
        )

    with open(MANIFIESTO, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def _escenarios(manifiesto: dict) -> list:
    escenarios = manifiesto.get("escenarios", [])
    if not isinstance(escenarios, list) or not escenarios:
        raise ValueError("El manifiesto no contiene escenarios válidos.")
    return escenarios


def listar(manifiesto: dict) -> None:
    print("Escenarios disponibles en '{}':".format(DATOS_PRUEBA))
    print("")

    for escenario in _escenarios(manifiesto):
        print(
            "  {:<30} {:>2} registro(s)  [{}]".format(
                escenario["carpeta"],
                escenario.get("registros", 0),
                escenario.get("estado", "?"),
            )
        )
        print("    {}".format(escenario.get("titulo", "")))
        print("    {}".format(escenario.get("descripcion", "")))
        print("    Esperado: {}".format(escenario.get("resultado_esperado", "")))
        print("")

    activo = [
        nombre
        for nombre in ARCHIVOS_ACTIVOS
        if os.path.isfile(os.path.join(BASE, nombre))
    ]
    print(
        "Estado activo en la raíz: {}".format(
            ", ".join(activo) if activo else "(sin archivos)"
        )
    )

    if os.path.isdir(CARPETA_RESPALDO):
        print(
            "Respaldo disponible en '00_actual' (restaurar con: "
            "python pruebas/cargar_escenario.py 00_actual)"
        )


# ---------------------------------------------------------------------------
# Selección e instalación
# ---------------------------------------------------------------------------
def resolver_escenario(manifiesto: dict, texto: str) -> dict:
    texto = texto.strip().lower()
    escenarios = _escenarios(manifiesto)

    exactos = [
        escenario
        for escenario in escenarios
        if escenario["carpeta"].lower() == texto
    ]
    if len(exactos) == 1:
        return exactos[0]

    parciales = []
    for escenario in escenarios:
        carpeta = escenario["carpeta"].lower()
        numero, _, nombre = carpeta.partition("_")
        if (
            carpeta.startswith(texto)
            or numero == texto
            or nombre.startswith(texto)
            or texto in carpeta
        ):
            parciales.append(escenario)

    if len(parciales) == 1:
        return parciales[0]

    if not parciales:
        raise ValueError(
            "No hay un escenario que coincida con '{}'. Usa --listar.".format(
                texto
            )
        )

    raise ValueError(
        "El texto '{}' coincide con varios escenarios: {}. Sé más "
        "específico.".format(
            texto, ", ".join(e["carpeta"] for e in parciales)
        )
    )


def respaldar_estado_activo() -> list:
    """Guarda los archivos activos actuales en ``00_actual/``."""
    activos = [
        nombre
        for nombre in ARCHIVOS_ACTIVOS
        if os.path.isfile(os.path.join(BASE, nombre))
    ]

    if not activos:
        return []

    if os.path.isdir(CARPETA_RESPALDO):
        shutil.rmtree(CARPETA_RESPALDO)
    os.makedirs(CARPETA_RESPALDO)

    for nombre in activos:
        shutil.copy2(
            os.path.join(BASE, nombre),
            os.path.join(CARPETA_RESPALDO, nombre),
        )

    return activos


def _limpiar_activos() -> None:
    for nombre in ARCHIVOS_ACTIVOS:
        ruta = os.path.join(BASE, nombre)
        if os.path.isfile(ruta):
            os.remove(ruta)


def _verificar_estado(escenario: dict) -> list:
    """Comprueba el estado recién instalado y devuelve líneas de resumen."""
    lineas = []

    ruta_dat = os.path.join(BASE, ARCHIVO_DAT)
    ruta_indice = os.path.join(BASE, ARCHIVO_INDICE)
    ruta_hash = os.path.join(BASE, ARCHIVO_HASH)

    if os.path.isfile(ruta_dat):
        tamano = os.path.getsize(ruta_dat)
        lineas.append(
            "  contactos.dat: {} bytes ({} registro(s) de 110 bytes)".format(
                tamano, tamano // 110
            )
        )
        if tamano % 110 != 0:
            lineas.append(
                "  AVISO: el tamaño no es múltiplo de 110 (escenario corrupto)."
            )
    else:
        lineas.append("  contactos.dat: no existe")

    if os.path.isfile(ruta_indice):
        try:
            with open(ruta_indice, "r", encoding="utf-8") as archivo:
                indice = json.load(archivo)
            lineas.append(
                "  indice.json: {} entrada(s)".format(len(indice))
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            lineas.append("  indice.json: inválido a propósito ({})".format(error))
    else:
        lineas.append("  indice.json: no existe")

    if os.path.isfile(ruta_hash) and os.path.isfile(ruta_dat):
        with open(ruta_dat, "rb") as archivo:
            actual = hashlib.sha256(archivo.read()).hexdigest()
        with open(ruta_hash, "r", encoding="utf-8") as archivo:
            guardado = archivo.read().strip().lower()
        lineas.append(
            "  contactos.sha256: {}".format(
                "coincide" if actual == guardado else "NO coincide (a propósito)"
            )
        )
    else:
        lineas.append("  contactos.sha256: no existe")

    return lineas


def _escenario_respaldo() -> dict:
    """Describe el respaldo 00_actual para poder restaurarlo."""
    if not os.path.isdir(CARPETA_RESPALDO):
        raise FileNotFoundError(
            "No existe '{}'. Todavía no se ha respaldado ningún estado.".format(
                CARPETA_RESPALDO
            )
        )

    archivos = [
        nombre
        for nombre in ARCHIVOS_ACTIVOS
        if os.path.isfile(os.path.join(CARPETA_RESPALDO, nombre))
    ]
    if not archivos:
        raise FileNotFoundError(
            "'{}' está vacía: no hay un estado anterior que restaurar.".format(
                CARPETA_RESPALDO
            )
        )

    registros = 0
    ruta_dat = os.path.join(CARPETA_RESPALDO, ARCHIVO_DAT)
    if os.path.isfile(ruta_dat):
        registros = os.path.getsize(ruta_dat) // 110

    return {
        "carpeta": "00_actual",
        "titulo": "Respaldo del estado activo anterior",
        "descripcion": "Archivos guardados automáticamente antes de cargar un escenario.",
        "resultado_esperado": "Restaura el estado que estaba activo antes de la última carga.",
        "estado": "respaldo",
        "registros": registros,
        "ids_en_orden_de_registro": [],
        "archivos": archivos,
        "esperado": {},
        "notas": "",
    }


def instalar(manifiesto: dict, escenario: dict, respaldar: bool = True) -> int:
    carpeta_origen = os.path.join(DATOS_PRUEBA, escenario["carpeta"])
    if not os.path.isdir(carpeta_origen):
        raise FileNotFoundError(
            "No existe la carpeta '{}'. Vuelve a ejecutar el generador.".format(
                carpeta_origen
            )
        )

    print("Cargando escenario: {}".format(escenario["carpeta"]))
    print("  {}".format(escenario.get("titulo", "")))
    print("")

    if respaldar:
        respaldados = respaldar_estado_activo()
        if respaldados:
            print(
                "Estado anterior respaldado en '{}': {}".format(
                    CARPETA_RESPALDO, ", ".join(respaldados)
                )
            )
        else:
            print("No había archivos activos que respaldar.")

    _limpiar_activos()

    copiados = []
    for nombre in ARCHIVOS_ACTIVOS:
        origen = os.path.join(carpeta_origen, nombre)
        if os.path.isfile(origen):
            shutil.copy2(origen, os.path.join(BASE, nombre))
            copiados.append(nombre)

    print(
        "Archivos copiados a la raíz: {}".format(
            ", ".join(copiados) if copiados else "(ninguno)"
        )
    )
    print("")

    for linea in _verificar_estado(escenario):
        print(linea)

    print("")
    print("Resultado esperado:")
    print("  {}".format(escenario.get("resultado_esperado", "")))
    print("")
    print("Listo. Abre la aplicación con: python main.py")
    return 0


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------
def main(argv: list) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    try:
        manifiesto = cargar_manifiesto()
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        print("ERROR: {}".format(error), file=sys.stderr)
        return 1

    if not argv or argv[0] in ("-h", "--help", "-l", "--listar", "listar"):
        listar(manifiesto)
        return 0

    respaldar = "--sin-respaldo" not in argv
    argumentos = [arg for arg in argv if arg != "--sin-respaldo"]

    if len(argumentos) != 1:
        print(
            "Uso:\n"
            "  python pruebas/cargar_escenario.py --listar\n"
            "  python pruebas/cargar_escenario.py <numero_o_nombre> "
            "[--sin-respaldo]",
            file=sys.stderr,
        )
        return 1

    try:
        if argumentos[0].strip().lower() in ("00", "00_actual", "actual"):
            escenario = _escenario_respaldo()
            # No se respalda sobre sí mismo: se restauraría lo que se acaba
            # de borrar.
            return instalar(manifiesto, escenario, respaldar=False)

        escenario = resolver_escenario(manifiesto, argumentos[0])
        return instalar(manifiesto, escenario, respaldar=respaldar)
    except (ValueError, FileNotFoundError, OSError) as error:
        print("ERROR: {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
