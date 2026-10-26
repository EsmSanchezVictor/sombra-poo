# Instalación — v35.6-etapa2

Los dos ZIP son acumulativos: contienen Etapas 1 y 2. Conservá una copia completa de la carpeta y de tus proyectos antes de actualizar. La base estable original v35.6 y v35.6-etapa1 no necesitan borrarse.

## Opción A: carpeta nueva

1. Extraé proyecto_sombra_v35_6_etapa2_completo.zip en una carpeta nueva cuya raíz contenga main.py.
2. Prepará el entorno Python con `python -m pip install -r requirements.txt`. Para pvlib y UTCI: `python -m pip install -r requirements-optional.txt` (o requirements-full.txt).
3. Si venís de Etapa 1, las cuentas siguen en la ruta estable de usuarios; no copies ni sustituyas esa base. Conservá/restaurá tus proyectos y ajustes desde la copia de tu instalación.
4. Si venís directamente de v35.6, seguí INSTRUCCIONES_ETAPA1.md para migrar la base histórica junto a main.py o usar --legacy-db. El ZIP no contiene bases privadas ni contraseñas.
5. Ejecutá `python main.py`. Una instalación sin usuarios solicita un administrador humano; la cuenta histórica admin/admin exige sustitución verificada de la clave.

## Opción B: reemplazo acumulativo

1. Cerrá la aplicación y hacé una copia de la instalación actual y sus proyectos.
2. Extraé proyecto_sombra_v35_6_etapa2_reemplazo.zip en la raíz de esa **copia**, junto a main.py, aceptando sustituir los archivos incluidos.
3. El reemplazo se aplica tanto a v35.6 como a Etapa 1: incluye todos los módulos nuevos/cambiados necesarios. No contiene users.db. No borres bases, proyectos ni resultados.
4. Instalá dependencias faltantes y ejecutá main.py.

## Comprobación local antes de usar resultados

- Alta/login/gestión de usuarios, abrir/guardar/importar .3es y restaurar un elemento del carrusel.
- Fecha de otro año y año bisiesto; guardar/abrir Excel y confirmar fecha, ubicación y hora.
- En Simple, cambiar previamente selectores avanzados no debe cambiar el cálculo; revisar punto, mapa, sensibilidad e informe.
- En Avanzado, probar cielo claro con/sin pvlib, escenario manual y serie observada; comprobar fuentes y datos efectivos.
- Comparar vistas 2D/3D y animación; revisar convergencia y advertencias del balance superficial.
- Si UTCI queda fuera del dominio debe mostrarse N/D y su estado; el mapa debe conservar ese porcentaje.

Los resultados avanzados anteriores pueden cambiar por la unificación de cielo claro, viento y correcciones de RH. Conservá los resultados previos para comparación; los cambios no sustituyen una calibración de campo. Para repetir pruebas automáticas, instalá pytest y ejecutá `python -m pytest test/ -q` desde la raíz.
