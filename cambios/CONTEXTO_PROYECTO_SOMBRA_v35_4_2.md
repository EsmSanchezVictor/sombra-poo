# Contexto de continuidad — Proyecto Sombra v35.4.2

Versión base recomendada actual: **v35.4.2**.

Corrige el arranque en Windows después de incorporar formas de copa. El código interno ya no depende del archivo con `ñ`: usa `diseno.py`. El módulo `core/crown_shapes.py` está incluido explícitamente en el paquete completo y en el reemplazo autosuficiente.

Las formas de copa siguen siendo un atributo visual/persistente del árbol y no alteran todavía la formulación física de sombra, radiación o temperatura.

Validación final: 218 tests aprobados, 5 omitidos, sin ResourceWarning.
