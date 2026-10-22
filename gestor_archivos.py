# -*- coding: utf-8 -*-
"""
gestor_archivos.py
==================

Motor de acceso aleatorio para la agenda de contactos.

Trabaja sobre ``contactos.dat``, un archivo binario formado por registros de
longitud fija (``TAMANO_REGISTRO`` = 110 bytes). Gracias a ello no hace falta
leer el archivo completo: cada operación salta directamente al byte que le
interesa mediante ``seek()`` y confirma la posición con ``tell()``.

Además mantiene un índice primario en ``indice.json`` (UTF-8) que asocia el
ID de cada contacto (como cadena) con su número de registro::

    {"10": 0, "25": 1}

Operaciones de bajo nivel:

* ``escribir_registro_final``: agrega un contacto al final del archivo.
* ``leer_registro_aleatorio``: lee un contacto por su número de registro.
* ``sobrescribir_registro_en_lugar``: modifica un contacto existente sin
  reescribir los demás registros ni truncar el archivo.

Operaciones de alto nivel (pensadas para la interfaz gráfica):

* ``agregar_contacto``: valida el ID en el índice, escribe, actualiza el
  índice y refresca el hash SHA-256.
* ``buscar_por_id``: localiza un contacto usando primero ``indice.json``.
* ``modificar_por_id``: localiza por ID, sobrescribe el registro in-place y
  refresca el hash SHA-256.

La relación entre número de registro, offset y posición es siempre::

    offset = numero_registro * TAMANO_REGISTRO

El número de registro empieza en 0.
"""

import json
import os
from typing import Dict, Tuple, Union

from modelo_contacto import (
    TAMANO_REGISTRO,
    desempaquetar_contacto,
    empaquetar_contacto,
    validar_id,
)
from utilidades_sistema import guardar_hash_sha256

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
ARCHIVO_CONTACTOS = "contactos.dat"
ARCHIVO_INDICE = "indice.json"

# Campos que debe contener el diccionario de entrada.
CAMPOS_CONTACTO = ("id", "nombre", "telefono", "correo", "ciudad")

__all__ = [
    "ARCHIVO_CONTACTOS",
    "ARCHIVO_INDICE",
    "IndiceCorruptoError",
    "escribir_registro_final",
    "leer_registro_aleatorio",
    "sobrescribir_registro_en_lugar",
    "cargar_indice",
    "guardar_indice",
    "reconstruir_indice",
    "agregar_contacto",
    "buscar_por_id",
    "modificar_por_id",
]


class IndiceCorruptoError(ValueError):
    """El índice primario no tiene una estructura válida."""


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
# Índice primario (indice.json)
# ---------------------------------------------------------------------------
def _normalizar_indice(indice: dict) -> Dict[str, int]:
    """Valida y normaliza el índice a ``{"id": numero_registro}``.

    Las claves se guardan siempre como cadenas sin ceros a la izquierda y los
    valores deben ser enteros no negativos.
    """
    if not isinstance(indice, dict):
        raise IndiceCorruptoError(
            "El índice debe ser un diccionario con el formato {id: numero_registro}."
        )

    normalizado: Dict[str, int] = {}

    for clave, valor in indice.items():
        if isinstance(valor, bool) or not isinstance(valor, int):
            raise IndiceCorruptoError(
                "El número de registro del ID {!r} debe ser un entero.".format(
                    clave
                )
            )
        if valor < 0:
            raise IndiceCorruptoError(
                "El número de registro del ID {!r} no puede ser negativo.".format(
                    clave
                )
            )

        if isinstance(clave, bool):
            raise IndiceCorruptoError(
                "Las claves del índice deben ser IDs numéricos."
            )
        if isinstance(clave, int):
            clave_texto = str(clave)
        elif isinstance(clave, str):
            clave_texto = clave.strip()
        else:
            raise IndiceCorruptoError(
                "Las claves del índice deben ser IDs numéricos."
            )

        if not clave_texto.isdigit():
            raise IndiceCorruptoError(
                "El ID {!r} del índice no es un entero positivo.".format(clave)
            )

        id_numero = int(clave_texto)
        if id_numero <= 0:
            raise IndiceCorruptoError(
                "El ID {!r} del índice no es un entero positivo.".format(clave)
            )

        clave_canonica = str(id_numero)
        if clave_canonica in normalizado:
            raise IndiceCorruptoError(
                "El ID {} aparece duplicado en el índice.".format(clave_canonica)
            )

        normalizado[clave_canonica] = valor

    # Orden numérico para que el JSON sea legible y estable.
    return dict(sorted(normalizado.items(), key=lambda item: int(item[0])))


