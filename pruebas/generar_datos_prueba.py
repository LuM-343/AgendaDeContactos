# -*- coding: utf-8 -*-
"""
generar_datos_prueba.py
=======================

Genera los escenarios de datos de prueba de la Agenda de Contactos.

Cada escenario queda en su propia carpeta dentro de ``datos_prueba/`` con los
tres archivos que usa la aplicación en tiempo de ejecución:

* ``contactos.dat``    -> registros binarios de 110 bytes.
* ``indice.json``      -> índice primario ``{"id": numero_registro}``.
* ``contactos.sha256`` -> SHA-256 del archivo de contactos.

El script es idempotente: vuelve a crear los escenarios desde cero cada vez
que se ejecuta. **No modifica** los archivos activos de la raíz del proyecto.

Uso::

    python pruebas/generar_datos_prueba.py

Los escenarios se describen en ``datos_prueba/LEEME.md`` y en
``datos_prueba/manifest.json``. Para cargar uno en la raíz activa::

    python pruebas/cargar_escenario.py 01_agenda_normal
"""

import hashlib
import json
import os
import shutil
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "src")
for ruta in (BASE, SRC):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

from modelo.contacto import (  # noqa: E402
    CIUDAD_LEN,
    CORREO_LEN,
    ID_LEN,
    NOMBRE_LEN,
    TAMANO_REGISTRO,
    TELEFONO_LEN,
    desempaquetar_contacto,
    empaquetar_contacto,
)

DATOS_PRUEBA = os.path.join(BASE, "datos_prueba")
ARCHIVO_DAT = "contactos.dat"
ARCHIVO_INDICE = "indice.json"
ARCHIVO_HASH = "contactos.sha256"
CAMPOS = ("id", "nombre", "telefono", "correo", "ciudad")


# ---------------------------------------------------------------------------
# Datos base
# ---------------------------------------------------------------------------
CONTACTOS_NORMAL = [
    {
        "id": 7,
        "nombre": "Ana Lucía Morales",
        "telefono": "5555-0101",
        "correo": "ana.morales@correo.com",
        "ciudad": "Quetzaltenango",
    },
    {
        "id": 1,
        "nombre": "Carlos Enrique Pérez",
        "telefono": "5555-0102",
        "correo": "carlos.perez@correo.com",
        "ciudad": "Guatemala",
    },
    {
        "id": 25,
        "nombre": "María José Hernández",
        "telefono": "5555-0103",
        "correo": "maria.hernandez@correo.com",
        "ciudad": "Cobán",
    },
    {
        "id": 3,
        "nombre": "José Núñez",
        "telefono": "8888-1234",
        "correo": "jose.nunez@correo.com",
        "ciudad": "San José",
    },
    {
        "id": 12,
        "nombre": "Lucía Fernández",
        "telefono": "5555-0104",
        "correo": "lucia.fernandez@correo.com",
        "ciudad": "Antigua Guatemala",
    },
    {
        "id": 99,
        "nombre": "Pedro Ixcoy",
        "telefono": "5555-0105",
        "correo": "pedro.ixcoy@correo.com",
        "ciudad": "Huehuetenango",
    },
    {
        "id": 42,
        "nombre": "Rosa Elena Chávez",
        "telefono": "5555-0106",
        "correo": "rosa.chavez@correo.com",
        "ciudad": "Mazatenango",
    },
    {
        "id": 8,
        "nombre": "Miguel Ángel Tzul",
        "telefono": "5555-0107",
        "correo": "miguel.tzul@correo.com",
        "ciudad": "Puerto Barrios",
    },
    {
        "id": 100,
        "nombre": "Sofía de León",
        "telefono": "5555-0108",
        "correo": "sofia.deleon@correo.com",
        "ciudad": "Chimaltenango",
    },
    {
        "id": 2147483647,
        "nombre": "Juan Pablo García",
        "telefono": "5555-0109",
        "correo": "juan.garcia@correo.com",
        "ciudad": "Escuintla",
    },
    {
        "id": 15,
        "nombre": "Andrea Michelle Recinos",
        "telefono": "5555-0110",
        "correo": "andrea.recinos@correo.com",
        "ciudad": "Sololá",
    },
    {
        "id": 60,
        "nombre": "Luis Fernando Ajú",
        "telefono": "5555-0111",
        "correo": "luis.aju@correo.com",
        "ciudad": "Zacapa",
    },
]

