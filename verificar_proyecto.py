# -*- coding: utf-8 -*-
"""
verificar_proyecto.py
=====================

Verificación automática, sin abrir la interfaz gráfica, del proyecto
"Agenda de Contactos con Acceso Aleatorio".

Comprueba:

* Codificación UTF-8 en todas las aperturas de archivos de texto/JSON.
* Alta, búsqueda con ``seek()``/``tell()``, modificación in-place de 110 bytes,
  actualización inmediata de ``contactos.sha256``, exportación PDF y ZIP.
* Respuesta controlada ante archivos ausentes, vacíos, corruptos o sin
  permisos de lectura/escritura.
* Que la interfaz muestre los errores con ``messagebox.showerror``.

Uso::

    python verificar_proyecto.py

El script trabaja en carpetas temporales y no modifica los archivos reales
del proyecto. Devuelve código de salida 0 si todo pasa y 1 si algo falla.
"""

import ast
import builtins
import contextlib
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import traceback
import zipfile
from typing import Dict, Iterator, List, Tuple
from unittest.mock import patch

PROYECTO = os.path.dirname(os.path.abspath(__file__))
if PROYECTO not in sys.path:
    sys.path.insert(0, PROYECTO)

import exportador  # noqa: E402
import gestor_archivos as gestor  # noqa: E402
import modelo_contacto as modelo  # noqa: E402
import utilidades_sistema as utilidades  # noqa: E402

TAMANO = modelo.TAMANO_REGISTRO
FALLOS: List[str] = []
PASADOS = 0


# ---------------------------------------------------------------------------
# Utilidades de la verificación
# ---------------------------------------------------------------------------
def check(nombre: str, condicion: bool, detalle: str = "") -> None:
    """Registra una comprobación y muestra su resultado."""
    global PASADOS
    if condicion:
        PASADOS += 1
        print("[OK]    {}".format(nombre))
    else:
        FALLOS.append(nombre)
        print("[FALLO] {}".format(nombre))
        if detalle:
            print("        -> {}".format(detalle))


def ejecutar_grupo(nombre: str, funcion) -> None:
    """Ejecuta un grupo de pruebas sin detener el resto si algo explota."""
    print("\n== {} ==".format(nombre))
    try:
        funcion()
    except Exception as error:  # pragma: no cover - reporte defensivo
        FALLOS.append("Excepción no controlada en {}".format(nombre))
        print("[FALLO] Excepción no controlada: {}".format(error))
        traceback.print_exc()


@contextlib.contextmanager
def directorio_temporal(nombre: str) -> Iterator[str]:
    """Crea un directorio de trabajo aislado y lo elimina al terminar."""
    anterior = os.getcwd()
    ruta = tempfile.mkdtemp(prefix="agenda_verif_{}_".format(nombre))
    os.chdir(ruta)
    try:
        yield ruta
    finally:
        os.chdir(anterior)
        # En Windows un archivo de solo lectura impide borrar su carpeta.
        for raiz, _dirs, archivos in os.walk(ruta):
            for archivo in archivos:
                try:
                    os.chmod(os.path.join(raiz, archivo), stat.S_IWRITE)
                except OSError:
                    pass
        shutil.rmtree(ruta, ignore_errors=True)


@contextlib.contextmanager
def solo_lectura(ruta: str) -> Iterator[None]:
    """Marca temporalmente un archivo como de solo lectura."""
    os.chmod(ruta, stat.S_IREAD)
    try:
        yield
    finally:
        try:
            os.chmod(ruta, stat.S_IWRITE)
        except OSError:
            pass


def leer_bytes(ruta: str) -> bytes:
    with open(ruta, "rb") as archivo:
        return archivo.read()


def escribir_texto(ruta: str, texto: str) -> None:
    with open(ruta, "w", encoding="utf-8", newline="") as archivo:
        archivo.write(texto)


def leer_texto(ruta: str) -> str:
    with open(ruta, "r", encoding="utf-8") as archivo:
        return archivo.read()


def sha256_archivo(ruta: str) -> str:
    sha = hashlib.sha256()
    with open(ruta, "rb") as archivo:
        while True:
            bloque = archivo.read(64 * 1024)
            if not bloque:
                break
            sha.update(bloque)
    return sha.hexdigest()


def contacto_base(numero_id: str = "1") -> Dict[str, str]:
    return {
        "id": numero_id,
        "nombre": "Jos\u00e9 N\u00fa\u00f1ez",
        "telefono": "8888-1234",
        "correo": "jose.nunez@correo.com",
        "ciudad": "San Jos\u00e9",
    }


class _ProxyArchivo:
    """Envuelve un archivo para registrar seek(), tell() y write()."""

    def __init__(self, real, modo: str) -> None:
        self._real = real
        self.modo = modo
        self.llamadas: List[Tuple[object, ...]] = []

    def __enter__(self):
        self._real.__enter__()
        return self

    def __exit__(self, *argumentos):
        return self._real.__exit__(*argumentos)

    def __getattr__(self, nombre):
        return getattr(self._real, nombre)

    def seek(self, offset, whence=0):
        resultado = self._real.seek(offset, whence)
        self.llamadas.append(("seek", offset, whence, resultado))
        return resultado

    def tell(self):
        resultado = self._real.tell()
        self.llamadas.append(("tell", resultado))
        return resultado

    def write(self, datos):
        resultado = self._real.write(datos)
        self.llamadas.append(("write", len(datos), resultado))
        return resultado

    def flush(self):
        self.llamadas.append(("flush",))
        return self._real.flush()


