# -*- coding: utf-8 -*-
"""
exportador.py
=============

Funciones del menú **Exportar** de la agenda de contactos:

* ``exportar_contactos_json``: vuelca todos los contactos a un JSON UTF-8.
* ``generar_reporte_pdf``: crea un reporte PDF tabular a partir de ese JSON.

La fuente de los datos es el índice primario (``indice.json``) y el archivo de
registros de longitud fija (``contactos.dat``). El PDF se genera con ``fpdf2``
usando la fuente estándar Helvetica y texto convertido a Latin-1 con
reemplazo, de modo que tildes y 'ñ' no provoquen errores de codificación.
"""

import json
import os
from datetime import datetime
from typing import Dict, List

from almacenamiento.gestor_archivos import (
    cargar_indice,
    leer_registro_aleatorio,
)

try:  # fpdf2 puede no estar instalado; se informa de forma controlada.
    from fpdf import FPDF
except ImportError:  # pragma: no cover
    FPDF = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
ARCHIVO_JSON_EXPORTADO = "contactos_exportados.json"
ARCHIVO_PDF_REPORTE = "reporte_contactos.pdf"

CAMPOS_CONTACTO = ("id", "nombre", "telefono", "correo", "ciudad")

TITULO_REPORTE = "Agenda de Contactos - Reporte General"

ENCABEZADOS_TABLA = ("ID", "Nombre", "Teléfono", "Correo", "Ciudad")
ANCHOS_COLUMNAS = (16, 48, 30, 62, 34)  # suman 190 mm (A4 con márgenes de 10)
ALTO_ENCABEZADO = 8
ALTO_LINEA = 4.5
ALTO_MINIMO_FILA = 7.5
MARGEN_CELDA = 1.0
TAMANO_FUENTE_TABLA = 8

__all__ = [
    "ARCHIVO_JSON_EXPORTADO",
    "ARCHIVO_PDF_REPORTE",
    "exportar_contactos_json",
    "generar_reporte_pdf",
]


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------
def _error_exportacion(mensaje: str, ruta_json: str) -> Dict[str, object]:
    return {
        "ok": False,
        "error": mensaje,
        "ruta_json": ruta_json,
        "cantidad": 0,
        "total": 0,
        "contactos": [],
    }


def _error_pdf(
    mensaje: str,
    ruta_json: str,
    ruta_pdf: str,
) -> Dict[str, object]:
    return {
        "ok": False,
        "error": mensaje,
        "ruta_json": ruta_json,
        "ruta_pdf": ruta_pdf,
        "cantidad": 0,
        "tamano_pdf": 0,
    }


def _texto_pdf(valor: object) -> str:
    """Convierte un valor a texto seguro para la fuente estándar de fpdf2."""
    if valor is None:
        return ""
    texto = str(valor).replace("\r", " ").replace("\n", " ")
    # Helvetica (fuente estándar) trabaja con Latin-1; se reemplaza lo que no
    # sea representable (por ejemplo emojis) sin lanzar UnicodeEncodeError.
    return texto.encode("latin-1", errors="replace").decode("latin-1")


def _lineas_celda(pdf: "FPDF", texto: str, ancho: float) -> List[str]:
    """Calcula cuántas líneas ocuparía un texto dentro de una celda."""
    if not texto:
        return [""]

    try:
        # fpdf2 >= 2.7.4
        lineas = pdf.multi_cell(
            ancho,
            ALTO_LINEA,
            texto,
            border=0,
            align="L",
            dry_run=True,
            output="LINES",
        )
    except TypeError:
        # Compatibilidad con versiones anteriores de fpdf/pyfpdf.
        lineas = pdf.multi_cell(
            ancho,
            ALTO_LINEA,
            texto,
            border=0,
            align="L",
            split_only=True,
        )

    if not lineas:
        return [texto]
    return list(lineas)


def _dibujar_encabezado_tabla(pdf: "FPDF") -> None:
    """Dibuja la fila de encabezados de la tabla."""
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(210, 225, 240)

    for titulo, ancho in zip(ENCABEZADOS_TABLA, ANCHOS_COLUMNAS):
        pdf.cell(
            ancho,
            ALTO_ENCABEZADO,
            _texto_pdf(titulo),
            border=1,
            align="C",
            fill=True,
        )

    pdf.ln(ALTO_ENCABEZADO)


def _nueva_pagina_tabla(pdf: "FPDF") -> None:
    """Agrega una página y repite el encabezado de la tabla."""
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(
        0,
        6,
        _texto_pdf(TITULO_REPORTE + " (continuación)"),
        align="C",
    )
    pdf.ln(8)
    _dibujar_encabezado_tabla(pdf)