# Todos los campos llegan exactamente al límite de bytes del registro.
CONTACTOS_LIMITES = [
    {
        "id": 9999999999,  # 10 dígitos: máximo para ID_LEN
        "nombre": "Ana Lucía Fernández de León",  # 30 bytes exactos
        "telefono": "+502 5555-12345",             # 15 bytes exactos
        "correo": "maria.fernanda.lopez@correos.com.gt",  # 35 bytes exactos
        "ciudad": "San Marcos La Laguna",          # 20 bytes exactos
    },
    {
        "id": 555,
        "nombre": "José Ángel Núñez Ixcoy",
        "telefono": "7777-8888",
        "correo": "jose.nunez@correo.com",
        "ciudad": "Totonicapán",
    },
    {
        "id": 2,
        "nombre": "Ñandú Pérez",
        "telefono": "1234-5678",
        "correo": "nandu.perez@correo.com",
        "ciudad": "Chichicastenango",
    },
    {
        "id": 1000000000,
        "nombre": "María Fernanda López",
        "telefono": "5555-2222",
        "correo": "maria.lopez@correo.com",
        "ciudad": "San Juan Ostuncalco",
    },
]

CONTACTO_UNICO = [
    {
        "id": 42,
        "nombre": "Contacto Único",
        "telefono": "4000-0001",
        "correo": "unico@correo.com",
        "ciudad": "Quetzaltenango",
    },
]


# ---------------------------------------------------------------------------
# Utilidades de generación
# ---------------------------------------------------------------------------
def _crear_carpeta(nombre: str) -> str:
    """Crea (o recrea) la carpeta de un escenario."""
    carpeta = os.path.join(DATOS_PRUEBA, nombre)
    if os.path.isdir(carpeta):
        shutil.rmtree(carpeta)
    os.makedirs(carpeta)
    return carpeta


def _empaquetar(contacto: dict) -> bytes:
    """Empaqueta un contacto y comprueba que ningún campo se recortó."""
    registro = empaquetar_contacto(
        contacto["id"],
        contacto["nombre"],
        contacto["telefono"],
        contacto["correo"],
        contacto["ciudad"],
    )
    recuperado = desempaquetar_contacto(registro)

    for campo in CAMPOS:
        original = str(contacto[campo]).strip()
        obtenido = str(recuperado[campo])
        if obtenido != original:
            raise ValueError(
                "El campo '{}' del ID {} se recortó: {!r} -> {!r}.".format(
                    campo, contacto["id"], original, obtenido
                )
            )

    return registro


def _guardar_dat(carpeta: str, contactos: list) -> bytes:
    """Escribe ``contactos.dat`` con registros de exactamente 110 bytes."""
    datos = b"".join(_empaquetar(contacto) for contacto in contactos)
    esperado = len(contactos) * TAMANO_REGISTRO
    if len(datos) != esperado:
        raise RuntimeError(
            "Tamaño inesperado: {} bytes en lugar de {}.".format(
                len(datos), esperado
            )
        )

    with open(os.path.join(carpeta, ARCHIVO_DAT), "wb") as archivo:
        archivo.write(datos)

    return datos


def _indice_de(contactos: list, limite: int = None) -> dict:
    """Construye ``{"id": numero_registro}`` en el orden físico del archivo."""
    seleccion = contactos if limite is None else contactos[:limite]
    return {
        str(int(contacto["id"])): posicion
        for posicion, contacto in enumerate(seleccion)
    }


