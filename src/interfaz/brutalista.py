# -*- coding: utf-8 -*-
"""
brutalista.py - Interfaz gráfica

Interfaz gráfica de la "Agenda de Contactos con Acceso Aleatorio".

Estética **neo-brutalista / industrial de alto contraste**:

* Fondo crema de papel crudo (``#F4F0EA``) con bordes negros gruesos.
* Acentos planos de alto contraste: amarillo ácido, naranja neón, verde lima
  y blanco puro con texto negro.
* Tipografía monoespaciada en negrita (Consolas) para el aire de terminal.

Esta capa es únicamente *presentación*: toda la lógica de archivos vive en
``almacenamiento/gestor_archivos.py``, ``servicios/utilidades_sistema.py``,
``servicios/exportador.py`` y ``modelo/contacto.py``. La interfaz se limita a
traducir sus resultados a la pantalla y a capturar cualquier error con
``messagebox`` para que la aplicación nunca se cierre de forma abrupta.

Uso::

    python src/interfaz/brutalista.py
"""

import os
import sys
import traceback
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Dict, Optional

# Permite ejecutar este archivo directamente (`python src/interfaz/brutalista.py`)
# además de hacerlo a través de `python main.py`.
SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SRC not in sys.path:
    sys.path.insert(0, SRC)

# ---------------------------------------------------------------------------
# Importaciones de la capa de lógica
# ---------------------------------------------------------------------------
try:
    from servicios.exportador import (
        ARCHIVO_JSON_EXPORTADO,
        ARCHIVO_PDF_REPORTE,
        exportar_contactos_json,
        generar_reporte_pdf,
    )
    from almacenamiento.gestor_archivos import (
        ARCHIVO_CONTACTOS,
        ARCHIVO_INDICE,
        agregar_contacto,
        buscar_por_id,
        cargar_indice,
        leer_registro_aleatorio,
        modificar_por_id,
    )
    from modelo.contacto import TAMANO_REGISTRO
    from servicios.utilidades_sistema import (
        ARCHIVO_HASH,
        ARCHIVO_RESPALDO,
        crear_respaldo_zip,
        obtener_metadatos_archivo,
        verificar_integridad_sha256,
    )
except ImportError as error:  # pragma: no cover - fallo de instalación
    sys.stderr.write(
        "No se pudieron importar los módulos del proyecto: {}\n".format(error)
    )
    raise


# ---------------------------------------------------------------------------
# Paleta neo-brutalista
# ---------------------------------------------------------------------------
COLOR_FONDO = "#F4F0EA"      # crema / papel crudo
COLOR_NEGRO = "#000000"      # bordes y tipografía
COLOR_BLANCO = "#FFFFFF"     # blanco puro
COLOR_AMARILLO = "#FFE600"   # amarillo ácido
COLOR_NARANJA = "#FF5722"    # naranja neón
COLOR_LIMA = "#A3E635"       # verde lima
COLOR_CONSOLA = "#111111"    # fondo de la consola de registro
COLOR_GRIS = "#9A9A94"       # gris concreto para textos secundarios

# ---------------------------------------------------------------------------
# Tipografías monoespaciadas
# ---------------------------------------------------------------------------
FUENTE_CUERPO = ("Consolas", 10, "bold")
FUENTE_TITULO = ("Consolas", 20, "bold")
FUENTE_SUBTITULO = ("Consolas", 11, "bold")
FUENTE_CABECERA = ("Consolas", 10, "bold")
FUENTE_MONITOR = ("Consolas", 22, "bold")
FUENTE_MONITOR_TITULO = ("Consolas", 12, "bold")
FUENTE_PEQUENA = ("Consolas", 8, "bold")

# Columnas de la tabla de contactos.
COLUMNAS = (
    ("id", "ID", 60),
    ("nombre", "NOMBRE", 190),
    ("telefono", "TELEFONO", 130),
    ("correo", "CORREO", 240),
    ("ciudad", "CIUDAD", 130),
)

__all__ = ["InterfazBrutalista", "main"]


# ---------------------------------------------------------------------------
# Ayudantes de estilo
# ---------------------------------------------------------------------------
def _marco_brutalista(padre, **extra):
    """Crea un ``Frame`` con borde negro grueso de 4 px."""
    opciones = {
        "bg": COLOR_NEGRO,
        "bd": 0,
        "relief": "flat",
    }
    opciones.update(extra)
    return tk.Frame(padre, **opciones)


def _panel_brutalista(padre, titulo):
    """Crea un ``LabelFrame`` crema con contorno negro y título en negrita."""
    marco = tk.LabelFrame(
        padre,
        text=" " + titulo + " ",
        bg=COLOR_FONDO,
        fg=COLOR_NEGRO,
        font=FUENTE_SUBTITULO,
        bd=0,
        relief="flat",
        highlightbackground=COLOR_NEGRO,
        highlightcolor=COLOR_NEGRO,
        highlightthickness=3,
        padx=10,
        pady=8,
    )
    return marco


def _boton_brutalista(padre, texto, comando, color=COLOR_AMARILLO, ancho=16):
    """Crea un botón plano de alto contraste con borde negro grueso."""
    return tk.Button(
        padre,
        text=texto,
        command=comando,
        bg=color,
        fg=COLOR_NEGRO,
        activebackground=COLOR_BLANCO,
        activeforeground=COLOR_NEGRO,
        font=FUENTE_CABECERA,
        bd=3,
        relief="solid",
        highlightbackground=COLOR_NEGRO,
        highlightcolor=COLOR_NEGRO,
        highlightthickness=2,
        anchor="center",
        width=ancho,
        cursor="hand2",
        padx=8,
        pady=6,
    )


