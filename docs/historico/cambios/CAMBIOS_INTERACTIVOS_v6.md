# Cambios interactivos v6 — curvas de nivel Tmrt

## Objetivo
Hacer que el mapa de curvas de nivel permita consultar con el mouse los valores térmicos locales y que la escala de color represente exactamente el rango de Tmrt que puede aparecer en esa consulta.

## Cambios aplicados

### 1. Curva de nivel interactiva
La curva ya no se muestra como una captura PNG dentro de un `Label` de Tkinter al generarla. Se utiliza el `FigureCanvasTkAgg` real de Matplotlib para conservar eventos de mouse.

Al mover el mouse se muestran:
- coordenadas X/Y del punto;
- Tmrt local (°C);
- temperatura del aire de referencia (°C);
- sombra local (%);
- radiación efectiva local (W/m²);
- reducción de Tmrt respecto a pleno sol (°C).

Clic izquierdo: fija el punto consultado.
Clic derecho: libera el punto fijado.

### 2. Escala térmica = rango consultable
El mínimo y el máximo de la colorbar se obtienen de los valores finitos reales de `Tmrt_map`.

Por lo tanto:
- el mínimo de la escala es el mínimo Tmrt que puede devolver el hover;
- el máximo de la escala es el máximo Tmrt que puede devolver el hover;
- los extremos aparecen explícitamente entre los ticks de la colorbar.

En un mapa térmicamente uniforme se muestra un único valor, evitando inventar un rango físico.

### 3. Mismo origen de datos
El tooltip no reconstruye la temperatura a partir del color. Consulta directamente las mismas matrices utilizadas para dibujar el mapa, evitando diferencias por redondeo o por interpolación visual.

### 4. Etiquetado físico más claro
El gráfico se titula `Tmrt estimada según distribución local de sombra` y la colorbar se rotula `Tmrt (°C)` para no confundirla con temperatura del aire.

### 5. Compatibilidad con exportación
Se sigue generando una imagen PNG estática para historial, PDF y restauración de proyectos. La interacción está disponible en el canvas vivo cuando el mapa es generado/regenerado.

## Archivos modificados
- `ui/app_ui.py`
- `plot_style.py`

## Validación
Suite completa ejecutada con `PYTHONPATH=.`:
- 71 tests aprobados
- 5 omitidos exclusivamente porque pvlib no está instalado en el entorno de validación
