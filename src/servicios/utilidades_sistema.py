# -*- coding: utf-8 -*-
"""
utilidades_sistema.py
=====================

Herramientas del menú **Herramientas** de la agenda de contactos:

* Integridad del archivo de datos mediante SHA-256 (``contactos.sha256``).
* Respaldo comprimido de ``contactos.dat`` e ``indice.json`` en un ZIP.
* Metadatos y permisos del archivo de contactos con ``os.stat``/``os.access``.

Todas las funciones públicas capturan sus errores y retornan diccionarios con
información útil, de modo que la interfaz gráfica nunca reciba una excepción
inesperada por un archivo ausente o sin permisos.
"""

import hashlib
import os
import zipfile
from datetime import datetime
from typing import Dict

from modelo.contacto import TAMANO_REGISTRO

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
ARCHIVO_CONTACTOS = "contactos.dat"
ARCHIVO_INDICE = "indice.json"
ARCHIVO_HASH = "contactos.sha256"
ARCHIVO_RESPALDO = "respaldo_agenda.zip"

BLOQUE_LECTURA = 64 * 1024  # 64 KiB por lectura al calcular el hash

MENSAJE_ALERTA = (
    "ALERTA: El archivo contactos.dat fue modificado fuera de la aplicación."
)

__all__ = [
    "ARCHIVO_CONTACTOS",
    "ARCHIVO_INDICE",
    "ARCHIVO_HASH",
    "ARCHIVO_RESPALDO",
    "guardar_hash_sha256",
    "verificar_integridad_sha256",
    "crear_respaldo_zip",
    "obtener_metadatos_archivo",
]


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------
def _calcular_sha256(ruta: str) -> str:
    """Calcula el SHA-256 de un archivo leyéndolo por bloques."""
    sha = hashlib.sha256()
    with open(ruta, "rb") as archivo:
        while True:
            bloque = archivo.read(BLOQUE_LECTURA)
            if not bloque:
                break
            sha.update(bloque)
    return sha.hexdigest()


def _error_hash(mensaje: str) -> Dict[str, object]:
    return {
        "ok": False,
        "error": mensaje,
        "hash": None,
        "ruta_hash": ARCHIVO_HASH,
    }


def _error_zip(mensaje: str, ruta_zip: str) -> Dict[str, object]:
    return {
        "ok": False,
        "error": mensaje,
        "ruta_zip": ruta_zip,
        "archivos_incluidos": [],
        "tamano_original": 0,
        "tamano_zip": 0,
        "porcentaje_compresion": 0.0,
    }


def _error_metadatos(mensaje: str, existe: bool = False) -> Dict[str, object]:
    return {
        "ok": False,
        "existe": existe,
        "ruta": ARCHIVO_CONTACTOS,
        "error": mensaje,
        "tamano": 0,
        "tamano_bytes": 0,
        "cantidad_registros": 0,
        "ultima_modificacion": None,
        "fecha_modificacion": None,
        "permiso_lectura": False,
        "permiso_escritura": False,
    }


# ---------------------------------------------------------------------------
# Integridad SHA-256
# ---------------------------------------------------------------------------
def guardar_hash_sha256() -> Dict[str, object]:
    """Calcula el SHA-256 de ``contactos.dat`` y lo guarda en UTF-8.

    La escritura se hace en un archivo temporal y luego se reemplaza el
    original con ``os.replace`` para no dejar un hash a medias si ocurre un
    fallo durante el guardado.

    Returns:
        dict: En éxito, ``{"ok": True, "hash": str, "ruta_hash": str, ...}``.
        Si no existe el archivo de datos o hay un problema de permisos,
        ``{"ok": False, "error": str, ...}``.
    """
    ruta_temporal = ARCHIVO_HASH + ".tmp"

    try:
        if not os.path.isfile(ARCHIVO_CONTACTOS):
            return _error_hash(
                "No existe '{}'; no se puede calcular el hash.".format(
                    ARCHIVO_CONTACTOS
                )
            )

        hash_actual = _calcular_sha256(ARCHIVO_CONTACTOS)

        with open(
            ruta_temporal, "w", encoding="utf-8", newline="\n"
        ) as archivo:
            archivo.write(hash_actual)
            archivo.flush()

        os.replace(ruta_temporal, ARCHIVO_HASH)

        return {
            "ok": True,
            "hash": hash_actual,
            "ruta_hash": ARCHIVO_HASH,
            "mensaje": "Hash SHA-256 guardado correctamente.",
        }

    except FileNotFoundError:
        return _error_hash(
            "No se encontró '{}' al calcular el hash.".format(ARCHIVO_CONTACTOS)
        )
    except PermissionError:
        return _error_hash(
            "No hay permisos para leer '{}' o escribir '{}'.".format(
                ARCHIVO_CONTACTOS, ARCHIVO_HASH
            )
        )
    except OSError as error:
        return _error_hash(
            "Error de entrada/salida al guardar el hash: {}".format(error)
        )
    except Exception as error:
        return _error_hash(
            "Error inesperado al guardar el hash: {}".format(error)
        )
    finally:
        # Limpieza defensiva del temporal si algo falló antes del reemplazo.
        try:
            if os.path.exists(ruta_temporal):
                os.remove(ruta_temporal)
        except OSError:
            pass