def _entrada_brutalista(padre, ancho=34):
    """Crea un ``Entry`` blanco con borde negro grueso."""
    return tk.Entry(
        padre,
        bg=COLOR_BLANCO,
        fg=COLOR_NEGRO,
        insertbackground=COLOR_NEGRO,
        font=FUENTE_CUERPO,
        bd=3,
        relief="solid",
        highlightbackground=COLOR_NEGRO,
        highlightcolor=COLOR_NARANJA,
        highlightthickness=2,
        justify="left",
        width=ancho,
    )


def _etiqueta_brutalista(padre, texto):
    """Crea una ``Label`` negra y monoespaciada."""
    return tk.Label(
        padre,
        text=texto,
        bg=COLOR_FONDO,
        fg=COLOR_NEGRO,
        font=FUENTE_CABECERA,
        anchor="w",
    )


# ---------------------------------------------------------------------------
# Ventana principal
# ---------------------------------------------------------------------------
class InterfazBrutalista(tk.Tk):
    """Ventana principal de la agenda, en estilo neo-brutalista."""

    def __init__(self) -> None:
        super().__init__()

        self.title("AGENDA DE CONTACTOS :: ACCESO ALEATORIO // v2.0")
        self.configure(bg=COLOR_FONDO)

        # Tamaño inicial ajustado a la pantalla disponible.
        ancho = min(1380, self.winfo_screenwidth() - 80)
        alto = min(880, self.winfo_screenheight() - 110)
        self.geometry("{}x{}".format(ancho, alto))
        self.minsize(1080, 640)

        # Estado de la interfaz.
        self.campos: Dict[str, tk.Entry] = {}
        self.ultimo_registro = 0
        self.ultimo_offset = 0
        self.ultimo_hash: Optional[str] = None

        self._construir_estilos_ttk()
        self._construir_cabecera()
        self._construir_menu()
        self._construir_monitor()
        # La barra de estado y la consola se anclan abajo ANTES que el cuerpo
        # expandible; de lo contrario el cuerpo se queda con todo el espacio
        # y las empuja fuera de la ventana.
        self._construir_barra_estado()
        self._construir_consola()
        self._construir_cuerpo()

        self.protocol("WM_DELETE_WINDOW", self._salir)
        self.report_callback_exception = self._manejar_error_no_controlado

        # Verificación automática de integridad al iniciar.
        self.after(150, self._verificar_integridad_inicial)
        self.after(300, lambda: self._recargar_tabla(silencioso=True))

    # ------------------------------------------------------------------
    # Estilos ttk (Treeview)
    # ------------------------------------------------------------------
    def _construir_estilos_ttk(self) -> None:
        """Configura el tema ``clam`` con los colores de la paleta."""
        estilo = ttk.Style(self)
        try:
            estilo.theme_use("clam")
        except tk.TclError:  # pragma: no cover
            pass

        estilo.configure(
            "Brutal.Treeview",
            background=COLOR_BLANCO,
            fieldbackground=COLOR_BLANCO,
            foreground=COLOR_NEGRO,
            font=FUENTE_CUERPO,
            borderwidth=3,
            bordercolor=COLOR_NEGRO,
            relief="solid",
            rowheight=26,
        )
        estilo.map(
            "Brutal.Treeview",
            background=[("selected", COLOR_AMARILLO)],
            foreground=[("selected", COLOR_NEGRO)],
        )
        estilo.configure(
            "Brutal.Treeview.Heading",
            background=COLOR_NEGRO,
            foreground=COLOR_BLANCO,
            font=FUENTE_CABECERA,
            borderwidth=2,
            bordercolor=COLOR_NEGRO,
            relief="solid",
            padding=(6, 6),
        )
        estilo.map(
            "Brutal.Treeview.Heading",
            background=[("active", COLOR_NARANJA)],
            foreground=[("active", COLOR_BLANCO)],
        )
        estilo.configure(
            "Brutal.Vertical.TScrollbar",
            background=COLOR_NEGRO,
            troughcolor=COLOR_FONDO,
            bordercolor=COLOR_NEGRO,
            arrowcolor=COLOR_AMARILLO,
            relief="solid",
            borderwidth=2,
        )

    # ------------------------------------------------------------------
    # Cabecera
    # ------------------------------------------------------------------
    def _construir_cabecera(self) -> None:
        """Banner superior negro con el título de la aplicación."""
        marco = tk.Frame(self, bg=COLOR_NEGRO)
        marco.pack(fill="x")

        interior = tk.Frame(marco, bg=COLOR_NEGRO)
        interior.pack(fill="x", padx=12, pady=(10, 10))

        tk.Label(
            interior,
            text="AGENDA DE CONTACTOS :: ACCESO ALEATORIO",
            bg=COLOR_NEGRO,
            fg=COLOR_AMARILLO,
            font=FUENTE_TITULO,
            anchor="w",
        ).pack(side="left")

        tk.Label(
            interior,
            text="ARCHIVO: {}\nREGISTRO FIJO: {} BYTES".format(
                ARCHIVO_CONTACTOS, TAMANO_REGISTRO
            ),
            bg=COLOR_NEGRO,
            fg=COLOR_LIMA,
            font=FUENTE_PEQUENA,
            anchor="e",
            justify="right",
        ).pack(side="right")

        # Franja de acento inferior.
        franja = tk.Frame(self, bg=COLOR_NARANJA, height=6)
        franja.pack(fill="x")

    # ------------------------------------------------------------------
    # Barra de menús
    # ------------------------------------------------------------------
    def _construir_menu(self) -> None:
        """Barra de menú superior con las cuatro secciones del laboratorio."""
        self.barra_menu = tk.Menu(
            self,
            bg=COLOR_FONDO,
            fg=COLOR_NEGRO,
            activebackground=COLOR_AMARILLO,
            activeforeground=COLOR_NEGRO,
            bd=0,
            relief="flat",
            font=FUENTE_CABECERA,
            tearoff=0,
        )
        self.configure(menu=self.barra_menu)

        # --- Contactos ---
        self.menu_contactos = tk.Menu(
            self.barra_menu,
            bg=COLOR_FONDO,
            fg=COLOR_NEGRO,
            activebackground=COLOR_AMARILLO,
            activeforeground=COLOR_NEGRO,
            bd=0,
            relief="flat",
            font=FUENTE_CUERPO,
            tearoff=0,
        )
        self.menu_contactos.add_command(
            label="Agregar", command=self.accion_agregar
        )
        self.menu_contactos.add_command(
            label="Buscar por ID", command=self.accion_buscar
        )
        self.menu_contactos.add_command(
            label="Modificar", command=self.accion_modificar
        )
        self.barra_menu.add_cascade(
            label="Contactos", menu=self.menu_contactos
        )

        # --- Exportar ---
        self.menu_exportar = tk.Menu(
            self.barra_menu,
            bg=COLOR_FONDO,
            fg=COLOR_NEGRO,
            activebackground=COLOR_AMARILLO,
            activeforeground=COLOR_NEGRO,
            bd=0,
            relief="flat",
            font=FUENTE_CUERPO,
            tearoff=0,
        )
        self.menu_exportar.add_command(
            label="Exportar a JSON", command=self.accion_exportar_json
        )
        self.menu_exportar.add_command(
            label="Generar reporte PDF", command=self.accion_generar_pdf
        )
        self.barra_menu.add_cascade(
            label="Exportar", menu=self.menu_exportar
        )

        # --- Herramientas ---
        self.menu_herramientas = tk.Menu(
            self.barra_menu,
            bg=COLOR_FONDO,
            fg=COLOR_NEGRO,
            activebackground=COLOR_AMARILLO,
            activeforeground=COLOR_NEGRO,
            bd=0,
            relief="flat",
            font=FUENTE_CUERPO,
            tearoff=0,
        )
        self.menu_herramientas.add_command(
            label="Verificar integridad", command=self.accion_verificar_integridad
        )
        self.menu_herramientas.add_command(
            label="Crear respaldo ZIP", command=self.accion_crear_respaldo
        )
        self.menu_herramientas.add_command(
            label="Información del archivo", command=self.accion_info_archivo
        )
        self.barra_menu.add_cascade(
            label="Herramientas", menu=self.menu_herramientas
        )

        # --- Ayuda ---
        self.menu_ayuda = tk.Menu(
            self.barra_menu,
            bg=COLOR_FONDO,
            fg=COLOR_NEGRO,
            activebackground=COLOR_AMARILLO,
            activeforeground=COLOR_NEGRO,
            bd=0,
            relief="flat",
            font=FUENTE_CUERPO,
            tearoff=0,
        )
        self.menu_ayuda.add_command(
            label="Acerca de", command=self.accion_acerca_de
        )
        self.barra_menu.add_cascade(label="Ayuda", menu=self.menu_ayuda)

    # ------------------------------------------------------------------
    # Monitor de puntero
    # ------------------------------------------------------------------
    def _construir_monitor(self) -> None:
        """Panel destacado con la posición física del puntero en el archivo."""
        contenedor = _marco_brutalista(self)
        contenedor.pack(fill="x", padx=8, pady=(8, 0))

        interior = tk.Frame(contenedor, bg=COLOR_AMARILLO)
        interior.pack(fill="x", padx=4, pady=4)

        cabecera = tk.Frame(interior, bg=COLOR_AMARILLO)
        cabecera.pack(fill="x", padx=12, pady=(8, 0))

        tk.Label(
            cabecera,
            text="MONITOR DE PUNTERO :: SEEK / TELL",
            bg=COLOR_AMARILLO,
            fg=COLOR_NEGRO,
            font=FUENTE_MONITOR_TITULO,
            anchor="w",
        ).pack(side="left")

        self.etiqueta_estado_monitor = tk.Label(
            cabecera,
            text="ESTADO: EN ESPERA",
            bg=COLOR_NEGRO,
            fg=COLOR_LIMA,
            font=FUENTE_PEQUENA,
            padx=8,
            pady=3,
        )
        self.etiqueta_estado_monitor.pack(side="right")

        # Lectura principal en grande.
        marco_lectura = tk.Frame(interior, bg=COLOR_NEGRO)
        marco_lectura.pack(fill="x", padx=12, pady=8)

        caja = tk.Frame(marco_lectura, bg=COLOR_BLANCO)
        caja.pack(fill="x", padx=4, pady=4)

        self.etiqueta_monitor = tk.Label(
            caja,
            text=self._texto_monitor(0, 0),
            bg=COLOR_BLANCO,
            fg=COLOR_NEGRO,
            font=FUENTE_MONITOR,
            anchor="w",
            padx=14,
            pady=8,
        )
        self.etiqueta_monitor.pack(fill="x")

        # Detalle técnico: SEEK, TELL, tamaño y hash.
        fila_detalle = tk.Frame(interior, bg=COLOR_AMARILLO)
        fila_detalle.pack(fill="x", padx=12, pady=(0, 8))

        self.etiqueta_seek = self._crear_chip(fila_detalle, "SEEK")
        self.etiqueta_tell = self._crear_chip(fila_detalle, "TELL")
        self.etiqueta_tamano = self._crear_chip(fila_detalle, "SIZE")
        self.etiqueta_hash = self._crear_chip(fila_detalle, "SHA-256")

    def _crear_chip(self, padre, titulo):
        """Crea una etiqueta técnica tipo 'pastilla' dentro del monitor."""
        marco = tk.Frame(padre, bg=COLOR_NEGRO)
        marco.pack(side="left", padx=(0, 8), pady=2)

        tk.Label(
            marco,
            text=titulo,
            bg=COLOR_NEGRO,
            fg=COLOR_AMARILLO,
            font=FUENTE_PEQUENA,
            padx=4,
        ).pack(side="left")

        etiqueta = tk.Label(
            marco,
            text="-",
            bg=COLOR_NEGRO,
            fg=COLOR_BLANCO,
            font=FUENTE_PEQUENA,
            padx=4,
        )
        etiqueta.pack(side="left")
        return etiqueta

    @staticmethod
    def _texto_monitor(numero_registro: int, posicion: int) -> str:
        """Texto grande del monitor: ``REGISTRO #[X] // OFFSET SEEK/TELL: BYTE [Y]``."""
        return "REGISTRO #[{}] // OFFSET SEEK/TELL: BYTE [{}]".format(
            numero_registro, posicion
        )

    def _actualizar_monitor(
        self,
        numero_registro: int,
        posicion: int,
        estado: str = "OK",
        hash_actual: Optional[str] = None,
    ) -> None:
        """Refresca el panel de monitor con la posición actual del puntero."""
        self.ultimo_registro = numero_registro
        self.ultimo_offset = posicion

        self.etiqueta_monitor.configure(
            text=self._texto_monitor(numero_registro, posicion)
        )
        self.etiqueta_estado_monitor.configure(
            text="ESTADO: {}".format(estado),
            bg=COLOR_NEGRO if estado == "OK" else COLOR_NARANJA,
            fg=COLOR_LIMA if estado == "OK" else COLOR_BLANCO,
        )

        self.etiqueta_seek.configure(text=str(posicion))
        self.etiqueta_tell.configure(text=str(posicion))
        self.etiqueta_tamano.configure(
            text="{} BYTES".format(TAMANO_REGISTRO)
        )

        # El hash se conserva aunque no se vuelva a calcular.
        if hash_actual:
            self.ultimo_hash = hash_actual
        self.etiqueta_hash.configure(
            text=(self.ultimo_hash or "-")[:16].upper()
        )

    # ------------------------------------------------------------------
    # Cuerpo: formulario + tabla
    # ------------------------------------------------------------------
    def _construir_cuerpo(self) -> None:
        """Zona central con el formulario de captura y la tabla de datos."""
        cuerpo = tk.Frame(self, bg=COLOR_FONDO)
        cuerpo.pack(fill="both", expand=True, padx=8, pady=8)

        cuerpo.columnconfigure(0, weight=0, minsize=390)
        cuerpo.columnconfigure(1, weight=1)
        cuerpo.rowconfigure(0, weight=1)

        # ---------------- Formulario ----------------
        panel_formulario = _panel_brutalista(cuerpo, "01 :: CAPTURA DE CONTACTO")
        panel_formulario.grid(
            row=0, column=0, sticky="nsw", padx=(0, 8), pady=0
        )

        formulario = tk.Frame(panel_formulario, bg=COLOR_FONDO)
        formulario.pack(fill="x")

        definiciones = (
            ("id", "ID"),
            ("nombre", "NOMBRE"),
            ("telefono", "TELEFONO"),
            ("correo", "CORREO"),
            ("ciudad", "CIUDAD"),
        )

        for indice, (clave, titulo) in enumerate(definiciones):
            etiqueta = _etiqueta_brutalista(formulario, "> {}".format(titulo))
            etiqueta.grid(
                row=indice, column=0, sticky="w", pady=(0 if indice else 6, 6)
            )
            entrada = _entrada_brutalista(formulario)
            entrada.grid(
                row=indice, column=1, sticky="ew", padx=(10, 0),
                pady=(0 if indice else 6, 6),
            )
            self.campos[clave] = entrada

        formulario.columnconfigure(1, weight=1)

        # Botonera del formulario.
        botones = tk.Frame(panel_formulario, bg=COLOR_FONDO)
        botones.pack(fill="x", pady=(12, 0))

        _boton_brutalista(
            botones, "AGREGAR", self.accion_agregar, COLOR_AMARILLO, 20
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        _boton_brutalista(
            botones, "BUSCAR", self.accion_buscar, COLOR_NARANJA, 20
        ).grid(row=0, column=1, sticky="ew", padx=4)
        _boton_brutalista(
            botones, "MODIFICAR", self.accion_modificar, COLOR_LIMA, 20
        ).grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=(6, 0))
        _boton_brutalista(
            botones, "LIMPIAR", self.limpiar_formulario, COLOR_BLANCO, 20
        ).grid(row=1, column=1, sticky="ew", padx=4, pady=(6, 0))
        botones.columnconfigure(0, weight=1)
        botones.columnconfigure(1, weight=1)

        # ---------------- Tabla ----------------
        panel_tabla = _panel_brutalista(cuerpo, "02 :: REGISTROS EN DISCO")
        panel_tabla.grid(row=0, column=1, sticky="nsew")

        marco_tabla = _marco_brutalista(panel_tabla)
        marco_tabla.pack(fill="both", expand=True, pady=(6, 0))

        self.tabla = ttk.Treeview(
            marco_tabla,
            columns=[columna[0] for columna in COLUMNAS],
            show="headings",
            style="Brutal.Treeview",
            selectmode="browse",
        )
        for clave, titulo, ancho in COLUMNAS:
            self.tabla.heading(clave, text=titulo)
            self.tabla.column(
                clave,
                width=ancho,
                anchor="w" if clave != "id" else "center",
                stretch=(clave == "correo"),
            )

        barra = ttk.Scrollbar(
            marco_tabla,
            orient="vertical",
            command=self.tabla.yview,
            style="Brutal.Vertical.TScrollbar",
        )
        self.tabla.configure(yscrollcommand=barra.set)

        self.tabla.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)
        barra.pack(side="right", fill="y", padx=(0, 4), pady=4)

        self.tabla.bind("<<TreeviewSelect>>", self._al_seleccionar_fila)

    # ------------------------------------------------------------------
    # Consola de registro
    # ------------------------------------------------------------------
    def _construir_consola(self) -> None:
        """Panel inferior con la bitácora de operaciones."""
        marco = _marco_brutalista(self)
        marco.pack(side="bottom", fill="x", padx=8, pady=(4, 0))

        interior = tk.Frame(marco, bg=COLOR_NEGRO)
        interior.pack(fill="x", padx=4, pady=4)

        tk.Label(
            interior,
            text="CONSOLA DE REGISTRO",
            bg=COLOR_NEGRO,
            fg=COLOR_AMARILLO,
            font=FUENTE_PEQUENA,
            anchor="w",
        ).pack(fill="x", padx=6, pady=(4, 0))

        self.consola = tk.Text(
            interior,
            height=6,
            bg=COLOR_CONSOLA,
            fg=COLOR_LIMA,
            insertbackground=COLOR_AMARILLO,
            selectbackground=COLOR_AMARILLO,
            selectforeground=COLOR_NEGRO,
            font=FUENTE_PEQUENA,
            bd=3,
            relief="solid",
            highlightbackground=COLOR_NEGRO,
            highlightcolor=COLOR_NEGRO,
            highlightthickness=2,
            wrap="word",
            state="disabled",
        )
        self.consola.pack(fill="x", padx=6, pady=6)

    # ------------------------------------------------------------------
    # Barra de estado
    # ------------------------------------------------------------------
    def _construir_barra_estado(self) -> None:
        """Franja inferior con el estado de la última operación."""
        marco = tk.Frame(self, bg=COLOR_NEGRO)
        marco.pack(side="bottom", fill="x")

        self.etiqueta_estado = tk.Label(
            marco,
            text="LISTO // AGENDA DE CONTACTOS EN ESPERA",
            bg=COLOR_NEGRO,
            fg=COLOR_LIMA,
            font=FUENTE_PEQUENA,
            anchor="w",
            padx=10,
            pady=4,
        )
        self.etiqueta_estado.pack(fill="x")

    # ------------------------------------------------------------------
    # Utilidades de registro y estado
    # ------------------------------------------------------------------
    def _registrar(self, mensaje: str, nivel: str = "INFO") -> None:
        """Escribe una línea en la consola y en la barra de estado."""
        marca = datetime.now().strftime("%H:%M:%S")
        linea = "[{}] [{}] {}\n".format(marca, nivel, mensaje)

        self.consola.configure(state="normal")
        self.consola.insert("end", linea)
        self.consola.see("end")
        self.consola.configure(state="disabled")

        colores = {
            "INFO": COLOR_LIMA,
            "OK": COLOR_LIMA,
            "ALERTA": COLOR_NARANJA,
            "ERROR": COLOR_NARANJA,
        }
        self.etiqueta_estado.configure(
            text=linea.strip(),
            fg=colores.get(nivel, COLOR_LIMA),
        )

    def _mostrar_error(self, titulo: str, mensaje: str) -> None:
        """Muestra un error capturado en un ``messagebox``."""
        self._registrar("{}: {}".format(titulo, mensaje), "ERROR")
        messagebox.showerror(titulo, mensaje, parent=self)

    def _mostrar_alerta(self, titulo: str, mensaje: str) -> None:
        """Muestra una advertencia en un ``messagebox``."""
        self._registrar("{}: {}".format(titulo, mensaje), "ALERTA")
        messagebox.showwarning(titulo, mensaje, parent=self)

    def _mostrar_info(self, titulo: str, mensaje: str) -> None:
        """Muestra un mensaje informativo en un ``messagebox``."""
        self._registrar("{}: {}".format(titulo, mensaje), "OK")
        messagebox.showinfo(titulo, mensaje, parent=self)

    def _manejar_error_no_controlado(self, exc, val, tb) -> None:
        """Red de seguridad: captura cualquier excepción de la interfaz."""
        detalle = "".join(traceback.format_exception(exc, val, tb))
        self._registrar(detalle.strip(), "ERROR")
        messagebox.showerror(
            "ERROR NO CONTROLADO",
            "Se produjo un error inesperado:\n\n{}".format(val),
            parent=self,
        )

    # ------------------------------------------------------------------
    # Formulario
    # ------------------------------------------------------------------
    def _leer_formulario(self) -> Dict[str, object]:
        """Devuelve los valores del formulario como diccionario."""
        datos: Dict[str, object] = {}
        for clave, entrada in self.campos.items():
            datos[clave] = entrada.get().strip()
        return datos

    def _poblar_formulario(self, contacto: Dict[str, object]) -> None:
        """Escribe un contacto en los campos del formulario."""
        for clave, entrada in self.campos.items():
            valor = contacto.get(clave, "")
            entrada.delete(0, "end")
            entrada.insert(0, "" if valor is None else str(valor))

    def limpiar_formulario(self, resetear_monitor: bool = True) -> None:
        """Vacía los campos del formulario.

        Args:
            resetear_monitor: Si es ``True`` (por defecto) el monitor de
                puntero vuelve al estado inicial. Si es ``False`` se conserva
                la última posición leída o escrita, que es lo que se necesita
                tras agregar o modificar un contacto.
        """
        for entrada in self.campos.values():
            entrada.delete(0, "end")
        self.campos["id"].focus_set()
        if resetear_monitor:
            self._actualizar_monitor(0, 0, estado="EN ESPERA")
        self._registrar("Formulario limpiado.", "INFO")

    # ------------------------------------------------------------------
    # Tabla
    # ------------------------------------------------------------------
    def _recargar_tabla(self, silencioso: bool = False) -> None:
        """Vuelve a leer el índice y repuebla la tabla de contactos."""
        try:
            indice = cargar_indice()
        except Exception as error:
            self._mostrar_error(
                "ERROR AL LEER EL ÍNDICE",
                "No se pudo cargar '{}':\n\n{}".format(ARCHIVO_INDICE, error),
            )
            return

        self.tabla.delete(*self.tabla.get_children())

        for clave in sorted(indice, key=lambda item: int(item)):
            numero_registro = indice[clave]
            try:
                contacto = leer_registro_aleatorio(numero_registro)
            except Exception as error:
                self._mostrar_error(
                    "ERROR DE LECTURA",
                    "No se pudo leer el registro {} (ID {}):\n\n{}".format(
                        numero_registro, clave, error
                    ),
                )
                continue

            self.tabla.insert(
                "",
                "end",
                iid=str(contacto["id"]),
                values=(
                    contacto["id"],
                    contacto["nombre"],
                    contacto["telefono"],
                    contacto["correo"],
                    contacto["ciudad"],
                ),
            )

        if not silencioso:
            self._registrar(
                "Tabla recargada: {} registro(s) en '{}'.".format(
                    len(indice), ARCHIVO_CONTACTOS
                ),
                "OK",
            )

    def _al_seleccionar_fila(self, _evento=None) -> None:
        """Al seleccionar una fila, se vuelca el registro en el formulario."""
        seleccion = self.tabla.selection()
        if not seleccion:
            return

        iid = seleccion[0]
        valores = self.tabla.item(iid, "values")
        if not valores:
            return

        self._poblar_formulario(
            {
                "id": valores[0],
                "nombre": valores[1],
                "telefono": valores[2],
                "correo": valores[3],
                "ciudad": valores[4],
            }
        )

        try:
            indice = cargar_indice()
            numero_registro = indice.get(str(valores[0]), 0)
        except Exception as error:
            numero_registro = 0
            self._mostrar_error(
                "ERROR AL LEER EL ÍNDICE",
                "No se pudo localizar el registro del ID {}:\n\n{}".format(
                    valores[0], error
                ),
            )

        self._actualizar_monitor(
            numero_registro, numero_registro * TAMANO_REGISTRO
        )

    # ------------------------------------------------------------------
    # Acciones: Contactos
    # ------------------------------------------------------------------
    def accion_agregar(self) -> None:
        """Menú Contactos > Agregar: inserta un registro al final del archivo."""
        datos = self._leer_formulario()

        if not datos["id"]:
            self._mostrar_alerta(
                "ID REQUERIDO",
                "Escriba el ID del contacto (número entero positivo).",
            )
            self.campos["id"].focus_set()
            return

        try:
            resultado = agregar_contacto(datos)
        except Exception as error:
            self._mostrar_error(
                "ERROR AL AGREGAR",
                "No se pudo agregar el contacto:\n\n{}".format(error),
            )
            return

        if not resultado.get("ok"):
            self._mostrar_alerta(
                "NO SE AGREGÓ EL CONTACTO",
                str(resultado.get("error", "Error desconocido.")),
            )
            return

        numero_registro = int(resultado.get("numero_registro", 0))
        posicion = int(resultado.get("posicion_tell", 0))

        self._actualizar_monitor(numero_registro, posicion, estado="OK")
        self._recargar_tabla(silencioso=True)
        self._registrar(
            "Contacto {} agregado en el registro {} (byte {}).".format(
                resultado.get("id"), numero_registro, posicion
            ),
            "OK",
        )
        mensaje = (
            "ID: {}\nRegistro: #{}\nByte: {}\n\nEl registro fue escrito al "
            "final de '{}'.".format(
                resultado.get("id"), numero_registro, posicion,
                ARCHIVO_CONTACTOS,
            )
        )
        advertencia = resultado.get("advertencia")
        if advertencia:
            self._mostrar_alerta(
                "CONTACTO AGREGADO CON ADVERTENCIA",
                "{}\n\n{}".format(mensaje, advertencia),
            )
        else:
            self._mostrar_info("CONTACTO AGREGADO", mensaje)
        # El formulario se vacía sin perder la posición del puntero.
        self.limpiar_formulario(resetear_monitor=False)

    def accion_buscar(self) -> None:
        """Menú Contactos > Buscar por ID: lectura aleatoria por offset."""
        id_texto = self.campos["id"].get().strip()

        if not id_texto:
            self._mostrar_alerta(
                "ID REQUERIDO",
                "Escriba el ID que desea buscar.",
            )
            self.campos["id"].focus_set()
            return

        try:
            resultado = buscar_por_id(id_texto)
        except Exception as error:
            self._mostrar_error(
                "ERROR EN LA BÚSQUEDA",
                "No se pudo buscar el ID {}:\n\n{}".format(id_texto, error),
            )
            return

        if not resultado.get("ok"):
            self._mostrar_alerta(
                "CONTACTO NO ENCONTRADO",
                str(resultado.get("error", "Error desconocido.")),
            )
            return

        numero_registro = int(resultado.get("numero_registro", 0))
        posicion = int(resultado.get("posicion_tell", 0))

        self._poblar_formulario(resultado)
        self._actualizar_monitor(numero_registro, posicion, estado="OK")
        self._recargar_tabla(silencioso=True)

        iid = str(resultado.get("id"))
        if self.tabla.exists(iid):
            self.tabla.selection_set(iid)
            self.tabla.see(iid)

        self._registrar(
            "Lectura aleatoria: ID {} -> registro #{} (byte {}).".format(
                resultado.get("id"), numero_registro, posicion
            ),
            "OK",
        )

    def accion_modificar(self) -> None:
        """Menú Contactos > Modificar: sobrescribe el registro in-place."""
        id_texto = self.campos["id"].get().strip()

        if not id_texto:
            self._mostrar_alerta(
                "ID REQUERIDO",
                "Escriba el ID del contacto que desea modificar.",
            )
            self.campos["id"].focus_set()
            return

        datos = self._leer_formulario()
        datos.pop("id", None)

        try:
            resultado = modificar_por_id(id_texto, datos)
        except Exception as error:
            self._mostrar_error(
                "ERROR AL MODIFICAR",
                "No se pudo modificar el contacto {}:\n\n{}".format(
                    id_texto, error
                ),
            )
            return

        if not resultado.get("ok"):
            self._mostrar_alerta(
                "NO SE MODIFICÓ EL CONTACTO",
                str(resultado.get("error", "Error desconocido.")),
            )
            return

        numero_registro = int(resultado.get("numero_registro", 0))
        posicion = int(resultado.get("posicion_tell", 0))

        self._poblar_formulario(resultado)
        self._actualizar_monitor(numero_registro, posicion, estado="OK")
        self._recargar_tabla(silencioso=True)
        self._registrar(
            "Contacto {} sobrescrito en el registro #{} (byte {}).".format(
                resultado.get("id"), numero_registro, posicion
            ),
            "OK",
        )
        mensaje = (
            "ID: {}\nRegistro: #{}\nByte: {}\n\nSe sobrescribieron {} "
            "bytes sin reescribir el resto del archivo.".format(
                resultado.get("id"), numero_registro, posicion,
                TAMANO_REGISTRO,
            )
        )
        advertencia = resultado.get("advertencia")
        if advertencia:
            self._mostrar_alerta(
                "CONTACTO MODIFICADO CON ADVERTENCIA",
                "{}\n\n{}".format(mensaje, advertencia),
            )
        else:
            self._mostrar_info("CONTACTO MODIFICADO", mensaje)

    # ------------------------------------------------------------------
    # Acciones: Exportar
    # ------------------------------------------------------------------
    def accion_exportar_json(self) -> None:
        """Menú Exportar > Exportar a JSON."""
        try:
            resultado = exportar_contactos_json()
        except Exception as error:
            self._mostrar_error(
                "ERROR AL EXPORTAR A JSON",
                "No se pudo generar el JSON:\n\n{}".format(error),
            )
            return

        if not resultado.get("ok"):
            self._mostrar_error(
                "ERROR AL EXPORTAR A JSON",
                str(resultado.get("error", "Error desconocido.")),
            )
            return

        cantidad = resultado.get("cantidad", 0)
        self._registrar(
            "Exportación JSON: {} contacto(s) en '{}'.".format(
                cantidad, resultado.get("ruta_json")
            ),
            "OK",
        )
        self._mostrar_info(
            "EXPORTACIÓN A JSON",
            "Se exportaron {} contacto(s).\n\nArchivo: {}".format(
                cantidad, resultado.get("ruta_json")
            ),
        )

    def accion_generar_pdf(self) -> None:
        """Menú Exportar > Generar reporte PDF."""
        try:
            resultado = generar_reporte_pdf()
        except Exception as error:
            self._mostrar_error(
                "ERROR AL GENERAR EL PDF",
                "No se pudo generar el reporte:\n\n{}".format(error),
            )
            return

        if not resultado.get("ok"):
            self._mostrar_error(
                "ERROR AL GENERAR EL PDF",
                str(resultado.get("error", "Error desconocido.")),
            )
            return

        self._registrar(
            "Reporte PDF: {} contacto(s) en '{}'.".format(
                resultado.get("cantidad", 0), resultado.get("ruta_pdf")
            ),
            "OK",
        )
        self._mostrar_info(
            "REPORTE PDF GENERADO",
            "Contactos incluidos: {}\nFecha: {}\n\nArchivo: {}".format(
                resultado.get("cantidad", 0),
                resultado.get("fecha_generacion", "-"),
                resultado.get("ruta_pdf"),
            ),
        )

    # ------------------------------------------------------------------
    # Acciones: Herramientas
    # ------------------------------------------------------------------
    def _verificar_integridad_inicial(self) -> None:
        """Comprobación automática de integridad al iniciar la aplicación."""
        try:
            resultado = verificar_integridad_sha256()
        except Exception as error:
            self._mostrar_error(
                "ERROR EN LA VERIFICACIÓN",
                "No se pudo verificar la integridad:\n\n{}".format(error),
            )
            return

        integro = resultado.get("integro")
        mensaje = str(resultado.get("mensaje", ""))

        if integro is False:
            self._registrar(mensaje, "ALERTA")
            self._actualizar_monitor(
                self.ultimo_registro,
                self.ultimo_offset,
                estado="INTEGRIDAD",
            )
            messagebox.showwarning(
                "ALERTA DE INTEGRIDAD",
                "{}\n\nHash actual:  {}\nHash guardado: {}\n\nEl archivo '{}' "
                "fue modificado fuera de la aplicación.".format(
                    mensaje,
                    resultado.get("hash_actual"),
                    resultado.get("hash_guardado"),
                    ARCHIVO_CONTACTOS,
                ),
                parent=self,
            )
            return

        if integro is None:
            self._registrar(mensaje, "ALERTA")
            self._mostrar_alerta(
                "VERIFICACIÓN IMPOSIBLE", mensaje
            )
            return

        self._registrar("Arranque: {}".format(mensaje), "OK")
        self._actualizar_monitor(
            0, 0, estado="OK", hash_actual=resultado.get("hash_actual")
        )

    def accion_verificar_integridad(self) -> None:
        """Menú Herramientas > Verificar integridad."""
        try:
            resultado = verificar_integridad_sha256()
        except Exception as error:
            self._mostrar_error(
                "ERROR EN LA VERIFICACIÓN",
                "No se pudo verificar la integridad:\n\n{}".format(error),
            )
            return

        integro = resultado.get("integro")
        mensaje = str(resultado.get("mensaje", ""))

        if integro is False:
            self._registrar(mensaje, "ALERTA")
            self._actualizar_monitor(
                self.ultimo_registro,
                self.ultimo_offset,
                estado="INTEGRIDAD",
            )
            messagebox.showwarning(
                "ALERTA DE INTEGRIDAD",
                "{}\n\nHash actual:  {}\nHash guardado: {}\n\nEl archivo '{}' "
                "fue modificado fuera de la aplicación.".format(
                    mensaje,
                    resultado.get("hash_actual"),
                    resultado.get("hash_guardado"),
                    ARCHIVO_CONTACTOS,
                ),
                parent=self,
            )
            return

        if integro is None:
            self._mostrar_alerta("VERIFICACIÓN IMPOSIBLE", mensaje)
            return

        self._actualizar_monitor(
            self.ultimo_registro,
            self.ultimo_offset,
            estado="OK",
            hash_actual=resultado.get("hash_actual"),
        )
        self._registrar("Integridad verificada: {}".format(mensaje), "OK")
        self._mostrar_info(
            "INTEGRIDAD VERIFICADA",
            "{}\n\nHash actual:  {}\nHash guardado: {}\nArchivo de hash: {}".format(
                mensaje,
                resultado.get("hash_actual"),
                resultado.get("hash_guardado"),
                ARCHIVO_HASH,
            ),
        )

    def accion_crear_respaldo(self) -> None:
        """Menú Herramientas > Crear respaldo ZIP."""
        try:
            resultado = crear_respaldo_zip()
        except Exception as error:
            self._mostrar_error(
                "ERROR AL CREAR EL RESPALDO",
                "No se pudo crear el ZIP:\n\n{}".format(error),
            )
            return

        if not resultado.get("ok"):
            self._mostrar_error(
                "ERROR AL CREAR EL RESPALDO",
                str(resultado.get("error", "Error desconocido.")),
            )
            return

        self._registrar(
            "Respaldo ZIP creado: '{}'.".format(resultado.get("ruta_zip")),
            "OK",
        )

        texto = (
            "Archivo: {}\n\nArchivos incluidos: {}\n"
            "Tamaño original: {} bytes\nTamaño ZIP: {} bytes\n"
            "Compresión: {}%".format(
                resultado.get("ruta_zip"),
                ", ".join(resultado.get("archivos_incluidos", [])),
                resultado.get("tamano_original", 0),
                resultado.get("tamano_zip", 0),
                resultado.get("porcentaje_compresion", 0.0),
            )
        )
        advertencia = resultado.get("advertencia")
        if advertencia:
            texto += "\n\nAdvertencia: {}".format(advertencia)

        self._mostrar_info("RESPALDO ZIP CREADO", texto)

    def accion_info_archivo(self) -> None:
        """Menú Herramientas > Información del archivo."""
        try:
            resultado = obtener_metadatos_archivo()
        except Exception as error:
            self._mostrar_error(
                "ERROR AL CONSULTAR EL ARCHIVO",
                "No se pudieron obtener los metadatos:\n\n{}".format(error),
            )
            return

        if not resultado.get("ok"):
            self._mostrar_error(
                "ERROR AL CONSULTAR EL ARCHIVO",
                str(resultado.get("error", "Error desconocido.")),
            )
            return

        self._registrar(
            "Metadatos leídos: {} bytes, {} registro(s).".format(
                resultado.get("tamano_bytes", 0),
                resultado.get("cantidad_registros", 0),
            ),
            "OK",
        )
        self._mostrar_info(
            "INFORMACIÓN DEL ARCHIVO",
            "Ruta: {}\n\n"
            "Tamaño: {} bytes ({} registros de {} bytes)\n"
            "Última modificación: {}\n"
            "Permiso de lectura: {}\n"
            "Permiso de escritura: {}\n\n"
            "Índice: {}\nHash: {}".format(
                resultado.get("ruta"),
                resultado.get("tamano_bytes", 0),
                resultado.get("cantidad_registros", 0),
                TAMANO_REGISTRO,
                resultado.get("ultima_modificacion", "-"),
                "SÍ" if resultado.get("permiso_lectura") else "NO",
                "SÍ" if resultado.get("permiso_escritura") else "NO",
                ARCHIVO_INDICE,
                ARCHIVO_HASH,
            ),
        )

    # ------------------------------------------------------------------
    # Acciones: Ayuda
    # ------------------------------------------------------------------
    def accion_acerca_de(self) -> None:
        """Menú Ayuda > Acerca de."""
        self._mostrar_info(
            "ACERCA DE",
            "AGENDA DE CONTACTOS :: ACCESO ALEATORIO\n"
            "Laboratorio 2 - Manejo e Implementación de Archivos\n"
            "--------------------------------------------\n\n"
            "Acceso aleatorio sobre '{}':\n"
            "    offset = numero_registro * {}\n"
            "    archivo.seek(offset) -> archivo.tell()\n\n"
            "Módulos:\n"
            "  · modelo_contacto.py   (registro fijo de {} bytes)\n"
            "  · gestor_archivos.py  (lectura/escritura aleatoria)\n"
            "  · utilidades_sistema.py (SHA-256, ZIP, metadatos)\n"
            "  · exportador.py        (JSON y reporte PDF)\n"
            "  · interfaz_brutalista.py (esta capa de presentación)\n\n"
            "Archivo de datos: {}\n"
            "Índice: {}\n"
            "Hash: {}\n"
            "Respaldo: {}".format(
                ARCHIVO_CONTACTOS,
                TAMANO_REGISTRO,
                TAMANO_REGISTRO,
                ARCHIVO_CONTACTOS,
                ARCHIVO_INDICE,
                ARCHIVO_HASH,
                ARCHIVO_RESPALDO,
            ),
        )

    # ------------------------------------------------------------------
    # Cierre
    # ------------------------------------------------------------------
    def _salir(self) -> None:
        """Cierra la aplicación con una confirmación."""
        if messagebox.askokcancel(
            "SALIR",
            "¿Desea cerrar la agenda de contactos?",
            parent=self,
        ):
            self.destroy()


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------
def main() -> int:
    """Arranca la aplicación gráfica."""
    # Los módulos trabajan con rutas relativas: se anclan a la raíz del
    # proyecto (dos niveles arriba de src/interfaz) para que los datos queden
    # junto al código.
    try:
        base = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        if base:
            os.chdir(base)
    except OSError:
        pass

    aplicacion = InterfazBrutalista()
    aplicacion.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
