# Sombra – correcciones integradas v5

Esta entrega combina las modificaciones previas con las correcciones de coherencia física, numérica y de integración revisadas sobre el proyecto completo.

## Cambios principales

- Ciclo de temperatura del aire único, continuo y periódico de 24 h.
- Modo simple del Panel 4 usa realmente `T_amb_base`; modo avanzado usa Tmin/Tmax.
- Zona horaria propagada desde la ubicación y calculada para la fecha analizada.
- `SolarEngine` centraliza posición + radiación; pvlib se activa de forma autónoma y el fallback conserva `GHI = DNI·sin(elev) + DHI`.
- 0 % de sombra implica transmitancia efectiva 1.0; 100 % usa la transmitancia residual de sombra completa.
- La transmitancia de especie se usa en la proyección de sombra de árboles cuando hay especie asignada.
- Eje mayor de la elipse de copa alineado con la dirección de la sombra.
- Paredes diagonales conservan sus extremos; galerías proyectan la cubierta según altura y Sol.
- El material de pared/cubierta ya no se asigna erróneamente al suelo; la grilla de temperatura superficial usa materiales de elementos a nivel de suelo (`Sendero`).
- Selecciones circulares/poligonales conservan máscaras válidas y no introducen píxeles negros ficticios.
- El cálculo fotográfico se rotula como **índice de sombra fotográfica**, no como cobertura geométrica certificada.
- Heat Index y Temperatura Aparente usan temperatura del aire; la comparación sol/sombra se expresa mediante Tmrt y UTCI.
- Categorías UTCI corregidas (0–9 °C = estrés leve por frío).
- Integración de grados-hora corrige exactamente los cruces de umbral.
- `tmrt_map` guarda el mapa Tmrt real, no la matriz fotográfica.
- Marcadores de la barra de temperatura corregidos a coordenadas reales en °C.

## Validación

- Compilación global de todos los `.py`: OK.
- Suite actualizada: **71 tests aprobados**.
- **5 tests omitidos** únicamente porque pvlib no está instalado en el entorno de validación; `requirements.txt` ya declara pvlib.

## Alcance del modelo

Tmrt sigue siendo un modelo empírico rápido (`Ta + k·radiación`) y el Panel 4 sigue siendo un balance estacionario simplificado de temperatura superficial. No se incorporaron todavía evapotranspiración dinámica, almacenamiento térmico multicapa ni balance radiativo humano 3D, porque requieren entradas/calibración adicionales y no conviene introducir falsa precisión.
