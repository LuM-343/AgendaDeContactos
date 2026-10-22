"""
gestor_archivos.py
==================

Motor de acceso aleatorio para la agenda de contactos.

Trabaja sobre ``contactos.dat``, un archivo binario formado por registros de
longitud fija (``TAMANO_REGISTRO`` = 110 bytes). Gracias a ello no hace falta
leer el archivo completo: cada operación salta directamente al byte que le
interesa mediante ``seek()`` y confirma la posición con ``tell()``.

Operaciones disponibles:

* ``escribir_registro_final``: agrega un contacto al final del archivo.
* ``leer_registro_aleatorio``: lee un contacto por su número de registro.
* ``sobrescribir_registro_en_lugar``: modifica un contacto existente sin
  reescribir los demás registros ni truncar el archivo.

La relación entre número de registro, offset y posición es siempre::

    offset = numero_registro * TAMANO_REGISTRO

El número de registro empieza en 0.
"""

from typing import Dict, Tuple, Union

from modelo_contacto import (
    TAMANO_REGISTRO,
    desempaquetar_contacto,
    empaquetar_contacto,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
ARCHIVO_CONTACTOS = "contactos.dat"

# Campos que debe contener el diccionario de entrada.
CAMPOS_CONTACTO = ("id", "nombre", "telefono", "correo", "ciudad")

__all__ = [
    "ARCHIVO_CONTACTOS",
    "escribir_registro_final",
    "leer_registro_aleatorio",
    "sobrescribir_registro_en_lugar",
]


# ---------------------------------------------------------------------------
# Validaciones internas
# ---------------------------------------------------------------------------
def _validar_numero_registro(numero_registro: Union[int, str]) -> int:
    """Valida que el número de registro sea un entero mayor o igual que 0."""
    if isinstance(numero_registro, bool):
        raise TypeError("El número de registro no puede ser un booleano.")

    if isinstance(numero_registro, int):
        numero = numero_registro
    elif isinstance(numero_registro, str):
        limpio = numero_registro.strip()
        if not limpio or not limpio.isdigit():
            raise ValueError(
                "El número de registro debe ser un entero mayor o igual que 0."
            )
        numero = int(limpio)
    else:
        raise TypeError(
            "El número de registro debe ser un entero o una cadena numérica."
        )

    if numero < 0:
        raise ValueError(
            "El número de registro debe ser un entero mayor o igual que 0."
        )

    return numero


def _extraer_campos(datos_contacto: Dict[str, object]) -> Tuple[object, ...]:
    """Obtiene los cinco campos del contacto en el orden del registro."""
    if not isinstance(datos_contacto, dict):
        raise TypeError("Los datos del contacto deben ser un diccionario.")

    faltantes = [
        campo for campo in CAMPOS_CONTACTO if campo not in datos_contacto
    ]
    if faltantes:
        raise ValueError(
            "Faltan campos obligatorios del contacto: {}.".format(
                ", ".join(faltantes)
            )
        )

    return tuple(datos_contacto[campo] for campo in CAMPOS_CONTACTO)


# ---------------------------------------------------------------------------
# Escritura al final del archivo
# ---------------------------------------------------------------------------
def escribir_registro_final(datos_contacto: Dict[str, object]) -> Dict[str, int]:
    """Agrega un contacto al final de ``contactos.dat``.

    El archivo se crea si todavía no existe. La posición de escritura se
    obtiene con ``seek(0, 2)`` (desplazamiento desde el final) y ``tell()``;
    el número de registro resulta de dividir esa posición entre el tamaño
    fijo del registro.

    Args:
        datos_contacto: Diccionario con las claves ``id``, ``nombre``,
            ``telefono``, ``correo`` y ``ciudad``. Se ignoran claves extra
            (por ejemplo ``numero_registro`` o ``posicion_tell``).

    Returns:
        dict: ``{"numero_registro": int, "posicion_tell": int}``, donde
        ``posicion_tell`` es el byte en el que quedó escrito el registro.

    Raises:
        TypeError: Si los datos no son un diccionario o el ID es inválido.
        ValueError: Si faltan campos, el ID no es válido o el archivo no
            está alineado al tamaño de registro.
        FileNotFoundError: Si no se pudo crear el archivo.
        PermissionError: Si no hay permisos de escritura.
        OSError: Ante cualquier otro error de entrada/salida.
    """
    id_c, nombre, telefono, correo, ciudad = _extraer_campos(datos_contacto)
    registro = empaquetar_contacto(id_c, nombre, telefono, correo, ciudad)

    try:
        try:
            # "r+b" exige que el archivo exista; si no, se crea con "w+b".
            archivo = open(ARCHIVO_CONTACTOS, "r+b")
        except FileNotFoundError:
            archivo = open(ARCHIVO_CONTACTOS, "w+b")

        with archivo:
            archivo.seek(0, 2)               # ir al final del archivo
            posicion_bytes = archivo.tell()  # byte donde se escribirá

            # Protección de la invariante del acceso aleatorio.
            if posicion_bytes % TAMANO_REGISTRO != 0:
                raise ValueError(
                    "El archivo '{}' está corrupto: su tamaño ({} bytes) no "
                    "es múltiplo de {}.".format(
                        ARCHIVO_CONTACTOS, posicion_bytes, TAMANO_REGISTRO
                    )
                )

            numero_registro = posicion_bytes // TAMANO_REGISTRO
            escritos = archivo.write(registro)
            if escritos != TAMANO_REGISTRO:
                raise OSError(
                    "Se escribieron {} bytes en lugar de {}.".format(
                        escritos, TAMANO_REGISTRO
                    )
                )
            archivo.flush()

    except FileNotFoundError:
        raise FileNotFoundError(
            "No se pudo crear '{}'. Verifique que la carpeta exista.".format(
                ARCHIVO_CONTACTOS
            )
        ) from None
    except PermissionError:
        raise PermissionError(
            "No hay permisos para escribir en '{}'.".format(ARCHIVO_CONTACTOS)
        ) from None
    except OSError as error:
        raise OSError(
            "Error de entrada/salida al escribir en '{}': {}".format(
                ARCHIVO_CONTACTOS, error
            )
        ) from error

    return {
        "numero_registro": numero_registro,
        "posicion_tell": posicion_bytes,
    }


# ---------------------------------------------------------------------------
# Lectura aleatoria
# ---------------------------------------------------------------------------
def leer_registro_aleatorio(
    numero_registro: Union[int, str],
) -> Dict[str, object]:
    """Lee un contacto directamente en su offset, sin recorrer el archivo.

    Args:
        numero_registro: Número del registro a leer (empieza en 0).

    Returns:
        dict: Diccionario del contacto (``id``, ``nombre``, ``telefono``,
        ``correo``, ``ciudad``) más ``numero_registro`` y ``posicion_tell``.

    Raises:
        TypeError: Si el número de registro no es entero ni cadena numérica.
        ValueError: Si el número es negativo o el registro no existe.
        FileNotFoundError: Si ``contactos.dat`` no existe.
        PermissionError: Si no hay permisos de lectura.
        OSError: Ante cualquier otro error de entrada/salida.
    """
    numero = _validar_numero_registro(numero_registro)
    offset = numero * TAMANO_REGISTRO

    try:
        with open(ARCHIVO_CONTACTOS, "rb") as archivo:
            archivo.seek(offset)                 # salto directo al registro
            posicion_actual = archivo.tell()     # debe coincidir con offset
            registro = archivo.read(TAMANO_REGISTRO)

    except FileNotFoundError:
        raise FileNotFoundError(
            "No existe '{}'. Agregue al menos un contacto primero.".format(
                ARCHIVO_CONTACTOS
            )
        ) from None
    except PermissionError:
        raise PermissionError(
            "No hay permisos para leer '{}'.".format(ARCHIVO_CONTACTOS)
        ) from None
    except OSError as error:
        raise OSError(
            "Error de entrada/salida al leer '{}': {}".format(
                ARCHIVO_CONTACTOS, error
            )
        ) from error

    if posicion_actual != offset:
        raise OSError(
            "No se pudo posicionar el archivo en el byte {} (tell() = {}).".format(
                offset, posicion_actual
            )
        )

    if len(registro) != TAMANO_REGISTRO:
        raise ValueError(
            "El registro {} no existe o está incompleto en '{}' "
            "(se leyeron {} de {} bytes).".format(
                numero, ARCHIVO_CONTACTOS, len(registro), TAMANO_REGISTRO
            )
        )

    contacto = desempaquetar_contacto(registro)
    contacto["numero_registro"] = numero
    contacto["posicion_tell"] = posicion_actual
    return contacto


# ---------------------------------------------------------------------------
# Sobrescritura in-place
# ---------------------------------------------------------------------------
def sobrescribir_registro_en_lugar(
    numero_registro: Union[int, str],
    nuevos_datos: Dict[str, object],
) -> Dict[str, object]:
    """Modifica un registro existente sin reescribir el resto del archivo.

    Abre ``contactos.dat`` en modo ``r+b`` (lectura/escritura, sin truncar),
    se posiciona exactamente en ``numero_registro * TAMANO_REGISTRO`` y
    sobrescribe solo esos 110 bytes.

    Args:
        numero_registro: Número del registro a modificar (empieza en 0).
        nuevos_datos: Diccionario con ``id``, ``nombre``, ``telefono``,
            ``correo`` y ``ciudad``.

    Returns:
        dict: Datos almacenados del contacto ya actualizado, más
        ``numero_registro`` y ``posicion_tell``.

    Raises:
        TypeError: Si los datos o el número de registro tienen un tipo inválido.
        ValueError: Si faltan campos, el ID es inválido, el número es negativo,
            el registro no existe o el archivo está desalineado.
        FileNotFoundError: Si ``contactos.dat`` no existe.
        PermissionError: Si no hay permisos de escritura.
        OSError: Ante cualquier otro error de entrada/salida.
    """
    numero = _validar_numero_registro(numero_registro)
    id_c, nombre, telefono, correo, ciudad = _extraer_campos(nuevos_datos)
    registro = empaquetar_contacto(id_c, nombre, telefono, correo, ciudad)
    offset = numero * TAMANO_REGISTRO

    try:
        with open(ARCHIVO_CONTACTOS, "r+b") as archivo:
            # Tamaño actual sin leer el contenido.
            archivo.seek(0, 2)
            tamano_archivo = archivo.tell()

            if offset + TAMANO_REGISTRO > tamano_archivo:
                raise ValueError(
                    "No se puede sobrescribir el registro {}: no existe en "
                    "'{}' (tamaño actual: {} bytes).".format(
                        numero, ARCHIVO_CONTACTOS, tamano_archivo
                    )
                )

            if tamano_archivo % TAMANO_REGISTRO != 0:
                raise ValueError(
                    "El archivo '{}' está corrupto: su tamaño ({} bytes) no "
                    "es múltiplo de {}.".format(
                        ARCHIVO_CONTACTOS, tamano_archivo, TAMANO_REGISTRO
                    )
                )

            archivo.seek(offset)                 # salto directo al registro
            posicion_actual = archivo.tell()
            if posicion_actual != offset:
                raise OSError(
                    "No se pudo posicionar el archivo en el byte {} "
                    "(tell() = {}).".format(offset, posicion_actual)
                )

            escritos = archivo.write(registro)
            if escritos != TAMANO_REGISTRO:
                raise OSError(
                    "Se escribieron {} bytes en lugar de {}.".format(
                        escritos, TAMANO_REGISTRO
                    )
                )
            archivo.flush()

    except FileNotFoundError:
        raise FileNotFoundError(
            "No existe '{}'. No hay ningún registro que sobrescribir.".format(
                ARCHIVO_CONTACTOS
            )
        ) from None
    except PermissionError:
        raise PermissionError(
            "No hay permisos para modificar '{}'.".format(ARCHIVO_CONTACTOS)
        ) from None
    except OSError as error:
        raise OSError(
            "Error de entrada/salida al sobrescribir en '{}': {}".format(
                ARCHIVO_CONTACTOS, error
            )
        ) from error

    actualizado = desempaquetar_contacto(registro)
    actualizado["numero_registro"] = numero
    actualizado["posicion_tell"] = posicion_actual
    return actualizado
