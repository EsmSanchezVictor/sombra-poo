# v12 — Etapas 4 + 7: balance avanzado de superficies y materiales

## Filosofía de la versión

Se mantiene **sin cambios** el modelo térmico de superficies histórico como
`standard` y predeterminado. El usuario puede activar en Preferencias un
segundo modelo `advanced` para comparar resultados sin romper proyectos ni
series anteriores.

## Modelo estándar

Conserva exactamente:

`Ts = Ta + alpha * I * tau / (hc + hr)`

con `hr = 4 epsilon sigma Ta^3`.

## Modelo avanzado de superficie v1

Resuelve numéricamente, por celda, el balance estacionario no lineal:

`alpha K + epsilon Ldown - epsilon sigma Ts^4 - hc(Ts-Ta) - hg(Ts-Tsub) - LE = 0`

En v12:
- `LE = 0` por defecto; evapotranspiración se incorpora en la próxima etapa.
- Stefan–Boltzmann se resuelve sin linealizar.
- `Ldown` se estima con emisividad de cielo de Brutsaert + corrección explícita de nubosidad.
- `hg = k/d` representa acoplamiento conductivo al sustrato.
- se informa el residuo energético para auditar el cierre del balance.
- bajo copa y bajo galerías, la onda larga local se ajusta para no tratar esos puntos como cielo totalmente abierto.

## Materiales avanzados

Se agregó `core/materials.py` con propiedades separadas:
- absorptancia solar alpha
- reflectancia solar rho
- transmitancia solar tau
- emisividad de onda larga
- conductividad térmica
- profundidad térmica efectiva
- capacidad térmica volumétrica

Para los materiales ópticos se verifica `alpha + rho + tau = 1`.

Los materiales transmisivos (vidrio, policarbonato, ETFE, etc.) ya no se
comportan en el modo avanzado como obstáculos necesariamente opacos.
La transmitancia efectiva de una estructura es:

`tau_eff = (1 - opacidad) + opacidad * tau_material`

El modo estándar conserva la semántica antigua de opacidad para compatibilidad.

## Persistencia y trazabilidad

- Nuevo setting: `surface_model_mode = standard|advanced`.
- El modo se guarda en Excel (`Parametros`) y se restaura al recargar.
- El informe PDF registra el modelo de superficie activo.
- Los snapshots registran `modelo_superficie`.

## Interfaz

Preferencias > Modelo térmico de superficies:
- Estándar (linealizado, predeterminado)
- Avanzado (balance energético no lineal v1)

El título y la barra del mapa indican explícitamente que se trata de
**temperatura superficial** y qué modelo la produjo.

## Validación

Suite final v12:
- 106 tests aprobados
- 5 omitidos por pvlib opcional no instalado en el entorno de prueba

Se agregaron tests de:
- cierre alpha+rho+tau
- transmisión de vidrio vs material opaco
- respuesta de emisividad de cielo a humedad/nubosidad
- cierre del balance energético
- enfriamiento radiativo nocturno
- compatibilidad exacta del modelo estándar
- material transmisivo en galerías
- LW bajo cubierta opaca