def guardar_indice(indice: dict) -> None:
    """Guarda el índice en ``indice.json`` con codificación UTF-8.

    La escritura se hace primero en un archivo temporal y luego se reemplaza
    el original con ``os.replace`` para evitar dejar un JSON a medias si el
    proceso falla durante la escritura.

    Args:
        indice: Diccionario ``{"id": numero_registro}``.

    Raises:
        IndiceCorruptoError: Si el índice no tiene la estructura esperada.
        FileNotFoundError: Si no se pudo crear el archivo.
        PermissionError: Si no hay permisos de escritura.
        OSError: Ante cualquier otro error de entrada/salida.
    """
    normalizado = _normalizar_indice(indice)
    ruta_temporal = ARCHIVO_INDICE + ".tmp"

    try:
        with open(
            ruta_temporal, "w", encoding="utf-8", newline="\n"
        ) as archivo:
            json.dump(normalizado, archivo, ensure_ascii=False, indent=2)
            archivo.write("\n")
            archivo.flush()

        os.replace(ruta_temporal, ARCHIVO_INDICE)

    except FileNotFoundError:
        raise FileNotFoundError(
            "No se pudo crear '{}'. Verifique que la carpeta exista.".format(
                ARCHIVO_INDICE
            )
        ) from None
    except PermissionError:
        raise PermissionError(
            "No hay permisos para escribir en '{}'.".format(ARCHIVO_INDICE)
        ) from None
    except OSError as error:
        raise OSError(
            "Error de entrada/salida al guardar '{}': {}".format(
                ARCHIVO_INDICE, error
            )
        ) from error
    finally:
        # Limpieza defensiva si la escritura o el reemplazo fallaron.
        try:
            if os.path.exists(ruta_temporal):
                os.remove(ruta_temporal)
        except OSError:
            pass


def reconstruir_indice() -> Dict[str, int]:
    """Reconstruye el índice leyendo ``contactos.dat`` en bloques de 110 bytes.

    Se usa cuando ``indice.json`` está corrupto o no existe. El resultado se
    guarda en disco para que las siguientes consultas sean directas.

    Returns:
        dict: Índice reconstruido ``{"id": numero_registro}``. Si
        ``contactos.dat`` no existe, retorna ``{}``.

    Raises:
        IndiceCorruptoError: Si algún registro del archivo está incompleto o
            no se puede desempaquetar.
        PermissionError: Si no hay permisos de lectura/escritura.
        OSError: Ante cualquier otro error de entrada/salida.
    """
    indice: Dict[str, int] = {}

    try:
        with open(ARCHIVO_CONTACTOS, "rb") as archivo:
            numero_registro = 0

            while True:
                bloque = archivo.read(TAMANO_REGISTRO)
                if not bloque:
                    break

                if len(bloque) != TAMANO_REGISTRO:
                    raise IndiceCorruptoError(
                        "No se pudo reconstruir el índice: el registro {} de "
                        "'{}' está incompleto ({} de {} bytes).".format(
                            numero_registro,
                            ARCHIVO_CONTACTOS,
                            len(bloque),
                            TAMANO_REGISTRO,
                        )
                    )

                try:
                    contacto = desempaquetar_contacto(bloque)
                except (TypeError, ValueError) as error:
                    raise IndiceCorruptoError(
                        "No se pudo reconstruir el índice: el registro {} de "
                        "'{}' es inválido: {}".format(
                            numero_registro, ARCHIVO_CONTACTOS, error
                        )
                    ) from error

                # Si hubiera IDs repetidos, el último registro prevalece.
                indice[str(contacto["id"])] = numero_registro
                numero_registro += 1

    except FileNotFoundError:
        # Sin archivo de contactos, el índice correcto es vacío.
        indice = {}
    except PermissionError:
        raise PermissionError(
            "No hay permisos para leer '{}'.".format(ARCHIVO_CONTACTOS)
        ) from None
    except OSError as error:
        raise OSError(
            "Error de entrada/salida al reconstruir el índice desde '{}': "
            "{}".format(ARCHIVO_CONTACTOS, error)
        ) from error

    guardar_indice(indice)
    return indice


