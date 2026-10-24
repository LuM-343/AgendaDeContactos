# Guía de pruebas manuales

Esta guía usa los escenarios de `datos_prueba/` y los datos ya cargados en la
raíz. Cada bloque indica qué hacer y qué debería ocurrir.

## Preparación

```bat
python pruebas/cargar_escenario.py 01_agenda_normal
python main.py
```

Estado inicial esperado:

- `contactos.dat`: 1320 bytes (12 registros de 110 bytes).
- `indice.json`: 12 entradas.
- `contactos.sha256`: coincide con el archivo.
- La tabla muestra 12 contactos ordenados por ID, no por orden físico.

## 1. Acceso aleatorio y búsqueda por ID

| ID buscado | Registro físico | Offset que debe mostrar `tell()` |
|---|---:|---:|
| 7 | 0 | 0 |
| 1 | 1 | 110 |
| 25 | 2 | 220 |
| 2147483647 | 9 | 990 |
| 60 | 11 | 1210 |

Pasos:

1. Menú **Contactos > Buscar por ID**.
2. Buscar `1` y luego `7`.
3. Observar el monitor de posición: debe saltar al offset indicado, no recorrer
   el archivo desde el principio.

Resultado esperado: se muestran los datos correctos y el offset coincide con
`numero_registro * 110`.

## 2. ID inexistente y duplicado

- Buscar `999`: debe aparecer un aviso de que el ID no existe; la aplicación
  sigue abierta.
- Intentar agregar un contacto con ID `1`: debe rechazarse por duplicado.

## 3. Agregar un contacto

1. Menú **Contactos > Agregar**.
2. Usar ID `500`, nombre `Prueba de Alta`, teléfono `5555-9999`,
   correo `prueba@correo.com`, ciudad `Quetzaltenango`.
3. Guardar.

Resultado esperado:

- Nuevo registro = 12; offset de escritura = 1320.
- `contactos.dat` pasa de 1320 a 1430 bytes.
- `indice.json` incluye `"500": 12`.
- `contactos.sha256` cambia.
- La tabla muestra 13 contactos.

## 4. Modificar en el lugar

1. Menú **Contactos > Modificar**.
2. Modificar el ID `25` (por ejemplo, cambiar el teléfono).
3. Guardar.

Resultado esperado:

- El archivo conserva exactamente 1430 bytes.
- El offset modificado es 220 (registro 2).
- Los demás registros no cambian.
- El hash se actualiza.

## 5. Exportar JSON y PDF

1. Menú **Exportar > Exportar a JSON**.
2. Menú **Exportar > Generar reporte PDF**.

Resultado esperado: se crean `contactos_exportados.json` y
`reporte_contactos.pdf` en la raíz (la interfaz usa esas rutas). El JSON debe
tener 13 contactos y conservar tildes y eñe; el PDF debe mostrar la fecha de
generación y la tabla.

Para generarlos directamente en `salidas/`:

```bat
python pruebas/generar_salidas.py
```

## 6. Integridad SHA-256

Con el escenario normal:

1. Menú **Herramientas > Verificar integridad**.
2. Debe indicar que el archivo coincide con el hash.

Para probar la alerta:

```bat
python pruebas/cargar_escenario.py 05_hash_alterado
python main.py
```

Resultado esperado: al iniciar aparece **ALERTA DE INTEGRIDAD** porque el hash
guardado no coincide. Los contactos siguen visibles.

Después de la prueba, volver al escenario normal:

```bat
python pruebas/cargar_escenario.py 01_agenda_normal
```

## 7. Respaldo ZIP y metadatos

1. Menú **Herramientas > Crear respaldo ZIP**.
2. Menú **Herramientas > Información del archivo**.

Resultado esperado:

- Se crea `respaldo_agenda.zip` con `contactos.dat` e `indice.json`.
- La ventana muestra tamaño, cantidad de registros, fecha de modificación y
  permisos de lectura/escritura.
- La interfaz informa el tamaño original y el tamaño comprimido.

## 8. Escenarios de error y recuperación

| Escenario | Qué debe ocurrir |
|---|---|
| `04_agenda_vacia` | Abre sin contactos y permite agregar el primero. |
| `06_archivo_truncado` | Aviso controlado: el tamaño no es múltiplo de 110. |
| `07_indice_corrupto` | Reconstruye el índice desde `contactos.dat`. |
| `08_indice_ausente` | Reconstruye el índice automáticamente. |
| `09_datos_ausentes_con_indice` | Avisos de lectura por cada ID; no se cierra. |
| `10_sin_archivos` | Agenda nueva vacía, sin alertas. |
| `11_indice_incompleto` | Completa el índice con las entradas faltantes. |
| `12_registro_invalido` | El ID 7 falla de forma controlada; el ID 5 sigue visible. |

Para cargar cualquiera:

```bat
python pruebas/cargar_escenario.py 07_indice_corrupto
python main.py
```

## 9. Verificación automática

```bat
python pruebas/comprobar_escenarios.py
python pruebas/verificar_proyecto.py
```

La primera valida los 12 escenarios; la segunda valida el código y el manejo
de archivos.

## 10. Volver al estado inicial

```bat
python pruebas/cargar_escenario.py 01_agenda_normal
```

Si se quiere recuperar el estado que estaba activo antes de la primera carga:

```bat
python pruebas/cargar_escenario.py 00_actual
```