def _crear_dos_contactos() -> None:
    """Crea dos contactos y comprueba que el estado inicial sea correcto."""
    resultado_1 = gestor.agregar_contacto(contacto_base("1"))
    resultado_2 = gestor.agregar_contacto(
        {
            "id": "2",
            "nombre": "Ana",
            "telefono": "7777-0000",
            "correo": "ana@correo.com",
            "ciudad": "Cartago",
        }
    )
    check("Alta del primer contacto", resultado_1.get("ok") is True)
    check("Alta del segundo contacto", resultado_2.get("ok") is True)
    check(
        "Posiciones tell() 0 y 110",
        resultado_1.get("posicion_tell") == 0
        and resultado_2.get("posicion_tell") == TAMANO,
        repr((resultado_1.get("posicion_tell"), resultado_2.get("posicion_tell"))),
    )
    check(
        "Archivo con exactamente dos registros de 110 bytes",
        os.path.getsize(gestor.ARCHIVO_CONTACTOS) == 2 * TAMANO,
    )


# ---------------------------------------------------------------------------
# 1. Flujo completo: alta, búsqueda, modificación, hash, PDF y ZIP
# ---------------------------------------------------------------------------
def probar_flujo_completo() -> None:
    with directorio_temporal("flujo"):
        check("Agenda nueva: cargar_indice() devuelve {}", gestor.cargar_indice() == {})
        check(
            "Agenda nueva: no se crean archivos prematuramente",
            not os.path.exists(gestor.ARCHIVO_INDICE)
            and not os.path.exists(gestor.ARCHIVO_CONTACTOS),
        )

        _crear_dos_contactos()

        indice = json.loads(leer_bytes(gestor.ARCHIVO_INDICE).decode("utf-8"))
        check("Índice JSON UTF-8 correcto", indice == {"1": 0, "2": 1}, repr(indice))

        datos = leer_bytes(gestor.ARCHIVO_CONTACTOS)
        check("Tamaño total 220 bytes", len(datos) == 2 * TAMANO)
        contacto_0 = modelo.desempaquetar_contacto(datos[:TAMANO])
        check(
            "Acentos y eñe conservados en el registro binario",
            contacto_0["nombre"] == "Jos\u00e9 N\u00fa\u00f1ez"
            and contacto_0["ciudad"] == "San Jos\u00e9",
            repr(contacto_0),
        )

        hash_guardado = leer_bytes(utilidades.ARCHIVO_HASH)
        check(
            "contactos.sha256 es UTF-8 sin BOM",
            not hash_guardado.startswith(b"\xef\xbb\xbf")
            and len(hash_guardado.decode("utf-8").strip()) == 64,
        )
        check(
            "Hash inicial igual al SHA-256 real del archivo",
            hash_guardado.decode("utf-8").strip()
            == hashlib.sha256(datos).hexdigest(),
        )
        check(
            "verificar_integridad_sha256() reporta archivo íntegro",
            utilidades.verificar_integridad_sha256().get("integro") is True,
        )

        # Búsqueda con acceso aleatorio: los metadatos vienen de seek/tell.
        busqueda_1 = gestor.buscar_por_id("1")
        busqueda_2 = gestor.buscar_por_id("2")
        check(
            "Buscar ID 1 devuelve posición 0",
            busqueda_1.get("ok") is True
            and busqueda_1.get("posicion_tell") == 0,
        )
        check(
            "Buscar ID 2 devuelve posición 110",
            busqueda_2.get("ok") is True
            and busqueda_2.get("posicion_tell") == TAMANO,
        )

        # ID duplicado: no debe escribir ni cambiar el hash.
        tamano_antes = os.path.getsize(gestor.ARCHIVO_CONTACTOS)
        hash_antes_dup = leer_bytes(utilidades.ARCHIVO_HASH)
        duplicado = gestor.agregar_contacto(contacto_base("1"))
        check("ID duplicado rechazado", duplicado.get("ok") is False)
        check(
            "ID duplicado no altera contactos.dat ni el hash",
            os.path.getsize(gestor.ARCHIVO_CONTACTOS) == tamano_antes
            and leer_bytes(utilidades.ARCHIVO_HASH) == hash_antes_dup,
        )

        # Modificación in-place con espía de open/seek/tell/write.
        datos_antes = leer_bytes(gestor.ARCHIVO_CONTACTOS)
        hash_antes = leer_bytes(utilidades.ARCHIVO_HASH).decode("utf-8").strip()
        indice_antes = leer_bytes(gestor.ARCHIVO_INDICE)

        registros: List[_ProxyArchivo] = []
        real_open = builtins.open

        def open_espia(ruta, modo="r", *args, **kwargs):
            archivo = real_open(ruta, modo, *args, **kwargs)
            if os.path.basename(os.fspath(ruta)) == gestor.ARCHIVO_CONTACTOS:
                proxy = _ProxyArchivo(archivo, modo)
                registros.append(proxy)
                return proxy
            return archivo

        gestor.open = open_espia
        try:
            modificado = gestor.modificar_por_id(
                "2", {"nombre": "Ana Mar\u00eda", "ciudad": "Heredia"}
            )
        finally:
            del gestor.open

        check("Modificación reportada como exitosa", modificado.get("ok") is True)
        check(
            "Modificación devuelve la misma posición (110)",
            modificado.get("posicion_tell") == TAMANO,
        )
        check(
            "Modificación conserva los acentos",
            modificado.get("nombre") == "Ana Mar\u00eda",
            repr(modificado.get("nombre")),
        )
        check(
            "Modificación no reporta advertencia de hash",
            not modificado.get("advertencia"),
            repr(modificado.get("advertencia")),
        )

        aperturas_rb_mas = [proxy for proxy in registros if proxy.modo == "r+b"]
        check(
            "Se abrió contactos.dat en modo r+b",
            len(aperturas_rb_mas) == 1,
            repr([(p.modo, p.llamadas) for p in registros]),
        )
        if aperturas_rb_mas:
            llamadas = aperturas_rb_mas[0].llamadas
            check(
                "seek() se posicionó exactamente en el byte 110",
                any(
                    llamada[0] == "seek"
                    and llamada[1] == TAMANO
                    and llamada[2] == 0
                    for llamada in llamadas
                ),
                repr(llamadas),
            )
            escrituras = [llamada for llamada in llamadas if llamada[0] == "write"]
            check(
                "Solo se escribieron 110 bytes en una operación",
                len(escrituras) == 1
                and escrituras[0][1] == TAMANO
                and escrituras[0][2] == TAMANO,
                repr(escrituras),
            )
            check(
                "La posición final del puntero es 220",
                any(
                    llamada[0] == "tell" and llamada[1] == 2 * TAMANO
                    for llamada in llamadas
                ),
                repr(llamadas),
            )

        datos_despues = leer_bytes(gestor.ARCHIVO_CONTACTOS)
        check("El tamaño del archivo no cambió", len(datos_despues) == len(datos_antes))
        check(
            "El registro anterior (bytes 0-109) quedó intacto",
            datos_despues[:TAMANO] == datos_antes[:TAMANO],
        )
        check(
            "El registro modificado (bytes 110-219) cambió",
            datos_despues[TAMANO:2 * TAMANO] != datos_antes[TAMANO:2 * TAMANO],
        )
        registro_1 = modelo.desempaquetar_contacto(
            datos_despues[TAMANO:2 * TAMANO]
        )
        check(
            "El registro 1 contiene los nuevos datos",
            registro_1["nombre"] == "Ana Mar\u00eda"
            and registro_1["ciudad"] == "Heredia",
            repr(registro_1),
        )
        check(
            "indice.json no cambió al modificar",
            leer_bytes(gestor.ARCHIVO_INDICE) == indice_antes,
        )

        hash_despues = leer_bytes(utilidades.ARCHIVO_HASH).decode("utf-8").strip()
        check("El hash cambió tras la modificación", hash_despues != hash_antes)
        check(
            "El hash nuevo coincide con el SHA-256 real",
            hash_despues == sha256_archivo(gestor.ARCHIVO_CONTACTOS),
        )
        check(
            "La verificación SHA-256 queda en estado íntegro",
            utilidades.verificar_integridad_sha256().get("integro") is True,
        )
        check(
            "Buscar de nuevo devuelve el dato modificado",
            gestor.buscar_por_id("2").get("nombre") == "Ana Mar\u00eda",
        )

        # Exportación JSON.
        resultado_json = exportador.exportar_contactos_json(
            exportador.ARCHIVO_JSON_EXPORTADO
        )
        check("Exportación JSON exitosa", resultado_json.get("ok") is True)
        check("Exportación JSON con 2 contactos", resultado_json.get("cantidad") == 2)
        raw_json = leer_bytes(exportador.ARCHIVO_JSON_EXPORTADO)
        check(
            "JSON UTF-8 sin BOM",
            not raw_json.startswith(b"\xef\xbb\xbf"),
        )
        exportados = json.loads(raw_json.decode("utf-8"))
        check(
            "JSON conserva acentos y datos modificados",
            exportados[0]["nombre"] == "Jos\u00e9 N\u00fa\u00f1ez"
            and exportados[1]["nombre"] == "Ana Mar\u00eda",
            repr(exportados),
        )

        # Reporte PDF.
        if exportador.FPDF is None:
            print("[OMITIDO] fpdf2 no está instalado; no se prueba el PDF.")
        else:
            resultado_pdf = exportador.generar_reporte_pdf(
                exportador.ARCHIVO_JSON_EXPORTADO,
                exportador.ARCHIVO_PDF_REPORTE,
            )
            check("Generación del PDF exitosa", resultado_pdf.get("ok") is True)
            check(
                "El PDF existe y tiene tamaño mayor que cero",
                os.path.isfile(exportador.ARCHIVO_PDF_REPORTE)
                and os.path.getsize(exportador.ARCHIVO_PDF_REPORTE) > 0,
            )
            check(
                "El PDF tiene cabecera %PDF",
                leer_bytes(exportador.ARCHIVO_PDF_REPORTE).startswith(b"%PDF"),
            )

        # Respaldo ZIP.
        resultado_zip = utilidades.crear_respaldo_zip()
        check("Creación del ZIP exitosa", resultado_zip.get("ok") is True)
        with zipfile.ZipFile(utilidades.ARCHIVO_RESPALDO) as respaldo:
            check("El ZIP no está corrupto", respaldo.testzip() is None)
            nombres = set(respaldo.namelist())
            check(
                "El ZIP contiene contactos.dat e indice.json",
                nombres == {gestor.ARCHIVO_CONTACTOS, gestor.ARCHIVO_INDICE},
                repr(nombres),
            )
            check(
                "El contactos.dat dentro del ZIP coincide con el disco",
                respaldo.read(gestor.ARCHIVO_CONTACTOS) == datos_despues,
            )


