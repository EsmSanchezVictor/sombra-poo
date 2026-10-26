# Aplicar la corrección v35.6-etapa3.1

Para la instalación v35.6-etapa3 que mostró el error, usar `proyecto_sombra_v35_6_etapa3_1_correccion_windows.zip`. No hace falta reemplazar toda la aplicación.

1. Conservá una copia de la carpeta y del proyecto. Si el último guardado falló, anotá o capturá los cambios que aún estén sólo en memoria antes de cerrar: no deben darse por guardados.
2. Cerrá Proyecto Sombra.
3. Extraé el ZIP de corrección **en la carpeta donde está main.py**, aceptando reemplazar los archivos. Deben quedar `core/safe_io.py` y `services/project_storage.py` dentro de las carpetas existentes, sin crear una segunda carpeta de aplicación.
4. Iniciá de nuevo con `python main.py` y abrí el proyecto. Si aparece un aviso de recuperación, conservá las copias preservadas y revisá el contenido como indican las instrucciones de Etapa 3.
5. Probá Guardar: debe completar la consolidación y crear el respaldo .3es. Cerrá y reabrí para comprobar estado, escenas y carrusel. Los registros de arranque identifican v35.6-etapa3.1.

La corrección no incluye ni sustituye users.db, proyectos, contraseñas o resultados. No requiere instalar dependencias nuevas. Conservá `.sombra-recovery` y los respaldos existentes; no los borres para intentar evitar el error.

También se suministran un ZIP completo para carpeta nueva y un reemplazo acumulativo sobre v35.6/Etapas 1/2/3. Son opciones alternativas al parche pequeño. Para esos paquetes siguen vigentes las instrucciones de dependencias/usuarios de INSTRUCCIONES_ETAPA3.md.

La validación automática se hizo en Linux con simulación específica del rechazo de descriptores de lectura de Windows; aún falta la comprobación real en tu máquina. Si persiste el aviso, el detalle de la excepción está en `ProyectoSombra/logs/sombra.log`, junto a los datos locales de usuarios.
