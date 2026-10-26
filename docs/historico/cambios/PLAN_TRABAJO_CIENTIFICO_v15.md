# Plan científico — estado v15

## Etapas implementadas
1. Correcciones físicas e integración base.
2. Modelo Tmrt dual: estándar + avanzado radiativo.
3. Calibración y validación científica.
4. Separación cobertura de sombra / atenuación óptica.
5. Balance energético avanzado de superficies.
6. Materiales opacos y transmisivos.
7. Vegetación, fenología y evapotranspiración.
8. Fuentes radiativas explícitas y meteorología observada.
9. Incertidumbre operativa, sensibilidad y reporte científico.

## Arquitectura final actual
### Nivel estándar — predeterminado
Se conserva para estabilidad, rapidez, docencia y comparabilidad histórica.

### Nivel avanzado
Integra componentes radiativos, balance de superficies, materiales, vegetación y evapotranspiración, con trazabilidad de datos.

### Validación
Permite comparar Estándar, Estándar calibrado y Avanzado contra mediciones independientes.

### Datos meteorológicos
Distingue datos modelados, medidos, interpolados y derivados.

### Incertidumbre
El programa informa sensibilidad e intervalo operativo, sin presentarlo como certeza metrológica.

## Próximas mejoras opcionales, no bloqueantes
- polígonos espaciales de césped/canteros/suelo desnudo/humedad en lugar de una fracción vegetal global;
- temperatura radiativa de cielo y superficies observada/modelada en Tmrt avanzada;
- SVF y radiación de onda larga direccional 3D;
- calibración específica por especie de LAI/Kc/transmitancia;
- soporte de archivos meteorológicos estándar adicionales (EPW, NetCDF) si el proyecto lo requiere;
- caracterización metrológica real de sensores para reemplazar supuestos operativos de incertidumbre por incertidumbres instrumentales documentadas.

Estas mejoras ya no son necesarias para corregir inconsistencias básicas: son refinamientos de investigación avanzada.
