# Proyecto Sombra — v35.6-etapa4.3

Continuación de la v35.6-etapa4.2 construida sobre el ZIP actualizado del usuario. La base inmediata tiene SHA256 `bae640d1869ed00716d026a5b39d80caa227141b7b1b44a68b2beacf5dfde822`. Se conservan su física, meteorología, datos locales y compatibilidad de proyectos.

Se conservan el modelo `advanced_radiative_v2`, su factor de área proyectada dependiente de elevación, el modo fijo compatible, la incertidumbre, el controlador meteorológico y las implementaciones de visualización del ZIP actual. Los cálculos de superficie se extraen sin cambiar ecuaciones.

## Instalar y ejecutar

Use un entorno independiente; Python 3.12 es el intérprete con el que se ejecutó la regresión de esta entrega:

```bat
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-full.txt
.venv\Scripts\python tools\check_installation.py --require-full --report autocomprobacion.json
.venv\Scripts\python main.py
```

Para el núcleo sin extensiones científicas use requirements.txt. El lock requirements-qa-linux-py312.lock fija el perfil probado en Linux, usa OpenCV headless y no debe mezclarse con el perfil de escritorio. Las pruebas no acreditan instalación o interfaz nativas Windows.

## Elegir el archivo

- **sombra-poo.zip**: copia completa actualizada. Contiene las fuentes nuevas y conserva los datos locales que venían en su archivo; el original recibido se conserva como versión anterior.
- **Actualizar_4_2_a_4_3.zip**: cambios de código/documentación exclusivamente para la v35.6-etapa4.2 cuya huella aparece arriba. Cierre Sombra, conserve su carpeta y extraiga en la que contiene main.py. No incluye bases de cuentas, configuración local ni máscaras de trabajo.

El parche solo corresponde a esa etapa4.2 exacta. Si tiene otra versión, use la copia completa en una carpeta nueva y abra una copia de sus proyectos. Para ejecutar no necesita git. Puede abrir sus proyectos en su ubicación habitual; esta adaptación conserva las rutas y la política de almacenamiento de su versión actual.

## Uso

Cree/abra un proyecto, seleccione ubicación, fecha y meteorología. Para fotografía, elija área de cálculo y una referencia iluminada de la misma superficie; revise la máscara antes de interpretar cobertura y atenuación. Para escenas, agregue árboles/estructuras y seleccione el modelo científico. Guarde con respaldo y compruebe la reapertura de una copia.

## Documentación vigente

- [Cambios](CHANGELOG.md), con notas históricas conservadas en docs/historico/cambios/.
- [Estado y resultados de validación](docs/VALIDACION_ACTUAL.md).
- [Arquitectura y alcance del refactor](docs/ARQUITECTURA.md).
- [Cobertura y evaluación de sombra](docs/DETECCION_SOMBRA.md).
- [Exclusiones manuales: uso y compatibilidad](docs/EXCLUSIONES_FOTOGRAFICAS.md).
- [Campaña de mediciones](docs/VALIDACION_CAMPO.md).
- [Versiones y continuidad](docs/CONTEXTO_ACTUAL.md).
- [Cierre de F3–F7 y evidencia externa](docs/CIERRE_CLAUDE.md).
- [Comprobación de escritorio Windows](docs/ACEPTACION_WINDOWS.md).
- [Mapa de archivos y carpeta validacion/](docs/MAPA_DE_ARCHIVOS.md).

En 4.2 puede excluir manualmente materiales de un elemento ya calculado y recuperar esas correcciones al reabrir. Los proyectos corregidos requieren 4.2 o posterior (esquema de estado 3).

La ronda de implementación F3–F7 está documentada en docs/CIERRE_CLAUDE.md. Quedan por obtener las fotos reales anotadas, las mediciones de campo y la aceptación visual en Windows. Las exclusiones de materiales son manuales. Se entrega código Python, no un instalador compilado; el refactor es incremental y conserva la dependencia de los componentes respecto de SombraApp.
