# Organización de archivos del proyecto

## 1. Estructura implementada

```text
Proyecto 2/
├── main.py                     # Lanzador: importa src.app y ejecuta main()
├── src/
│   ├── __init__.py
│   ├── app.py                  # Arranque real y manejador global de excepciones
│   ├── modelo/
│   │   ├── __init__.py
│   │   └── contacto.py         # Formato del registro de 110 bytes
│   ├── almacenamiento/
│   │   ├── __init__.py
│   │   └── gestor_archivos.py  # Acceso aleatorio e índice primario
│   ├── servicios/
│   │   ├── __init__.py
│   │   ├── exportador.py       # Exportación JSON y reporte PDF
│   │   └── utilidades_sistema.py  # SHA-256, ZIP y metadatos
│   └── interfaz/
│       ├── __init__.py
│       └── brutalista.py       # Interfaz Tkinter
│
├── requirements.txt            # Dependencia fpdf2
├── README.md                   # Inicio rápido
├── ORGANIZACION.md             # Este documento
│
├── contactos.dat               # Estado activo de la agenda
├── indice.json                 # Índice activo {"id": numero_registro}
├── contactos.sha256            # Hash activo del archivo de contactos
│
├── datos_prueba/               # Escenarios de prueba (no editar a mano)
│   ├── manifest.json           # Descripción legible por máquina
│   ├── LEEME.md                # Guía de escenarios y resultados esperados
│   ├── 00_actual/              # Respaldo del estado activo anterior
│   ├── 01_agenda_normal/
│   ├── 02_limites_utf8/
│   ├── 03_un_registro/
│   ├── 04_agenda_vacia/
│   ├── 05_hash_alterado/
│   ├── 06_archivo_truncado/
│   ├── 07_indice_corrupto/
│   ├── 08_indice_ausente/
│   ├── 09_datos_ausentes_con_indice/
│   ├── 10_sin_archivos/
│   ├── 11_indice_incompleto/
│   └── 12_registro_invalido/
│
├── pruebas/
│   ├── generar_datos_prueba.py  # Reconstruye datos_prueba/
│   ├── cargar_escenario.py      # Copia un escenario a la raíz activa
│   ├── comprobar_escenarios.py  # Verifica los 12 escenarios
│   ├── generar_salidas.py       # Genera JSON, PDF y ZIP de entrega
│   ├── GUIA_PRUEBAS.md          # Pruebas manuales paso a paso
│   └── verificar_proyecto.py    # Suite general del proyecto
│
├── salidas/
│   ├── contactos_exportados.json
│   ├── reporte_contactos.pdf
│   └── respaldo_agenda.zip
│
└── docs/
    ├── Laboratorio 2 Manejo de archivos Borrador.pdf
    └── INFORME_TECNICO.md
```

## 2. Por qué esta organización

### `src/`: código separado por capas

El código de producción ya no está mezclado con datos, pruebas, salidas y
documentación. Dentro de `src/` cada paquete tiene una responsabilidad clara:

| Paquete | Responsabilidad |
|---|---|
| `src/modelo/` | Definir el registro de longitud fija y serializar sus campos. |
| `src/almacenamiento/` | Leer, escribir y modificar registros con acceso aleatorio; mantener el índice JSON. |
| `src/servicios/` | Exportar a JSON/PDF, calcular SHA-256, crear el ZIP y obtener metadatos. |
| `src/interfaz/` | Presentar la aplicación en Tkinter y traducir los errores a mensajes. |

`src/app.py` contiene el arranque real: comprueba dependencias, instala el
manejador global de excepciones y abre la interfaz. El `main.py` de la raíz es
un lanzador mínimo que añade `src/` a `sys.path` y llama a `src.app.main()`.
Así se conserva el comando habitual `python main.py` sin duplicar lógica.

Los imports entre paquetes son absolutos y explícitos, por ejemplo
`from almacenamiento.gestor_archivos import ...`. Los archivos `__init__.py`
solo marcan los paquetes y documentan su propósito; no ocultan dependencias con
re-exportaciones innecesarias.

No se dividió `gestor_archivos.py` en más archivos porque sus funciones
comparten el mismo estado (archivo de datos, índice y hash) y separarlas
añadiría indirección sin un beneficio real para el tamaño del proyecto.

### Archivos activos en la raíz

`src/almacenamiento/gestor_archivos.py`,
`src/servicios/utilidades_sistema.py` y `src/servicios/exportador.py` usan
nombres relativos (`contactos.dat`, `indice.json`, `contactos.sha256`). Moverlos
a una carpeta `datos/` obligaría a cambiar constantes en varios módulos y a
ajustar la suite de verificación. Por eso el estado activo se queda en la raíz,
que es exactamente donde la aplicación lo espera. `src/app.py` y la interfaz
anclan el proceso a esa raíz antes de abrir la ventana.

### `datos_prueba/`: escenarios separados y reproducibles

Cada carpeta contiene exactamente los tres archivos que la aplicación lee.
Así se puede cambiar de caso de prueba copiando tres archivos, sin mezclar
datos buenos con datos corruptos. Los escenarios no se editan a mano: se
regeneran con `pruebas/generar_datos_prueba.py`.