# ---------------------------------------------------------------------------
# 2. Archivos ausentes, vacíos y corruptos
# ---------------------------------------------------------------------------
def probar_archivos_ausentes_y_vacios() -> None:
    with directorio_temporal("ausentes"):
        check("Sin archivos: índice vacío", gestor.cargar_indice() == {})
        check(
            "Sin archivos: no se crea indice.json",
            not os.path.exists(gestor.ARCHIVO_INDICE),
        )
        check(
            "Sin archivos: integridad se considera estado inicial",
            utilidades.verificar_integridad_sha256().get("integro") is True,
        )
        metadatos = utilidades.obtener_metadatos_archivo()
        check("Sin archivos: metadatos devuelven ok=False", metadatos.get("ok") is False)
        respaldo = utilidades.crear_respaldo_zip()
        check("Sin archivos: ZIP devuelve ok=False", respaldo.get("ok") is False)
        exportacion = exportador.exportar_contactos_json("vacio.json")
        check("Sin archivos: JSON vacío se exporta sin excepción",
              exportacion.get("ok") is True and exportacion.get("cantidad") == 0)

    with directorio_temporal("vacios"):
        with open(gestor.ARCHIVO_CONTACTOS, "wb"):
            pass
        with open(gestor.ARCHIVO_INDICE, "w", encoding="utf-8"):
            pass

        check("contactos.dat vacío + indice.json vacío no lanza excepción",
              gestor.cargar_indice() == {})
        reparado = json.loads(leer_bytes(gestor.ARCHIVO_INDICE).decode("utf-8"))
        check("El índice vacío se repara como {}", reparado == {})
        check(
            "El archivo de datos vacío sigue midiendo 0 bytes",
            os.path.getsize(gestor.ARCHIVO_CONTACTOS) == 0,
        )


