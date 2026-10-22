# -*- coding: utf-8 -*-
"""
modelo_contacto.py
==================

Modelo de registro de longitud fija para el proyecto
"Agenda de Contactos con Acceso Aleatorio".

Cada contacto ocupa exactamente ``TAMANO_REGISTRO`` bytes (110) dentro del
archivo, sin separadores ni saltos de línea. Eso permite localizar cualquier
registro directamente con aritmética de offsets::

    posicion = numero_registro * TAMANO_REGISTRO
    archivo.seek(posicion)
    registro = archivo.read(TAMANO_REGISTRO)

Distribución del registro (offsets calculados en bytes):

    Campo       Bytes   Offset
    ---------   -----   ------
    id          10      0
    nombre      30      10
    telefono    15      40
    correo      35      55
    ciudad      20      90
    ---------   -----
    Total       110

"""

from typing import Dict, Union

# ---------------------------------------------------------------------------
# Constantes del formato
# ---------------------------------------------------------------------------
ID_LEN = 10
NOMBRE_LEN = 30
TELEFONO_LEN = 15
CORREO_LEN = 35
CIUDAD_LEN = 20
TAMANO_REGISTRO = 110  # 10 + 30 + 15 + 35 + 20, sin bytes adicionales

CODIFICACION = "utf-8"
BYTE_RELLENO = b" "  # espacio ASCII: siempre ocupa 1 byte

# Orden físico de los campos dentro del registro.
NOMBRES_CAMPOS = ("id", "nombre", "telefono", "correo", "ciudad")
LONGITUDES_CAMPOS = (ID_LEN, NOMBRE_LEN, TELEFONO_LEN, CORREO_LEN, CIUDAD_LEN)

# Salvaguarda: el tamaño fijo debe coincidir con la suma de los campos.
assert TAMANO_REGISTRO == sum(LONGITUDES_CAMPOS), (
    "TAMANO_REGISTRO no coincide con la suma de los campos."
)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def ajustar_campo_utf8(texto: str, largo_bytes: int) -> bytes:
    """Devuelve ``texto`` ocupando exactamente ``largo_bytes`` bytes en UTF-8.

    El relleno se hace con ``.ljust()`` y espacios ASCII. Si el texto contiene
    caracteres multibyte (tildes, 'ñ', etc.) y al codificarlo supera el límite,
    se recorta de forma segura: nunca se deja un carácter UTF-8 partido a la
    mitad, y los bytes faltantes se completan con espacios.

    Args:
        texto: Valor del campo. ``None`` se trata como cadena vacía.
        largo_bytes: Longitud fija del campo en bytes (entero positivo).

    Returns:
        bytes: Campo ajustado con longitud exactamente igual a ``largo_bytes``.

    Raises:
        ValueError: Si ``largo_bytes`` no es un entero positivo.
    """
    if isinstance(largo_bytes, bool) or not isinstance(largo_bytes, int) or largo_bytes <= 0:
        raise ValueError("largo_bytes debe ser un entero positivo.")

    if texto is None:
        texto = ""
    elif not isinstance(texto, str):
        texto = str(texto)

    # 1) Relleno por caracteres para dejar el campo "cuadrado".
    ajustado = texto.ljust(largo_bytes)
    datos = ajustado.encode(CODIFICACION)

    # 2) Si los caracteres multibyte hacen que se exceda el límite, se corta
    #    a nivel de bytes y se descarta el carácter que haya quedado partido.
    if len(datos) > largo_bytes:
        datos = datos[:largo_bytes]
        datos = datos.decode(CODIFICACION, errors="ignore").encode(CODIFICACION)

    # 3) Si faltan bytes (por el recorte anterior), se rellena con espacios.
    if len(datos) < largo_bytes:
        datos += BYTE_RELLENO * (largo_bytes - len(datos))

    return datos


def validar_id(id_c: Union[int, str]) -> int:
    """Valida y normaliza el ID de un contacto.

    Args:
        id_c: ID como entero o como cadena numérica (por ejemplo ``"7"``).

    Returns:
        int: El ID como entero positivo.

    Raises:
        TypeError: Si el ID no es entero ni cadena.
        ValueError: Si no representa un entero positivo o no cabe en ID_LEN.
    """
    if isinstance(id_c, bool):
        raise TypeError("El ID no puede ser un valor booleano.")

    if isinstance(id_c, int):
        numero = id_c
    elif isinstance(id_c, str):
        limpio = id_c.strip()
        if not limpio or not limpio.isdigit():
            raise ValueError("El ID debe ser un número entero positivo.")
        numero = int(limpio)
    else:
        raise TypeError("El ID debe ser un entero o una cadena numérica.")

    if numero <= 0:
        raise ValueError("El ID debe ser un número entero positivo.")
    if len(str(numero)) > ID_LEN:
        raise ValueError(
            "El ID no puede tener más de {} dígitos.".format(ID_LEN)
        )

    return numero


