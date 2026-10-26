# Guía de serie meteorológica — v15

## Plantilla recomendada

```text
timestamp,ghi,dni,dhi,ta_c,rh_pct,wind_m_s,cloud_fraction
```

Solo `timestamp` y alguna forma de radiación utilizable son imprescindibles para usar la serie como fuente radiativa.

### Unidades
- `timestamp`: fecha y hora local del sitio;
- `ghi`: W/m²;
- `dni`: W/m²;
- `dhi`: W/m²;
- `ta_c`: °C;
- `rh_pct`: %;
- `wind_m_s`: m/s;
- `cloud_fraction`: 0–1. También se acepta 0–100 y se normaliza a fracción.

## Columnas incompletas

### GHI + DNI + DHI
Se usan los tres valores observados. Si no cierran energéticamente, el programa avisa pero no corrige la medición.

### GHI + DHI
Se deriva DNI por identidad radiométrica.

### GHI + DNI
Se deriva DHI por identidad radiométrica.

### Solo GHI
DNI y DHI se estiman con Erbs y quedan marcados como derivados.

## Interpolación
El programa interpola entre dos filas solo si el intervalo entre ambas no supera 90 minutos por defecto. No extrapola antes de la primera ni después de la última observación.

## Fuente radiativa en la interfaz
- **Cielo despejado modelado**: simulación clear-sky.
- **Medición puntual**: valor medido que se ingresa manualmente.
- **Escenario manual**: valor hipotético para ensayar condiciones.
- **Serie meteorológica CSV**: usa el archivo importado.

No conviene llamar “medición” a un valor prescripto o hipotético: por eso ambos modos están separados.