def _guardar_indice(carpeta: str, indice: dict) -> None:
    """Escribe el índice con el mismo formato que usa la aplicación."""
    normalizado = {
        str(int(clave)): int(valor) for clave, valor in indice.items()
    }
    ordenado = dict(
        sorted(normalizado.items(), key=lambda elemento: int(elemento[0]))
    )

    with open(
        os.path.join(carpeta, ARCHIVO_INDICE),
        "w",
        encoding="utf-8",
        newline="\n",
    ) as archivo:
        json.dump(ordenado, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")


def _guardar_hash(carpeta: str, valor: str = None) -> str:
    """Calcula y guarda el SHA-256 del ``contactos.dat`` del escenario."""
    if valor is None:
        with open(os.path.join(carpeta, ARCHIVO_DAT), "rb") as archivo:
            valor = hashlib.sha256(archivo.read()).hexdigest()

    with open(
        os.path.join(carpeta, ARCHIVO_HASH),
        "w",
        encoding="utf-8",
        newline="\n",
    ) as archivo:
        archivo.write(valor)

    return valor


def _copiar(origen: str, destino: str, nombres: list) -> None:
    """Copia archivos de un escenario ya generado a otro."""
    for nombre in nombres:
        shutil.copy2(
            os.path.join(DATOS_PRUEBA, origen, nombre),
            os.path.join(DATOS_PRUEBA, destino, nombre),
        )


def _esperado(
    lecturas_ok: int,
    lecturas_error: int,
    hash_integro: bool = True,
    cargar_indice: str = "ok",
    excepcion: str = None,
    indice_reparado: bool = False,
) -> dict:
    return {
        "cargar_indice": cargar_indice,
        "excepcion": excepcion,
        "registros_leibles": lecturas_ok,
        "registros_con_error": lecturas_error,
        "hash_integro": hash_integro,
        "indice_reparado": indice_reparado,
    }


def _entrada(
    carpeta: str,
    titulo: str,
    descripcion: str,
    resultado: str,
    estado: str,
    registros: int,
    ids: list,
    archivos: list,
    esperado: dict,
    notas: str = "",
) -> dict:
    return {
        "carpeta": carpeta,
        "titulo": titulo,
        "descripcion": descripcion,
        "resultado_esperado": resultado,
        "estado": estado,
        "registros": registros,
        "ids_en_orden_de_registro": ids,
        "archivos": archivos,
        "esperado": esperado,
        "notas": notas,
    }


# ---------------------------------------------------------------------------
# Escenarios
# ---------------------------------------------------------------------------
def escenario_01() -> dict:
    nombre = "01_agenda_normal"
    carpeta = _crear_carpeta(nombre)
    _guardar_dat(carpeta, CONTACTOS_NORMAL)
    _guardar_indice(carpeta, _indice_de(CONTACTOS_NORMAL))
    _guardar_hash(carpeta)

    return _entrada(
        carpeta=nombre,
        titulo="Agenda normal (12 contactos)",
        descripcion=(
            "IDs no consecutivos y en orden físico desordenado; nombres con "
            "tildes y eñe; incluye el ID máximo de 10 dígitos."
        ),
        resultado=(
            "Carga 12 contactos ordenados por ID; permite buscar y modificar "
            "cualquier registro con seek()/tell()."
        ),
        estado="valido",
        registros=len(CONTACTOS_NORMAL),
        ids=[contacto["id"] for contacto in CONTACTOS_NORMAL],
        archivos=[ARCHIVO_DAT, ARCHIVO_INDICE, ARCHIVO_HASH],
        esperado=_esperado(len(CONTACTOS_NORMAL), 0),
        notas="Escenario recomendado para la demostración principal.",
    )


def escenario_02() -> dict:
    nombre = "02_limites_utf8"
    carpeta = _crear_carpeta(nombre)
    _guardar_dat(carpeta, CONTACTOS_LIMITES)
    _guardar_indice(carpeta, _indice_de(CONTACTOS_LIMITES))
    _guardar_hash(carpeta)

    return _entrada(
        carpeta=nombre,
        titulo="Límites de campo y UTF-8",
        descripcion=(
            "El primer registro ocupa exactamente 10/30/15/35/20 bytes en "
            "cada campo; hay tildes, eñe inicial y caracteres multibyte."
        ),
        resultado=(
            "Carga 4 contactos sin recortes; la exportación JSON y el PDF "
            "conservan tildes y eñe."
        ),
        estado="valido",
        registros=len(CONTACTOS_LIMITES),
        ids=[contacto["id"] for contacto in CONTACTOS_LIMITES],
        archivos=[ARCHIVO_DAT, ARCHIVO_INDICE, ARCHIVO_HASH],
        esperado=_esperado(len(CONTACTOS_LIMITES), 0),
        notas="Útil para comprobar que el corte es por bytes, no por caracteres.",
    )


def escenario_03() -> dict:
    nombre = "03_un_registro"
    carpeta = _crear_carpeta(nombre)
    _guardar_dat(carpeta, CONTACTO_UNICO)
    _guardar_indice(carpeta, _indice_de(CONTACTO_UNICO))
    _guardar_hash(carpeta)

    return _entrada(
        carpeta=nombre,
        titulo="Un solo registro",
        descripcion="Agenda con un único contacto en el offset 0.",
        resultado=(
            "Carga 1 contacto; al modificarlo, el archivo conserva 110 bytes."
        ),
        estado="valido",
        registros=1,
        ids=[CONTACTO_UNICO[0]["id"]],
        archivos=[ARCHIVO_DAT, ARCHIVO_INDICE, ARCHIVO_HASH],
        esperado=_esperado(1, 0),
        notas="Caso mínimo del acceso aleatorio.",
    )


def escenario_04() -> dict:
    nombre = "04_agenda_vacia"
    carpeta = _crear_carpeta(nombre)

    with open(os.path.join(carpeta, ARCHIVO_DAT), "wb"):
        pass
    _guardar_indice(carpeta, {})
    _guardar_hash(carpeta)

    return _entrada(
        carpeta=nombre,
        titulo="Agenda vacía (0 registros)",
        descripcion=(
            "contactos.dat existe pero mide 0 bytes; el índice es {} y el "
            "hash corresponde al archivo vacío."
        ),
        resultado="Carga sin contactos ni errores; permite agregar el primero.",
        estado="vacio",
        registros=0,
        ids=[],
        archivos=[ARCHIVO_DAT, ARCHIVO_INDICE, ARCHIVO_HASH],
        esperado=_esperado(0, 0),
    )


def escenario_05() -> dict:
    nombre = "05_hash_alterado"
    carpeta = _crear_carpeta(nombre)
    _copiar("01_agenda_normal", nombre, [ARCHIVO_DAT, ARCHIVO_INDICE])
    _guardar_hash(carpeta, valor="0" * 64)

    return _entrada(
        carpeta=nombre,
        titulo="Hash alterado",
        descripcion=(
            "Los datos y el índice son válidos, pero contactos.sha256 no "
            "coincide con el contenido real."
        ),
        resultado=(
            "Al iniciar aparece ALERTA DE INTEGRIDAD; los contactos siguen "
            "siendo legibles."
        ),
        estado="alerta",
        registros=len(CONTACTOS_NORMAL),
        ids=[contacto["id"] for contacto in CONTACTOS_NORMAL],
        archivos=[ARCHIVO_DAT, ARCHIVO_INDICE, ARCHIVO_HASH],
        esperado=_esperado(len(CONTACTOS_NORMAL), 0, hash_integro=False),
        notas="Escenario para la captura de integridad del informe.",
    )


def escenario_06() -> dict:
    nombre = "06_archivo_truncado"
    carpeta = _crear_carpeta(nombre)

    datos = b"".join(
        _empaquetar(contacto) for contacto in CONTACTOS_NORMAL[:3]
    )
    datos += b"X" * 37  # 3 registros completos + 37 bytes sueltos

    with open(os.path.join(carpeta, ARCHIVO_DAT), "wb") as archivo:
        archivo.write(datos)
    _guardar_indice(carpeta, _indice_de(CONTACTOS_NORMAL, limite=3))
    _guardar_hash(carpeta)  # hash válido del archivo ya corrupto

    return _entrada(
        carpeta=nombre,
        titulo="Archivo truncado",
        descripcion=(
            "contactos.dat mide 367 bytes (3 registros y 37 bytes extra), "
            "por lo que su tamaño no es múltiplo de 110."
        ),
        resultado=(
            "Error controlado al cargar el índice: la aplicación avisa y no "
            "se cierra."
        ),
        estado="error_controlado",
        registros=3,
        ids=[contacto["id"] for contacto in CONTACTOS_NORMAL[:3]],
        archivos=[ARCHIVO_DAT, ARCHIVO_INDICE, ARCHIVO_HASH],
        esperado=_esperado(
            0,
            0,
            cargar_indice="error",
            excepcion="IndiceCorruptoError",
        ),
        notas="El hash coincide: el fallo se detecta por el tamaño del registro.",
    )


def escenario_07() -> dict:
    nombre = "07_indice_corrupto"
    carpeta = _crear_carpeta(nombre)
    _copiar("01_agenda_normal", nombre, [ARCHIVO_DAT, ARCHIVO_HASH])

    with open(
        os.path.join(carpeta, ARCHIVO_INDICE),
        "w",
        encoding="utf-8",
        newline="\n",
    ) as archivo:
        archivo.write('{"7": 0, "1": 1\n')  # JSON inválido a propósito

    return _entrada(
        carpeta=nombre,
        titulo="Índice corrupto (JSON inválido)",
        descripcion=(
            "contactos.dat es válido, pero indice.json está truncado y no se "
            "puede interpretar."
        ),
        resultado=(
            "El índice se reconstruye desde contactos.dat (12 entradas) y se "
            "vuelve a escribir."
        ),
        estado="recuperable",
        registros=len(CONTACTOS_NORMAL),
        ids=[contacto["id"] for contacto in CONTACTOS_NORMAL],
        archivos=[ARCHIVO_DAT, ARCHIVO_INDICE, ARCHIVO_HASH],
        esperado=_esperado(
            len(CONTACTOS_NORMAL), 0, indice_reparado=True
        ),
    )


def escenario_08() -> dict:
    nombre = "08_indice_ausente"
    carpeta = _crear_carpeta(nombre)
    _copiar("01_agenda_normal", nombre, [ARCHIVO_DAT, ARCHIVO_HASH])

    return _entrada(
        carpeta=nombre,
        titulo="Índice ausente",
        descripcion=(
            "Existe contactos.dat con 12 registros y su hash, pero no existe "
            "indice.json."
        ),
        resultado=(
            "El índice se reconstruye automáticamente y se guarda con las 12 "
            "entradas."
        ),
        estado="recuperable",
        registros=len(CONTACTOS_NORMAL),
        ids=[contacto["id"] for contacto in CONTACTOS_NORMAL],
        archivos=[ARCHIVO_DAT, ARCHIVO_HASH],
        esperado=_esperado(
            len(CONTACTOS_NORMAL), 0, indice_reparado=True
        ),
    )


def escenario_09() -> dict:
    nombre = "09_datos_ausentes_con_indice"
    carpeta = _crear_carpeta(nombre)
    _guardar_indice(carpeta, {"7": 0, "1": 1})

    return _entrada(
        carpeta=nombre,
        titulo="Datos ausentes con índice",
        descripcion=(
            "Solo existe indice.json con dos IDs; contactos.dat y el hash no "
            "están."
        ),
        resultado=(
            "La aplicación abre y muestra ERROR DE LECTURA por cada ID, sin "
            "cerrarse."
        ),
        estado="error_controlado",
        registros=2,
        ids=[7, 1],
        archivos=[ARCHIVO_INDICE],
        esperado=_esperado(0, 2),
        notas="Sirve para probar el manejo de FileNotFoundError en la tabla.",
    )


def escenario_10() -> dict:
    nombre = "10_sin_archivos"
    carpeta = _crear_carpeta(nombre)
    with open(os.path.join(carpeta, ".gitkeep"), "w", encoding="utf-8"):
        pass

    return _entrada(
        carpeta=nombre,
        titulo="Carpeta sin archivos",
        descripcion=(
            "No existe ninguno de los tres archivos de la agenda (solo se "
            "conserva .gitkeep para versionar la carpeta)."
        ),
        resultado="Agenda nueva vacía; no se muestran alertas.",
        estado="vacio",
        registros=0,
        ids=[],
        archivos=[],
        esperado=_esperado(0, 0),
    )


def escenario_11() -> dict:
    nombre = "11_indice_incompleto"
    carpeta = _crear_carpeta(nombre)
    _copiar("01_agenda_normal", nombre, [ARCHIVO_DAT, ARCHIVO_HASH])
    _guardar_indice(
        carpeta, _indice_de(CONTACTOS_NORMAL, limite=5)
    )

    return _entrada(
        carpeta=nombre,
        titulo="Índice incompleto",
        descripcion=(
            "contactos.dat tiene 12 registros, pero indice.json solo contiene "
            "las primeras 5 entradas."
        ),
        resultado=(
            "La aplicación detecta que faltan entradas y reconstruye el "
            "índice completo."
        ),
        estado="recuperable",
        registros=len(CONTACTOS_NORMAL),
        ids=[contacto["id"] for contacto in CONTACTOS_NORMAL],
        archivos=[ARCHIVO_DAT, ARCHIVO_INDICE, ARCHIVO_HASH],
        esperado=_esperado(
            len(CONTACTOS_NORMAL), 0, indice_reparado=True
        ),
    )


def escenario_12() -> dict:
    nombre = "12_registro_invalido"
    carpeta = _crear_carpeta(nombre)

    valido = _empaquetar(
        {
            "id": 7,
            "nombre": "Registro Válido",
            "telefono": "5555-3000",
            "correo": "valido@correo.com",
            "ciudad": "Quetzaltenango",
        }
    )
    # El primer registro conserva el tamaño, pero su campo ID son espacios.
    corrupto = b" " * ID_LEN + valido[ID_LEN:]

    segundo = _empaquetar(
        {
            "id": 5,
            "nombre": "Registro Correcto",
            "telefono": "5555-3001",
            "correo": "correcto@correo.com",
            "ciudad": "Sololá",
        }
    )

    with open(os.path.join(carpeta, ARCHIVO_DAT), "wb") as archivo:
        archivo.write(corrupto + segundo)
    _guardar_indice(carpeta, {"7": 0, "5": 1})
    _guardar_hash(carpeta)

    return _entrada(
        carpeta=nombre,
        titulo="Registro con ID inválido",
        descripcion=(
            "El primer registro tiene espacios en el campo ID y no se puede "
            "desempaquetar; el segundo registro es válido."
        ),
        resultado=(
            "El ID 7 produce un error controlado al leerse; el ID 5 sigue "
            "visible y la aplicación no se cierra."
        ),
        estado="error_controlado",
        registros=2,
        ids=["(inválido)", 5],
        archivos=[ARCHIVO_DAT, ARCHIVO_INDICE, ARCHIVO_HASH],
        esperado=_esperado(1, 1),
        notas="Verifica que un registro corrupto no invalide toda la agenda.",
    )


# ---------------------------------------------------------------------------
# Manifiesto y documentación
# ---------------------------------------------------------------------------
def _escribir_manifiesto(escenarios: list) -> None:
    manifiesto = {
        "proyecto": "Agenda de Contactos con Acceso Aleatorio",
        "tamano_registro": TAMANO_REGISTRO,
        "campos": {
            "id": ID_LEN,
            "nombre": NOMBRE_LEN,
            "telefono": TELEFONO_LEN,
            "correo": CORREO_LEN,
            "ciudad": CIUDAD_LEN,
        },
        "escenarios": escenarios,
    }

    with open(
        os.path.join(DATOS_PRUEBA, "manifest.json"),
        "w",
        encoding="utf-8",
        newline="\n",
    ) as archivo:
        json.dump(manifiesto, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")


def _escribir_leeme(escenarios: list) -> None:
    lineas = [
        "# Datos de prueba",
        "",
        "Escenarios generados automáticamente por",
        "`pruebas/generar_datos_prueba.py`. **No los edites a mano**: vuelve a",
        "ejecutar el generador si necesitas cambiarlos.",
        "",
        "Cada carpeta contiene los archivos que la aplicación espera en su",
        "raíz: `contactos.dat`, `indice.json` y `contactos.sha256`.",
        "",
        "## Cómo cargar un escenario",
        "",
        "Cierra la aplicación, elige un escenario y vuelve a abrirla:",
        "",
        "```bat",
        "python pruebas/cargar_escenario.py --listar",
        "python pruebas/cargar_escenario.py 01_agenda_normal",
        "python main.py",
        "```",
        "",
        "El cargador guarda una copia del estado activo anterior en",
        "`datos_prueba/00_actual/` antes de reemplazarlo. Para volver a ese",
        "estado:",
        "",
        "```bat",
        "python pruebas/cargar_escenario.py 00_actual",
        "```",
        "",
        "## Escenarios",
        "",
        "| Carpeta | Contenido | Resultado esperado |",
        "|---|---|---|",
    ]

    for escenario in escenarios:
        lineas.append(
            "| `{carpeta}` | {descripcion} | {resultado} |".format(
                carpeta=escenario["carpeta"],
                descripcion=escenario["descripcion"],
                resultado=escenario["resultado_esperado"],
            )
        )

    lineas.extend(
        [
            "",
            "## Verificación automática",
            "",
            "```bat",
            "python pruebas/comprobar_escenarios.py",
            "```",
            "",
            "El verificador copia cada escenario a una carpeta temporal, llama",
            "a las funciones reales de la aplicación y comprueba el resultado",
            "descrito en `manifest.json`.",
            "",
            "## Escenario actual",
            "",
            "`00_actual/` no es un escenario de prueba: es el respaldo del",
            "último estado que estaba activo en la raíz del proyecto. Se",
            "actualiza cada vez que se carga un escenario.",
            "",
        ]
    )

    with open(
        os.path.join(DATOS_PRUEBA, "LEEME.md"),
        "w",
        encoding="utf-8",
        newline="\n",
    ) as archivo:
        archivo.write("\n".join(lineas))


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------
def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    os.makedirs(DATOS_PRUEBA, exist_ok=True)

    escenarios = [
        escenario_01(),
        escenario_02(),
        escenario_03(),
        escenario_04(),
        escenario_05(),
        escenario_06(),
        escenario_07(),
        escenario_08(),
        escenario_09(),
        escenario_10(),
        escenario_11(),
        escenario_12(),
    ]

    _escribir_manifiesto(escenarios)
    _escribir_leeme(escenarios)

    print("Datos de prueba generados en:")
    print("  {}".format(DATOS_PRUEBA))
    print("")
    for escenario in escenarios:
        archivos = ", ".join(escenario["archivos"]) or "(ninguno)"
        print(
            "  [{estado:>16}] {carpeta:<28} {registros:>2} reg.  {archivos}".format(
                estado=escenario["estado"],
                carpeta=escenario["carpeta"],
                registros=escenario["registros"],
                archivos=archivos,
            )
        )

    print("")
    print("Manifiesto: {}".format(os.path.join(DATOS_PRUEBA, "manifest.json")))
    print("Guía:       {}".format(os.path.join(DATOS_PRUEBA, "LEEME.md")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
