# Datos de prueba

Escenarios generados automáticamente por
`pruebas/generar_datos_prueba.py`. **No los edites a mano**: vuelve a
ejecutar el generador si necesitas cambiarlos.

Cada carpeta contiene los archivos que la aplicación espera en su
raíz: `contactos.dat`, `indice.json` y `contactos.sha256`.

## Cómo cargar un escenario

Cierra la aplicación, elige un escenario y vuelve a abrirla:

```bat
python pruebas/cargar_escenario.py --listar
python pruebas/cargar_escenario.py 01_agenda_normal
python main.py
```

El cargador guarda una copia del estado activo anterior en
`datos_prueba/00_actual/` antes de reemplazarlo. Para volver a ese
estado:

```bat
python pruebas/cargar_escenario.py 00_actual
```

## Escenarios

| Carpeta | Contenido | Resultado esperado |
|---|---|---|
| `01_agenda_normal` | IDs no consecutivos y en orden físico desordenado; nombres con tildes y eñe; incluye el ID máximo de 10 dígitos. | Carga 12 contactos ordenados por ID; permite buscar y modificar cualquier registro con seek()/tell(). |
| `02_limites_utf8` | El primer registro ocupa exactamente 10/30/15/35/20 bytes en cada campo; hay tildes, eñe inicial y caracteres multibyte. | Carga 4 contactos sin recortes; la exportación JSON y el PDF conservan tildes y eñe. |
| `03_un_registro` | Agenda con un único contacto en el offset 0. | Carga 1 contacto; al modificarlo, el archivo conserva 110 bytes. |
| `04_agenda_vacia` | contactos.dat existe pero mide 0 bytes; el índice es {} y el hash corresponde al archivo vacío. | Carga sin contactos ni errores; permite agregar el primero. |
| `05_hash_alterado` | Los datos y el índice son válidos, pero contactos.sha256 no coincide con el contenido real. | Al iniciar aparece ALERTA DE INTEGRIDAD; los contactos siguen siendo legibles. |
| `06_archivo_truncado` | contactos.dat mide 367 bytes (3 registros y 37 bytes extra), por lo que su tamaño no es múltiplo de 110. | Error controlado al cargar el índice: la aplicación avisa y no se cierra. |
| `07_indice_corrupto` | contactos.dat es válido, pero indice.json está truncado y no se puede interpretar. | El índice se reconstruye desde contactos.dat (12 entradas) y se vuelve a escribir. |
| `08_indice_ausente` | Existe contactos.dat con 12 registros y su hash, pero no existe indice.json. | El índice se reconstruye automáticamente y se guarda con las 12 entradas. |
| `09_datos_ausentes_con_indice` | Solo existe indice.json con dos IDs; contactos.dat y el hash no están. | La aplicación abre y muestra ERROR DE LECTURA por cada ID, sin cerrarse. |
| `10_sin_archivos` | No existe ninguno de los tres archivos de la agenda (solo se conserva .gitkeep para versionar la carpeta). | Agenda nueva vacía; no se muestran alertas. |
| `11_indice_incompleto` | contactos.dat tiene 12 registros, pero indice.json solo contiene las primeras 5 entradas. | La aplicación detecta que faltan entradas y reconstruye el índice completo. |
| `12_registro_invalido` | El primer registro tiene espacios en el campo ID y no se puede desempaquetar; el segundo registro es válido. | El ID 7 produce un error controlado al leerse; el ID 5 sigue visible y la aplicación no se cierra. |

## Verificación automática

```bat
python pruebas/comprobar_escenarios.py
```

El verificador copia cada escenario a una carpeta temporal, llama
a las funciones reales de la aplicación y comprueba el resultado
descrito en `manifest.json`.

## Escenario actual

`00_actual/` no es un escenario de prueba: es el respaldo del
último estado que estaba activo en la raíz del proyecto. Se
actualiza cada vez que se carga un escenario.