def probar_indice_corrupto_o_ausente() -> None:
    with directorio_temporal("indice"):
        _crear_dos_contactos()
        indice_esperado = {"1": 0, "2": 1}

        escribir_texto(gestor.ARCHIVO_INDICE, "{esto no es JSON")
        reconstruido = gestor.cargar_indice()
        check("Índice corrupto se reconstruye", reconstruido == indice_esperado)
        check(
            "Índice corrupto se reescribe como JSON UTF-8 válido",
            json.loads(leer_bytes(gestor.ARCHIVO_INDICE).decode("utf-8"))
            == indice_esperado,
        )

        escribir_texto(gestor.ARCHIVO_INDICE, "")
        reconstruido = gestor.cargar_indice()
        check("Índice vacío (0 bytes) se reconstruye", reconstruido == indice_esperado)

        escribir_texto(gestor.ARCHIVO_INDICE, "{}")
        reconstruido = gestor.cargar_indice()
        check("Índice vacío pero válido ({}) se reconstruye",
              reconstruido == indice_esperado)

        escribir_texto(gestor.ARCHIVO_INDICE, '{"1": 0}')
        reconstruido = gestor.cargar_indice()
        check("Índice incompleto se completa desde los datos",
              reconstruido == indice_esperado, repr(reconstruido))

        escribir_texto(
            gestor.ARCHIVO_INDICE, '{"1": 0, "2": 1, "3": 2}'
        )
        try:
            gestor.cargar_indice()
        except gestor.IndiceCorruptoError as error:
            check("Índice con más entradas que registros se rechaza",
                  True, str(error))
        except Exception as error:
            check("Índice con más entradas que registros se rechaza",
                  False, "{}: {}".format(type(error).__name__, error))
        else:
            check("Índice con más entradas que registros se rechaza", False)

        # Mismo número de entradas, pero mapeo incorrecto: agregar debe
        # bloquearse para no dejar registros huérfanos.
        escribir_texto(gestor.ARCHIVO_INDICE, '{"1": 1, "2": 0}')
        tamano_antes = os.path.getsize(gestor.ARCHIVO_CONTACTOS)
        try:
            gestor.agregar_contacto(
                {"id": "3", "nombre": "Luis", "telefono": "3",
                 "correo": "luis@x.com", "ciudad": "Lim\u00f3n"}
            )
        except ValueError as error:
            check("Agregar con mapeo de índice incorrecto se bloquea",
                  True, str(error))
        except Exception as error:
            check("Agregar con mapeo de índice incorrecto se bloquea",
                  False, "{}: {}".format(type(error).__name__, error))
        else:
            check("Agregar con mapeo de índice incorrecto se bloquea", False)
        check(
            "El bloqueo por mapeo incorrecto no escribió datos",
            os.path.getsize(gestor.ARCHIVO_CONTACTOS) == tamano_antes,
        )

        gestor.guardar_indice(indice_esperado)

        os.remove(gestor.ARCHIVO_INDICE)
        reconstruido = gestor.cargar_indice()
        check("Índice ausente con datos se reconstruye", reconstruido == indice_esperado)
        check(
            "Índice ausente se vuelve a crear",
            os.path.isfile(gestor.ARCHIVO_INDICE),
        )
        check(
            "Buscar sigue funcionando tras reconstruir",
            gestor.buscar_por_id("2").get("ok") is True,
        )
        check(
            "Exportar sigue viendo los 2 contactos",
            exportador.exportar_contactos_json("reconstruido.json").get("cantidad")
            == 2,
        )


