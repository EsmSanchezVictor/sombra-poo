# Proyecto Sombra v35.6 — Homogeneización de ventanas emergentes

Base: **v35.5**.

## Objetivo
Unificar todas las ventanas emergentes propias de Proyecto Sombra con el lenguaje visual aplicado en v35.5 a **Añadir árbol** y **Añadir estructura**, sin modificar cálculos científicos.

## Criterio visual común
- Fondo claro uniforme.
- Tipografía principal **Segoe UI**.
- Títulos y subtítulos consistentes.
- Campos alineados y espaciados de forma regular.
- Botón de acción principal diferenciado y botones secundarios neutros.
- Diálogos centrados respecto de la ventana principal.
- `Esc` cierra el diálogo cuando corresponde.
- `Enter` confirma en los formularios principales.
- Formularios modales cuando la operación requiere terminar/cancelar antes de continuar.
- Ventanas de resultados/figuras siguen siendo redimensionables.

## Infraestructura nueva
Se agrega `ui/modal_style.py` como única fuente para:
- estilo y centrado de `Toplevel`;
- normalización de widgets Tk clásicos;
- cabeceras y contenedores de diálogo;
- botones primarios/éxito;
- reemplazo homogéneo de `simpledialog.askstring`;
- cambio/restablecimiento de contraseña en un único formulario.

## Ventanas alcanzadas
- Añadir árbol.
- Añadir estructura.
- Editar árbol / estructura en Edición.
- Editar árbol / estructura en Modelo.
- Primeras configuraciones.
- Preferencias.
- Ejecutar simulación.
- Progreso de animación diurna.
- Ubicación del proyecto.
- Nombre de proyecto.
- Duplicar proyecto.
- Añadir usuario.
- Editar usuario.
- Restablecer contraseña.
- Panel de administración emergente.
- Calibración de k_factor.
- Confort térmico.
- Escenario A/B.
- Calibración/validación científica.
- Auditoría científica.
- Biblioteca de especies.
- Edición de especies.
- Ranking de árboles.
- Análisis comparativo.
- Curva de sensibilidad.
- Máscara de sombra.

## Diálogos nativos de Windows
Se mantienen deliberadamente nativos:
- Abrir archivo.
- Guardar como.
- Seleccionar carpeta.
- Mensajes estándar `messagebox` (información, advertencia, error, confirmación).

Esto preserva el comportamiento esperado del sistema operativo y accesibilidad del selector de archivos.

## Ajustes adicionales
- `Editar elemento` de Edición y Modelo ahora usa el mismo formulario limpio que Añadir árbol/estructura.
- Preferencias incorpora cabecera visual común.
- Ejecutar simulación fue reorganizado visualmente sin cambiar su lógica.
- Los prompts de nombre de proyecto y duplicación ya no usan `simpledialog` estándar; usan el nuevo formulario común.
- Restablecer contraseña pide contraseña y confirmación en una sola ventana.

## Ciencia
**Sin cambios** en:
- geometría solar;
- cálculo de sombras;
- Tmrt;
- temperatura superficial;
- materiales;
- confort térmico;
- animación científica.

## Validación
- `python -m compileall -q .`: OK.
- `PYTHONPATH=. PYTHONWARNINGS='error::ResourceWarning' pytest -q`: **224 passed, 5 skipped**.
- Barrido de código: todos los `Toplevel` propios relevantes pasan por `prepare_dialog`.
- Smoke Tk real:
  - Añadir árbol: 468×342 px, 0 superposiciones de controles.
  - Añadir estructura: 437×304 px, 0 superposiciones.
  - Ejecutar simulación: sin superposición de controles.
  - Añadir usuario: apertura correcta bajo Tk/Xvfb.
