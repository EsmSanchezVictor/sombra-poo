# Proyecto Sombra v35.1 — Fase 1 de animación diurna

Base funcional reconstruida: **v35 estable** (v34 + indicador solar v35), incorporando también el parche solicitado para ocultar los bordes de `frame2`, `frame3`, `frame4` y `frame5`.

> Esta versión se denomina **v35.1** para no confundirla con la v36 de seguridad/integridad que había quedado en desarrollo y nunca fue declarada estable.

## Objetivo
Iniciar la simulación temporal diaria desde el botón **Ejecutar**, mostrando la evolución conjunta de:

- posición solar;
- sombra efectiva;
- temperatura superficial.

## Nuevo flujo del botón Ejecutar
En Edición o Modelo, **Ejecutar** abre ahora un selector con:

- **Instantánea**: conserva el comportamiento anterior.
- **Animación diurna (sombra + temperatura)**: seleccionada por defecto.

Parámetros:

- hora inicial;
- hora final;
- paso temporal: 15, 30 o 60 minutos;
- velocidad de reproducción: 1000, 750, 500, 300 o 150 ms/cuadro.

## Cálculo y reproducción
La animación usa dos etapas separadas:

1. **Cálculo de secuencia**: cada hora/paso se resuelve con los mismos kernels científicos que ya usa Edición o Modelo.
2. **Reproducción**: los fotogramas quedan en memoria y se reproducen sin recalcular la física.

Esto evita que la velocidad visual altere el cálculo y permite pausar, avanzar o retroceder instantáneamente.

## Reproductor 2D
La Vista 2D muestra simultáneamente:

- izquierda: mapa de **sombra efectiva** (`1 - transmitancia`);
- derecha: mapa de **temperatura superficial**;
- misma escala térmica durante toda la secuencia;
- árboles y estructuras superpuestos;
- indicador solar representativo;
- hora actual, azimut, elevación, temperatura media y sombra media;
- botones Reproducir/Pausar, Anterior, Siguiente e Inicio;
- deslizador temporal;
- velocidad de reproducción.

## Precisión conceptual
La Fase 1 es una **secuencia diurna cuasi-estacionaria**. Cada fotograma resuelve el estado correspondiente a esa hora, pero **todavía no modela memoria/inercia térmica entre un fotograma y el siguiente**. La interfaz lo indica explícitamente para no presentar una dinámica transitoria que el kernel actual no calcula.

## Compatibilidad
Funciona en:

- **Edición**, usando su escena y parámetros actuales;
- **Modelo**, incluyendo el modo Simple/Avanzado y la fuente radiativa configurada en el modelo.

Durante el cálculo se suspenden temporalmente los traces de autosave causados por el cambio horario y al finalizar se restauran los valores originales del escenario.

## Cambios preservados de v35
- indicador solar 2D;
- marcador solar representativo 3D;
- el sol 3D usa `SetUseBounds(False)` para no alejar la cámara;
- frames 2, 3, 4 y 5 sin borde visible.

## Archivos principales modificados/agregados
- `ui/app_ui.py`
- `ui/diurnal_animation.py` (nuevo)
- `ui/solar_indicator.py` (reconstruido de v35)
- `ui/scene3d.py`
- `diseño.py`
- `modelo_con_excel.py`
- `test/test_v36_diurnal_animation.py`

## Validación
- `python -m compileall -q ...` ✔
- suite completa: **207 passed, 5 skipped** ✔
- prueba Tk/Xvfb del reproductor con múltiples frames ✔
- integración Edición 10:00 → 11:00: 2 fotogramas 100×100 ✔
- integración Modelo Simple 10:00 → 11:00: 2 fotogramas 100×100 ✔

Los 5 tests omitidos son los mismos dependientes de componentes opcionales del entorno; no son fallos de la animación.