def probar_datos_corruptos() -> None:
    with directorio_temporal("corruptos"):
        _crear_dos_contactos()

        # Primer registro con UTF-8 inválido.
        with open(gestor.ARCHIVO_CONTACTOS, "r+b") as archivo:
            archivo.seek(0)
            archivo.write(b"\xff" * TAMANO)

        try:
            gestor.leer_registro_aleatorio(0)
        except ValueError as error:
            check("Leer un registro corrupto lanza ValueError controlado", True,
                  str(error))
        except Exception as error:
            check("Leer un registro corrupto lanza ValueError controlado", False,
                  "{}: {}".format(type(error).__name__, error))
        else:
            check("Leer un registro corrupto lanza ValueError controlado", False,
                  "no se lanzó ninguna excepción")

        exportacion = exportador.exportar_contactos_json("corrupto.json")
        check(
            "Exportar con un registro corrupto devuelve ok=False sin excepción",
            exportacion.get("ok") is False,
            repr(exportacion),
        )

        os.remove(gestor.ARCHIVO_INDICE)
        try:
            gestor.cargar_indice()
        except ValueError as error:
            check("Reconstruir desde datos corruptos lanza IndiceCorruptoError",
                  True, str(error))
        except Exception as error:
            check("Reconstruir desde datos corruptos lanza IndiceCorruptoError",
                  False, "{}: {}".format(type(error).__name__, error))
        else:
            check("Reconstruir desde datos corruptos lanza IndiceCorruptoError",
                  False, "no se lanzó ninguna excepción")

    with directorio_temporal("incompleto"):
        _crear_dos_contactos()
        with open(gestor.ARCHIVO_CONTACTOS, "ab") as archivo:
            archivo.write(b"XYZ")  # Registro incompleto.

        try:
            gestor.leer_registro_aleatorio(2)
        except ValueError as error:
            check("Leer el registro incompleto lanza ValueError", True, str(error))
        else:
            check("Leer el registro incompleto lanza ValueError", False)

        try:
            gestor.agregar_contacto(
                {"id": "3", "nombre": "Luis", "telefono": "1",
                 "correo": "luis@x.com", "ciudad": "Lim\u00f3n"}
            )
        except ValueError as error:
            check("Agregar con archivo desalineado se bloquea", True, str(error))
        else:
            check("Agregar con archivo desalineado se bloquea", False)

        os.remove(gestor.ARCHIVO_INDICE)
        try:
            gestor.cargar_indice()
        except ValueError as error:
            check("Reconstruir con registro incompleto se bloquea", True, str(error))
        else:
            check("Reconstruir con registro incompleto se bloquea", False)


def probar_datos_ausentes_con_indice() -> None:
    with directorio_temporal("datos_ausentes"):
        escribir_texto(gestor.ARCHIVO_INDICE, '{"1": 0}')

        try:
            gestor.buscar_por_id("1")
        except FileNotFoundError as error:
            check("Buscar con contactos.dat ausente lanza FileNotFoundError",
                  True, str(error))
        except Exception as error:
            check("Buscar con contactos.dat ausente lanza FileNotFoundError",
                  False, "{}: {}".format(type(error).__name__, error))
        else:
            check("Buscar con contactos.dat ausente lanza FileNotFoundError", False)

        exportacion = exportador.exportar_contactos_json("sin_datos.json")
        check(
            "Exportar con contactos.dat ausente devuelve ok=False",
            exportacion.get("ok") is False,
            repr(exportacion),
        )

        try:
            gestor.agregar_contacto(
                {"id": "2", "nombre": "Nuevo", "telefono": "2",
                 "correo": "n@x.com", "ciudad": "Cartago"}
            )
        except FileNotFoundError as error:
            check(
                "Agregar con índice no vacío y datos ausentes se bloquea",
                True,
                str(error),
            )
        else:
            check(
                "Agregar con índice no vacío y datos ausentes se bloquea",
                False,
            )
        check(
            "El bloqueo no crea un contactos.dat inconsistente",
            not os.path.exists(gestor.ARCHIVO_CONTACTOS),
        )


