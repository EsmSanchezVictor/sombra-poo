# Cambios v7 — Excel reproducible Edición ↔ Modelo

Esta versión corrige el error al recargar archivos Excel y unifica la reproducción del gráfico entre Edición y Modelo.

## Correcciones principales

1. **Hojas vacías con esquema estable**
   - `Árboles` y `Estructuras` se guardan siempre con sus encabezados, aunque no haya objetos.
   - Se evita el error `None of [Index(...)] are in the [columns]`.

2. **Compatibilidad con archivos antiguos**
   - El lector acepta una hoja `Estructuras` vacía y sin columnas, tal como la generaban versiones anteriores.
   - También tolera archivos sin hoja `Estructuras` y archivos sin `Parametros`.

3. **Nueva hoja `Parametros`**
   Guarda las condiciones necesarias para reproducir el cálculo:
   - temperatura base;
   - irradiancia base;
   - Tmin/Tmax;
   - día del año y hora;
   - latitud/longitud;
   - humedad;
   - viento;
   - timezone;
   - modo de cálculo;
   - datos del modo simple cuando correspondan.

4. **Misma geometría solar en Edición y Modelo**
   - Edición ahora usa el timezone real de la ubicación cuando está disponible, igual que Modelo.
   - Esto evita que Buenos Aires, por ejemplo, sea tratado por heurística como UTC−4 en un módulo y UTC−3 en otro.

5. **Mismo rango gráfico**
   - Modelo y Edición usan el mínimo/máximo real de la misma matriz térmica para construir los niveles.
   - Se eliminó el margen artificial de ±1 ° que hacía parecer distintos dos cálculos iguales.

6. **Misma representación de objetos**
   - Las paredes diagonales se dibujan con ambos extremos reales.
   - Árboles, senderos y galerías usan la misma convención visual que en Edición.

7. **Guardar Excel de Modelo ahora guarda el estado actual**
   - Ya no se limita a copiar el archivo originalmente cargado.
   - Serializa la escena y los parámetros actuales del modelo.

8. **Carga de Modelo con regeneración inmediata**
   - Al abrir el Excel se restaura el estado y se intenta regenerar el gráfico automáticamente.

## Archivos modificados

- `core/excel_scene.py` (nuevo)
- `diseño.py`
- `modelo_con_excel.py`
- `ui/app_ui.py`
- `test/test_excel_scene.py` (nuevo)

## Validación

- 75 tests aprobados.
- 5 tests omitidos por dependencia opcional de pvlib no instalada en el entorno de validación.
- Importación de `ui.app_ui` y `diseño` verificada.