# ---------------------------------------------------------------------------
# Serialización / deserialización
# ---------------------------------------------------------------------------
def empaquetar_contacto(
    id_c: Union[int, str],
    nombre: str,
    telefono: str,
    correo: str,
    ciudad: str,
) -> bytes:
    """Convierte los datos de un contacto en un registro de 110 bytes UTF-8.

    Args:
        id_c: ID del contacto (entero positivo o cadena numérica).
        nombre: Nombre del contacto.
        telefono: Teléfono del contacto.
        correo: Correo electrónico del contacto.
        ciudad: Ciudad del contacto.

    Returns:
        bytes: Registro de exactamente ``TAMANO_REGISTRO`` bytes, listo para
        escribirse en el archivo con ``write()``.

    Raises:
        TypeError: Si el ID tiene un tipo inválido.
        ValueError: Si el ID no es un entero positivo o no cabe en su campo.
    """
    numero_id = validar_id(id_c)

    piezas = (
        ajustar_campo_utf8(str(numero_id), ID_LEN),
        ajustar_campo_utf8(nombre, NOMBRE_LEN),
        ajustar_campo_utf8(telefono, TELEFONO_LEN),
        ajustar_campo_utf8(correo, CORREO_LEN),
        ajustar_campo_utf8(ciudad, CIUDAD_LEN),
    )
    registro = b"".join(piezas)

    # Verificación defensiva: mantiene la invariante del acceso aleatorio.
    if len(registro) != TAMANO_REGISTRO:
        raise RuntimeError(
            "Registro inválido: se esperaban {} bytes y se generaron {}.".format(
                TAMANO_REGISTRO, len(registro)
            )
        )

    return registro


def desempaquetar_contacto(registro_bytes: bytes) -> Dict[str, object]:
    """Convierte un registro binario de 110 bytes en un diccionario.

    La separación de campos se hace por longitudes fijas en BYTES (no en
    caracteres), que es lo que garantiza que los offsets del archivo sean
    siempre los mismos.

    Args:
        registro_bytes: Exactamente ``TAMANO_REGISTRO`` bytes leídos del
            archivo.

    Returns:
        dict: ``{"id": int, "nombre": str, "telefono": str, "correo": str,
        "ciudad": str}``, con los espacios de relleno eliminados.

    Raises:
        TypeError: Si ``registro_bytes`` no es un objeto de bytes.
        ValueError: Si el tamaño no es el esperado, si algún campo no es
            UTF-8 válido o si el ID almacenado no es un entero.
    """
    if isinstance(registro_bytes, str):
        raise TypeError(
            "Se esperaba un registro en bytes; no se debe abrir el archivo "
            "en modo texto."
        )
    if not isinstance(registro_bytes, (bytes, bytearray, memoryview)):
        raise TypeError("El registro debe ser de tipo bytes.")

    registro = bytes(registro_bytes)
    if len(registro) != TAMANO_REGISTRO:
        raise ValueError(
            "El registro debe medir {} bytes; se recibieron {}.".format(
                TAMANO_REGISTRO, len(registro)
            )
        )

    valores = []
    offset = 0
    for nombre_campo, largo in zip(NOMBRES_CAMPOS, LONGITUDES_CAMPOS):
        fragmento = registro[offset:offset + largo]
        try:
            valores.append(fragmento.decode(CODIFICACION).strip())
        except UnicodeDecodeError as error:
            raise ValueError(
                "El campo '{}' no contiene UTF-8 válido.".format(nombre_campo)
            ) from error
        offset += largo

    texto_id, nombre, telefono, correo, ciudad = valores

    try:
        numero_id = int(texto_id)
    except ValueError as error:
        raise ValueError(
            "El ID almacenado no es un entero válido: {!r}.".format(texto_id)
        ) from error

    return {
        "id": numero_id,
        "nombre": nombre,
        "telefono": telefono,
        "correo": correo,
        "ciudad": ciudad,
    }


# ---------------------------------------------------------------------------
# Demostración rápida
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    ejemplo = empaquetar_contacto(
        7,
        "José Núñez",
        "8888-1234",
        "jose.nunez@correo.com",
        "San José",
    )
    print("Bytes del registro:", len(ejemplo))
    print("Registro binario:  ", ejemplo)
    print("Contacto:          ", desempaquetar_contacto(ejemplo))