# ---------------------------------------------------------------------------
# 3. Permisos de lectura/escritura
# ---------------------------------------------------------------------------
def probar_permisos_escritura() -> None:
    with directorio_temporal("permisos_escritura"):
        _crear_dos_contactos()
        tamano_inicial = os.path.getsize(gestor.ARCHIVO_CONTACTOS)

        with solo_lectura(gestor.ARCHIVO_CONTACTOS):
            try:
                gestor.agregar_contacto(
                    {"id": "3", "nombre": "Luis", "telefono": "3",
                     "correo": "luis@x.com", "ciudad": "Lim\u00f3n"}
                )
            except PermissionError as error:
                check("Agregar con contactos.dat de solo lectura lanza PermissionError",
                      True, str(error))
            except Exception as error:
                check("Agregar con contactos.dat de solo lectura lanza PermissionError",
                      False, "{}: {}".format(type(error).__name__, error))
            else:
                check("Agregar con contactos.dat de solo lectura lanza PermissionError",
                      False)

            try:
                gestor.modificar_por_id("1", {"nombre": "Otro"})
            except PermissionError as error:
                check("Modificar con contactos.dat de solo lectura lanza PermissionError",
                      True, str(error))
            except Exception as error:
                check("Modificar con contactos.dat de solo lectura lanza PermissionError",
                      False, "{}: {}".format(type(error).__name__, error))
            else:
                check("Modificar con contactos.dat de solo lectura lanza PermissionError",
                      False)

        check(
            "Los intentos fallidos no cambiaron el tamaño de contactos.dat",
            os.path.getsize(gestor.ARCHIVO_CONTACTOS) == tamano_inicial,
        )

        # Índice de solo lectura: la escritura del contacto debe deshacerse.
        indice_antes = leer_bytes(gestor.ARCHIVO_INDICE)
        with solo_lectura(gestor.ARCHIVO_INDICE):
            try:
                gestor.agregar_contacto(
                    {"id": "4", "nombre": "Rosa", "telefono": "4",
                     "correo": "rosa@x.com", "ciudad": "Alajuela"}
                )
            except PermissionError as error:
                check("Agregar con indice.json de solo lectura lanza PermissionError",
                      True, str(error))
            except Exception as error:
                check("Agregar con indice.json de solo lectura lanza PermissionError",
                      False, "{}: {}".format(type(error).__name__, error))
            else:
                check("Agregar con indice.json de solo lectura lanza PermissionError",
                      False)

        check(
            "El rollback dejó contactos.dat con su tamaño original",
            os.path.getsize(gestor.ARCHIVO_CONTACTOS) == tamano_inicial,
        )
        check(
            "El rollback no alteró indice.json",
            leer_bytes(gestor.ARCHIVO_INDICE) == indice_antes,
        )
        check(
            "No quedaron archivos temporales del índice",
            not os.path.exists(gestor.ARCHIVO_INDICE + ".tmp"),
        )

        # Hash de solo lectura: el dato se guarda y se informa advertencia.
        with solo_lectura(utilidades.ARCHIVO_HASH):
            resultado = gestor.agregar_contacto(
                {"id": "5", "nombre": "Marta", "telefono": "5",
                 "correo": "marta@x.com", "ciudad": "P\u00e9rez Zeled\u00f3n"}
            )
        check("Agregar con hash de solo lectura no falla el alta",
              resultado.get("ok") is True)
        check(
            "El alta con hash de solo lectura devuelve advertencia",
            bool(resultado.get("advertencia")),
            repr(resultado),
        )
        check(
            "El hash quedó desactualizado y la verificación lo detecta",
            utilidades.verificar_integridad_sha256().get("integro") is False,
        )

        # Al volver a escribir el hash, la integridad se recupera.
        estado_hash = utilidades.guardar_hash_sha256()
        check("Se puede regenerar el hash después del problema de permisos",
              estado_hash.get("ok") is True, repr(estado_hash))
        check(
            "La integridad vuelve a ser correcta",
            utilidades.verificar_integridad_sha256().get("integro") is True,
        )