def verificar_integridad_sha256() -> Dict[str, object]:
    """Compara el SHA-256 actual de ``contactos.dat`` con el guardado.

    Returns:
        dict: Siempre con las claves ``integro``, ``mensaje``, ``hash_actual``
        y ``hash_guardado``. Si no existe ``contactos.dat`` o todavía no hay
        un hash de referencia, se considera un estado inicial válido.

        Si los hashes no coinciden, ``integro`` es ``False`` y ``mensaje``
        contiene la alerta de modificación externa.
    """
    try:
        if not os.path.isfile(ARCHIVO_CONTACTOS):
            return {
                "integro": True,
                "mensaje": (
                    "Estado inicial: todavía no existe '{}'.".format(
                        ARCHIVO_CONTACTOS
                    )
                ),
                "hash_actual": None,
                "hash_guardado": None,
            }

        hash_actual = _calcular_sha256(ARCHIVO_CONTACTOS)

        if not os.path.isfile(ARCHIVO_HASH):
            return {
                "integro": True,
                "mensaje": (
                    "Estado inicial: todavía no existe un hash de referencia."
                ),
                "hash_actual": hash_actual,
                "hash_guardado": None,
            }

        with open(ARCHIVO_HASH, "r", encoding="utf-8") as archivo:
            hash_guardado = archivo.read().strip().lower()

        if not hash_guardado:
            return {
                "integro": True,
                "mensaje": (
                    "Estado inicial: el archivo de hash está vacío."
                ),
                "hash_actual": hash_actual,
                "hash_guardado": None,
            }

        if hash_actual == hash_guardado:
            return {
                "integro": True,
                "mensaje": (
                    "Integridad verificada: '{}' coincide con el hash "
                    "guardado.".format(ARCHIVO_CONTACTOS)
                ),
                "hash_actual": hash_actual,
                "hash_guardado": hash_guardado,
            }

        return {
            "integro": False,
            "mensaje": MENSAJE_ALERTA,
            "hash_actual": hash_actual,
            "hash_guardado": hash_guardado,
        }

    except FileNotFoundError:
        # Los archivos pudieron desaparecer entre la comprobación y la lectura.
        return {
            "integro": True,
            "mensaje": "Estado inicial: no hay archivos para verificar.",
            "hash_actual": None,
            "hash_guardado": None,
        }
    except PermissionError as error:
        return {
            "integro": None,
            "mensaje": (
                "No se pudo verificar la integridad por permisos: {}".format(
                    error
                )
            ),
            "hash_actual": None,
            "hash_guardado": None,
        }
    except OSError as error:
        return {
            "integro": None,
            "mensaje": (
                "No se pudo verificar la integridad por un error de "
                "entrada/salida: {}".format(error)
            ),
            "hash_actual": None,
            "hash_guardado": None,
        }
    except Exception as error:
        return {
            "integro": None,
            "mensaje": (
                "No se pudo verificar la integridad: {}".format(error)
            ),
            "hash_actual": None,
            "hash_guardado": None,
        }


