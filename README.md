# Proyecto Sombra — v35.6-etapa4.3.5

Revisión visual de los cuatro paneles laterales sobre v35.6-etapa4.3.4. Sirve para ejecutar el software y preparar pruebas piloto. La validación científica de campo, la evaluación con fotografías reales anotadas y la aceptación manual final en Windows siguen pendientes.

## Abrir en Windows

1. Extraé el ZIP en una carpeta nueva. Conservá tu copia anterior y tus proyectos.
2. Desde **CMD** abierto en la carpeta de `main.py`, ejecutá `PREPARAR_SOMBRA.cmd`. Requiere Python 3.12 de 64 bits e instala las dependencias de `requirements-full.txt` en el entorno local `.venv`.
3. Ejecutá `ABRIR_SOMBRA.cmd`. Si usás VS Code, elegí `.venv\Scripts\python.exe` como intérprete.

El archivo de arranque usa el mismo intérprete que instaló NumPy, pandas y el resto de las dependencias. Si moviste el proyecto, prepará el entorno en su nueva ubicación. El perfil de QA de Linux usa OpenCV headless y no es el perfil de escritorio Windows.

## Usar y compilar

Después de iniciar sesión, la bienvenida permite crear, abrir o importar un proyecto. El escritorio aparece cuando esa operación termina. Los proyectos abiertos recuperan el panel guardado; los nuevos empiezan en la vista de sombra, con el lateral plegado.

- [Manual y guía rápida](docs/MANUAL_SOMBRA.html), también disponibles en Ayuda.
- [Portada y acceso](docs/ARRANQUE_VISUAL.md), [cierre técnico anterior](docs/CIERRE_VERSION.md) y [estado de evidencia](validacion/README.md).
- [Compilación e instalador de Windows](COMPILAR_WINDOWS.md). El perfil ya está incorporado a esta entrega. Los binarios se generan en Windows.
- [Recorrido manual en Windows](validacion/windows/recorrido_cierre.md).
- [Plan de validación de campo](docs/VALIDACION_CAMPO.md) y [evaluación de sombra](docs/DETECCION_SOMBRA.md).
- [Cambios](CHANGELOG.md) y [arquitectura](docs/ARQUITECTURA.md).

## Datos y compatibilidad

La distribución se entrega sin las bases de cuentas, configuraciones personales, máscaras de trabajo, registros ni resultados del ZIP de origen. El archivo original conserva esos datos. Las cuentas existentes del perfil Windows se usan desde su ubicación habitual; una instalación limpia pide crear su administrador. Para migrar un proyecto de trabajo, conservá una copia y usá su carpeta existente o exportá/importá un `.3es`.

Las ecuaciones y el registro científico se mantienen, incluido `advanced_radiative_v2`. Se conservan los esquemas de proyecto y las exclusiones manuales introducidas en 4.2. Los archivos de evidencia de la etapa4.3 siguen disponibles como antecedentes; no constituyen una prueba del instalador de esta entrega.