def probar_permisos_lectura() -> None:
    with directorio_temporal("permisos_lectura"):
        _crear_dos_contactos()
        real_open = builtins.open

        def open_denegado_contactos(ruta, modo="r", *args, **kwargs):
            if os.path.basename(os.fspath(ruta)) == gestor.ARCHIVO_CONTACTOS:
                raise PermissionError("lectura denegada simulada")
            return real_open(ruta, modo, *args, **kwargs)

        gestor.open = open_denegado_contactos
        try:
            try:
                gestor.buscar_por_id("1")
            except PermissionError as error:
                check("Buscar sin permiso de lectura lanza PermissionError",
                      True, str(error))
            except Exception as error:
                check("Buscar sin permiso de lectura lanza PermissionError",
                      False, "{}: {}".format(type(error).__name__, error))
            else:
                check("Buscar sin permiso de lectura lanza PermissionError", False)

            os.remove(gestor.ARCHIVO_INDICE)
            try:
                gestor.cargar_indice()
            except PermissionError as error:
                check("Reconstruir índice sin permiso lanza PermissionError",
                      True, str(error))
            except Exception as error:
                check("Reconstruir índice sin permiso lanza PermissionError",
                      False, "{}: {}".format(type(error).__name__, error))
            else:
                check("Reconstruir índice sin permiso lanza PermissionError", False)
        finally:
            del gestor.open

        # Índice ilegible: la exportación devuelve error, no excepción.
        # El índice se había borrado para probar la reconstrucción; se
        # regenera a partir de los dos contactos que siguen en disco.
        gestor.cargar_indice()

        def open_denegado_indice(ruta, modo="r", *args, **kwargs):
            if os.path.basename(os.fspath(ruta)) == gestor.ARCHIVO_INDICE:
                raise PermissionError("lectura de índice denegada")
            return real_open(ruta, modo, *args, **kwargs)

        gestor.open = open_denegado_indice
        try:
            try:
                gestor.cargar_indice()
            except PermissionError as error:
                check("cargar_indice sin permiso lanza PermissionError", True,
                      str(error))
            else:
                check("cargar_indice sin permiso lanza PermissionError", False)

            exportacion = exportador.exportar_contactos_json("sin_permiso.json")
            check(
                "Exportar con índice ilegible devuelve ok=False",
                exportacion.get("ok") is False,
                repr(exportacion),
            )
        finally:
            del gestor.open

        # Hash ilegible: la verificación devuelve integro=None.
        real_open_utilidades = builtins.open

        def open_denegado_hash(ruta, modo="r", *args, **kwargs):
            if os.path.basename(os.fspath(ruta)) == utilidades.ARCHIVO_HASH:
                raise PermissionError("lectura de hash denegada")
            return real_open_utilidades(ruta, modo, *args, **kwargs)

        utilidades.open = open_denegado_hash
        try:
            verificacion = utilidades.verificar_integridad_sha256()
        finally:
            del utilidades.open
        check(
            "Verificar integridad con hash ilegible devuelve integro=None",
            verificacion.get("integro") is None,
            repr(verificacion),
        )

        # Metadatos sin permiso: os.stat lanza PermissionError.
        with patch.object(os, "stat", side_effect=PermissionError("stat denegado")):
            metadatos = utilidades.obtener_metadatos_archivo()
        check(
            "Metadatos sin permiso devuelven ok=False sin excepción",
            metadatos.get("ok") is False,
            repr(metadatos),
        )

        # ZIP sin permiso de lectura del archivo de datos.
        def open_denegado_zip(ruta, modo="r", *args, **kwargs):
            if os.path.basename(os.fspath(ruta)) == gestor.ARCHIVO_CONTACTOS:
                raise PermissionError("lectura para ZIP denegada")
            return real_open_utilidades(ruta, modo, *args, **kwargs)

        with patch("builtins.open", side_effect=open_denegado_zip):
            respaldo = utilidades.crear_respaldo_zip("sin_permiso.zip")
        check(
            "ZIP sin permiso de lectura devuelve ok=False sin excepción",
            respaldo.get("ok") is False,
            repr(respaldo),
        )


# ---------------------------------------------------------------------------
# 4. Auditoría estática: UTF-8, sintaxis, imports y messagebox
# ---------------------------------------------------------------------------
def _modo_constante(nodo: ast.Call) -> Tuple[bool, str]:
    """Devuelve (es_constante, modo) para una llamada open()."""
    if len(nodo.args) >= 2:
        valor = nodo.args[1]
    else:
        valor = next(
            (kw.value for kw in nodo.keywords if kw.arg == "mode"),
            None,
        )
    if valor is None:
        return True, "r"
    if isinstance(valor, ast.Constant) and isinstance(valor.value, str):
        return True, valor.value
    return False, ""


def probar_auditoria_estatica() -> None:
    archivos_py = sorted(
        os.path.join(PROYECTO, nombre)
        for nombre in os.listdir(PROYECTO)
        if nombre.endswith(".py")
    )
    check("Se encontraron archivos .py para auditar", len(archivos_py) >= 5,
          repr(archivos_py))

    for ruta in archivos_py:
        nombre = os.path.basename(ruta)
        fuente = leer_texto(ruta)
        try:
            arbol = ast.parse(fuente, filename=nombre)
        except SyntaxError as error:
            check("{} compila sin errores de sintaxis".format(nombre), False,
                  str(error))
            continue
        check("{} compila sin errores de sintaxis".format(nombre), True)

        problemas = []
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            if not isinstance(nodo.func, ast.Name) or nodo.func.id != "open":
                continue

            es_constante, modo = _modo_constante(nodo)
            if not es_constante:
                problemas.append(
                    "open() en línea {} con modo no verificable".format(nodo.lineno)
                )
                continue
            if "b" in modo:
                continue

            encoding = next(
                (kw.value for kw in nodo.keywords if kw.arg == "encoding"),
                None,
            )
            if not (
                isinstance(encoding, ast.Constant)
                and isinstance(encoding.value, str)
                and encoding.value.lower() in ("utf-8", "utf8")
            ):
                problemas.append(
                    "open() de texto en línea {} sin encoding='utf-8' "
                    "(modo {!r})".format(nodo.lineno, modo)
                )

        check(
            "{}: aperturas de texto/JSON con encoding UTF-8".format(nombre),
            not problemas,
            "; ".join(problemas),
        )

    # main.py debe importar un módulo de interfaz que exista realmente.
    arbol_main = ast.parse(leer_texto(os.path.join(PROYECTO, "main.py")))
    modulos_interfaz = []
    for nodo in ast.walk(arbol_main):
        if isinstance(nodo, ast.ImportFrom) and nodo.module:
            if nodo.module.startswith("interfaz"):
                modulos_interfaz.append(nodo.module)
    check(
        "main.py importa al menos una interfaz",
        bool(modulos_interfaz),
        repr(modulos_interfaz),
    )
    for modulo in modulos_interfaz:
        check(
            "main.py: el módulo {} existe".format(modulo),
            os.path.isfile(os.path.join(PROYECTO, modulo + ".py")),
        )

    fuente_ui = leer_texto(os.path.join(PROYECTO, "interfaz_brutalista.py"))
    check(
        "La interfaz define messagebox.showerror",
        "messagebox.showerror" in fuente_ui,
    )
    check(
        "La interfaz captura excepciones de callbacks de Tk",
        "report_callback_exception" in fuente_ui,
    )


