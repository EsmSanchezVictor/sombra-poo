# Instalación — v35.6-etapa1

Esta entrega corresponde solamente a Etapa 1. Conservá la v35.6 original como respaldo. No uses el ZIP v35.7 descartado.

## Opción A: proyecto completo

1. Extraé proyecto_sombra_v35_6_etapa1_completo.zip en una carpeta nueva.
2. El ZIP no incluye users.db ni tus proyectos: evita distribuir cuentas existentes.
3. Para conservar usuarios e historial de la v35.6, antes del primer arranque copiá su users.db junto al nuevo main.py. Copiá también tus carpetas proyectos y archivos de configuración/datos propios que necesites conservar. No hace falta copiar módulos viejos.
4. Si ya existe %APPDATA%/ProyectoSombra/users.db, se utiliza esa base estable y no se reemplaza desde la carpeta del programa.
5. Instalá las dependencias con `python -m pip install -r requirements.txt` y ejecutá `python main.py`.
6. Sin cuentas administradoras, se solicita crear el primer administrador. Si conservaste admin/admin, verificá esa clave y reemplazala por una de 12 caracteres o más cuando el login lo solicite.

## Opción B: reemplazo sobre una copia de v35.6

1. Cerrá todas las instancias del programa.
2. Trabajá sobre una copia de tu instalación v35.6.
3. Extraé proyecto_sombra_v35_6_etapa1_reemplazo.zip en la raíz que contiene main.py. Aceptá reemplazar los archivos incluidos. No borres users.db ni la carpeta proyectos.
4. El paquete contiene también los módulos nuevos necesarios; no copies solo database_manager.py.
5. Ejecutá main.py. La primera migración conserva IDs, usuarios e historial y mueve el uso activo de la base a la ubicación estable.

Si la base vieja está fuera de la carpeta del programa, antes del primer arranque y antes de que exista la base estable podés indicar su ubicación:

`python migrate_db.py --legacy-db "D:/ruta/users.db"`

La contraseña olvidada se restablece mediante otro administrador autenticado. La recuperación insegura por nombre de usuario fue retirada.

## Comprobación local en Windows

- Alta inicial o sustitución de la clave histórica, cancelación del alta, login correcto/incorrecto.
- Agregar/editar usuario, restablecer contraseña, proteger al último administrador; cuenta interna ausente de la lista.
- Verificar historial y proyectos asociados a las sesiones.
- Abrir un proyecto existente, cambiar un dato, Guardar, cerrar y volver a abrir.
- Exportar/importar un .3es propio; restaurar una miniatura y revisar sus valores.
- Revisar formularios nuevos y animaciones 2D/3D.

En Linux pasaron 285 pruebas y se omitieron 5 por falta de pvlib. Eso no equivale a haber probado la GUI en Windows ni a validación científica de campo.

## Volver a v35.6

La carpeta original y su base local se conservaron. Para revertir el código, usá esa carpeta original. No borres la nueva base estable: contiene las sesiones posteriores a la actualización. No mezcles bases de usuarios ni resultados de versiones distintas sin conservar primero sus copias.
