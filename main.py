# -*- coding: utf-8 -*-
"""
main.py - Lanzador de la Agenda de Contactos

El código de la aplicación vive en ``src/``:

* ``src/app.py``                  -> arranque y manejo global de errores.
* ``src/modelo/``                 -> formato del registro.
* ``src/almacenamiento/``         -> acceso aleatorio e índice.
* ``src/servicios/``              -> exportación, integridad y respaldo.
* ``src/interfaz/``               -> interfaz Tkinter.

Este archivo se conserva en la raíz para que el comando habitual siga siendo::

    python main.py
"""

import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "src")

for ruta in (BASE, SRC):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

try:
    from src.app import main
except ImportError as error:  # pragma: no cover - instalación incompleta
    print(
        "ERROR: no se pudo importar la aplicación desde 'src/': {}".format(
            error
        ),
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