def probar_manejador_de_errores() -> None:
    """Comprueba que la interfaz muestra errores con messagebox sin abrir Tk."""
    try:
        import interfaz_brutalista as ui
    except Exception as error:
        check("La interfaz se puede importar sin abrir la ventana", False,
              str(error))
        return
    check("La interfaz se puede importar sin abrir la ventana", True)

    class FalsoUI:
        def __init__(self) -> None:
            self.registros = []

        def _registrar(self, mensaje: str, nivel: str = "INFO") -> None:
            self.registros.append((mensaje, nivel))

    falso = FalsoUI()
    with patch("interfaz_brutalista.messagebox.showerror") as mock:
        ui.InterfazBrutalista._mostrar_error(falso, "Título", "Mensaje")
        check(
            "_mostrar_error usa messagebox.showerror",
            mock.called,
        )
        if mock.called:
            argumentos, opciones = mock.call_args
            check(
                "_mostrar_error pasa el parent correcto",
                opciones.get("parent") is falso
                and argumentos == ("Título", "Mensaje"),
                repr((argumentos, opciones)),
            )

    with patch("interfaz_brutalista.messagebox.showerror") as mock:
        ui.InterfazBrutalista._manejar_error_no_controlado(
            falso, ValueError, ValueError("fallo simulado"), None
        )
        check(
            "El manejador de callbacks usa messagebox.showerror",
            mock.called,
        )


def probar_arranque_de_main() -> None:
    """Simula python main.py sin abrir una ventana real."""
    try:
        import main as modulo_main
        import interfaz_brutalista as ui
    except Exception as error:
        check("main.py se puede importar", False, str(error))
        return
    check("main.py se puede importar", True)

    instancias: List[object] = []

    class FalsaUI:
        def __init__(self) -> None:
            self.mainloop_ejecutado = False
            self.destroy_ejecutado = False
            instancias.append(self)

        def mainloop(self) -> None:
            self.mainloop_ejecutado = True

        def destroy(self) -> None:
            self.destroy_ejecutado = True

    interfaz_original = ui.InterfazBrutalista
    directorio_anterior = os.getcwd()
    try:
        ui.InterfazBrutalista = FalsaUI
        codigo = modulo_main.main()
    finally:
        ui.InterfazBrutalista = interfaz_original
        os.chdir(directorio_anterior)

    check("main() termina con código 0", codigo == 0, repr(codigo))
    check("main() creó la ventana una sola vez", len(instancias) == 1,
          repr(instancias))
    if instancias:
        aplicacion = instancias[0]
        check(
            "main() ejecutó mainloop() y destroy()",
            aplicacion.mainloop_ejecutado and aplicacion.destroy_ejecutado,
        )


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------
def main() -> int:
    print("Verificación del proyecto: {}".format(PROYECTO))
    print("Python: {}".format(sys.version.split()[0]))

    ejecutar_grupo("Flujo completo", probar_flujo_completo)
    ejecutar_grupo("Archivos ausentes o vacíos", probar_archivos_ausentes_y_vacios)
    ejecutar_grupo("Índice corrupto o ausente", probar_indice_corrupto_o_ausente)
    ejecutar_grupo("Datos corruptos o incompletos", probar_datos_corruptos)
    ejecutar_grupo("Datos ausentes con índice existente",
                   probar_datos_ausentes_con_indice)
    ejecutar_grupo("Permisos de escritura", probar_permisos_escritura)
    ejecutar_grupo("Permisos de lectura", probar_permisos_lectura)
    ejecutar_grupo("Auditoría estática", probar_auditoria_estatica)
    ejecutar_grupo("Manejador de errores de la interfaz",
                   probar_manejador_de_errores)
    ejecutar_grupo("Arranque de main.py", probar_arranque_de_main)

    print("\n" + "=" * 62)
    print("Comprobaciones superadas: {}".format(PASADOS))
    print("Comprobaciones fallidas:  {}".format(len(FALLOS)))
    if FALLOS:
        print("\nFallos:")
        for fallo in FALLOS:
            print(" - {}".format(fallo))
        print("=" * 62)
        return 1
    print("RESULTADO: TODAS LAS COMPROBACIONES PASARON")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
