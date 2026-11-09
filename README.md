# Agenda de Contactos con Acceso Aleatorio

Aplicación de escritorio en Python/Tkinter para administrar una agenda de
contactos en un archivo binario de registros de tamaño fijo (110 bytes),
con índice primario en JSON, exportación a JSON/PDF, verificación de
integridad SHA-256 y respaldo ZIP.

## Requisitos

- Python 3.10 o superior.
- Tkinter (incluido normalmente con Python; en Linux puede requerir
  `python3-tk`).
- `fpdf2` para el reporte PDF.

```bat
python -m pip install -r requirements.txt
```

## Ejecución

```bat
python main.py
```

La aplicación trabaja con rutas relativas. `main.py` actúa como lanzador y
`src/app.py` ancla el proceso a la raíz del proyecto antes de abrir la
interfaz.

## Estructura rápida

| Ruta | Contenido |
|---|---|
| `main.py` | Lanzador de la aplicación. |
| `src/` | Código por capas: `modelo/`, `almacenamiento/`, `servicios/` e `interfaz/`. |
| `contactos.dat`, `indice.json`, `contactos.sha256` | Estado activo de la agenda. |
| `datos_prueba/` | 12 escenarios de prueba listos para cargar. |
| `pruebas/` | Generadores, cargador de escenarios y suites de verificación. |
| `salidas/` | JSON exportado, reporte PDF y respaldo ZIP de entrega. |
| `docs/` | Enunciado del laboratorio e informe técnico. |

La explicación completa y el diseño técnico están en
[`docs/INFORME_TECNICO.md`](docs/INFORME_TECNICO.md).

## Datos de prueba

Los escenarios ya están generados. Para verlos y cargar uno:

```bat
python pruebas/cargar_escenario.py --listar
python pruebas/cargar_escenario.py 01_agenda_normal
python main.py
```

Antes de reemplazar el estado activo, el cargador guarda una copia en
`datos_prueba/00_actual/`. La descripción de cada escenario está en
[`datos_prueba/LEEME.md`](datos_prueba/LEEME.md). La guía paso a paso para
probar el menú, el acceso aleatorio, los errores y la entrega está en
[`pruebas/GUIA_PRUEBAS.md`](pruebas/GUIA_PRUEBAS.md).

Para regenerar los escenarios desde cero:

```bat
python pruebas/generar_datos_prueba.py
```

## Verificación

```bat
python pruebas/comprobar_escenarios.py
python pruebas/verificar_proyecto.py
```

- `comprobar_escenarios.py` valida los 12 escenarios contra las funciones
  reales de la aplicación.
- `verificar_proyecto.py` ejecuta la suite general del proyecto (registros
  fijos, `seek()`/`tell()`, índice, hash, exportación, ZIP, permisos y manejo
  de errores).

## Generar las salidas de entrega

Con el escenario que quieras exportar ya cargado:

```bat
python pruebas/generar_salidas.py
```

Esto crea `salidas/contactos_exportados.json`, `salidas/reporte_contactos.pdf`
y `salidas/respaldo_agenda.zip`.

## Formato del registro

| Campo | Bytes | Offset |
|---|---:|---:|
| `id` | 10 | 0 |
| `nombre` | 30 | 10 |
| `telefono` | 15 | 40 |
| `correo` | 35 | 55 |
| `ciudad` | 20 | 90 |
| **Total** | **110** | |

Cada campo se rellena con espacios ASCII y se codifica en UTF-8. El acceso a
un registro usa `offset = numero_registro * 110` con `seek()` y `tell()`.
