<!--
  INFORME_TECNICO.md
  ==================
  Documento base para el PDF entregable del Laboratorio 2.
  Las secciones 2, 3, 4 y 6 corresponden exactamente a los cuatro puntos
  solicitados. Reemplace los datos entre corchetes [ ] antes de convertir a PDF.
  Sugerencia: exporte con un conversor Markdown -> PDF (VS Code + Markdown PDF,
  Pandoc + LaTeX o Google Docs/Word) usando una fuente con soporte para tildes
  y eñe (Calibri, Arial, DejaVu Sans) y Consolas para los bloques de código.
-->

# Informe técnico
## Agenda de Contactos con Acceso Aleatorio

**Proyecto:** Laboratorio 2 — Manejo e Implementación de Archivos  
**Tema:** Registros de longitud fija, acceso aleatorio con `seek()`/`tell()`, índice primario, integridad SHA-256 y respaldo ZIP  
**Estudiante:** [Nombre completo]  
**Carné:** [Número de carné]  
**Profesor:** [Nombre del profesor]  
**Fecha de entrega:** [DD/MM/AAAA]  
**Entorno de ejecución:** Windows 10/11, Python 3.x, Tkinter  
**Archivo de datos:** `contactos.dat`  
**Tamaño del registro:** 110 bytes en UTF-8  
**Repositorio/carpeta del proyecto:** `Proyecto 2`

---

## Resumen ejecutivo

El proyecto implementa una agenda de contactos que almacena la información en un archivo binario de registros de longitud fija llamado `contactos.dat`. Cada contacto ocupa exactamente **110 bytes** distribuidos en cinco campos: `id` (10 bytes), `nombre` (30), `telefono` (15), `correo` (35) y `ciudad` (20). Al no existir separadores, saltos de línea ni cabecera, la posición de cualquier registro se calcula con una operación aritmética:

```text
offset = numero_registro × 110
```

Esa igualdad es la base del acceso aleatorio: el programa abre el archivo en modo binario, ejecuta `seek(offset)` para mover el puntero directamente al byte deseado, confirma la posición con `tell()` y lee o escribe exactamente 110 bytes. Para modificar un contacto no se reescribe el archivo completo: se abre en modo `r+b` y se sobrescriben únicamente los 110 bytes del registro seleccionado, conservando intactos los demás registros y el tamaño total del archivo.

La búsqueda por ID se acelera con un **índice primario** almacenado en `indice.json`, que asocia cada ID con su número de registro. La consulta al diccionario es de tiempo constante promedio, O(1), y evita recorrer y desempacar todos los registros, lo que equivaldría a un costo lineal O(n). El proyecto también calcula un **SHA-256** de `contactos.dat` después de cada alta o modificación y lo guarda en `contactos.sha256`; si el archivo se altera fuera de la aplicación, la verificación detecta la diferencia y muestra una alerta. Por último, la opción de **respaldo ZIP** comprime `contactos.dat` e `indice.json`, lo que permite conservar una copia del estado anterior y compararla con el estado posterior a una alteración.

La suite `pruebas/verificar_proyecto.py` ejecutó **161 comprobaciones y las 161 pasaron** en este equipo, incluyendo pruebas de posicionamiento exacto con `seek()`/`tell()`, escritura de 110 bytes en una sola operación, conservación del registro anterior, actualización del hash, exportación JSON/PDF y creación/validación del ZIP. Si `fpdf2` no está instalado, las comprobaciones del PDF se omiten y el total disminuye; el resto de la suite se ejecuta igual.

---

## Tabla de contenido