def _dibujar_fila(
    pdf: "FPDF",
    contacto: Dict[str, object],
    numero_fila: int,
) -> None:
    """Dibuja una fila de la tabla, ajustando su alto al texto más largo."""
    valores = [
        _texto_pdf(contacto.get(campo, "")) for campo in CAMPOS_CONTACTO
    ]

    pdf.set_font("Helvetica", "", TAMANO_FUENTE_TABLA)
    lineas_por_celda = [
        _lineas_celda(pdf, valor, ancho - 2 * MARGEN_CELDA)
        for valor, ancho in zip(valores, ANCHOS_COLUMNAS)
    ]

    max_lineas = max(len(lineas) for lineas in lineas_por_celda)
    alto_fila = max(
        ALTO_MINIMO_FILA,
        max_lineas * ALTO_LINEA + 2 * MARGEN_CELDA,
    )

    # Salto de página manual para repetir los encabezados.
    if pdf.get_y() + alto_fila > pdf.page_break_trigger:
        _nueva_pagina_tabla(pdf)

    y = pdf.get_y()
    x = pdf.l_margin

    # Fondo alternado y bordes de todas las celdas de la fila.
    if numero_fila % 2 == 1:
        pdf.set_fill_color(245, 247, 250)
    else:
        pdf.set_fill_color(255, 255, 255)

    for ancho in ANCHOS_COLUMNAS:
        pdf.rect(x, y, ancho, alto_fila, style="DF")
        x += ancho

    # Contenido de cada celda, con salto de línea automático.
    pdf.set_text_color(0, 0, 0)
    x = pdf.l_margin
    for valor, ancho in zip(valores, ANCHOS_COLUMNAS):
        pdf.set_xy(x + MARGEN_CELDA, y + MARGEN_CELDA)
        pdf.multi_cell(
            ancho - 2 * MARGEN_CELDA,
            ALTO_LINEA,
            valor,
            border=0,
            align="L",
        )
        x += ancho

    pdf.set_xy(pdf.l_margin, y + alto_fila)


# ---------------------------------------------------------------------------
# Exportación a JSON
# ---------------------------------------------------------------------------
def exportar_contactos_json(
    ruta_json: str = ARCHIVO_JSON_EXPORTADO,
) -> Dict[str, object]:
    """Exporta todos los contactos a un archivo JSON en UTF-8.

    Lee el índice primario y, para cada entrada, accede directamente al
    registro correspondiente de ``contactos.dat``. Solo se incluyen los cinco
    campos del contacto, sin los metadatos de posición.

    Args:
        ruta_json: Ruta del JSON de salida.

    Returns:
        dict: En éxito, ``{"ok": True, "ruta_json": ..., "cantidad": ...,
        "total": ..., "contactos": [...]}``. Ante cualquier error,
        ``{"ok": False, "error": str, ...}``.
    """
    ruta_temporal = "{}.tmp".format(ruta_json)

    try:
        indice = cargar_indice()
        contactos: List[Dict[str, object]] = []

        # Orden ascendente por ID para que la exportación sea determinista.
        entradas = sorted(indice.items(), key=lambda item: int(item[0]))

        for id_texto, numero_registro in entradas:
            try:
                registro = leer_registro_aleatorio(numero_registro)
            except (
                FileNotFoundError,
                PermissionError,
                OSError,
                ValueError,
            ) as error:
                return _error_exportacion(
                    "No se pudo leer el registro {} (ID {}): {}".format(
                        numero_registro, id_texto, error
                    ),
                    ruta_json,
                )

            contacto: Dict[str, object] = {}
            for campo in CAMPOS_CONTACTO:
                valor = registro.get(campo, "")
                if isinstance(valor, str):
                    valor = valor.strip()
                contacto[campo] = valor

            contactos.append(contacto)

        with open(
            ruta_temporal, "w", encoding="utf-8", newline="\n"
        ) as archivo:
            json.dump(
                contactos,
                archivo,
                ensure_ascii=False,
                indent=4,
            )
            archivo.write("\n")
            archivo.flush()

        os.replace(ruta_temporal, ruta_json)

        return {
            "ok": True,
            "ruta_json": ruta_json,
            "cantidad": len(contactos),
            "total": len(contactos),
            "contactos": contactos,
            "mensaje": "Contactos exportados correctamente a JSON.",
        }

    except FileNotFoundError:
        return _error_exportacion(
            "No se encontró un archivo necesario para la exportación.",
            ruta_json,
        )
    except PermissionError:
        return _error_exportacion(
            "No hay permisos para leer los contactos o escribir el JSON.",
            ruta_json,
        )
    except ValueError as error:
        return _error_exportacion(
            "No se pudo interpretar el índice de contactos: {}".format(error),
            ruta_json,
        )
    except OSError as error:
        return _error_exportacion(
            "Error de entrada/salida al exportar a JSON: {}".format(error),
            ruta_json,
        )
    except Exception as error:
        return _error_exportacion(
            "Error inesperado al exportar a JSON: {}".format(error),
            ruta_json,
        )
    finally:
        try:
            if os.path.exists(ruta_temporal):
                os.remove(ruta_temporal)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Reporte PDF
