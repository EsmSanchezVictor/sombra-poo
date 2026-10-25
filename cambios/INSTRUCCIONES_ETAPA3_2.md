# Instalación — v35.6-etapa3.2

1. Cierre Proyecto Sombra. Conserve la carpeta actual y una copia de sus proyectos antes de reemplazar código.
2. Elija **un solo ZIP** según su punto de partida:

| Archivo | Uso |
|---|---|
| proyecto_sombra_v35_6_etapa3_2_actualizacion_desde3_1.zip | Sobre una instalación v35.6-etapa3.1. Extraer en la carpeta que contiene main.py y aceptar reemplazar archivos. |
| proyecto_sombra_v35_6_etapa3_2_reemplazo.zip | Reemplazo acumulativo sobre la v35.6 original. Incluye todas las etapas y correcciones. |
| proyecto_sombra_v35_6_etapa3_2_completo.zip | Código completo para una carpeta nueva; opción más clara si no sabe qué versión tiene. |

3. En el entorno Python de su instalación ejecute `python -m pip install -r requirements-full.txt` si quiere pvlib/UTCI. Para el núcleo basta `python -m pip install -r requirements.txt`. Esto incluye tzdata. No combine estos perfiles con el lock headless de QA Linux.
4. Inicie `python main.py`, abra una copia del proyecto, use **Guardar con respaldo**, cierre y reabra. Siga CONTROL_WINDOWS_ETAPA3_2.md. No se incluyen bases privadas de usuarios en los ZIP; la gestión de cuentas y migraciones de las etapas anteriores sigue vigente.

## Uso de los cambios

- Si una fecha/hora es inexistente o ambigua por el cambio de horario de su zona, aparecerá la causa. En campos de UI elija otro horario inequívoco. No se modifica automáticamente.
- En CSV, para conservar las dos ocurrencias de una hora repetida, indique offsets: `2024-11-03T01:30:00-04:00` y `2024-11-03T01:30:00-05:00` en America/New_York. Todas las filas deben usar la misma convención: con offset o sin offset. Las entradas con offset se convierten a la zona seleccionada.
- En **Herramientas → Ranking**, elija la escena de árboles Edición/Modelo. La fecha, hora, ubicación, temperatura y modo científico corresponden al contexto de Temperatura. Recalcule después de cambiar controles; Exportar JSON conserva el resultado calculado con su procedencia.
- El ranking expresa potencial individual dentro de 60×60 m centrados en (0, 0), en °C. No sume sus reducciones para estimar el beneficio de toda la escena.

La corrección de guardado Windows de Etapa 3.1 está incluida. Ante otro fallo, conserve el texto y el registro `%LOCALAPPDATA%\ProyectoSombra\logs\sombra.log` (ubicación por defecto). No elimine archivos de recuperación o cuarentena. La prueba visual en Windows/Tk/VTK aún no fue ejecutada aquí.