def cargar_indice() -> Dict[str, int]:
    """Carga el índice primario desde ``indice.json``.

    Si el archivo no existe, retorna ``{}``. Si el JSON está corrupto
    (``json.JSONDecodeError``) o su estructura no es válida, reconstruye el
    índice leyendo ``contactos.dat`` en bloques de ``TAMANO_REGISTRO`` y lo
    vuelve a guardar.

    Returns:
        dict: Índice ``{"id": numero_registro}`` con claves ``str`` y valores
        ``int``.

    Raises:
        PermissionError: Si no hay permisos de lectura/escritura.
        OSError: Ante cualquier otro error de entrada/salida.
    """
    try:
        with open(ARCHIVO_INDICE, "r", encoding="utf-8") as archivo:
            contenido = json.load(archivo)

    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Índice ilegible: se regenera desde el archivo de datos.
        return reconstruir_indice()
    except PermissionError:
        raise PermissionError(
            "No hay permisos para leer '{}'.".format(ARCHIVO_INDICE)
        ) from None
    except OSError as error:
        raise OSError(
            "Error de entrada/salida al cargar '{}': {}".format(
                ARCHIVO_INDICE, error
            )
        ) from error

    try:
        return _normalizar_indice(contenido)
    except IndiceCorruptoError:
        # JSON válido pero con estructura incorrecta: también se regenera.
        return reconstruir_indice()



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


# ---------------------------------------------------------------------------
# API de alto nivel para la interfaz gráfica
# ---------------------------------------------------------------------------
def _resultado_error(mensaje: str, **extra: object) -> Dict[str, object]:
    """Construye un resultado uniforme de error para la interfaz."""
    resultado: Dict[str, object] = {"ok": False, "error": mensaje}
    resultado.update(extra)
    return resultado


def _deshacer_ultimo_registro(posicion_bytes: int) -> None:
    """Recorta ``contactos.dat`` si el índice no se pudo actualizar.

    Es una compensación de mejor esfuerzo: evita que quede un contacto escrito
    pero ausente del índice. Si el recorte también falla, se conserva el error
    original que provocó la llamada.
    """
    try:
        with open(ARCHIVO_CONTACTOS, "r+b") as archivo:
            archivo.truncate(posicion_bytes)
    except OSError:
        pass


def agregar_contacto(datos: Dict[str, object]) -> Dict[str, object]:
    """Agrega un contacto nuevo y actualiza el índice primario.

    Primero verifica en ``indice.json`` que el ID no exista. Si ya existe,
    no escribe nada y retorna un resultado con ``ok=False``. Si no existe,
    agrega el registro al final de ``contactos.dat``, guarda la relación
    ``id -> numero_registro`` en ``indice.json`` y retorna los datos.

    Args:
        datos: Diccionario con ``id``, ``nombre``, ``telefono``, ``correo`` y
            ``ciudad``.

    Returns:
        dict: En éxito, ``{"ok": True, "id": int, ..., "numero_registro": int,
        "posicion_tell": int}``. Si el ID ya existe,
        ``{"ok": False, "error": str, ...}``.

    Raises:
        TypeError: Si los datos no son un diccionario o el ID es inválido.
        ValueError: Si faltan campos o el ID no es válido.
        FileNotFoundError: Si no se pudo crear algún archivo.
        PermissionError: Si no hay permisos de escritura.
        OSError: Ante cualquier otro error de entrada/salida.
    """
    id_c, nombre, telefono, correo, ciudad = _extraer_campos(datos)
    numero_id = validar_id(id_c)
    clave = str(numero_id)

    indice = cargar_indice()

    if clave in indice:
        return _resultado_error(
            "Ya existe un contacto con el ID {}.".format(numero_id),
            id=numero_id,
            numero_registro=indice[clave],
        )

    # Escritura física al final del archivo.
    resultado = escribir_registro_final(datos)

    # Actualización del índice; si falla, se deshace la escritura física.
    indice[clave] = resultado["numero_registro"]
    try:
        guardar_indice(indice)
    except (OSError, ValueError):
        _deshacer_ultimo_registro(resultado["posicion_tell"])
        raise

    # El contenido de contactos.dat cambió: se actualiza su hash SHA-256.
    guardar_hash_sha256()

    # Datos canónicos (con el recorte real que aplicó el modelo de registro).
    contacto = desempaquetar_contacto(
        empaquetar_contacto(numero_id, nombre, telefono, correo, ciudad)
    )

    return {
        "ok": True,
        **contacto,
        "numero_registro": resultado["numero_registro"],
        "posicion_tell": resultado["posicion_tell"],
    }