# ---------------------------------------------------------------------------
def generar_reporte_pdf(
    ruta_json: str = ARCHIVO_JSON_EXPORTADO,
    ruta_pdf: str = ARCHIVO_PDF_REPORTE,
) -> Dict[str, object]:
    """Genera un reporte PDF a partir del JSON exportado.

    Primero actualiza el JSON llamando a ``exportar_contactos_json`` y luego
    lee los datos desde ese archivo. El PDF incluye título, fecha y hora de
    generación, cantidad de contactos y una tabla con bordes.

    Args:
        ruta_json: Ruta del JSON que se genera y se lee.
        ruta_pdf: Ruta del PDF de salida.

    Returns:
        dict: En éxito, ``{"ok": True, "ruta_json": ..., "ruta_pdf": ...,
        "cantidad": ..., "tamano_pdf": ...}``. Ante cualquier error,
        ``{"ok": False, "error": str, ...}``.
    """
    resultado_json = exportar_contactos_json(ruta_json)

    if not resultado_json.get("ok"):
        return _error_pdf(
            "No se pudo actualizar el JSON antes del PDF: {}".format(
                resultado_json.get("error", "error desconocido")
            ),
            ruta_json,
            ruta_pdf,
        )

    if FPDF is None:
        return _error_pdf(
            "La librería 'fpdf2' no está instalada. Instálela con: "
            "python -m pip install fpdf2",
            ruta_json,
            ruta_pdf,
        )

    try:
        with open(ruta_json, "r", encoding="utf-8") as archivo:
            contactos = json.load(archivo)

        if not isinstance(contactos, list):
            return _error_pdf(
                "El JSON exportado no contiene una lista de contactos.",
                ruta_json,
                ruta_pdf,
            )

        fecha_generacion = datetime.now()
        fecha_texto = fecha_generacion.strftime("%d/%m/%Y %H:%M:%S")

        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_margins(10, 10, 10)
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_title(_texto_pdf(TITULO_REPORTE))
        pdf.set_author("Agenda de Contactos")
        pdf.add_page()

        # Encabezado del reporte.
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 9, _texto_pdf(TITULO_REPORTE), align="C")
        pdf.ln(9)

        pdf.set_font("Helvetica", "", 9)
        pdf.cell(
            0,
            6,
            _texto_pdf("Fecha y hora de generación: " + fecha_texto),
            align="C",
        )
        pdf.ln(6)
        pdf.cell(
            0,
            6,
            _texto_pdf(
                "Total de contactos: {}".format(len(contactos))
            ),
            align="C",
        )
        pdf.ln(10)

        _dibujar_encabezado_tabla(pdf)

        if not contactos:
            pdf.set_font("Helvetica", "I", 10)
            pdf.cell(
                sum(ANCHOS_COLUMNAS),
                10,
                _texto_pdf("No hay contactos registrados."),
                border=1,
                align="C",
            )
            pdf.ln(10)
        else:
            for numero_fila, contacto in enumerate(contactos):
                if not isinstance(contacto, dict):
                    return _error_pdf(
                        "El JSON contiene un elemento que no es un contacto.",
                        ruta_json,
                        ruta_pdf,
                    )
                _dibujar_fila(pdf, contacto, numero_fila)

        pdf.output(ruta_pdf)

        if not os.path.isfile(ruta_pdf):
            return _error_pdf(
                "El PDF no se generó en la ruta indicada.",
                ruta_json,
                ruta_pdf,
            )

        return {
            "ok": True,
            "ruta_json": ruta_json,
            "ruta_pdf": ruta_pdf,
            "cantidad": len(contactos),
            "tamano_pdf": os.path.getsize(ruta_pdf),
            "fecha_generacion": fecha_texto,
            "mensaje": "Reporte PDF generado correctamente.",
        }

    except json.JSONDecodeError as error:
        return _error_pdf(
            "El JSON exportado está corrupto: {}".format(error),
            ruta_json,
            ruta_pdf,
        )
    except FileNotFoundError:
        return _error_pdf(
            "No se encontró el JSON exportado o la carpeta del PDF.",
            ruta_json,
            ruta_pdf,
        )
    except PermissionError:
        return _error_pdf(
            "No hay permisos para leer el JSON o escribir el PDF.",
            ruta_json,
            ruta_pdf,
        )
    except OSError as error:
        return _error_pdf(
            "Error de entrada/salida al generar el PDF: {}".format(error),
            ruta_json,
            ruta_pdf,
        )
    except Exception as error:
        return _error_pdf(
            "Error inesperado al generar el PDF: {}".format(error),
            ruta_json,
            ruta_pdf,
        )
