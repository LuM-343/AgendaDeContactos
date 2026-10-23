# -*- coding: utf-8 -*-
"""
main.py
======

Punto de entrada de la **Agenda de Contactos** con acceso aleatorio.

Responsabilidades:
    * Arrancar la interfaz neo-brutalista
      (``interfaz_brutalista.InterfazBrutalista``).
    * Instalar un manejador global de excepciones (``sys.excepthook``) para que
      ningún error inesperado tumbe la aplicación: se registra en la consola y
      se informa al usuario con un ``messagebox``.
    * Comprobar que el módulo ``tkinter`` esté disponible en la instalación.

Uso:
    python main.py
"""

import os
import sys
import traceback
from typing import Optional


def _manejar_excepcion_global(
    tipo_exc: type,
    valor_exc: BaseException,
    traza: Optional[traceback.TracebackException],
) -> None:
    """Manejador global de excepciones: informa sin cerrar la aplicación."""
    detalle = "".join(traceback.format_exception(tipo_exc, valor_exc, traza))

    try:
        print(detalle, file=sys.stderr)
    except Exception:  # pragma: no cover - defensivo
        pass

    try:
        from tkinter import messagebox

        messagebox.showerror(
            "Error inesperado",
            "Ocurrió un error no controlado en la aplicación:\n\n"
            "{}\n\nLa aplicación seguirá funcionando.".format(valor_exc),
        )
    except Exception:  # pragma: no cover - si Tk no está disponible
        pass


def verificar_dependencias() -> bool:
    """Comprueba que ``tkinter`` esté instalado. Devuelve ``True`` si lo está."""
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print(
            "ERROR: no se pudo importar 'tkinter'.\n"
            "En Windows, reinstala Python marcando 'tcl/tk and IDLE'.\n"
            "En Linux, instala el paquete 'python3-tk'.",
            file=sys.stderr,
        )
        return False
    return True


def main() -> int:
    """Arranca la aplicación. Devuelve el código de salida del proceso."""
    if not verificar_dependencias():
        return 1

    # Todos los módulos usan rutas relativas (contactos.dat, indice.json...);
    # se ancla el proceso a la carpeta del proyecto aunque se invoque desde
    # otra ubicación.
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
    except OSError as error:
        print(
            "ADVERTENCIA: no se pudo cambiar a la carpeta del proyecto: "
            "{}".format(error),
            file=sys.stderr,
        )

    sys.excepthook = _manejar_excepcion_global

    try:
        from interfaz_brutalista import InterfazBrutalista
    except ImportError as error:
        print(
            "ERROR: no se pudo importar 'interfaz_brutalista' ({}).\n"
            "Ejecuta el programa desde la carpeta del proyecto.".format(error),
            file=sys.stderr,
        )
        try:
            from tkinter import messagebox

            messagebox.showerror(
                "Error al iniciar",
                "No se pudo cargar la interfaz de la agenda:\n\n{}".format(
                    error
                ),
            )
        except Exception:
            pass
        return 1

    try:
        aplicacion = InterfazBrutalista()
    except Exception as error:  # pragma: no cover - defensivo
        print(
            "ERROR: no se pudo crear la ventana principal: {}".format(error),
            file=sys.stderr,
        )
        traceback.print_exc()
        try:
            from tkinter import messagebox

            messagebox.showerror(
                "Error al iniciar",
                "No se pudo abrir la ventana principal:\n\n{}".format(error),
            )
        except Exception:
            pass
        return 1

    try:
        aplicacion.mainloop()
    except KeyboardInterrupt:
        pass
    except Exception as error:  # pragma: no cover - defensivo
        _manejar_excepcion_global(
            type(error), error, error.__traceback__
        )
    finally:
        try:
            aplicacion.destroy()
        except Exception:  # pragma: no cover - defensivo
            pass

    return 0


if __name__ == "__main__":
    # La aplicación trabaja con rutas relativas a la carpeta del proyecto.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
