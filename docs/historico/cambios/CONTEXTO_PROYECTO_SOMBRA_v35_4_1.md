# Contexto de continuidad — Proyecto Sombra v35.4.1

Base funcional: **v35.4**.

Esta revisión corrige exclusivamente la visibilidad del selector **Forma de copa** en **Edición > Añadir árbol** y el empaquetado Unicode de `diseño.py`.

La propiedad `forma_copa` sigue persistiendo en Excel/proyecto y se representa en 2D/3D de Edición, Modelo y animaciones. La física permanece sin cambios: la forma de copa es por ahora una propiedad geométrica/visual y no altera las fórmulas de sombra, radiación ni temperatura.

El formulario Nuevo Árbol queda ordenado como: Especie → Forma de copa → Altura → Densidad de copa → Radio de copa.

Opciones: Esférica, Cónica, Columnar, Piramidal, Extendida, Irregular, Llora.

Validación: 218 tests aprobados, 5 omitidos; smoke Tk del diálogo correcto.
