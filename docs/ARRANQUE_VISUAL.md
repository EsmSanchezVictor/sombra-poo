# Arranque y acceso — v35.6-etapa4.3.2

Revisión visual de v35.6-etapa4.3.1. Se conserva el flujo de autenticación, usuarios, proyectos, cálculos y escritorio después de iniciar sesión.

- **Portada:** ventana pequeña centrada con la imagen de presentación y una barra discreta. Las etiquetas muestran la etapa que se está ejecutando: NumPy/pandas, interfaz y visualización, o datos locales. Se mantiene visible al menos 1,6 segundos. Si la carga tarda más, permanece hasta que termina.
- **Acceso:** pantalla completa con fondo claro, logo principal por encima del formulario y la firma 3Esfera debajo. Enter desde un campo envía el formulario. Esc sale del modo de pantalla completa, F11 lo alterna y Salir cierra la aplicación.
- **Primera instalación:** el alta de administrador sigue siendo obligatoria. Se presenta sobre la pantalla de acceso una vez terminada la portada.
- **Recursos:** se incluyen los PNG originales, sin cambios, en `assest/proyecto.png`, `assest/marca.png` y `assest/protada.png`. El programa adapta su tamaño y recorta solo el margen transparente de los dos logotipos al dibujarlos. El perfil de empaquetado incorpora los tres archivos.
- **Pruebas:** 621 aprobadas y autocomprobación de fuentes aprobada. Los resultados numéricos del conjunto comparado coinciden con la revisión anterior. La prueba visual nativa y la generación del binario deben realizarse en Windows.

Para ver el flujo, ejecutá `ABRIR_SOMBRA.cmd` en la carpeta de esta revisión. Si todavía no preparaste su entorno, ejecutá antes `PREPARAR_SOMBRA.cmd`. Comprobá el formulario también en una resolución o escala menor, Esc/F11, una sesión habitual y el primer inicio con una cuenta Windows de prueba.
