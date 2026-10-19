# Zénit 0.5.5 · preview 1

Esta entrega amplía los flujos de proyecto y unifica las superficies de ayuda del editor. Mantiene las preferencias, los proyectos y los SDK opcionales ya preparados.

## Documentación y acciones del editor

Los paneles de documentación, avisos de acciones y menús contextuales tienen una superficie con 35 % de transparencia y texto opaco. La referencia muestra el símbolo, lenguaje, archivo y posición; ajusta su altura al contenido y permanece dentro de la ventana. La documentación larga conserva acceso a todo el texto. Incluye copia y preparación de una consulta en Melody, sin enviar automáticamente el contenido. Los diagnósticos mantienen su tarjeta independiente.

La interfaz y Monaco componen los fondos de los temas de extensión de la misma forma. Se corrige el contraste insuficiente de números de línea, texto de campos, ayudas y sugerencias; los colores de sintaxis legibles de cada tema se conservan. Las cabeceras utilizan su propio fondo y primer plano declarados. La prueba con los paquetes instalados verifica 39 variantes, cambios de fuente, ventanas separadas y recarga sin perder el búfer pendiente.

Los atajos Ctrl+Alt+1/2/3 reconocen también la posición física de los dígitos en distribuciones como AZERTY y la tecla virtual cuando Windows omite el código físico. Se verificaron los tres atajos en la aplicación instalada, con el editor enfocado, sin insertar caracteres en el archivo. La entrada de caracteres mediante AltGr no cambia el tema.

## Proyecto y Melody

El botón Proyecto de la barra de estado y la paleta abren un espacio con herramientas detectadas, plantillas revisables y acciones Comprobar, Compilar y Ejecutar. Las plantillas cubren Python con pruebas, C y C++ con cabecera y CMake/CTest, Java con Maven, NASM x86-64 y paquetes creados con el compilador nC real.

El archivo activo y el destino encabezan la página. Un selector de lenguaje utiliza un único formulario de preparación, con estado de herramientas y acceso al SDK. La página distingue los cambios pendientes y permite guardarlos expresamente antes de revisar un plan. La actividad conserva los resultados en filas compactas y adaptables al espacio disponible.

Los planes muestran las órdenes y verifican de nuevo sus entradas antes de ejecutarlas. Usan el destino común del proyecto; una compilación separada no está disponible en destinos remotos que solo exponen ejecución. Repetir una petición del mismo plan reutiliza su trabajo. Solo hay un flujo de proyecto simultáneo por carpeta. Los recibos conservan órdenes, hashes, salida y estado; HILO mantiene la planificación y cancelación en el backend.

Melody puede preparar un mensaje con el objetivo, búfer, archivo consultado y su hash, diagnósticos y últimos resultados realmente registrados. El programador revisa y envía el mensaje. Se mantienen la revisión de cambios en varios archivos, pruebas y restauración de R17.

## Lantern, entornos y máquinas

Se mantienen los entornos Python por sesión y los descriptores reproducibles `.tern` con exportación y reconstrucción. La biblioteca de máquinas añade medios ISO y QCOW2 independientes importados mediante SHA-256. Copia el medio y conserva el original. Los clones QCOW2 separan la base de los cambios y crecen al utilizarse.

Las máquinas del proyecto permiten elegir RAM, CPU y disco, consola serie o ventana gráfica de QEMU, guardar y recuperar una sesión con `.tern`, y exportar un disco comprimido sin archivo base. Una sesión temporal se elimina al cerrarse; una sesión guardada conserva el disco. Es necesario detener una máquina antes de exportarla. El descriptor por sí solo no contiene los bytes del disco ni hace portable una ISO.

El catálogo enlaza con Arch, Debian, Kali, Microsoft y Apple. Las imágenes no se descargan automáticamente ni se redistribuyen dentro de Zénit. El medio debe corresponder a x86-64 y a su modo de arranque. La consola serie requiere configuración en el invitado; el modo gráfico requiere un backend gráfico de QEMU. Esta edición utiliza emulación por software. Windows 11 necesita TPM/UEFI que este perfil local todavía no prepara: se conecta una VM existente por SSH. macOS se conecta por SSH a hardware Apple. No se certifica el arranque de cada distribución o versión de Windows sin una prueba específica.

## Actualizaciones

En Ajustes → General → Actualizaciones y novedades se elige Estable o Estable y preview. Las versiones publicadas en el repositorio oficial se descargan con reanudación y SHA-256. La descarga nunca inicia la instalación.

En Windows, Instalar y reiniciar prepara el instalador verificado, registra la sesión, espera a que cierre el editor, copia metadatos de recuperación, instala en una carpeta de versión independiente y abre el lanzador estable con el proyecto anterior. Se conservan los SDK y payloads anteriores. El proceso se detiene ante ventanas externas, trabajos, terminales o parches binarios pendientes. Los cambios de texto recuperados siguen sin guardar en los archivos fuente. No se fuerzan cierres de procesos. En macOS y Linux se abre el paquete nativo mediante el instalador del sistema; el reinicio automático de Windows no se presenta como verificado en esos sistemas.

Al abrir una versión nueva en la aplicación de escritorio se presenta su panel de novedades una vez. También puede consultarse manualmente. La disponibilidad pública de una actualización depende de publicar su release y sus artefactos con hash; compilar localmente no publica una release.

El instalador comprueba el presupuesto de longitud de las rutas de Windows antes de iniciar la instalación. La actualización automática realiza esta comprobación antes de pedir el cierre del editor, de modo que una ruta incompatible no interrumpe la sesión.

## Extensiones

Los avisos informativos de instalación se agrupan en un recibo de compatibilidad. Las tarjetas mantienen identidad, descripción y acciones alineadas. La compatibilidad añade las factorías FileIsADirectory y FileNotADirectory y códigos FileSystemError reales. La matriz distingue las pruebas de comportamiento de una simple activación y queda ligada a versión y SHA-256 exactos.

La auditoría encontró 16 paquetes en el perfil de prueba. Quince se activaron; Jupyter sigue requiriendo el modelo de documentos notebook, no implementado. Su activación y sus kernels no se anuncian como compatibles.

## Validación

Pruebas específicas: `tests/test_project_workflows.py`, `tests/test_release_055.py`, `tests/test_extension_fs_errors.py` y `tests/check_055_interface.py`. Se ejecutan sobre proyectos y perfiles temporales. Los recibos y capturas locales se guardan en `qa-output/055-*`. Las pruebas de discos y compilación usan herramientas reales disponibles en el SDK; una omisión de una prueba se registra como tal.