def buscar_por_id(id_contacto: Union[int, str]) -> Dict[str, object]:
    """Busca un contacto consultando primero ``indice.json``.

    Si el ID está en el índice, obtiene su número de registro y llama a
    ``leer_registro_aleatorio`` para leer solo esos 110 bytes.

    Args:
        id_contacto: ID del contacto a buscar.

    Returns:
        dict: En éxito, los datos del contacto más ``numero_registro``,
        ``posicion_tell`` y ``"ok": True``. Si el ID no existe,
        ``{"ok": False, "error": str, "id": int}``.

    Raises:
        TypeError: Si el ID no es entero ni cadena numérica.
        ValueError: Si el ID no es un entero positivo.
        FileNotFoundError: Si ``contactos.dat`` no existe.
        PermissionError: Si no hay permisos de lectura.
        OSError: Ante cualquier otro error de entrada/salida.
    """
    numero_id = validar_id(id_contacto)
    clave = str(numero_id)
    indice = cargar_indice()

    if clave not in indice:
        return _resultado_error(
            "No existe un contacto con el ID {}.".format(numero_id),
            id=numero_id,
        )

    numero_registro = indice[clave]
    contacto = leer_registro_aleatorio(numero_registro)

    # Control de consistencia: el registro apuntado debe tener el mismo ID.
    if contacto["id"] != numero_id:
        return _resultado_error(
            "El índice está inconsistente: el ID {} apunta al registro {}, "
            "que contiene el ID {}.".format(
                numero_id, numero_registro, contacto["id"]
            ),
            id=numero_id,
            numero_registro=numero_registro,
        )

    contacto["ok"] = True
    return contacto


def modificar_por_id(
    id_contacto: Union[int, str],
    nuevos_datos: Dict[str, object],
) -> Dict[str, object]:
    """Modifica un contacto localizado por su ID en el índice primario.

    Obtiene el ``numero_registro`` desde ``indice.json`` y llama a
    ``sobrescribir_registro_en_lugar``. Se permiten actualizaciones parciales:
    los campos ausentes en ``nuevos_datos`` conservan su valor actual.

    Args:
        id_contacto: ID del contacto a modificar.
        nuevos_datos: Diccionario con los campos a cambiar. Puede incluir o no
            ``id``; si se incluye, debe coincidir con ``id_contacto`` porque
            el ID es la clave primaria.

    Returns:
        dict: En éxito, los datos actualizados más ``numero_registro``,
        ``posicion_tell`` y ``"ok": True``. Si el ID no existe o el índice es
        inconsistente, ``{"ok": False, "error": str, "id": int}``.

    Raises:
        TypeError: Si los datos no son un diccionario o el ID es inválido.
        ValueError: Si se intenta cambiar el ID del contacto.
        FileNotFoundError: Si ``contactos.dat`` no existe.
        PermissionError: Si no hay permisos de escritura.
        OSError: Ante cualquier otro error de entrada/salida.
    """
    numero_id = validar_id(id_contacto)
    clave = str(numero_id)
    indice = cargar_indice()

    if clave not in indice:
        return _resultado_error(
            "No existe un contacto con el ID {}.".format(numero_id),
            id=numero_id,
        )

    if not isinstance(nuevos_datos, dict):
        raise TypeError("Los nuevos datos deben ser un diccionario.")

    if "id" in nuevos_datos:
        id_nuevo = validar_id(nuevos_datos["id"])
        if id_nuevo != numero_id:
            raise ValueError(
                "No se puede cambiar el ID al modificar un contacto: se buscó "
                "el ID {} y se recibió {}.".format(numero_id, id_nuevo)
            )

    numero_registro = indice[clave]
    actual = leer_registro_aleatorio(numero_registro)

    if actual["id"] != numero_id:
        return _resultado_error(
            "El índice está inconsistente: el ID {} apunta al registro {}, "
            "que contiene el ID {}.".format(
                numero_id, numero_registro, actual["id"]
            ),
            id=numero_id,
            numero_registro=numero_registro,
        )

    # Se parte del registro actual y se aplican solo los campos enviados.
    fusion = {campo: actual[campo] for campo in CAMPOS_CONTACTO}
    for campo in CAMPOS_CONTACTO:
        if campo != "id" and campo in nuevos_datos:
            fusion[campo] = nuevos_datos[campo]
    fusion["id"] = numero_id

    actualizado = sobrescribir_registro_en_lugar(numero_registro, fusion)

    # El contenido de contactos.dat cambió: se actualiza su hash SHA-256.
    guardar_hash_sha256()

    actualizado["ok"] = True
    return actualizado

