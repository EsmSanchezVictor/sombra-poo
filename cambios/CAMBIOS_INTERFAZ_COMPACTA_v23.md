# Cambios de interfaz compacta v23

## Objetivo
Reducir aproximadamente un 30 % el volumen visual de los controles de los cuatro paneles laterales y ajustar los márgenes horizontales, sin volver a introducir recortes ni superposición con el área de trabajo.

## Cambios
- `PANEL_ELEMENT_SCALE = 0.70`: paddings, separaciones y dimensiones explícitas de controles se compactan aproximadamente un 30 %.
- La tipografía se compacta solo cuando supera 7 pt; nunca baja de 7 pt para conservar legibilidad.
- `PANEL_CONTENT_RATIO` pasa de 0.80 a 0.90: el contenido ocupa el 90 % del Canvas, con márgenes laterales cercanos al 5 % por lado.
- La scrollbar vertical conserva una columna exclusiva y se reduce de 12 px a 10 px.
- El sidebar abierto se ajusta a una geometría más compacta: mínimo 350 px, máximo 500 px y objetivo del 26 % del viewport.
- La compactación se aplica desde `_crear_panel_desplazable`, por lo que alcanza a los cuatro paneles y también a controles que se agreguen dinámicamente después.

## Ejemplo a 1400 px de ancho
- Sidebar: 364 px.
- Canvas útil: 350 px.
- Contenido: 315 px (90 %).
- Margen lateral efectivo: ~17 px por lado.

## Verificación
Se comprobó en Tkinter que los cuatro paneles usan una relación contenido/Canvas de 0.900 y que la scrollbar permanece fuera del área de contenido.

Suite: 167 tests aprobados, 5 omitidos por dependencias opcionales.
