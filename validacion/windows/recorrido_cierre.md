# Recorrido manual de aceptación — v35.6-etapa4.3.5

**Estado: pendiente.** Completá este registro sobre una copia de prueba y anotá fecha, versión, Windows, resolución/escala y motor gráfico. Si usás también el instalador, registrá por separado el resultado de la versión empaquetada.

| Comprobación | Resultado esperado | Resultado / observación |
|---|---|---|
| Arranque y primer administrador | La instalación limpia permite crear el administrador y abrir el espacio de trabajo. | |
| Bienvenida y activación | La cinta, los paneles y el pie quedan ocultos hasta crear, abrir o importar un proyecto. Cancelar o seleccionar un archivo inválido mantiene la bienvenida. | |
| Tema y vista guardada | Cinta, lateral, pestañas, administración y diálogos muestran el tema violeta. Reabrir un proyecto recupera el panel guardado. | |
| Ayuda y versión | Se abre el manual local y Acerca de muestra v35.6-etapa4.3.5. | |
| Paneles, árbol y estructura | El lateral de Edición muestra el tema violeta en ambos modos. Añadir o modificar elementos conserva las pestañas 2D y 3D. Una ventana por acción, campos visibles y formas de copa conservadas. | |
| Paneles laterales | Temperatura, Sombra y Modelo usan la misma jerarquía que Edición. Revisar simple/avanzado, scroll y botones en resoluciones habituales. | |
| Fotografía y exclusiones | Aplicar, deshacer/cancelar y regenerar funcionan; se recupera el elemento correcto al reabrir. | |
| 2D, 3D y animación | Mapas, cámara, rotación, zoom y animación funcionan en el motor declarado. | |
| Persistencia y exportación | Guardar/reabrir y exportar/importar .3es recuperan la escena; se generan Excel y PDF. | |
| Instalador, si se distribuye | Instalar en una cuenta de prueba, abrir, actualizar y desinstalar conservando los datos. | |

Comprobaciones automáticas de fuentes:

```bat
.venv\Scripts\python.exe tools\check_installation.py --require-full --report autocomprobacion_cierre.json
.venv\Scripts\python.exe tools\check_desktop.py --vtk --require-windows --report escritorio_cierre.json
```

La evidencia de etapa4.3 se conserva en su carpeta de octubre de 2026. No se traslada automáticamente el estado aprobado a esta revisión ni al instalador.