# ---------------------------------------------------------------------------
# Respaldo comprimido
# ---------------------------------------------------------------------------
def crear_respaldo_zip(
    ruta_zip: str = ARCHIVO_RESPALDO,
) -> Dict[str, object]:
    """Crea un respaldo ZIP comprimido con los archivos de la agenda.

    Incluye ``contactos.dat`` y, si existe, ``indice.json``. El porcentaje de
    compresión se calcula como el porcentaje de bytes ahorrados respecto del
    tamaño original; un valor negativo indica que el ZIP quedó más grande que
    los archivos originales (algo normal en archivos muy pequeños).

    Args:
        ruta_zip: Ruta del archivo ZIP a crear.

    Returns:
        dict: En éxito, ``ok``, ``ruta_zip``, ``archivos_incluidos``,
        ``tamano_original``, ``tamano_zip`` y ``porcentaje_compresion``.
        Ante cualquier error, ``{"ok": False, "error": str, ...}`` sin lanzar
        excepciones.
    """
    ruta_temporal = "{}.tmp".format(ruta_zip)

    try:
        if not os.path.isfile(ARCHIVO_CONTACTOS):
            return _error_zip(
                "No existe '{}'; no hay datos para respaldar.".format(
                    ARCHIVO_CONTACTOS
                ),
                ruta_zip,
            )

        archivos = [ARCHIVO_CONTACTOS]
        archivos_faltantes = []

        if os.path.isfile(ARCHIVO_INDICE):
            archivos.append(ARCHIVO_INDICE)
        else:
            archivos_faltantes.append(ARCHIVO_INDICE)

        tamano_original = sum(
            os.path.getsize(ruta) for ruta in archivos
        )

        with zipfile.ZipFile(
            ruta_temporal,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
        ) as respaldo:
            for ruta in archivos:
                respaldo.write(ruta, arcname=os.path.basename(ruta))

        os.replace(ruta_temporal, ruta_zip)
        tamano_zip = os.path.getsize(ruta_zip)

        if tamano_original > 0:
            porcentaje = round(
                (1 - (tamano_zip / tamano_original)) * 100, 2
            )
        else:
            porcentaje = 0.0

        resultado: Dict[str, object] = {
            "ok": True,
            "ruta_zip": ruta_zip,
            "archivos_incluidos": archivos,
            "archivos_faltantes": archivos_faltantes,
            "tamano_original": tamano_original,
            "tamano_zip": tamano_zip,
            "porcentaje_compresion": porcentaje,
            "ahorro_bytes": tamano_original - tamano_zip,
            "mensaje": "Respaldo ZIP creado correctamente.",
        }

        if archivos_faltantes:
            resultado["advertencia"] = (
                "No se incluyeron en el respaldo: {}.".format(
                    ", ".join(archivos_faltantes)
                )
            )

        return resultado

    except FileNotFoundError as error:
        return _error_zip(
            "No se encontró un archivo necesario para el respaldo: {}".format(
                error
            ),
            ruta_zip,
        )
    except PermissionError:
        return _error_zip(
            "No hay permisos para leer los archivos de la agenda o escribir "
            "el ZIP.",
            ruta_zip,
        )
    except zipfile.BadZipFile as error:
        return _error_zip(
            "No se pudo crear el ZIP: {}".format(error), ruta_zip
        )
    except zipfile.LargeZipFile as error:
        return _error_zip(
            "El respaldo excede el tamaño permitido por ZIP: {}".format(error),
            ruta_zip,
        )
    except OSError as error:
        return _error_zip(
            "Error de entrada/salida al crear el respaldo: {}".format(error),
            ruta_zip,
        )
    except Exception as error:
        return _error_zip(
            "Error inesperado al crear el respaldo: {}".format(error),
            ruta_zip,
        )
    finally:
        try:
            if os.path.exists(ruta_temporal):
                os.remove(ruta_temporal)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Metadatos y permisos
# ---------------------------------------------------------------------------
def obtener_metadatos_archivo() -> Dict[str, object]:
    """Obtiene tamaño, registros, fecha y permisos de ``contactos.dat``.

    Returns:
        dict: En éxito incluye ``tamano``/``tamano_bytes``, ``cantidad_registros``
        (``tamano // TAMANO_REGISTRO``), ``ultima_modificacion`` (texto
        legible), ``fecha_modificacion`` (objeto ``datetime``),
        ``permiso_lectura`` y ``permiso_escritura``. Si el archivo no existe o
        no hay permisos, retorna ``ok=False`` y los campos con valores seguros.
    """
    try:
        info = os.stat(ARCHIVO_CONTACTOS)
        fecha = datetime.fromtimestamp(info.st_mtime)

        permiso_lectura = os.access(ARCHIVO_CONTACTOS, os.R_OK)
        permiso_escritura = os.access(ARCHIVO_CONTACTOS, os.W_OK)

        return {
            "ok": True,
            "existe": True,
            "ruta": ARCHIVO_CONTACTOS,
            "tamano": info.st_size,
            "tamano_bytes": info.st_size,
            "cantidad_registros": info.st_size // TAMANO_REGISTRO,
            "ultima_modificacion": fecha.strftime("%Y-%m-%d %H:%M:%S"),
            "fecha_modificacion": fecha,
            "permiso_lectura": permiso_lectura,
            "permiso_escritura": permiso_escritura,
            "mensaje": "Metadatos obtenidos correctamente.",
        }

    except FileNotFoundError:
        return _error_metadatos(
            "No existe '{}'.".format(ARCHIVO_CONTACTOS), existe=False
        )
    except PermissionError as error:
        return _error_metadatos(
            "No hay permisos para consultar '{}': {}".format(
                ARCHIVO_CONTACTOS, error
            ),
            existe=os.path.exists(ARCHIVO_CONTACTOS),
        )
    except OSError as error:
        return _error_metadatos(
            "Error de entrada/salida al consultar '{}': {}".format(
                ARCHIVO_CONTACTOS, error
            ),
            existe=os.path.exists(ARCHIVO_CONTACTOS),
        )
    except Exception as error:
        return _error_metadatos(
            "Error inesperado al consultar '{}': {}".format(
                ARCHIVO_CONTACTOS, error
            ),
            existe=os.path.exists(ARCHIVO_CONTACTOS),
        )
