# Cambios v9 — Modelo Tmrt dual

## Implementado

- Nuevo `core/radiative_tmrt.py` con balance radiativo humano simplificado.
- `shadow_temp.Temperatura` acepta `model_mode="standard"|"advanced"`.
- Modo estándar conserva la ecuación empírica histórica sin cambios.
- Modo avanzado usa GHI/DNI/DHI, onda corta reflejada y onda larga equivalente.
- Preferencias incorpora selector de modelo Tmrt.
- Predeterminado: `standard`.
- Panel 1 informa el modelo activo.
- Panel 4 renombra los viejos "Modo Simple/Avanzado" como "Entrada simple/detallada" para evitar confusión con el modelo científico.
- Curvas de nivel usan el modelo seleccionado y muestran su nombre en el título.
- Confort térmico usa la Tmrt del modelo seleccionado.
- Escenarios horarios pasan por `calculate_tmrt`, por lo que admiten ambos modelos.
- Snapshots, Excel e informe registran el modelo usado.
- Nuevos tests del modelo avanzado y de preservación del estándar.

## Fórmula del avanzado v1

La estructura implementada es:

`Tmrt = [ ((alpha_sw/epsilon_lw)*K + L) / sigma ]^(1/4) - 273.15`

con:

`K = tau * (f_p*DNI + f_a*DHI + f_a*albedo*GHI)`

`L = f_a * (L_down + L_up)`

En v1, `L_down` y `L_up` se aproximan mediante temperatura radiativa igual a Ta.

## Parámetros por defecto

- alpha_sw = 0.70
- epsilon_lw = 0.97
- f_p = 0.28
- f_a = 0.50
- albedo = 0.20

## Validación automática

86 tests aprobados; 5 omitidos porque requieren pvlib opcional en el entorno de prueba.