`00_actual/` no es un escenario: es el respaldo automático del último estado
activo. Puede contener datos personales, por eso está en `.gitignore`.

### `pruebas/`: herramientas, no datos

Los scripts de prueba quedan juntos y separados del código de producción:

| Script | Responsabilidad |
|---|---|
| `generar_datos_prueba.py` | Crear los 12 escenarios y su manifiesto. |
| `cargar_escenario.py` | Respaldar el estado activo e instalar un escenario. |
| `comprobar_escenarios.py` | Verificar que cada escenario produce lo esperado. |
| `generar_salidas.py` | Producir los artefactos de entrega en `salidas/`. |
| `GUIA_PRUEBAS.md` | Pasos manuales y resultados esperados por criterio. |
| `verificar_proyecto.py` | Probar el código: acceso aleatorio, índice, hash, ZIP, permisos, etc. |

### `salidas/`: artefactos generados

El JSON, el PDF y el ZIP son productos de la aplicación, no código fuente ni
datos de entrada. Tenerlos en una carpeta aparte evita confundirlos con los
archivos activos y facilita adjuntarlos a la entrega.

### `docs/`: enunciado e informe

El PDF del laboratorio y el informe técnico son documentación. No participan
en la ejecución ni en las pruebas.

## 3. Reglas de nombres

- Carpetas de escenarios: `NN_nombre_descriptivo`, con dos dígitos para
  conservar el orden (`01_agenda_normal`, `05_hash_alterado`, ...).
- Archivos activos: nombres exactos que espera el código; no renombrar.
- Salidas: nombres descriptivos y estables
  (`contactos_exportados.json`, `reporte_contactos.pdf`,
  `respaldo_agenda.zip`).
- Scripts: verbos en infinitivo (`generar_`, `cargar_`, `comprobar_`,
  `verificar_`).
- Documentación: `README.md` para inicio, `LEEME.md` para datos de prueba,
  `ORGANIZACION.md` para la estructura.

## 4. Flujo de trabajo recomendado

1. Verificar que los escenarios siguen sanos:

   ```bat
   python pruebas/comprobar_escenarios.py
   ```

2. Verificar el código:

   ```bat
   python pruebas/verificar_proyecto.py
   ```

3. Cargar el escenario que se va a demostrar:

   ```bat
   python pruebas/cargar_escenario.py 01_agenda_normal
   ```

4. Abrir la aplicación:

   ```bat
   python main.py
   ```

5. Generar las salidas de entrega:

   ```bat
   python pruebas/generar_salidas.py
   ```

6. Para volver al estado anterior, cargar `00_actual`:

   ```bat
   python pruebas/cargar_escenario.py 00_actual
   ```

## 5. Relación con los criterios de evaluación

| Criterio | Dónde se demuestra |
|---|---|
| Menú y operaciones de contactos | `src/interfaz/brutalista.py`, escenario `01_agenda_normal`. |
| Registros fijos y `seek()`/`tell()` | `src/modelo/contacto.py`, `src/almacenamiento/gestor_archivos.py`, escenarios `02` y `03`. |
| Índice primario en JSON | `indice.json`, escenarios `07`, `08` y `11`. |
| Exportación JSON y PDF | `salidas/contactos_exportados.json`, `salidas/reporte_contactos.pdf`. |
| Integridad SHA-256 y respaldo ZIP | Escenario `05_hash_alterado`, `salidas/respaldo_agenda.zip`. |
| Metadatos, permisos y errores | Escenarios `06`, `09`, `10` y `12`; `src/servicios/utilidades_sistema.py`. |

## 6. Qué evitar

- No editar los archivos de `datos_prueba/` a mano: el generador los
  sobrescribe.
- No cargar un escenario con la aplicación abierta.
- No commitear `datos_prueba/00_actual/` si contiene datos reales.
- No renombrar `contactos.dat`, `indice.json` ni `contactos.sha256`: el código
  y las pruebas dependen de esos nombres.
- No mover los módulos de `src/` de vuelta a la raíz sin actualizar imports y
  rutas: `main.py` añade `src/` a `sys.path`.
- No mezclar salidas generadas con el estado activo: si se usan los menús de
  la aplicación, los archivos se crean en la raíz; para la entrega se copian o
  se regeneran en `salidas/` con `generar_salidas.py`.

## 7. Si más adelante se quiere separar `datos/`

La organización actual prioriza que el proyecto funcione sin cambios. Para
pasar a una estructura con `datos/` y `salidas/` fijas habría que:

1. Definir las rutas en un único módulo de configuración dentro de `src/`.
2. Reemplazar las constantes `ARCHIVO_*` de
   `src/almacenamiento/gestor_archivos.py`,
   `src/servicios/utilidades_sistema.py` y `src/servicios/exportador.py`.
3. Ajustar `verificar_proyecto.py`, `comprobar_escenarios.py` y el cargador.
4. Añadir `datos/` y `salidas/` a `.gitignore` o versionar solo archivos de
   ejemplo.

No se hizo ahora para no romper la compatibilidad con `python main.py` ni con
la suite existente.