1. [Contexto, alcance y arquitectura](#1-contexto-alcance-y-arquitectura)
2. [Estructura del registro de 110 bytes](#2-estructura-del-registro-de-110-bytes)
3. [Acceso aleatorio con `seek()` y `tell()`](#3-acceso-aleatorio-con-seek-y-tell)
4. [Índice primario `indice.json` y complejidad O(1) vs. O(n)](#4-índice-primario-indicejson-y-complejidad-o1-vs-on)
5. [Integridad SHA-256 y respaldo ZIP](#5-integridad-sha-256-y-respaldo-zip)
6. [Guía paso a paso para la prueba manual y las capturas](#6-guía-paso-a-paso-para-la-prueba-manual-y-las-capturas)
7. [Conclusiones](#7-conclusiones)
8. [Referencias](#8-referencias)
9. [Apéndices](#9-apéndices)

---

# 1. Contexto, alcance y arquitectura

## 1.1 Objetivo del proyecto

Diseñar e implementar una agenda de contactos que demuestre, sobre un archivo real en disco, los siguientes conceptos de manejo de archivos:

* Organización de registros de **longitud fija**.
* Acceso **secuencial** para escritura al final y acceso **aleatorio** para lectura y modificación.
* Uso de `seek()` para posicionar el puntero del archivo y `tell()` para verificar la posición en bytes.
* Modificación **in-place** (en el lugar), sin reescribir el resto del archivo.
* Uso de un **índice primario** para reducir el costo de búsqueda.
* Verificación de **integridad** mediante una función hash criptográfica (SHA-256).
* **Respaldo** comprimido en formato ZIP.
* Manejo controlado de errores: archivo ausente, archivo corrupto, permisos insuficientes, registros incompletos, índice desincronizado, entre otros.

## 1.2 Módulos del proyecto y responsabilidades

El código de producción está organizado en `src/`. Para simplificar la lectura,
las secciones siguientes citan el nombre lógico del módulo
(`gestor_archivos.py`, `modelo_contacto.py`, etc.); la ruta física exacta es la
de esta tabla.

| Archivo | Responsabilidad principal | Elementos clave |
|---|---|---|
| `src/modelo/contacto.py` | Define el formato del registro y serializa/deserializa los datos. | `TAMANO_REGISTRO = 110`, `empaquetar_contacto()`, `desempaquetar_contacto()`, `ajustar_campo_utf8()` |
| `src/almacenamiento/gestor_archivos.py` | Motor de acceso aleatorio y gestión del índice primario. | `escribir_registro_final()`, `leer_registro_aleatorio()`, `sobrescribir_registro_en_lugar()`, `agregar_contacto()`, `buscar_por_id()`, `modificar_por_id()` |
| `src/servicios/utilidades_sistema.py` | Integridad SHA-256, respaldo ZIP y metadatos del archivo. | `guardar_hash_sha256()`, `verificar_integridad_sha256()`, `crear_respaldo_zip()`, `obtener_metadatos_archivo()` |
| `src/servicios/exportador.py` | Exportación de los contactos a JSON y generación de un reporte PDF. | `exportar_contactos_json()`, `generar_reporte_pdf()` |
| `src/interfaz/brutalista.py` | Capa de presentación en Tkinter. No contiene lógica de archivos. | Formulario, tabla, monitor `SEEK`/`TELL`, consola, menús, `messagebox` |
| `main.py` | Lanzador mínimo: añade `src/` a `sys.path` y llama a `src.app.main()`. | `main()` importado desde `src.app` |
| `src/app.py` | Arranque real de la aplicación y manejador global de excepciones. | `main()`, `sys.excepthook`, comprobación de dependencias |
| `pruebas/verificar_proyecto.py` | Suite de verificación automática sin abrir la interfaz. | 161 comprobaciones sobre archivos, permisos, corrupción, PDF y ZIP |

## 1.3 Flujo general de una operación

```text
+---------------------------+
|  interfaz_brutalista.py   |
|  (formulario / menús)     |
+-------------+-------------+
              |
              | llama a funciones de alto nivel
              v
+---------------------------+        +----------------------+
|    gestor_archivos.py     |<------>|    indice.json       |
|  búsqueda, alta, cambio   |        |  {"id": registro}    |
+------+------+-------------+        +----------------------+
       |      |
       |      | usa el formato del registro
       |      v
       |  +---------------------------+
       |  |    modelo_contacto.py     |
       |  |  empaquetar / desempaquetar|
       |  +---------------------------+
       |
       v
+---------------------------+        +----------------------+
|     contactos.dat         |<------>| utilidades_sistema.py|
|  registros de 110 bytes   |        | SHA-256 / ZIP / stat |
+---------------------------+        +----------------------+
```

## 1.4 Archivos que genera la aplicación

| Archivo | Formato | Contenido | ¿Cuándo se crea o actualiza? |
|---|---|---|---|
| `contactos.dat` | Binario, registros fijos de 110 bytes | Los contactos, en orden de inserción | Al agregar un contacto; se modifica in-place al editar |
| `indice.json` | Texto JSON UTF-8 | Mapa `{"id": numero_registro}` | Al agregar un contacto, al reconstruir el índice o al repararlo |
| `contactos.sha256` | Texto UTF-8, 64 caracteres hexadecimales | SHA-256 del contenido de `contactos.dat` | Después de cada alta o modificación exitosa |
| `respaldo_agenda.zip` | ZIP con compresión DEFLATE | `contactos.dat` e `indice.json` | Al usar **Herramientas > Crear respaldo ZIP** |
| `contactos_exportados.json` | Texto JSON UTF-8 | Copia legible de todos los contactos | Al usar **Exportar > Exportar a JSON** |
| `reporte_contactos.pdf` | PDF A4 | Tabla con todos los contactos | Al usar **Exportar > Generar reporte PDF** |

## 1.5 Convenciones de este informe

* **Byte:** unidad de 8 bits. Todas las posiciones y longitudes de este informe están en bytes, no en caracteres.
* **Offset:** posición absoluta dentro del archivo, contada desde 0.
* **Registro:** conjunto de 110 bytes que representa un contacto.
* **Número de registro:** índice lógico del contacto dentro del archivo; empieza en 0.
* **Puntero del archivo:** posición interna que el sistema operativo mantiene para el archivo abierto; `seek()` la cambia y `tell()` la consulta.
* **n:** cantidad de registros en `contactos.dat`.
* **m:** cantidad de entradas en `indice.json`. En operación normal, `m = n`.
* **S:** tamaño de `contactos.dat` en bytes; `S = 110 × n`.
* **O(1):** tiempo constante (independiente del tamaño de los datos).
* **O(n):** tiempo lineal (crece proporcionalmente con la cantidad de registros).

---

# 2. Estructura del registro de 110 bytes

## 2.1 Requisito y decisión de diseño

El requisito central es que cada contacto ocupe **exactamente la misma cantidad de bytes**. Esto elimina la necesidad de buscar separadores (coma, punto y coma, salto de línea) y permite calcular la posición de cualquier registro con una multiplicación. El formato se define en `modelo_contacto.py` con las siguientes constantes:

```python
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
```

La aserción es una salvaguarda de programación: si en el futuro alguien cambia la longitud de un campo y olvida actualizar `TAMANO_REGISTRO`, el módulo falla al importarse en lugar de generar registros de tamaño inconsistente.

## 2.2 Tabla de estructura del registro

| # | Campo | Tipo lógico | Longitud (bytes) | Offset inicial | Offset final (inclusive) | Rango de bytes | Ejemplo | Bytes usados por el ejemplo | Relleno |
|---:|---|---|---:|---:|---:|---|---|---:|---|
| 1 | `id` | Entero positivo almacenado como texto | **10** | 0 | 9 | 0–9 | `7` | 1 | 9 espacios |
| 2 | `nombre` | Texto UTF-8 | **30** | 10 | 39 | 10–39 | `José Núñez` | 13 | 17 espacios |
| 3 | `telefono` | Texto UTF-8 | **15** | 40 | 54 | 40–54 | `8888-1234` | 9 | 6 espacios |
| 4 | `correo` | Texto UTF-8 | **35** | 55 | 89 | 55–89 | `jose.nunez@correo.com` | 21 | 14 espacios |
| 5 | `ciudad` | Texto UTF-8 | **20** | 90 | 109 | 90–109 | `San José` | 9 | 11 espacios |
| | **TOTAL** | | **110** | | | **0–109** | | **53** | **57** |

**Verificación de la suma:**

```text
10 + 30 + 15 + 35 + 20 = 110 bytes
```

**Verificación del ejemplo:** 53 bytes de datos + 57 bytes de relleno = 110 bytes. Los 53 bytes incluyen los caracteres multibyte de las tildes y la eñe (ver sección 2.4).

## 2.3 Mapa físico del registro

```text
Byte:   0        9 10       39 40      54 55          89 90        109
       +----------+----------+----------+--------------+------------+
       |    id    |  nombre  | telefono |    correo    |   ciudad   |
       |  10 B    |  30 B    |  15 B    |    35 B      |   20 B     |
       +----------+----------+----------+--------------+------------+
       |<----------------------- 110 bytes ------------------------>|
       ^                                                           ^
     offset 0                                                 offset 109
```

El archivo completo es una concatenación de estos bloques, sin cabecera, sin separadores y sin salto de línea final:

```text
contactos.dat con 3 registros (330 bytes)
+----------------------+----------------------+----------------------+
| Registro 0 (0–109)   | Registro 1 (110–219) | Registro 2 (220–329) |
| Contacto A           | Contacto B           | Contacto C           |
+----------------------+----------------------+----------------------+
```

La relación general es:

```text
inicio del registro n = n × 110
fin del registro n    = n × 110 + 109
tamaño del archivo    = 110 × cantidad_de_registros
cantidad_de_registros = tamaño_del_archivo // 110
```

## 2.4 UTF-8: longitud en bytes, no en caracteres

El formato se declara en UTF-8 porque permite representar tildes, eñes, símbolos y otros alfabetos. Sin embargo, **en UTF-8 un carácter no siempre ocupa un byte**:

| Carácter | Representación UTF-8 | Bytes |
|---|---|---:|
| `A` | `41` | 1 |
| `é` | `C3 A9` | 2 |
| `ñ` | `C3 B1` | 2 |
| `ú` | `C3 BA` | 2 |
| `😀` | `F0 9F 98 80` | 4 |

Por eso el código no puede rellenar con `str.ljust(30)` y codificar sin más: si el texto tiene acentos, el resultado podría superar los 30 bytes. La función `ajustar_campo_utf8()` resuelve el problema en tres pasos:

```python
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
```

### Ejemplo detallado: `José Núñez` en un campo de 30 bytes

| Concepto | Cálculo | Resultado |
|---|---|---:|
| Caracteres del texto | `J`, `o`, `s`, `é`, espacio, `N`, `ú`, `ñ`, `e`, `z` | 10 caracteres |
| Bytes del texto | 7 caracteres ASCII (1 byte) + 3 caracteres acentuados (2 bytes cada uno) | 13 bytes |
| Relleno inicial con `ljust(30)` | 30 caracteres en total; al codificar, los 3 acentos añaden 3 bytes | 33 bytes |
| Recorte | Se toman los primeros 30 bytes; en este caso se recortan 3 espacios sobrantes | 30 bytes |
| Relleno final | 30 − 13 = 17 espacios ASCII | 17 espacios |
| **Total del campo** | 13 + 17 | **30 bytes** |

El resultado real del campo es:

```text
b'Jos\xc3\xa9 N\xc3\xba\xc3\xb1ez                 '
```

Es decir: `José Núñez` seguido de 17 espacios. El campo mide exactamente 30 bytes.

> **Idea clave:** el relleno se hace con el espacio ASCII `0x20`, que siempre ocupa 1 byte en UTF-8. Si se usara un carácter multibyte como relleno, el campo dejaría de tener una longitud fija. Si se usara `\0`, también sería 1 byte, pero el archivo dejaría de ser legible como texto; el espacio mantiene el archivo "humanamente inspeccionable" con un editor de texto, algo útil para la prueba manual de la sección 6.

### Truncamiento seguro

Si el texto es más largo que el campo, el código corta a `largo_bytes` y luego hace:

```python
datos.decode(CODIFICACION, errors="ignore").encode(CODIFICACION)
```

Eso elimina cualquier secuencia UTF-8 incompleta que haya quedado al final. Por ejemplo, si el corte cae en medio de `é` (`C3 A9`), el `decode` ignora el byte suelto y el `encode` vuelve a producir una cadena válida; después se rellena con espacios hasta completar el tamaño. Así nunca se escribe un registro con UTF-8 inválido ni con un tamaño distinto de 110 bytes.

## 2.5 Ejemplo binario real y volcado hexadecimal

Para el contacto de ejemplo:

```text
id       = 7
nombre   = José Núñez
telefono = 8888-1234
correo   = jose.nunez@correo.com
ciudad   = San José
```

`empaquetar_contacto()` produce exactamente 110 bytes. Volcado hexadecimal (16 bytes por línea):

```text
0000  37 20 20 20 20 20 20 20 20 20 4A 6F 73 C3 A9 20  |7         Jos.. |
0010  4E C3 BA C3 B1 65 7A 20 20 20 20 20 20 20 20 20  |N....ez         |
0020  20 20 20 20 20 20 20 20 38 38 38 38 2D 31 32 33  |        8888-123|
0030  34 20 20 20 20 20 20 6A 6F 73 65 2E 6E 75 6E 65  |4      jose.nune|
0040  7A 40 63 6F 72 72 65 6F 2E 63 6F 6D 20 20 20 20  |z@correo.com    |
0050  20 20 20 20 20 20 20 20 20 20 53 61 6E 20 4A 6F  |          San Jo|
0060  73 C3 A9 20 20 20 20 20 20 20 20 20 20 20        |s..           |
```

Lectura del volcado:

* `37` en el offset `0000` es el carácter `7` del ID.
* `4A 6F 73 C3 A9 20` es `J o s é` + espacio; `C3 A9` es la `é`.
* `4E C3 BA C3 B1 65 7A` es `N ú ñ e z`; `C3 BA` es la `ú` y `C3 B1` la `ñ`.
* Los `20` son espacios de relleno.
* Los campos `telefono`, `correo` y `ciudad` comienzan en `0028` (40), `0037` (55) y `005A` (90) en hexadecimal, que corresponden a los offsets decimales 40, 55 y 90 de la tabla.

> **Nota:** el archivo es "binario" en el sentido de que se abre con `rb`/`r+b` y no tiene separadores; pero como todos los bytes son ASCII imprimible o UTF-8 válido y el relleno es espacio, un editor de texto puede abrirlo y mostrarlo como una sola línea larga. Eso es intencional y facilita la demostración de la alteración externa.

## 2.6 Empaquetado: de un diccionario a 110 bytes

La función `empaquetar_contacto()` construye el registro en el orden físico de los campos y concatena las cinco piezas:

```python
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
```

La verificación final es fundamental: si por cualquier motivo la suma no diera 110, el programa se detiene antes de escribir un registro desalineado. Un solo registro de tamaño incorrecto rompería la aritmética de offsets de todos los registros siguientes.

## 2.7 Desempaquetado: de 110 bytes a un diccionario

La operación inversa recorre las longitudes fijas y decodifica cada fragmento:

```python
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
```

El `strip()` elimina los espacios de relleno de los extremos. Luego el ID se convierte a entero y se devuelve el diccionario con los cinco campos. Si el fragmento no es UTF-8 válido, se lanza un `ValueError` controlado; la interfaz lo muestra con `messagebox` y no se cae la aplicación.

## 2.8 Invariantes del formato

El correcto funcionamiento del acceso aleatorio depende de que se cumplan estas invariantes:

| Invariante | ¿Dónde se comprueba? | Consecuencia si se viola |
|---|---|---|
| Cada registro mide exactamente 110 bytes | `empaquetar_contacto()`, `escribir_registro_final()`, `sobrescribir_registro_en_lugar()` | Los offsets dejan de coincidir; se rechaza la operación |
| El tamaño del archivo es múltiplo de 110 | `cargar_indice()`, `escribir_registro_final()`, `sobrescribir_registro_en_lugar()`, `_validar_indice_contra_datos()` | Se informa "archivo corrupto" y no se escribe |
| El orden físico es siempre `id`, `nombre`, `telefono`, `correo`, `ciudad` | `empaquetar_contacto()` y `desempaquetar_contacto()` | Se leerían campos cruzados |
| El ID es un entero positivo de máximo 10 dígitos | `validar_id()` | Se rechaza el alta |
| El ID es único en la agenda | `agregar_contacto()` consulta `indice.json` | Se rechaza el duplicado |
| Cada entrada del índice apunta a un registro que contiene ese ID | `buscar_por_id()`, `modificar_por_id()`, `_validar_indice_contra_datos()` | Se informa "índice inconsistente" |
| El índice tiene tantas entradas como registros | `cargar_indice()` | Se reconstruye o se rechaza, según el caso |

## 2.9 ¿Por qué no usar CSV o JSON para el archivo de datos?

| Criterio | Registro fijo de 110 bytes | CSV | JSON |
|---|---|---|---|
| Localización de un registro por número | `n × 110`, con `seek()` directo | Hay que contar comas y saltos de línea; no hay offset fijo | Hay que parsear todo el documento |
| Modificación de un registro | Se sobrescriben 110 bytes | Se reescribe al menos la línea; puede cambiar el tamaño | Se reescribe el archivo completo |
| Costo de búsqueda por ID sin índice | O(n) | O(n) | O(n) |
| Costo de búsqueda con índice | O(1) promedio | O(1) promedio, pero el índice debe mantenerse aparte | O(1) promedio, pero el parseo del JSON es costoso |
| Legibilidad humana | Buena (texto con relleno de espacios) | Buena | Muy buena |
| Resistencia a errores de edición manual | Media: un byte de más desalinea todo | Media | Alta: el parser detecta el error |
| Ideal para este laboratorio | **Sí**, porque el objetivo es demostrar acceso aleatorio | No | No |

El formato de longitud fija es el que permite que `seek()` sea verdaderamente útil. En un CSV, la posición del registro 100 depende de la longitud de los 99 anteriores; en el registro fijo, es siempre `100 × 110`.

## 2.10 Texto sugerido para el PDF (sección de estructura)

> La agenda utiliza un registro de longitud fija de 110 bytes, compuesto por cinco campos: ID (10 bytes), nombre (30), teléfono (15), correo (35) y ciudad (20). Los campos de texto se codifican en UTF-8 y se rellenan con espacios ASCII hasta completar su longitud; si el texto excede el límite, se recorta respetando los límites de los caracteres multibyte y se completa con espacios. Esta decisión elimina los separadores y permite calcular la posición de cualquier registro mediante `offset = número_de_registro × 110`. La suma de los campos se verifica con una aserción en `modelo_contacto.py`, de modo que cualquier cambio futuro en las longitudes obliga a actualizar el tamaño total del registro.

---

# 3. Acceso aleatorio con `seek()` y `tell()`

## 3.1 Fundamento teórico

Cuando un programa abre un archivo, el sistema operativo (y el objeto archivo de Python) mantiene un **puntero de posición**. Ese puntero indica el byte a partir del cual se realizará la próxima lectura o escritura.

* `archivo.seek(offset, whence)` cambia el puntero.
  * `whence=0` (valor por omisión): el offset es absoluto, contado desde el inicio del archivo.
  * `whence=1`: el offset es relativo a la posición actual.
  * `whence=2`: el offset es relativo al final del archivo.
* `archivo.tell()` devuelve la posición actual del puntero, en bytes.
* En modo binario (`rb`, `r+b`, `w+b`), las posiciones son **offsets de bytes reales**. En modo texto, `tell()` devuelve un valor opaco que no debe usarse para aritmética de offsets.
* `seek()` no lee el archivo completo: mueve el puntero. El sistema operativo puede leer un bloque completo de disco (por ejemplo, 4 KiB) para satisfacer la lectura, pero no recorre los registros anteriores. Algorítmicamente, el acceso es O(1).

La relación fundamental del proyecto es:

```text
offset = numero_registro × TAMANO_REGISTRO
offset = numero_registro × 110
```

y su inversa:

```text
numero_registro = offset // 110
```

## 3.2 Diagrama de posicionamiento

```text
archivo.seek(110)
                 |
                 v
+----------------------+----------------------+----------------------+
| Registro 0 (0–109)   | Registro 1 (110–219) | Registro 2 (220–329) |
+----------------------+----------------------+----------------------+
                 ^
                 |
        tell() devuelve 110
        read(110) devuelve exactamente el registro 1
```

Para el registro 2:

```text
offset = 2 × 110 = 220
archivo.seek(220)
archivo.tell()  -> 220
archivo.read(110) -> bytes 220..329
```

## 3.3 Escritura al final del archivo

### Código exacto (`gestor_archivos.py`, líneas 437–465)

```python
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
```

### Explicación paso a paso

| Paso | Operación | Efecto |
|---:|---|---|
| 1 | `open(ARCHIVO_CONTACTOS, "r+b")` | Abre el archivo existente para lectura y escritura **sin truncarlo**. Si no existe, se captura `FileNotFoundError`. |
| 2 | `open(ARCHIVO_CONTACTOS, "w+b")` | Crea el archivo y lo abre para lectura/escritura. Solo se usa cuando el archivo no existe. Nunca se usa `"wb"` sobre un archivo con datos, porque lo truncaría. |
| 3 | `archivo.seek(0, 2)` | Mueve el puntero al final del archivo (offset 0 desde el final). |
| 4 | `archivo.tell()` | Devuelve el tamaño actual del archivo en bytes. Es equivalente a `os.path.getsize()`, pero sobre el descriptor ya abierto. |
| 5 | `posicion_bytes % 110 != 0` | Si el tamaño no es múltiplo de 110, el archivo está desalineado y no se puede calcular un número de registro confiable. Se aborta. |
| 6 | `numero_registro = posicion_bytes // 110` | Calcula el número del nuevo registro. Si el archivo mide 0, el nuevo registro es el 0; si mide 110, es el 1; si mide 220, es el 2. |
| 7 | `archivo.write(registro)` | Escribe exactamente los 110 bytes del registro empaquetado. |
| 8 | `escritos != 110` | Verifica que la escritura haya sido completa. Si el sistema escribió menos bytes, se lanza un error. |
| 9 | `archivo.flush()` | Fuerza la escritura del búfer al sistema operativo antes de cerrar el archivo. |

### Ejemplo con tres altas

| Alta | Tamaño antes | `seek(0, 2)` deja el puntero en | `tell()` | `// 110` | Registro escrito | Tamaño después |
|---:|---:|---:|---:|---:|---|---:|
| 1.ª | 0 bytes | 0 | 0 | 0 | Registro 0 (bytes 0–109) | 110 bytes |
| 2.ª | 110 bytes | 110 | 110 | 1 | Registro 1 (bytes 110–219) | 220 bytes |
| 3.ª | 220 bytes | 220 | 220 | 2 | Registro 2 (bytes 220–329) | 330 bytes |

Este patrón garantiza que el archivo nunca tenga "huecos" ni registros parciales, siempre que la escritura sea completa y el tamaño previo sea múltiplo de 110.

## 3.4 Lectura aleatoria por número de registro

### Código exacto (`gestor_archivos.py`, líneas 512–556)

```python
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
```

### Explicación paso a paso

| Paso | Operación | Efecto |
|---:|---|---|
| 1 | `_validar_numero_registro()` | Convierte el argumento a entero no negativo; rechaza booleanos, textos no numéricos y negativos. |
| 2 | `offset = numero * 110` | Calcula la posición absoluta del registro. |
| 3 | `open(..., "rb")` | Abre el archivo en modo binario de solo lectura. |
| 4 | `seek(offset)` | Salta directamente al byte de inicio del registro. |
| 5 | `tell()` | Confirma que el puntero quedó exactamente en `offset`. Si no coincide, se lanza un `OSError`. |
| 6 | `read(110)` | Lee exactamente 110 bytes, ni más ni menos. |
| 7 | `len(registro) != 110` | Si se leyeron menos bytes, el registro no existe o el archivo está incompleto; se lanza `ValueError`. |
| 8 | `desempaquetar_contacto()` | Convierte los 110 bytes en un diccionario con los cinco campos. |
| 9 | Se agregan `numero_registro` y `posicion_tell` | La interfaz usa estos metadatos para mostrar el monitor `SEEK`/`TELL`. |

### Ejemplo de lectura

| Registro solicitado | Offset calculado | `seek()` | `tell()` | `read(110)` devuelve |
|---:|---:|---:|---:|---|
| 0 | 0 | 0 | 0 | Bytes 0–109 |
| 1 | 110 | 110 | 110 | Bytes 110–219 |
| 2 | 220 | 220 | 220 | Bytes 220–329 |
| 5 en un archivo de 2 registros | 550 | 550 | 550 | 0 bytes → `ValueError` ("no existe o está incompleto") |
| 2 en un archivo de 225 bytes | 220 | 220 | 220 | 5 bytes → `ValueError` ("incompleto") |

## 3.5 Modificación en el lugar (in-place)

### Código exacto (`gestor_archivos.py`, líneas 589–631)

```python
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
```

> **Sobre la cita:** el bloque anterior reproduce exactamente las líneas 589–631 de `gestor_archivos.py`. Los bloques `except` (líneas 633–648) y el `return` final (líneas 650–653) se muestran por separado para no alargar la cita; no se ha cambiado ninguna instrucción del código.

Al final de la función se devuelve el contacto actualizado con sus metadatos:

```python
    actualizado = desempaquetar_contacto(registro)
    actualizado["numero_registro"] = numero
    actualizado["posicion_tell"] = posicion_actual
    return actualizado
```

### Explicación paso a paso

| Paso | Operación | Efecto |
|---:|---|---|
| 1 | Validar el número de registro y extraer los cinco campos | Garantiza que los datos de entrada estén completos y que el registro destino sea válido. |
| 2 | `empaquetar_contacto(...)` | Genera los nuevos 110 bytes, con el mismo formato y relleno. |
| 3 | `offset = numero * 110` | Calcula la posición del registro que se va a modificar. |
| 4 | `open(..., "r+b")` | Abre el archivo existente para lectura y escritura **sin truncar**. Es la diferencia clave con `"w+b"`, que borraría todo. |
| 5 | `seek(0, 2)` + `tell()` | Obtiene el tamaño actual sin leer el contenido. |
| 6 | `offset + 110 > tamano_archivo` | Comprueba que el registro exista. Si se intenta modificar el registro 5 en un archivo de 2 registros, se aborta antes de escribir. |
| 7 | `tamano_archivo % 110 != 0` | Comprueba que el archivo esté alineado. Si no, no se puede confiar en la aritmética de offsets. |
| 8 | `seek(offset)` | Salta exactamente al inicio del registro. |
| 9 | `tell()` | Confirma que el puntero quedó en `offset`. |
| 10 | `write(registro)` | Sobrescribe **solo** los 110 bytes de ese registro. Los bytes anteriores y posteriores no se tocan. |
| 11 | `escritos != 110` | Verifica que la escritura haya sido completa. |
| 12 | `flush()` | Fuerza el vaciado del búfer. |

### Antes y después de una modificación in-place

Supóngase un archivo con tres registros (330 bytes) y que se modifica el registro 1 (el segundo):

```text
ANTES
+----------------------+----------------------+----------------------+
| Registro 0 (0–109)   | Registro 1 (110–219) | Registro 2 (220–329) |
| José Núñez           | Ana                  | Luis                 |
+----------------------+----------------------+----------------------+
                              ^
                              |
                     se reescriben solo estos 110 bytes

DESPUÉS
+----------------------+----------------------+----------------------+
| Registro 0 (0–109)   | Registro 1 (110–219) | Registro 2 (220–329) |
| José Núñez           | Ana María            | Luis                 |
+----------------------+----------------------+----------------------+
       intacto              modificado              intacto

Tamaño antes: 330 bytes
Tamaño después: 330 bytes
```

El puntero, después de `write()`, queda en `offset + 110 = 220`; el archivo no se trunca ni se extiende. El tamaño total permanece igual. Los bytes del registro 0 y del registro 2 son idénticos antes y después.

> **Diferencia esencial:** `"r+b"` conserva el contenido y permite sobrescribir; `"w+b"` trunca el archivo a cero. Para modificar in-place se debe usar siempre `"r+b"`.

## 3.6 Búsqueda y modificación de alto nivel

La interfaz no trabaja directamente con offsets: llama a funciones de alto nivel que combinan el índice con el acceso aleatorio.

### Búsqueda por ID (`gestor_archivos.py`, líneas 881–906)

```python
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
```

Flujo:

```text
ID solicitado
    |
    v
validar_id()  ->  "2"
    |
    v
cargar_indice()  ->  {"1": 0, "2": 1}
    |
    v
indice["2"]  ->  1
    |
    v
offset = 1 × 110 = 110
    |
    v
seek(110) + read(110) + desempaquetar()
    |
    v
verificar que contacto["id"] == 2
    |
    v
devolver el contacto con numero_registro=1 y posicion_tell=110
```

### Modificación por ID (`gestor_archivos.py`, líneas 958–987)

```python
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

    # El contenido de contactos.dat cambió: se actualiza su hash SHA-256
    # inmediatamente después de la sobrescritura in-place.
    estado_hash = guardar_hash_sha256()

    if not estado_hash.get("ok"):
        actualizado["advertencia"] = _advertencia_hash(estado_hash)

    actualizado["ok"] = True
    return actualizado
```

Observaciones:

* Se permite una **actualización parcial**: si el usuario solo cambia la ciudad, los demás campos se conservan. El código parte del registro actual (`actual`) y solo reemplaza los campos presentes en `nuevos_datos`.
* El **ID no se puede cambiar** desde la modificación, porque es la clave primaria y el índice depende de él. Si se envía un ID distinto, se lanza `ValueError` antes de escribir.
* Después de sobrescribir, se actualiza el hash SHA-256 porque el contenido de `contactos.dat` cambió. Ese costo es independiente del acceso aleatorio (ver sección 4.9).

## 3.7 ¿Por qué no reescribir todo el archivo?

| Estrategia | Bytes leídos | Bytes escritos | Riesgo | Complejidad |
|---|---:|---:|---|---|
| Reescribir todo el archivo en un temporal y reemplazarlo | S | S | Se duplica el espacio temporal; si falla a mitad, hay que restaurar | O(S) |
| Leer todos los registros, modificar uno en memoria y reescribir | S | S | Se pierde la ventaja del acceso aleatorio; se puede corromper el archivo si falla la escritura | O(S) |
| **Sobrescribir in-place los 110 bytes del registro** | 0 (solo se verifica el tamaño) | **110** | Muy bajo: no se toca el resto del archivo | **O(1)** |

La modificación in-place es más eficiente y más segura para este formato: no hay que reconstruir el archivo, no se pierde el orden de los registros y no se afecta a los contactos vecinos. La contrapartida es que una escritura parcial podría dejar un registro a medio escribir; el código lo mitiga verificando el número de bytes escritos y haciendo `flush()`. Para una transacción totalmente atómica habría que escribir en un temporal y reemplazar, pero eso volvería a costar O(S).

## 3.8 Validaciones y evidencias de la prueba automática

La suite `pruebas/verificar_proyecto.py` instrumenta `open()`, `seek()`, `tell()` y `write()` para comprobar el comportamiento real de `modificar_por_id()`. Estas son algunas de las comprobaciones que pasaron:

| Comprobación | Resultado |
|---|---|
| Se abrió `contactos.dat` en modo `r+b` | OK |
| `seek()` se posicionó exactamente en el byte 110 | OK |
| Solo se escribieron 110 bytes en una operación | OK |
| La posición final del puntero es 220 | OK |
| El tamaño del archivo no cambió | OK |
| El registro anterior (bytes 0–109) quedó intacto | OK |
| El registro modificado (bytes 110–219) cambió | OK |
| El registro 1 contiene los nuevos datos | OK |
| `indice.json` no cambió al modificar | OK |
| El hash cambió tras la modificación y coincide con el SHA-256 real | OK |
| La verificación SHA-256 queda en estado íntegro | OK |
| Buscar de nuevo devuelve el dato modificado | OK |

Resultado global de la ejecución:

```text
==============================================================
Comprobaciones superadas: 161
Comprobaciones fallidas:  0
RESULTADO: TODAS LAS COMPROBACIONES PASARON
==============================================================
```

Estas evidencias son útiles para el PDF porque demuestran que la modificación no se limita a "parecer" in-place: el espía registra que se abrió en `r+b`, que se hizo un solo `seek(110)` y un solo `write(110)`, y que el tamaño y el registro vecino no cambiaron.

## 3.9 Casos límite y errores controlados

| Caso | Detección | Resultado |
|---|---|---|
| `contactos.dat` no existe al leer | `FileNotFoundError` | Mensaje: "No existe 'contactos.dat'. Agregue al menos un contacto primero." |
| `contactos.dat` no existe al modificar | `FileNotFoundError` | Mensaje: "No existe 'contactos.dat'. No hay ningún registro que sobrescribir." |
| Archivo sin permisos de lectura | `PermissionError` | Mensaje controlado; no se cae la interfaz |
| Archivo sin permisos de escritura | `PermissionError` | Mensaje controlado; no se modifica nada |
| Tamaño no múltiplo de 110 | `ValueError` | "El archivo 'contactos.dat' está corrupto: su tamaño (X bytes) no es múltiplo de 110." |
| Registro fuera de rango | `ValueError` | "No se puede sobrescribir el registro N: no existe..." |
| `seek()` no llega al offset esperado | `OSError` | "No se pudo posicionar el archivo en el byte X (tell() = Y)." |
| `write()` escribe menos de 110 bytes | `OSError` | "Se escribieron X bytes en lugar de 110." |
| Registro incompleto al leer | `ValueError` | "El registro N no existe o está incompleto..." |
| UTF-8 inválido en un campo | `ValueError` | "El campo 'X' no contiene UTF-8 válido." |
| ID almacenado no numérico | `ValueError` | "El ID almacenado no es un entero válido..." |
| Índice apunta a un registro con otro ID | Resultado `ok=False` | "El índice está inconsistente..." |

## 3.10 Tabla resumen de operaciones

| Operación | Modo de apertura | `seek()` | `tell()` | Bytes leídos | Bytes escritos | Efecto en el tamaño |
|---|---|---|---:|---:|---:|---|
| Agregar | `r+b` (o `w+b` si no existe) | `seek(0, 2)` | Sí, para obtener el tamaño | 0 | 110 | +110 |
| Buscar | `rb` | `seek(n × 110)` | Sí, para verificar | 110 | 0 | 0 |
| Modificar (solo la sobrescritura) | `r+b` | `seek(0, 2)` y luego `seek(n × 110)` | Sí, dos veces | 0 | 110 | 0 |
| Reconstruir índice | `rb` | No usa `seek` explícito; lee secuencialmente | No | 110 × n | 0 | 0 |

> **Nota 1:** `reconstruir_indice()` es la única operación que recorre todo el archivo, y solo se usa como mecanismo de reparación cuando `indice.json` falta o está corrupto. La búsqueda normal no recorre el archivo.

> **Nota 2:** en el flujo de alto nivel, `modificar_por_id()` primero lee el registro actual con `leer_registro_aleatorio()` (110 bytes) para conservar los campos que no se envían; la sobrescritura en sí no lee, solo escribe 110 bytes. Por eso la tabla distingue "Modificar (solo la sobrescritura)".

---

# 4. Índice primario `indice.json` y complejidad O(1) vs. O(n)

## 4.1 ¿Qué es un índice primario?

Un **índice primario** es una estructura auxiliar que asocia el valor de la clave primaria de un registro con la ubicación física de ese registro. En este proyecto:

* La **clave primaria** es el `id` del contacto. Es único: `agregar_contacto()` rechaza los IDs duplicados.
* La **ubicación física** es el número de registro dentro de `contactos.dat`.
* La estructura auxiliar es un objeto JSON con pares `"id": numero_registro`.

Sin índice, para encontrar el contacto con ID 25 habría que recorrer los registros uno por uno, leerlos, desempacarlos y comparar el ID. Con índice, basta una consulta al diccionario para obtener el número de registro y luego un `seek()` directo.

## 4.2 Estructura y ejemplo

`indice.json` es un objeto JSON en UTF-8. Las claves son los IDs como cadenas (JSON exige que las claves de un objeto sean cadenas) y los valores son números de registro (enteros no negativos):

```json
{
  "1": 0,
  "2": 1,
  "25": 2
}
```

Interpretación:

| ID | Número de registro | Offset calculado | Bytes del registro |
|---:|---:|---:|---|
| 1 | 0 | 0 × 110 = 0 | 0–109 |
| 2 | 1 | 1 × 110 = 110 | 110–219 |
| 25 | 2 | 2 × 110 = 220 | 220–329 |

El archivo se guarda con `json.dump(..., ensure_ascii=False, indent=2)`, se ordena numéricamente por ID y termina con un salto de línea. El orden numérico evita el orden lexicográfico confuso (`"1"`, `"10"`, `"2"`); el resultado es `"1"`, `"2"`, `"10"`.

### Código exacto de guardado (`gestor_archivos.py`, líneas 211–222)

```python
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
```

### ¿Por qué se escribe en un archivo temporal?

Si el programa se interrumpe mientras escribe `indice.json` directamente, el archivo podría quedar truncado o con JSON inválido. La estrategia es:

1. Escribir todo el contenido en `indice.json.tmp`.
2. Hacer `flush()` para vaciar el búfer.
3. Reemplazar el original con `os.replace()`, que es atómico en el mismo sistema de archivos.
4. En el bloque `finally`, borrar el temporal si algo falló antes del reemplazo.

Así, o se conserva el índice anterior completo, o se tiene el nuevo completo; nunca un JSON a medias. La misma técnica se usa para `contactos.sha256`, para el ZIP y para el JSON exportado.

## 4.3 ¿Por qué se guarda el número de registro y no el offset?

Se podría guardar directamente el offset en bytes:

```json
{
  "1": 0,
  "2": 110,
  "25": 220
}
```

El proyecto guarda el **número de registro** por varias razones:

* El offset siempre se puede derivar con una multiplicación: `offset = numero_registro × 110`.
* El número de registro es un dato lógico y estable; el offset es una consecuencia del tamaño fijo.
* Si en el futuro se cambiara el tamaño del registro (por ejemplo, a 120 bytes), el índice seguiría siendo válido y solo cambiaría la constante de multiplicación. Si se guardaran offsets, habría que migrar todo el índice.
* Los números de registro son más pequeños y legibles.
* La validación es más simple: se comprueba que `numero_registro < total_registros`, en lugar de comprobar que el offset sea múltiplo de 110 y esté dentro del archivo.

## 4.4 Ciclo de vida del índice

### 4.4.1 Carga y normalización

`cargar_indice()` lee el JSON y lo normaliza:

* Las claves se convierten a cadenas canónicas sin ceros a la izquierda. `"007"` se convierte en `"7"`.
* Los valores deben ser enteros no negativos; los booleanos se rechazan (en Python, `bool` es subclase de `int`, y `True` no debe aceptarse como número de registro).
* No se permiten IDs duplicados.
* Se ordena numéricamente por ID.

### 4.4.2 Reconstrucción automática

Si `indice.json` no existe, está vacío, no es JSON válido, tiene una estructura incorrecta o tiene menos entradas que registros en `contactos.dat`, el programa llama a `reconstruir_indice()`. Esta función recorre `contactos.dat` en bloques de 110 bytes, desempaca cada registro y construye el mapa:

```python
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
```

La **lectura** del archivo durante la reconstrucción es O(n): se lee todo una vez. El guardado posterior del índice ordenado añade O(n log n) por el `sorted()` de `_normalizar_indice()` y `guardar_indice()`. En conjunto, la reconstrucción es O(n log n), pero solo ocurre cuando el índice falta o está dañado; en operación normal no se recorre el archivo. Es un costo aceptable para una reparación.

### 4.4.3 Verificación de coherencia

Después de normalizar, `cargar_indice()` compara la cantidad de entradas del índice con la cantidad de registros del archivo:

```python
        total_registros = tamano_archivo // TAMANO_REGISTRO

        if len(normalizado) < total_registros:
            # Faltan entradas en el índice: se recuperan desde los registros.
            return reconstruir_indice()

        if len(normalizado) > total_registros:
            raise IndiceCorruptoError(
                "El índice está desincronizado: contiene {} entrada(s), pero "
                "'{}' solo tiene {} registro(s).".format(
                    len(normalizado), ARCHIVO_CONTACTOS, total_registros
                )
            )
```

* Si el índice tiene **menos** entradas que registros, se reconstruye desde los datos (no se pierde ningún contacto).
* Si tiene **más** entradas que registros, se lanza un error: el índice apunta a registros que ya no existen. Es mejor detenerse que adivinar.
* Si el tamaño del archivo no es múltiplo de 110, también se lanza un error: la estructura está rota.

## 4.5 Algoritmo de búsqueda con índice

```text
Entrada: id_buscado
1. Validar y normalizar el ID: id_buscado -> "25"
2. Cargar el índice: indice = {"1": 0, "2": 1, "25": 2}
3. Si "25" no está en indice:
       devolver "No existe un contacto con el ID 25"
4. numero_registro = indice["25"]  -> 2
5. offset = 2 × 110 = 220
6. Abrir contactos.dat en "rb"
7. seek(220)
8. verificar tell() == 220
9. leer 110 bytes
10. desempaquetar el registro
11. verificar que el ID del registro sea 25
12. devolver el contacto con numero_registro=2 y posicion_tell=220
```

La comparación con la búsqueda secuencial es directa:

```text
Búsqueda secuencial (sin índice), peor caso:
para numero_registro = 0 hasta n-1:
    offset = numero_registro × 110
    seek(offset)
    leer 110 bytes
    desempaquetar
    si id == id_buscado:
        devolver
# Hasta n lecturas y n desempacados

Búsqueda con índice primario:
numero_registro = indice["25"]   # consulta al diccionario
seek(numero_registro × 110)
leer 110 bytes
desempaquetar
# Una sola lectura y un solo desempacado
```

## 4.6 ¿Por qué la búsqueda con índice es O(1)?

La clave está en la estructura de datos que se usa para el índice: un **diccionario** de Python (`dict`), que internamente es una **tabla hash**.

* Al construir el diccionario, cada clave se pasa por una función hash que produce un número. Ese número determina una "cubeta" (bucket) donde se guarda el valor.
* Para buscar una clave, Python calcula su hash y va directamente a la cubeta; no recorre todas las claves.
* En promedio, el número de claves en una cubeta es constante, por lo que la búsqueda es **O(1) promedio**.
* En el peor caso teórico, si todas las claves cayeran en la misma cubeta, la búsqueda sería O(m). En la práctica, con claves cortas y una buena función hash, el comportamiento es O(1) promedio.

Además, el acceso al archivo también es O(1):

* `seek(offset)` mueve el puntero directamente; no recorre los bytes anteriores.
* `read(110)` lee una cantidad fija de bytes.
* `desempaquetar_contacto()` procesa cinco campos de longitudes fijas; el tiempo no depende de `n`.

Por eso, la localización del registro es de tiempo constante: no importa si el archivo tiene 10, 1,000 o 1,000,000 de registros, la cantidad de lecturas y desempacados para encontrar un ID es la misma: **una**.

## 4.7 Comparación de volúmenes: O(1) vs. O(n)

Sea `n` la cantidad de registros. En la búsqueda secuencial, en el peor caso se leen los `n` registros; en promedio, `n/2` si el ID buscado está distribuido uniformemente. En la búsqueda con índice, se lee **un solo registro** de 110 bytes (más la carga del índice, que se analiza en la sección 4.8).

| Cantidad de contactos (n) | Búsqueda secuencial: lecturas (peor caso) | Bytes leídos (110 × n) | Búsqueda con índice: lecturas | Bytes leídos del archivo de datos | Reducción de datos leídos |
|---:|---:|---:|---:|---:|---:|
| 10 | 10 | 1,100 B (~1.1 KB) | 1 | 110 B | ~10× |
| 100 | 100 | 11,000 B (~10.7 KB) | 1 | 110 B | ~100× |
| 1,000 | 1,000 | 110,000 B (~107 KB) | 1 | 110 B | ~1,000× |
| 10,000 | 10,000 | 1,100,000 B (~1.05 MB) | 1 | 110 B | ~10,000× |
| 100,000 | 100,000 | 11,000,000 B (~10.5 MB) | 1 | 110 B | ~100,000× |

La tabla muestra el crecimiento lineal de la búsqueda secuencial frente al acceso constante del índice. En un archivo de 100,000 contactos, la búsqueda secuencial en el peor caso lee más de 10 MB y desempaca 100,000 registros; la búsqueda con índice lee 110 bytes y desempaca un solo registro (sin contar el costo de cargar el índice, que se discute a continuación).

### Costo aproximado del archivo de índice

| Cantidad de contactos | Entradas en `indice.json` | Tamaño aproximado del JSON (≈25 bytes/entrada) |
|---:|---:|---:|
| 100 | 100 | ~2.5 KB |
| 1,000 | 1,000 | ~25 KB |
| 10,000 | 10,000 | ~250 KB |
| 100,000 | 100,000 | ~2.5 MB |

El índice ocupa espacio adicional, pero es mucho más pequeño que el archivo de datos (cada entrada es un ID corto y un número, no un registro de 110 bytes con cinco campos). Es el clásico **trade-off espacio/tiempo**: se gasta un poco más de espacio para ahorrar tiempo de búsqueda.

## 4.8 Nota de rigor: el costo de cargar el índice

Para la exposición del laboratorio, la idea central es correcta: **la búsqueda primaria sobre el archivo de datos es O(1) promedio**, porque el diccionario y el `seek()` no dependen de `n`. Sin embargo, en esta implementación hay un detalle que conviene explicar con precisión:

`buscar_por_id()` llama a `cargar_indice()` en cada invocación. `cargar_indice()` hace lo siguiente:

1. Abre y parsea `indice.json` con `json.load()`: **O(m)**.
2. Normaliza y valida las `m` entradas: **O(m)**.
3. Las ordena numéricamente con `sorted(...)`: **O(m log m)**.
4. Consulta el diccionario: **O(1) promedio**.
5. Hace `seek()` y `read(110)`: **O(1)**.

Por lo tanto, el costo total de una llamada a `buscar_por_id()` en esta implementación es **O(m log m)**, no O(1) puro, porque se recarga y se reordena el índice cada vez. Como en operación normal `m = n`, eso es O(n log n) en el peor caso. La parte que es O(1) es la **localización y lectura del registro**; la carga del índice es un costo de infraestructura.

### ¿Cómo se justifica entonces la afirmación "O(1)"?

En el análisis de estructuras de datos, se dice que una búsqueda en una tabla hash es O(1) promedio **asumiendo que la tabla ya está construida en memoria**. El índice es esa tabla. La carga desde disco es una operación de mantenimiento que se puede hacer una sola vez.

Para que la implementación sea estrictamente O(1) por búsqueda, basta con **cachear el índice en memoria**:

* Cargarlo una vez al iniciar la aplicación.
* Mantener el diccionario en un atributo del gestor o de la interfaz.
* Actualizarlo después de cada alta (agregar una entrada) y después de una reconstrucción.
* No volver a leer `indice.json` en cada búsqueda.

Con esa optimización, la búsqueda sería: consulta al diccionario O(1) + `seek()`/`read()` O(1) = **O(1) promedio**. El proyecto actual prioriza la simplicidad y la tolerancia a cambios externos (si el índice se edita desde fuera, se detecta y se repara), a costa de recargarlo. Para el tamaño de una agenda de laboratorio, la diferencia es despreciable; para millones de contactos, el caché sería obligatorio.

> **Cómo redactarlo en el PDF sin que sea incorrecto:**
>
> "La búsqueda con el índice primario es O(1) promedio en lo que respecta a la localización del registro: se consulta una tabla hash y se hace un `seek()` directo, sin recorrer el archivo. La carga del índice desde `indice.json` es un costo aparte, O(m log m) en esta implementación, que se puede eliminar manteniendo el índice en memoria. Aun sin esa optimización, el ahorro en bytes leídos y en desempacados frente a la búsqueda secuencial es muy grande, porque se evita leer y desempacar los n registros del archivo de datos."

Esta formulación es técnicamente correcta y responde a la expectativa del laboratorio (O(1) vs. O(n)), sin ocultar el costo de la carga del índice. Dicho con precisión: la **localización** es O(1); la **llamada completa** a `buscar_por_id()` en esta implementación es O(m log m) por la recarga y el ordenamiento del JSON; con el índice cacheado en memoria, la llamada completa vuelve a ser O(1) promedio. Si se compara estrictamente la implementación actual con una búsqueda secuencial, la ventaja asintótica no está en la carga del índice sino en el acceso directo; la ventaja práctica está en que se evita leer y desempacar n registros, y se vuelve O(1) al cachear.

## 4.9 Costos de mantenimiento del índice

| Operación | Acceso al archivo de datos | Trabajo sobre el índice | Hash SHA-256 | Complejidad total aproximada |
|---|---|---|---|---|
| **Buscar por ID** | 1 `seek` + 1 `read(110)` | Cargar, normalizar y ordenar `indice.json` | No | O(m log m) en esta implementación; O(1) si el índice está en memoria |
| **Agregar** | 1 `seek(0,2)` + 1 `write(110)` | Verificar duplicado, validar todas las entradas contra los datos, insertar y guardar | Sí, sobre todo el archivo | O(S + m log m) |
| **Modificar** | 1 `seek` + 1 `write(110)` | Cargar y validar el índice; el índice no cambia | Sí, sobre todo el archivo | O(S + m log m) |
| **Reconstruir índice** | Lectura secuencial de los n registros | Construir el mapa y guardarlo | No | O(n log n) por el ordenamiento al guardar |
| **Crear respaldo ZIP** | Lectura completa de `contactos.dat` e `indice.json` | Compresión DEFLATE | No | O(S) |

Dos observaciones importantes:

1. **El hash SHA-256 se recalcula sobre todo `contactos.dat` después de cada alta o modificación.** Eso hace que la operación completa sea O(S), aunque la escritura aleatoria sea O(1). Es un costo deliberado: la integridad se paga leyendo el archivo completo. Si se quisiera mantener O(1), habría que usar un hash incremental o calcularlo solo bajo demanda; el proyecto prioriza la verificación inmediata.
2. **`_validar_indice_contra_datos()` recorre todas las entradas del índice antes de agregar un contacto**, y para cada una hace `seek()` y `read(110)` para comprobar que el registro contiene el ID esperado. Es una validación O(m) que evita dejar registros huérfanos si el índice fue editado a mano. Se ejecuta solo en el alta, no en la búsqueda.

## 4.10 ¿Por qué no usar búsqueda binaria?

La búsqueda binaria requiere que los registros estén **ordenados por la clave de búsqueda**. En este proyecto, los contactos se agregan al final en el orden en que el usuario los ingresa; el archivo no está ordenado por ID. Para usar búsqueda binaria habría que:

* Mantener el archivo ordenado por ID después de cada alta (lo que implicaría mover registros y actualizar offsets).
* O construir y mantener un archivo ordenado aparte.

La búsqueda binaria sería O(log n), mejor que O(n) pero peor que O(1). El índice primario evita reordenar el archivo y ofrece O(1) promedio. Además, el índice permite que el orden físico de los registros sea el orden de inserción, lo que simplifica las altas.

## 4.11 Salvaguardas de consistencia

El índice es una estructura auxiliar: si se desincroniza del archivo de datos, las búsquedas podrían devolver el contacto equivocado o fallar. El proyecto implementa varias defensas:

| Salvaguarda | Función | Qué evita |
|---|---|---|
| Normalización de claves y valores | `_normalizar_indice()` | IDs con formato raro, valores negativos, duplicados |
| Reconstrucción si falta o está corrupto | `cargar_indice()` / `reconstruir_indice()` | Perder contactos por un JSON dañado |
| Reconstrucción si faltan entradas | `cargar_indice()` | Índice incompleto que oculte contactos |
| Error si sobran entradas | `cargar_indice()` | Índice que apunte a registros inexistentes |
| Validación completa antes de agregar | `_validar_indice_contra_datos()` | Registros huérfanos por un mapeo incorrecto |
| Verificación del ID al buscar/modificar | `buscar_por_id()` / `modificar_por_id()` | Devolver o modificar el contacto equivocado |
| Rechazo de IDs duplicados | `agregar_contacto()` | Dos contactos con la misma clave primaria |
| Rollback del alta si falla el índice | `_deshacer_ultimo_registro()` | Contacto escrito pero ausente del índice |
| Escritura atómica del índice | `guardar_indice()` | JSON a medias si el proceso falla |

### Rollback del alta

`agregar_contacto()` escribe primero el registro al final y luego guarda el índice. Si el guardado del índice falla (por ejemplo, por permisos), el registro quedaría escrito pero invisible para las búsquedas. Para evitarlo, la función recorta el archivo a la posición anterior:

```python
def _deshacer_ultimo_registro(posicion_bytes: int) -> None:
    """Recorta ``contactos.dat`` si el índice no se pudo actualizar."""
    try:
        with open(ARCHIVO_CONTACTOS, "r+b") as archivo:
            archivo.truncate(posicion_bytes)
    except OSError:
        pass
```

`truncate(posicion_bytes)` elimina los bytes escritos a partir de esa posición. Si el recorte también falla, se conserva el error original; es una compensación de "mejor esfuerzo".

## 4.12 Comparación conceptual: índice primario vs. búsqueda secuencial

| Aspecto | Búsqueda secuencial | Búsqueda con índice primario |
|---|---|---|
| Estructura necesaria | Ninguna | `indice.json` (tabla hash en memoria) |
| Lecturas del archivo de datos | Hasta n | 1 |
| Bytes leídos | Hasta 110 × n | 110 |
| Desempacados | Hasta n | 1 |
| Complejidad de la localización | O(n) | O(1) promedio |
| Requiere ordenar el archivo | No | No |
| Espacio adicional | 0 | O(n) para el índice |
| Costo de alta | O(1) para escribir + hash | O(1) para escribir + validación/índice + hash |
| Costo de modificación | O(1) si se conoce el registro | O(1) si se conoce el registro |
| Tolerancia a ediciones externas | Alta (siempre lee el dato real) | Media: hay que validar/repasar el índice |
| Ideal para | Archivos pequeños o sin clave única | Búsquedas repetidas por clave única |

## 4.13 Texto sugerido para el PDF (sección de índice)

> El índice primario se almacena en `indice.json` como un objeto que asocia cada ID con su número de registro. La búsqueda de un contacto consulta primero ese diccionario, obtiene el número de registro y calcula el offset con `numero_registro × 110`. Luego hace un `seek()` directo y lee solo 110 bytes. La consulta al diccionario es O(1) promedio porque Python implementa `dict` como una tabla hash; el acceso al archivo también es O(1) porque `seek()` no recorre los bytes anteriores. En cambio, la búsqueda secuencial tendría que leer y desempacar hasta n registros, con costo O(n). Para 1,000 contactos, la diferencia es de hasta 110,000 bytes leídos frente a 110 bytes; para 100,000 contactos, de 11 MB frente a 110 bytes. El índice ocupa espacio adicional y debe mantenerse sincronizado, pero el ahorro en tiempo de búsqueda es considerable.

---

# 5. Integridad SHA-256 y respaldo ZIP

## 5.1 ¿Qué es SHA-256?

SHA-256 (Secure Hash Algorithm 256 bits) es una función hash criptográfica definida en el estándar FIPS 180-4. Recibe un mensaje de cualquier longitud y produce un **resumen de 256 bits**, que se representa como **64 caracteres hexadecimales** (cada carácter hexadecimal representa 4 bits; 64 × 4 = 256).

Propiedades relevantes para este proyecto:

* **Determinista:** el mismo contenido produce siempre el mismo hash.
* **Efecto avalancha:** un cambio mínimo en el contenido (incluso un solo bit) produce un hash completamente distinto, con aproximadamente la mitad de los bits cambiados.
* **Unidireccional:** no es factible reconstruir el contenido a partir del hash.
* **Resistente a colisiones:** no es factible encontrar dos contenidos distintos con el mismo hash en la práctica.

Estas propiedades permiten usar el hash como una **huella digital** del archivo: si el contenido cambia, el hash cambia. No se necesita comparar byte por byte para detectar una alteración; basta comparar 64 caracteres.

> **Importante:** SHA-256 detecta alteraciones accidentales o externas, pero no es una firma digital. Si un atacante modifica `contactos.dat` y también actualiza `contactos.sha256`, la verificación dará "íntegra". Para una seguridad fuerte habría que firmar el hash con una clave privada o guardarlo en un medio de solo lectura. Esta limitación se discute en la sección 5.6.

## 5.2 Implementación del cálculo

### Código exacto (`utilidades_sistema.py`, líneas 54–63)

```python
def _calcular_sha256(ruta: str) -> str:
    """Calcula el SHA-256 de un archivo leyéndolo por bloques."""
    sha = hashlib.sha256()
    with open(ruta, "rb") as archivo:
        while True:
            bloque = archivo.read(BLOQUE_LECTURA)
            if not bloque:
                break
            sha.update(bloque)
    return sha.hexdigest()
```

con

```python
BLOQUE_LECTURA = 64 * 1024  # 64 KiB por lectura al calcular el hash
```

La lectura por bloques de 64 KiB evita cargar el archivo completo en memoria. Para un archivo de 110 MB, se leerían 1,720 bloques de 64 KiB, actualizando el hash incrementalmente. El resultado es el mismo que calcularlo de una sola vez, pero con un uso de memoria constante.

### Guardado del hash

`guardar_hash_sha256()` calcula el hash y lo escribe en `contactos.sha256` con UTF-8 y sin salto de línea:

```python
        with open(
            ruta_temporal, "w", encoding="utf-8", newline="\n"
        ) as archivo:
            archivo.write(hash_actual)
            archivo.flush()

        os.replace(ruta_temporal, ARCHIVO_HASH)
```

El archivo resultante contiene exactamente 64 caracteres hexadecimales en minúsculas, sin BOM y sin salto de línea. La verificación hace `.strip().lower()` por si el archivo fue editado y quedó con espacios o mayúsculas.

## 5.3 ¿Cuándo se actualiza el hash?

| Evento | ¿Se actualiza `contactos.sha256`? | Código |
|---|---|---|
| Alta de un contacto | Sí, después de escribir y actualizar el índice | `agregar_contacto()` llama a `guardar_hash_sha256()` |
| Modificación in-place | Sí, inmediatamente después de sobrescribir | `modificar_por_id()` llama a `guardar_hash_sha256()` |
| Búsqueda | No | El archivo no cambia |
| Reconstrucción del índice | No | Solo cambia `indice.json`, no `contactos.dat` |
| Creación de respaldo ZIP | No | El ZIP es una copia, no modifica el original |
| Edición externa con un editor | **No** | Por eso se detecta la alteración |

La lógica es: el hash representa el último estado **conocido y generado por la aplicación**. Cualquier cambio que no pase por las funciones de alta o modificación deja el hash desactualizado y, por lo tanto, se detecta.

Si el alta o la modificación se guarda pero el hash no se puede actualizar (por ejemplo, porque `contactos.sha256` es de solo lectura), la función devuelve una **advertencia** en lugar de fallar el alta:

```python
        "El contacto se guardó en '{}', pero no se pudo actualizar '{}': {}"
```

En ese caso, el dato queda guardado pero la siguiente verificación detectará que el hash no corresponde; el usuario debe corregir los permisos y regenerar el hash. La suite de verificación cubre este caso y comprueba que la advertencia aparezca y que la integridad se recupere al regenerar el hash.

## 5.4 Verificación y alerta

### Comparación (`utilidades_sistema.py`, líneas 221–237)

```python
        if hash_actual == hash_guardado:
            return {
                "integro": True,
                "mensaje": (
                    "Integridad verificada: '{}' coincide con el hash "
                    "guardado.".format(ARCHIVO_CONTACTOS)
                ),
                "hash_actual": hash_actual,
                "hash_guardado": hash_guardado,
            }

        return {
            "integro": False,
            "mensaje": MENSAJE_ALERTA,
            "hash_actual": hash_actual,
            "hash_guardado": hash_guardado,
        }
```

con

```python
MENSAJE_ALERTA = (
    "ALERTA: El archivo contactos.dat fue modificado fuera de la aplicación."
)
```

### Alerta en la interfaz (`src/interfaz/brutalista.py`, líneas 1145-1155)

```python
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
```

La misma alerta se muestra en dos momentos:

* **Al iniciar la aplicación**, mediante `self.after(150, self._verificar_integridad_inicial)`.
* **Al usar Herramientas > Verificar integridad**, mediante `accion_verificar_integridad()`.

El diálogo es un `messagebox.showwarning` (icono amarillo de advertencia, no de error). Muestra el mensaje de alerta, el hash actual calculado en ese momento, el hash guardado en `contactos.sha256` y el nombre del archivo. Además, la interfaz escribe una línea `[ALERTA]` en la consola de registro y cambia el monitor a `ESTADO: INTEGRIDAD`.

## 5.5 Respaldo ZIP

### Código exacto (`utilidades_sistema.py`, líneas 324–340)

```python
        with zipfile.ZipFile(
            ruta_temporal,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
        ) as respaldo:
            for ruta in archivos:
                respaldo.write(ruta, arcname=os.path.basename(ruta))

        os.replace(ruta_temporal, ruta_zip)
        tamano_zip = os.path.getsize(ruta_zip)

        if tamano_original > 0:
            porcentaje = round(
                (1 - (tamano_zip / tamano_original)) * 100, 2
            )
        else:
            porcentaje = 0.0
```

### Contenido del ZIP

| Archivo | ¿Siempre se incluye? | Nombre dentro del ZIP |
|---|---|---|
| `contactos.dat` | Sí; si no existe, el respaldo falla con `ok=False` | `contactos.dat` |
| `indice.json` | Sí, si existe; si no, se advierte que faltó | `indice.json` |
| `contactos.sha256` | **No** | — |

El ZIP no incluye `contactos.sha256`. Para una restauración completa, conviene copiar también ese archivo por separado o regenerarlo después de restaurar. Esta es una mejora recomendable (ver sección 5.6).

### Cálculo del porcentaje de compresión

```text
porcentaje = (1 - tamano_zip / tamano_original) × 100
```

* Si el ZIP es más pequeño que los archivos originales, el porcentaje es positivo (ahorro).
* Si el ZIP es más grande, el porcentaje es negativo. Esto es normal en archivos muy pequeños: el ZIP agrega cabeceras, directorio central y metadatos. Por ejemplo, dos archivos de 220 y 30 bytes pueden producir un ZIP de 500 bytes; el porcentaje sería negativo.
* El resultado incluye `ahorro_bytes = tamano_original - tamano_zip`, que también puede ser negativo.

El porcentaje de compresión **no es un indicador de integridad**. Para comparar dos respaldos se deben comparar los hashes de los archivos extraídos, no los tamaños de los ZIP.

## 5.6 Limitaciones y mejoras

| Limitación | Consecuencia | Mejora posible |
|---|---|---|
| El hash se guarda junto a los datos | Un atacante con permiso de escritura puede actualizar ambos | Guardar el hash en una ubicación de solo lectura o firmarlo digitalmente |
| Si `contactos.sha256` no existe, la verificación se considera "estado inicial" | Borrar el hash desactiva la detección | Tratar la ausencia del hash como sospechosa si `contactos.dat` existe |
| El ZIP no incluye `contactos.sha256` | Una restauración solo desde el ZIP puede dejar el hash desactualizado | Incluir el hash en el ZIP o regenerarlo al restaurar |
| El ZIP no está cifrado | Cualquiera con acceso al archivo puede leerlo | Usar cifrado o un contenedor seguro |
| El hash se recalcula sobre todo el archivo | El alta y la modificación son O(S) | Hash incremental o cálculo bajo demanda |
| El índice se recarga en cada búsqueda | La búsqueda no es O(1) estricta | Cachear el índice en memoria |
| No hay operación de eliminación | Los contactos solo se agregan o modifican | Implementar baja lógica o compactación |

## 5.7 Texto sugerido para el PDF (sección de integridad)

> Después de cada alta o modificación, la aplicación calcula el SHA-256 de `contactos.dat` leyéndolo en bloques de 64 KiB y guarda el resultado en `contactos.sha256`. Al iniciar, la aplicación vuelve a calcular el hash y lo compara con el guardado. Si el archivo fue alterado fuera de la aplicación, los hashes no coinciden y se muestra un `messagebox` con el título "ALERTA DE INTEGRIDAD", el hash actual y el hash guardado. Este mecanismo detecta cambios de contenido aunque el tamaño del archivo se mantenga igual, porque el hash depende de los bytes, no de la longitud. El respaldo ZIP permite conservar una copia del estado anterior y compararla con el estado posterior, lo que aporta evidencia adicional de la alteración.

---

# 6. Guía paso a paso para la prueba manual y las capturas

## 6.1 Objetivo de la prueba

Demostrar, con evidencia visual, que:

1. La aplicación calcula y guarda un SHA-256 de `contactos.dat`.
2. Si el archivo se altera externamente con un editor de texto, la aplicación detecta la diferencia y muestra la alerta **"ALERTA DE INTEGRIDAD"**.
3. La alteración se detecta aunque el tamaño del archivo no cambie, porque el hash depende del contenido.
4. El respaldo ZIP tomado **antes** de la alteración contiene los bytes originales, y el tomado **después** contiene los bytes alterados; la comparación de hashes lo demuestra.
5. Al restaurar el archivo original, la verificación vuelve a ser correcta.

## 6.2 Materiales y recomendaciones previas

| Elemento | Detalle |
|---|---|
| Proyecto | Carpeta `Proyecto 2` con todos los `.py` |
| Python | 3.x con Tkinter instalado |
| Editor de texto | **Notepad++** (recomendado) o **HxD** (editor hexadecimal, para una edición exacta) |
| Terminal | PowerShell en Windows |
| Capturas | Herramienta de recortes (`Win + Shift + S`) o `Alt + PrintScreen` |
| Datos de prueba | Contactos ficticios, sin información personal real |
| Respaldo previo | Copia de la carpeta o del archivo antes de empezar |

> **Recomendación fuerte:** haga la prueba en una **copia** de la carpeta del proyecto (por ejemplo, `Proyecto 2 - prueba`) para no arriesgar los datos reales. Todos los comandos de esta guía suponen que la terminal está abierta en la carpeta del proyecto:
>
> ```powershell
> cd "C:\Users\Usuario\Documents\Universidad\Cuarto Semestre\Manejo_e_Implementación_de_Archivos\Proyecto 2"
> ```

## 6.3 Fase 0: verificar el estado inicial

1. Abra una terminal en la carpeta del proyecto.
2. Compruebe que existen los archivos principales:

```powershell
Get-ChildItem .\contactos.dat, .\indice.json, .\contactos.sha256 -ErrorAction SilentlyContinue |
    Select-Object Name, Length, LastWriteTime
```

Si alguno no existe, primero cree al menos un contacto con la aplicación (fase 1).

3. Compruebe que `contactos.dat` está alineado:

```powershell
$tamano = (Get-Item .\contactos.dat).Length
"Tamaño: $tamano bytes"
"Registros: $([math]::Floor($tamano / 110))"
"¿Alineado? $($tamano % 110 -eq 0)"
```

Resultado esperado para el ejemplo de dos contactos: `220 bytes`, `2 registros`, `¿Alineado? True`.

## 6.4 Fase 1: crear la agenda de prueba

1. Ejecute la aplicación:

```powershell
python main.py
```

2. Agregue dos contactos ficticios usando el formulario y el botón **AGREGAR**:

| Campo | Contacto 1 | Contacto 2 |
|---|---|---|
| ID | `1` | `2` |
| Nombre | `José Núñez` | `Ana` |
| Teléfono | `8888-1234` | `7777-0000` |
| Correo | `jose.nunez@correo.com` | `ana@correo.com` |
| Ciudad | `San José` | `Cartago` |

3. Cierre la aplicación con la **X** de la ventana y confirme el diálogo de salida ("¿Desea cerrar la agenda de contactos?"). No es necesario modificar nada más.

4. Verifique el estado inicial:

```powershell
Get-ChildItem .\contactos.dat, .\indice.json, .\contactos.sha256 |
    Select-Object Name, Length, LastWriteTime

Get-Content .\indice.json
Get-Content .\contactos.sha256
```

Resultados esperados:

* `contactos.dat`: **220 bytes** = 2 registros × 110.
* `indice.json`: un objeto con `"1": 0` y `"2": 1`.
* `contactos.sha256`: **64 caracteres hexadecimales** (sin salto de línea, por eso el archivo mide 64 bytes).

5. Guarde una **huella digital** del estado inicial:

```powershell
$hash = (Get-FileHash .\contactos.dat -Algorithm SHA256).Hash.ToLower()
[System.IO.File]::WriteAllText((Join-Path $PWD "hash_antes.txt"), $hash)
Get-Content .\hash_antes.txt
```

Esta huella se usará al final para comprobar la restauración.

## 6.5 Fase 2: crear el respaldo ZIP "antes"

1. Abra la aplicación y use **Herramientas > Crear respaldo ZIP**.
2. Cierre el diálogo informativo.
3. Copie el ZIP generado a un nombre que no se sobrescriba:

```powershell
Copy-Item .\respaldo_agenda.zip .\respaldo_antes.zip -Force
Get-Item .\respaldo_antes.zip | Select-Object Name, Length, LastWriteTime
```

> **¿Por qué copiarlo?** Porque `crear_respaldo_zip()` siempre escribe en `respaldo_agenda.zip` y reemplaza el anterior. Si no guarda una copia con otro nombre, el segundo respaldo borraría el primero y perdería la comparación.

4. Guarde también una copia del archivo de datos original:

```powershell
Copy-Item .\contactos.dat .\contactos_original.dat -Force
```

5. (Opcional) Guarde una copia del índice:

```powershell
Copy-Item .\indice.json .\indice_original.json -Force
```

6. Compruebe el contenido del ZIP:

```powershell
tar -tf .\respaldo_antes.zip
```

Debe listar `contactos.dat` e `indice.json`.

## 6.6 Fase 3: alterar `contactos.dat` con un editor de texto

### 6.6.1 Regla de oro

Para que la prueba demuestre que la alerta se debe al **contenido** y no al **tamaño**, modifique **un solo carácter ASCII por otro de la misma longitud**. Así el archivo sigue midiendo 220 bytes, sigue siendo UTF-8 válido y el registro sigue alineado. La alerta aparecerá igualmente porque el hash cambia.

> **No cambie el ID** ni introduzca caracteres no ASCII en esta prueba. Si cambia el ID, el índice quedará inconsistente y la aplicación podría mostrar un error adicional. Si cambia un carácter acentuado por uno ASCII, el tamaño en bytes cambiará (una `é` ocupa 2 bytes; una `e` ocupa 1). Para la prueba de integridad, lo más limpio es editar un campo ASCII como el nombre `Ana`, el teléfono o la ciudad `Cartago`.

### 6.6.2 Método recomendado: Notepad++

1. **Cierre la aplicación** antes de editar. Esto evita confusiones y bloqueos del archivo.
2. Abra `contactos.dat` con Notepad++:
   * Menú **Archivo > Abrir** y seleccione el archivo, o
   * clic derecho sobre `contactos.dat` > **Edit with Notepad++**.
3. Active el ajuste de línea: **Ver > Ajuste de línea** (Word wrap). El archivo aparecerá como una sola línea larga, porque no tiene saltos de línea.
4. Revise la barra de estado inferior:
   * Debe indicar **UTF-8** (sin BOM).
   * Si indica **ANSI** y los nombres con tildes se ven como `JosÃ©`, **cierre sin guardar** y use HxD o el método de PowerShell de la sección 6.6.4. Guardar en una codificación distinta cambiaría los bytes de las tildes y el tamaño.
5. Busque el texto `Ana` con `Ctrl + F` y active **Match case** (coincidir mayúsculas/minúsculas) para no confundirlo con el `ana` del correo. Cierre el cuadro de búsqueda.
6. Haga clic justo después de `An`, active el **modo sobrescritura** con la tecla **Insert** (o `Insert`/`Ins`) y escriba `i`. El texto debe quedar `Ani`. También puede usar `Ctrl + H`, buscar `Ana` con **Match case**, reemplazar por `Ani` y pulsar **Reemplazar** una sola vez (no **Reemplazar todo**).
7. Verifique que no se agregó ni se eliminó ningún carácter. La barra de estado debe seguir mostrando la misma longitud (220 para el ejemplo de dos contactos).
8. Guarde con `Ctrl + S`. **No use "Guardar como"**, no cambie la codificación y no pulse `Enter`.
9. Cierre Notepad++.
10. Compruebe el tamaño:

```powershell
(Get-Item .\contactos.dat).Length
```

Debe imprimir `220`. Si imprime otro valor, restaure el original y repita:

```powershell
Copy-Item .\contactos_original.dat .\contactos.dat -Force
```

### 6.6.3 Método exacto: HxD (editor hexadecimal)

Si Notepad++ agrega un BOM, cambia el fin de línea o convierte la codificación, HxD es la opción más segura porque trabaja byte por byte:

1. Abra `contactos.dat` con **HxD** (o cualquier editor hexadecimal como ImHex).
2. Use `Ctrl + G` y vaya al offset **`0x78`** (120 decimal). Ese es el primer byte del campo `nombre` del registro 1 (ID 2): `110 + 10 = 120`.
3. En la vista hexadecimal, el byte en `0x78` debe ser `41` (la `A` de `Ana`). Escriba `58` (`X`) o `69` (`i`) para cambiarlo.
4. Guarde con `Ctrl + S`. HxD conserva el tamaño exacto.
5. Verifique que el archivo sigue midiendo 220 bytes.

> **¿Por qué el offset 120?** Porque el registro 1 empieza en `1 × 110 = 110` y el campo `nombre` empieza 10 bytes después del inicio del registro: `110 + 10 = 120`.

### 6.6.4 Método reproducible: PowerShell (sin editor)

Si prefiere una alteración controlada y repetible, este comando cambia un solo byte y conserva el tamaño:

```powershell
$ruta = Join-Path $PWD "contactos.dat"
$bytes = [System.IO.File]::ReadAllBytes($ruta)
$offset = 120   # primer byte del nombre del registro 1 (ID 2)

"Tamaño antes: $($bytes.Length) bytes"
"Byte $offset antes: 0x{0:X2}" -f $bytes[$offset]

$bytes[$offset] = 0x58   # 'X'

[System.IO.File]::WriteAllBytes($ruta, $bytes)
$comprobacion = [System.IO.File]::ReadAllBytes($ruta)
"Tamaño después: $($comprobacion.Length) bytes"
"Byte $offset después: 0x{0:X2}" -f $comprobacion[$offset]
```

Resultado esperado: `220` bytes antes y después; el byte `120` pasa de `0x41` a `0x58`. Este método es útil para la captura de la comparación, pero para la captura de la "edición con editor de texto" se recomienda Notepad++ o HxD.

### 6.6.5 Variante: alterar el tamaño

Si el profesor pide demostrar que la alerta también funciona cuando cambia el tamaño, agregue un carácter al final del archivo con un editor de texto. La alerta de integridad aparecerá igual, porque el hash cambia. Sin embargo, el archivo quedará desalineado (221 bytes, no múltiplo de 110) y la tabla de contactos podría mostrar un error de "archivo corrupto" al recargarse. Para la captura principal se recomienda la variante de **mismo tamaño**, que demuestra que el hash detecta cambios de contenido y no solo de longitud.

## 6.7 Fase 4: comprobar la alteración desde la consola

Antes de abrir la aplicación, verifique que el hash actual ya no coincide con el guardado:

```powershell
$actual = (Get-FileHash .\contactos.dat -Algorithm SHA256).Hash.ToLower()
$guardado = (Get-Content .\contactos.sha256 -Raw).Trim().ToLower()

"Hash actual:   $actual"
"Hash guardado: $guardado"
"¿Coinciden?   $($actual -eq $guardado)"
```

Resultado esperado:

```text
Hash actual:   <64 caracteres distintos>
Hash guardado: <64 caracteres originales>
¿Coinciden?   False
```

También puede comprobar que el tamaño no cambió y localizar el byte alterado:

```powershell
$orig = [System.IO.File]::ReadAllBytes((Join-Path $PWD "contactos_original.dat"))
$mod  = [System.IO.File]::ReadAllBytes((Join-Path $PWD "contactos.dat"))

"Tamaño original:   $($orig.Length) bytes"
"Tamaño modificado: $($mod.Length) bytes"

for ($i = 0; $i -lt [Math]::Min($orig.Length, $mod.Length); $i++) {
    if ($orig[$i] -ne $mod[$i]) {
        "Primer byte diferente: $i (0x{0:X})  0x{1:X2} -> 0x{2:X2}" -f $i, $orig[$i], $mod[$i]
        break
    }
}
```

Resultado esperado con el ejemplo:

```text
Tamaño original:   220 bytes
Tamaño modificado: 220 bytes
Primer byte diferente: 120 (0x78)  0x41 -> 0x58
```

Esta salida es una evidencia excelente para el PDF: demuestra que el archivo cambió en **un solo byte** y que el tamaño permaneció igual. El hash, en cambio, es completamente distinto.

## 6.8 Fase 5: abrir la aplicación y capturar la alerta SHA-256

1. Ejecute de nuevo la aplicación:

```powershell
python main.py
```

2. Espere aproximadamente **150 milisegundos** (la verificación se programa con `self.after(150, self._verificar_integridad_inicial)`). Aparecerá un cuadro de advertencia con:
   * Título: **ALERTA DE INTEGRIDAD**.
   * Mensaje: `ALERTA: El archivo contactos.dat fue modificado fuera de la aplicación.`
   * `Hash actual:  <64 caracteres>`.
   * `Hash guardado: <64 caracteres>`.
   * Texto final: `El archivo 'contactos.dat' fue modificado fuera de la aplicación.`

3. Capture la pantalla con `Win + Shift + S` o `Alt + PrintScreen`. Asegúrese de que se vean:
   * El título del diálogo.
   * Los dos hashes completos (o al menos una parte claramente diferente).
   * El nombre `contactos.dat`.
   * Preferiblemente, la ventana de la aplicación detrás del diálogo.

4. Cierre el diálogo con **Aceptar**. En la consola de registro de la aplicación debe aparecer una línea similar a:

```text
[HH:MM:SS] [ALERTA] ALERTA: El archivo contactos.dat fue modificado fuera de la aplicación.
```

5. Capture también esa línea de la consola. Refuerza la evidencia de que la alerta quedó registrada.

> **Muy importante:** después de alterar el archivo, **no use Agregar ni Modificar** antes de tomar la captura. Esas operaciones llaman a `guardar_hash_sha256()` y actualizarían el hash al contenido alterado, haciendo que la próxima verificación aparezca como "íntegra". Para la demostración, solo abra la aplicación, capture la alerta y cierre.

### Si la alerta no aparece

| Posible causa | Solución |
|---|---|
| `contactos.sha256` no existe | La aplicación lo interpreta como "estado inicial". Cree un contacto antes de alterar o regenere el hash con `python -c "import utilidades_sistema as u; print(u.guardar_hash_sha256())"` **antes** de la alteración |
| Se editó una copia del archivo, no el del proyecto | Compruebe que está editando la ruta correcta; `src/app.py` ancla el proceso a la raíz del proyecto |
| La aplicación estaba abierta y se usó Agregar/Modificar después de la alteración | El hash se actualizó; restaure el original y repita sin usar esas acciones |
| El diálogo aparece detrás de otra ventana | Use `Alt + Tab` o busque la ventana "ALERTA DE INTEGRIDAD" |
| La verificación dice "VERIFICACIÓN IMPOSIBLE" | Puede ser un problema de permisos o el archivo está bloqueado por el editor; cierre el editor y reintente |
| La verificación dice "Estado inicial: todavía no existe un hash de referencia" | Falta `contactos.sha256`; créelo antes de la prueba |

## 6.9 Fase 6: comparar el respaldo ZIP antes y después

1. Con la aplicación abierta (o después de cerrarla), use **Herramientas > Crear respaldo ZIP**. Esto genera un nuevo `respaldo_agenda.zip` con el `contactos.dat` alterado.
2. Cierre el diálogo informativo.
3. Guarde una copia del nuevo ZIP con otro nombre:

```powershell
Copy-Item .\respaldo_agenda.zip .\respaldo_despues.zip -Force
```

4. Extraiga ambos respaldos en carpetas separadas:

```powershell
Remove-Item .\cmp -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive .\respaldo_antes.zip  -DestinationPath .\cmp\antes
Expand-Archive .\respaldo_despues.zip -DestinationPath .\cmp\despues
```

5. Compare los hashes de los `contactos.dat` extraídos:

```powershell
Get-FileHash .\cmp\antes\contactos.dat, .\cmp\despues\contactos.dat -Algorithm SHA256 |
    Format-Table Algorithm, Hash, Path -AutoSize
```

Resultado esperado: dos hashes **distintos**. El de `antes` debe coincidir con `hash_antes.txt`; el de `despues` debe coincidir con el hash actual del archivo alterado.

6. Compare los `indice.json` extraídos:

```powershell
Get-FileHash .\cmp\antes\indice.json, .\cmp\despues\indice.json -Algorithm SHA256 |
    Format-Table Algorithm, Hash, Path -AutoSize
```

Resultado esperado: hashes **iguales**. El índice no cambió porque la alteración fue solo en `contactos.dat`.

7. Localice la diferencia byte por byte:

```powershell
fc.exe /b .\cmp\antes\contactos.dat .\cmp\despues\contactos.dat
```

Resultado esperado (si se editó el byte 120):

```text
Comparando archivos .\cmp\antes\contactos.dat y .\cmp\despues\contactos.dat
00000078: 41 58
```

`00000078` es hexadecimal y equivale a 120 decimal. `41` es la `A` original y `58` es la `X` introducida. `fc` devuelve un código de salida 1 cuando encuentra diferencias; eso es normal.

8. Capture la ventana de PowerShell con los resultados de `Get-FileHash` y `fc.exe`. Es la **comparativa del respaldo ZIP**.

### Tabla para llenar en el PDF

| Momento | Archivo | Tamaño | SHA-256 | ¿Coincide con `contactos.sha256`? |
|---|---|---:|---|---|
| Antes (ZIP antes) | `contactos.dat` | 220 B | [hash antes] | Sí |
| Después (ZIP después) | `contactos.dat` | 220 B | [hash después] | No |
| Antes (ZIP antes) | `indice.json` | [tamaño] | [hash índice antes] | — |
| Después (ZIP después) | `indice.json` | [tamaño] | [hash índice después] | — |

### Comparación directa sin extraer (opcional)

Si desea comparar el `contactos.dat` dentro de los ZIP sin extraerlo, puede usar este script de PowerShell:

```powershell
Add-Type -AssemblyName System.IO.Compression.FileSystem

function Get-HashDeEntradaZip {
    param([string]$RutaZip, [string]$NombreEntrada)

    $zip = [System.IO.Compression.ZipFile]::OpenRead((Resolve-Path $RutaZip))
    try {
        $entrada = $zip.GetEntry($NombreEntrada)
        if (-not $entrada) { return "No existe la entrada $NombreEntrada" }

        $stream = $entrada.Open()
        try {
            $sha = [System.Security.Cryptography.SHA256]::Create()
            try {
                $hash = $sha.ComputeHash($stream)
                return ([System.BitConverter]::ToString($hash)).Replace("-", "").ToLower()
            }
            finally { $sha.Dispose() }
        }
        finally { $stream.Dispose() }
    }
    finally { $zip.Dispose() }
}

"Antes:   $(Get-HashDeEntradaZip .\respaldo_antes.zip 'contactos.dat')"
"Después: $(Get-HashDeEntradaZip .\respaldo_despues.zip 'contactos.dat')"
```

## 6.10 Fase 7: restaurar y verificar

1. Restaure el `contactos.dat` original:

```powershell
Copy-Item .\contactos_original.dat .\contactos.dat -Force
```

También puede restaurar desde el ZIP:

```powershell
Remove-Item .\restauracion -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive .\respaldo_antes.zip -DestinationPath .\restauracion
Copy-Item .\restauracion\contactos.dat .\contactos.dat -Force
Copy-Item .\restauracion\indice.json .\indice.json -Force
```

2. Compruebe que el hash vuelve a coincidir:

```powershell
$actual = (Get-FileHash .\contactos.dat -Algorithm SHA256).Hash.ToLower()
$guardado = (Get-Content .\contactos.sha256 -Raw).Trim().ToLower()
"Hash actual:   $actual"
"Hash guardado: $guardado"
"¿Coinciden?   $($actual -eq $guardado)"
```

Resultado esperado: `¿Coinciden? True`.

3. Abra la aplicación:

```powershell
python main.py
```

Debe aparecer el mensaje **"INTEGRIDAD VERIFICADA"** (o, si no aparece automáticamente, use **Herramientas > Verificar integridad**). Capture ese diálogo como evidencia de la restauración.

4. Si el hash no coincide porque se actualizó accidentalmente durante la prueba, puede restaurar la huella original:

```powershell
Copy-Item .\hash_antes.txt .\contactos.sha256 -Force
```

o regenerarlo (solo si el `contactos.dat` restaurado es el correcto):

```powershell
python -c "import utilidades_sistema as u; print(u.guardar_hash_sha256())"
```

> **Advertencia:** regenerar el hash sobre un archivo alterado **oculta** la alteración. Hágalo solo después de restaurar el contenido original.

## 6.11 Lista de capturas para el PDF

| # | Captura | Qué demuestra | Pie de foto sugerido |
|---:|---|---|---|
| 1 | Explorador de Windows con `contactos.dat`, `indice.json` y `contactos.sha256` y sus tamaños | Estado inicial consistente: 220 bytes = 2 registros de 110 | "Figura 1. Estado inicial de los archivos de la agenda." |
| 2 | `indice.json` abierto en un editor | El índice asocia IDs con números de registro | "Figura 2. Índice primario con las entradas 1→0 y 2→1." |
| 3 | Notepad++ o HxD con el texto `Ani` y el tamaño de 220 bytes | La alteración externa cambió un byte sin cambiar el tamaño | "Figura 3. Alteración manual del nombre del segundo contacto." |
| 4 | PowerShell con `¿Coinciden? False` y la diferencia en el byte 120 | El SHA-256 actual difiere del guardado | "Figura 4. El hash actual no coincide con `contactos.sha256`." |
| 5 | Diálogo **ALERTA DE INTEGRIDAD** de la aplicación | La aplicación detecta la modificación externa | "Figura 5. Alerta de integridad al iniciar la aplicación." |
| 6 | Consola de la aplicación con la línea `[ALERTA]` | La alerta quedó registrada en la bitácora | "Figura 6. Registro de la alerta en la consola." |
| 7 | PowerShell con los hashes de los ZIP antes/después y `fc /b` | El respaldo anterior conserva los bytes originales; el posterior, los alterados | "Figura 7. Comparativa de los respaldos ZIP antes y después de la alteración." |
| 8 | Diálogo **INTEGRIDAD VERIFICADA** tras restaurar | La restauración devuelve el archivo a su estado íntegro | "Figura 8. Verificación exitosa después de restaurar el respaldo." |

## 6.12 Relato listo para pegar en el PDF

> Para comprobar la detección de modificaciones externas, se creó una agenda con dos contactos ficticios (ID 1 y ID 2). Se verificó que `contactos.dat` midiera 220 bytes, es decir, dos registros de 110 bytes, y que `indice.json` asociara el ID 1 con el registro 0 y el ID 2 con el registro 1. Antes de alterar el archivo se generó un respaldo ZIP y se guardó una copia del `contactos.dat` original. Luego se abrió `contactos.dat` con Notepad++ en modo sobrescritura y se cambió el nombre del segundo contacto de "Ana" a "Ani", sin agregar ni eliminar caracteres; el archivo siguió midiendo 220 bytes. Al comparar el hash SHA-256 calculado después de la edición con el valor almacenado en `contactos.sha256`, se obtuvo una diferencia total, lo que confirma que el hash depende del contenido y no del tamaño. Al iniciar la aplicación, la verificación automática mostró el cuadro "ALERTA DE INTEGRIDAD" con el hash actual y el hash guardado, y registró la alerta en la consola. Finalmente, se creó un segundo respaldo ZIP, se extrajeron ambos y se compararon: el `contactos.dat` del respaldo anterior coincidió con el hash original, mientras que el del respaldo posterior coincidió con el hash alterado; el `indice.json` fue idéntico en ambos. Tras restaurar el archivo original, la aplicación volvió a mostrar "INTEGRIDAD VERIFICADA".

## 6.13 Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| La alerta no aparece | No existe `contactos.sha256`, o se actualizó el hash después de alterar | Cree un contacto antes de la prueba; no use Agregar/Modificar después de alterar |
| "Estado inicial: todavía no existe un hash de referencia" | Falta el archivo de hash | Genere el hash antes de la alteración |
| "VERIFICACIÓN IMPOSIBLE" | Permisos o archivo bloqueado | Cierre el editor, revise permisos, reintente |
| El archivo mide 221 bytes o más | El editor agregó un salto de línea, un BOM o un carácter | Restaure `contactos_original.dat` y use modo sobrescritura o HxD |
| Los acentos se ven como `Ã©` | El editor interpretó UTF-8 como ANSI | No guarde; use HxD o edite solo texto ASCII |
| "El archivo está corrupto: su tamaño no es múltiplo de 110" | Se agregó o quitó un byte | Restaure el original; para la prueba principal no cambie el tamaño |
| "El índice está inconsistente" | Se editó el campo ID o se modificó el índice | Restaure `contactos_original.dat` e `indice_original.json` |
| El ZIP no se crea | No existe `contactos.dat` | Cree al menos un contacto |
| El porcentaje de compresión es negativo | Es normal en archivos pequeños por las cabeceras del ZIP | No es un error; compare hashes, no tamaños |
| `fc.exe` devuelve código 1 | `fc` usa 1 para indicar diferencias | Es normal; revise la salida |
| `Expand-Archive` falla | La carpeta destino ya existe o el ZIP está en uso | Use `-Force` y cierre la aplicación |
| `python` no se reconoce | Python no está en el PATH | Use `py main.py` o el lanzador de Python instalado |

## 6.14 Qué no hacer

* **No** use Microsoft Word, WordPad ni Excel para editar `contactos.dat`: agregan formato, convierten la codificación y cambian el tamaño.
* **No** use el Bloc de notas de Windows si puede evitarlo: puede agregar un BOM o convertir los fines de línea.
* **No** pulse `Enter` al final del archivo en el editor: agrega un byte y desalinea el archivo.
* **No** cambie la codificación de UTF-8 a ANSI ni a UTF-8 con BOM.
* **No** edite el campo ID para la prueba de integridad: el índice dejaría de ser consistente.
* **No** use Agregar ni Modificar después de la alteración si quiere conservar la alerta.
* **No** sobrescriba `respaldo_antes.zip` con el segundo respaldo: copie cada uno con un nombre distinto.
* **No** comprima el proyecto completo mientras la aplicación está escribiendo; espere a que termine la operación.

---

# 7. Conclusiones

1. **El registro de longitud fija es la base del acceso aleatorio.** Al ocupar exactamente 110 bytes, la posición de cualquier contacto se calcula con `n × 110`; no hay que buscar separadores ni recorrer el archivo. La tabla de estructura y la aserción de `TAMANO_REGISTRO` garantizan que el formato se mantenga coherente.

2. **`seek()` y `tell()` permiten un acceso directo y verificable.** `seek(offset)` mueve el puntero al byte exacto, `tell()` confirma la posición y `read(110)` o `write(110)` operan sobre un único registro. La lectura aleatoria no depende del tamaño del archivo: siempre lee 110 bytes.

3. **La modificación in-place es eficiente y segura para este formato.** Abrir en `"r+b"`, posicionarse en `n × 110` y sobrescribir 110 bytes conserva el tamaño del archivo y no altera los registros vecinos. Las comprobaciones de alineación, de rango y de bytes escritos evitan corrupciones silenciosas. La suite automática confirmó que se hizo un solo `seek(110)`, un solo `write(110)`, que el tamaño no cambió y que el registro anterior quedó intacto.

4. **El índice primario reduce la búsqueda de O(n) a O(1) promedio en la localización del registro.** La consulta a `indice.json` obtiene el número de registro; luego se calcula el offset y se lee un solo registro. Para 1,000 contactos, esto puede suponer leer 110 bytes en lugar de 110,000; para 100,000, 110 bytes en lugar de 11 MB. El costo es espacio adicional y mantenimiento del índice; además, en esta implementación la carga del JSON añade un costo O(m log m) por búsqueda, que se puede eliminar cacheando el índice en memoria.

5. **La integridad SHA-256 detecta alteraciones externas.** El hash se actualiza después de cada alta o modificación y se verifica al iniciar y desde el menú de herramientas. Un cambio de un solo byte, aunque el tamaño se mantenga, produce un hash completamente distinto y dispara la alerta. El respaldo ZIP conserva una copia del estado anterior y permite comparar los bytes antes y después.

6. **El manejo de errores es parte del diseño.** El proyecto no se limita al "camino feliz": contempla archivos ausentes, vacíos, corruptos, desalineados, con permisos insuficientes, índices incompletos o desincronizados, registros incompletos y escrituras parciales. Las 161 comprobaciones automáticas que pasaron son evidencia de esa robustez.

7. **Limitaciones y trabajo futuro.** El hash se guarda junto a los datos y podría ser actualizado por un atacante con permisos de escritura; el ZIP no incluye `contactos.sha256`; no hay operación de eliminación; el índice se recarga en cada búsqueda; y el hash se recalcula sobre todo el archivo. Estas limitaciones no afectan el cumplimiento de los objetivos del laboratorio, pero son mejoras naturales para una versión de producción: firma digital del hash, caché del índice, hash incremental, inclusión del hash en el respaldo y operaciones de baja/compactación.

---

# 8. Referencias

1. Python Software Foundation. *Built-in Functions — `open()`*. Documentación oficial de Python. https://docs.python.org/3/library/functions.html#open
2. Python Software Foundation. *`io.IOBase.seek()` y `io.IOBase.tell()`*. https://docs.python.org/3/library/io.html#io.IOBase.seek
3. Python Software Foundation. *`hashlib` — Secure hash and message digest algorithms*. https://docs.python.org/3/library/hashlib.html
4. Python Software Foundation. *`json` — JSON encoder and decoder*. https://docs.python.org/3/library/json.html
5. Python Software Foundation. *`zipfile` — Work with ZIP archives*. https://docs.python.org/3/library/zipfile.html
6. Python Software Foundation. *`os.replace()`*. https://docs.python.org/3/library/os.html#os.replace
7. Yergeau, F. *UTF-8, a transformation format of ISO 10646* (RFC 3629), IETF, 2003. https://www.rfc-editor.org/rfc/rfc3629
8. National Institute of Standards and Technology. *FIPS PUB 180-4: Secure Hash Standard (SHS)*, 2015. https://csrc.nist.gov/publications/detail/fips/180/4/final
9. PKWARE, Inc. *APPNOTE.TXT — ZIP File Format Specification*. https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT
10. Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. *Introduction to Algorithms* (3.ª ed.). MIT Press, 2009. (Tablas hash y análisis de complejidad).
11. Tanenbaum, A. S., & Bos, H. *Modern Operating Systems* (4.ª ed.). Pearson, 2014. (Sistemas de archivos y acceso aleatorio).
12. Silberschatz, A., Galvin, P. B., & Gagne, G. *Operating System Concepts* (10.ª ed.). Wiley, 2018. (Archivos, asignación y acceso directo).

---

# 9. Apéndices

## Apéndice A. Constantes del proyecto

| Constante | Valor | Archivo | Significado |
|---|---|---|---|
| `ID_LEN` | 10 | `modelo_contacto.py` | Longitud del campo ID en bytes |
| `NOMBRE_LEN` | 30 | `modelo_contacto.py` | Longitud del campo nombre |
| `TELEFONO_LEN` | 15 | `modelo_contacto.py` | Longitud del campo teléfono |
| `CORREO_LEN` | 35 | `modelo_contacto.py` | Longitud del campo correo |
| `CIUDAD_LEN` | 20 | `modelo_contacto.py` | Longitud del campo ciudad |
| `TAMANO_REGISTRO` | 110 | `modelo_contacto.py` | Tamaño total del registro |
| `CODIFICACION` | `"utf-8"` | `modelo_contacto.py` | Codificación de los campos de texto |
| `BYTE_RELLENO` | `b" "` | `modelo_contacto.py` | Espacio ASCII de relleno |
| `ARCHIVO_CONTACTOS` | `"contactos.dat"` | `gestor_archivos.py` | Archivo de datos |
| `ARCHIVO_INDICE` | `"indice.json"` | `gestor_archivos.py` | Índice primario |
| `ARCHIVO_HASH` | `"contactos.sha256"` | `utilidades_sistema.py` | Hash de referencia |
| `ARCHIVO_RESPALDO` | `"respaldo_agenda.zip"` | `utilidades_sistema.py` | Respaldo comprimido |
| `BLOQUE_LECTURA` | `64 * 1024` | `utilidades_sistema.py` | Bloque de lectura para el hash (64 KiB) |
| `MENSAJE_ALERTA` | `"ALERTA: El archivo contactos.dat fue modificado fuera de la aplicación."` | `utilidades_sistema.py` | Mensaje de alerta |
| `ARCHIVO_JSON_EXPORTADO` | `"contactos_exportados.json"` | `exportador.py` | JSON de exportación |
| `ARCHIVO_PDF_REPORTE` | `"reporte_contactos.pdf"` | `exportador.py` | Reporte PDF |

## Apéndice B. Comandos útiles (chuleta)

```powershell
# Ir a la carpeta del proyecto
cd "C:\Users\Usuario\Documents\Universidad\Cuarto Semestre\Manejo_e_Implementación_de_Archivos\Proyecto 2"

# Ejecutar la aplicación
python main.py

# Ejecutar la suite de verificación (161 comprobaciones)
python pruebas/verificar_proyecto.py

# Ver tamaño y cantidad de registros
$tamano = (Get-Item .\contactos.dat).Length
"$tamano bytes / $([math]::Floor($tamano / 110)) registros / alineado: $($tamano % 110 -eq 0)"

# Ver el índice
Get-Content .\indice.json

# Ver el hash guardado
Get-Content .\contactos.sha256

# Calcular el hash actual
(Get-FileHash .\contactos.dat -Algorithm SHA256).Hash.ToLower()

# Comparar hash actual con el guardado
$actual = (Get-FileHash .\contactos.dat -Algorithm SHA256).Hash.ToLower()
$guardado = (Get-Content .\contactos.sha256 -Raw).Trim().ToLower()
"¿Coinciden? $($actual -eq $guardado)"

# Crear copia de seguridad manual
Copy-Item .\contactos.dat .\contactos_original.dat -Force
Copy-Item .\indice.json .\indice_original.json -Force

# Restaurar
Copy-Item .\contactos_original.dat .\contactos.dat -Force
Copy-Item .\indice_original.json .\indice.json -Force

# Extraer un ZIP
Expand-Archive .\respaldo_antes.zip -DestinationPath .\cmp\antes -Force

# Comparar dos archivos byte por byte
fc.exe /b .\cmp\antes\contactos.dat .\cmp\despues\contactos.dat

# Ver el contenido de un ZIP
tar -tf .\respaldo_antes.zip

# Regenerar el hash (solo si el archivo es el correcto)
python -c "import utilidades_sistema as u; print(u.guardar_hash_sha256())"
```

## Apéndice C. Glosario

| Término | Definición |
|---|---|
| **Acceso aleatorio** | Capacidad de leer o escribir directamente en una posición del archivo sin recorrer las anteriores. |
| **Acceso secuencial** | Lectura o escritura que avanza desde el inicio hasta la posición deseada. |
| **Byte** | Unidad de 8 bits; unidad de medida de las posiciones y longitudes del archivo. |
| **Offset** | Posición absoluta dentro del archivo, contada desde 0. |
| **Puntero del archivo** | Posición interna del archivo abierto; `seek()` la cambia y `tell()` la consulta. |
| **Registro** | Conjunto de campos que representan una entidad; en este proyecto, 110 bytes por contacto. |
| **Longitud fija** | Todos los registros ocupan exactamente la misma cantidad de bytes. |
| **Registro lógico** | Número de orden del registro dentro del archivo; empieza en 0. |
| **In-place** | Modificación en la misma posición del archivo, sin reescribir el resto. |
| **Índice primario** | Estructura auxiliar que asocia la clave primaria con la ubicación del registro. |
| **Clave primaria** | Campo que identifica de forma única un registro; en este proyecto, el ID. |
| **Tabla hash** | Estructura que asigna claves a valores mediante una función hash; base del `dict` de Python. |
| **O(1)** | Complejidad constante: el tiempo no depende de la cantidad de datos. |
| **O(n)** | Complejidad lineal: el tiempo crece proporcionalmente con la cantidad de datos. |
| **O(m log m)** | Complejidad del ordenamiento y de la carga del índice en esta implementación. |
| **SHA-256** | Función hash criptográfica que produce un resumen de 256 bits (64 caracteres hexadecimales). |
| **Hash** | Huella digital del contenido de un archivo. |
| **Integridad** | Propiedad de que el contenido no ha sido alterado. |
| **ZIP** | Formato de archivo comprimido que agrupa uno o más archivos. |
| **DEFLATE** | Algoritmo de compresión usado por `zipfile.ZIP_DEFLATED`. |
| **UTF-8** | Codificación de caracteres Unicode de longitud variable (1 a 4 bytes por carácter). |
| **BOM** | Marca de orden de bytes; el proyecto evita el BOM para no alterar los tamaños. |
| **Relleno (padding)** | Bytes adicionales que completan un campo hasta su longitud fija; aquí, espacios ASCII. |
| **Rollback** | Deshacer una operación cuando falla un paso posterior. |
| **Atomicidad** | Propiedad de que una operación se completa del todo o no se realiza; se logra con archivo temporal + `os.replace()`. |

## Apéndice D. Mapeo de los requisitos solicitados

| Requisito solicitado | Sección donde se desarrolla | Evidencia principal |
|---|---|---|
| 1. Tabla de estructura del registro (campos, largo y total de 110 bytes en UTF-8) | **2.2** y **2.3** | Tabla de cinco campos, offsets, ejemplo y volcado hexadecimal |
| 2. Explicación del acceso aleatorio con `seek()`/`tell()` y la modificación in-place, con fragmentos exactos de `gestor_archivos.py` | **3.3**, **3.4**, **3.5** y **3.6** | Código exacto de `escribir_registro_final()`, `leer_registro_aleatorio()`, `sobrescribir_registro_en_lugar()`, `buscar_por_id()` y `modificar_por_id()` |
| 3. Funcionamiento de `indice.json` y por qué la búsqueda con índice primario es O(1) y más eficiente que la secuencial O(n) | **4.1** a **4.13** | Estructura JSON, algoritmo, tablas de complejidad y comparación de volúmenes |
| 4. Guía paso a paso para alterar `contactos.dat` con un editor de texto y capturar la alerta SHA-256 y la comparativa del respaldo ZIP | **6.1** a **6.14** | Procedimiento con Notepad++/HxD, comandos de PowerShell, lista de capturas y relato listo para pegar |

## Apéndice E. Plantilla de la tabla comparativa del ZIP

| Momento | Archivo | Tamaño (bytes) | SHA-256 | ¿Coincide con el hash guardado? |
|---|---|---:|---|---|
| Antes de la alteración | `contactos.dat` (del ZIP antes) | 220 | [completar] | Sí |
| Después de la alteración | `contactos.dat` (del ZIP después) | 220 | [completar] | No |
| Antes de la alteración | `indice.json` (del ZIP antes) | [completar] | [completar] | — |
| Después de la alteración | `indice.json` (del ZIP después) | [completar] | [completar] | — |

## Apéndice F. Lista de verificación final antes de entregar

- [ ] Reemplacé `[Nombre completo]`, `[Número de carné]`, `[Nombre del profesor]` y `[DD/MM/AAAA]`.
- [ ] La tabla de la sección 2.2 suma 110 bytes y coincide con `TAMANO_REGISTRO`.
- [ ] Los fragmentos de código de la sección 3 coinciden con `gestor_archivos.py`.
- [ ] La explicación de O(1) incluye la nota de rigor sobre la carga del índice.
- [ ] La guía de la sección 6 usa la ruta correcta de mi proyecto.
- [ ] Tengo las capturas 1 a 8 (o al menos la alerta SHA-256 y la comparativa ZIP).
- [ ] Las capturas muestran los hashes completos o claramente diferentes.
- [ ] La tabla comparativa del ZIP está llena con mis hashes reales.
- [ ] El PDF conserva tildes y eñes (fuente con soporte UTF-8).
- [ ] Los bloques de código usan una fuente monoespaciada y no se cortan en el PDF.
- [ ] El informe tiene número de página, título y nombre del estudiante.
- [ ] Restauré el `contactos.dat` original después de la prueba.

---

**Fin del informe.**
