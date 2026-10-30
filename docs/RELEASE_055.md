# Zénit 0.5.5 · R6

## R6 · Auditoría de compatibilidad y cierre de procesos

El adaptador de sugerencias de extensiones conserva listas incompletas, contexto de activación, categorías de símbolos, fragmentos, etiquetas estructuradas y rangos de inserción y sustitución. Se añade `resolveCompletionItem` con referencias al elemento original y rechazo de respuestas caducadas. Varios proveedores del mismo motor comparten un adaptador de Monaco para evitar duplicados. Una excepción de un proveedor conserva los resultados de los demás; el error queda registrado y se retira de las capacidades cuando se recupera. La documentación diferida no puede reemplazar la edición principal ni los criterios de ordenación de un elemento ya mostrado.

Las reproducciones de Lantern distinguen pruebas aprobadas, fallos reproducidos, salidas coincidentes, discrepancias y ejecuciones incompletas. Terminar un ensayo conserva una propuesta recibida mientras se ejecutaba. HILO limpia el consumo muestreado al quedar inactivo y muestra los presupuestos actuales aunque no haya trabajo en marcha.

La selección explícita de WSL activa su descubrimiento cuando todavía no se ha consultado el inventario. Los invitados de QEMU conservan sus reservas y ciclo de vida propios: el apagado ordenado precede a la cancelación genérica y no se fuerza un escritor de disco que siga activo. Se distingue la terminación del proceso de un puente ConPTY que todavía esté esperando la señal de cierre.

La auditoría y las pruebas se documentan en `qa-output/audit-20261030.json`. La activación de una extensión no certifica todos sus comandos, adaptadores ni servicios remotos.

## R6 · Investigación verificable y prioridad de interacción

Melody conecta los resultados registrados con su revisión de fuentes, dependencias declaradas, herramientas, entorno y destino. **Investigar resultado** conserva observaciones e interpretación por separado y permite consultar fuentes capturadas, comparar una prueba anterior aprobada cuando existe, revisar las órdenes y repetir en copias locales. Se pueden excluir fragmentos de la propuesta, probar la selección, revisarla antes de aplicarla y restaurar el conjunto en la ventana actual. Las fuentes originales no cambian durante la reproducción. La ausencia de evidencia histórica, versiones instaladas o estado del depurador se muestra sin presumirla.

HILO mantiene su papel interno. Se separan las acciones breves de archivos del mantenimiento y se aplica un presupuesto compartido a los procesos de herramientas registrados, con menor prioridad para el trabajo de fondo, afinidad de CPU cuando está disponible y control de RAM mediante muestreo. La cancelación conserva el seguimiento de descendientes. La interfaz del editor conserva su propia afinidad. La reutilización válida de compilaciones sigue verificando fuentes, dependencias, herramientas, entorno y artefactos.

Los ensayos son locales y secuenciales; las copias no son un sandbox. Dos observaciones coincidentes no prueban determinismo ni causalidad. La restauración de cambios depende del recibo de la ventana actual. El alcance, límites de captura y controles de privacidad se detallan en [Investigaciones verificables](VERIFIABLE_INVESTIGATIONS.md).

## R6 · Continuidad y claridad de la interfaz

Se conserva la identidad visual del inicio, incluidos el paisaje y la esfera. Se añaden búsqueda en archivos recientes, acceso a la recuperación de sesión y proyectos y espacios fijados. Los fijados se guardan en el perfil y se pueden gestionar desde Actividad y Espacios guardados. En ventanas bajas, el inicio utiliza una composición vertical sin superponer los accesos.

Las herramientas de navegación y lenguaje del editor aparecen según el archivo actual. Las pestañas distinguen el archivo activo y los cambios sin guardar; los grupos temporales indican su contenido y pendientes. Volver al conjunto de pestañas muestra todos sus archivos. Un indicador separado permite localizar los documentos abiertos en otras ventanas. Los controles de cabecera mantienen su orden y alineación, con botones de 32 píxeles en densidad cómoda y 28 en compacta.

Proyecto muestra el número de elementos y el destino completo antes de soltar, sin desplazar el árbol durante el arrastre. Escape cancela. Alt+M desde el árbol abre la elección de destino y Ctrl+Z deshace el último movimiento u orden desde Proyecto. Se conservan hasta 16 operaciones de esta sesión; el motor verifica la identidad de los archivos y rechaza un deshacer que sobrescribiría otro archivo. Los cambios realizados después del movimiento y los búferes pendientes se conservan.

La consola identifica su programa, destino, estado y acción de detener independientemente del archivo seleccionado en el editor. **Escribir aquí** dirige el foco a la entrada de ese programa; Alt+I funciona desde la consola. La preparación deshabilita la entrada hasta que el programa toma su control y el fin del proceso actualiza inmediatamente su estado. Los terminales separados conservan el contexto de ejecución suministrado por el servicio.

Las ayudas mantienen el fondo con 35 % de transparencia y el texto opaco. Apariencia permite elegir **Fondo sólido en menús y ayudas**, y se respetan el movimiento reducido y el contraste forzado del sistema. La documentación y los diagnósticos extensos siguen disponibles en un detalle persistente. Las cancelaciones LSP por cambios del documento se tratan como resultados descartados, sin ocultar los errores reales del servidor.

Actividad ofrece **Resultados y cambios** para consultar las ejecuciones registradas y los resultados de pruebas del proyecto, o el último conjunto de cambios revisado. Abrirlos conserva una instantánea y no repite órdenes ni guarda archivos. Los resultados de terminal y el último conjunto de cambios corresponden a la sesión actual; los historiales de ejecución y pruebas conservan la persistencia de sus respectivos servicios.

## R2 · Referencias, casos y continuidad

Se corrigen los iconos de los archivos recientes del inicio: un contenedor de imagen independiente evita que hereden el crecimiento del texto. Se comprueban con Material Icon Theme instalado y en cuatro tamaños de ventana. Actividad mantiene su filtro por proyecto y distingue el singular del plural. Los formularios, indicadores de foco y superficies de resultados comparten su estilo. La pila de arrastre utiliza sus dimensiones reales para permanecer dentro de la ventana, también junto al borde inferior.

Melody añade **Huella de cambio** en Herramientas y memoria. Examina un máximo de 400 fuentes y 6 MB, excluye archivos generados y secretos del árbol, identifica referencias estáticas y posibles pruebas relacionadas hasta cuatro niveles, y registra los archivos consultados y sus hashes. Permite abrir cada referencia o preparar una consulta revisable. Las importaciones dinámicas, macros y opciones del compilador pueden producir relaciones adicionales; el informe no representa un análisis semántico completo. La vista de respuesta evita programar fotogramas y desplazar contenido cuando no ha llegado texto nuevo.

Lantern incorpora **Matriz de casos** y **Comparar revisiones** desde su engranaje. La matriz revisa entradas, salidas esperadas, códigos y límites antes de ejecutar las copias del búfer, de una en una. Cada caso usa una copia independiente del mismo contexto preparado. La interfaz propone hasta tres casos y el servicio admite hasta seis. Cancelar impide iniciar el siguiente caso. Un fallo de compilación no puede pasar como resultado esperado del programa. Las copias conservan los permisos del usuario y no son un sandbox del sistema operativo.

El comparador utiliza dos revisiones reales del historial, sus códigos, huellas de fuente y salida, tiempos y resultados de reglas. No inicia otro proceso. Las diferencias muestran extractos limitados; la equivalencia depende de las huellas de la captura completa. Las revisiones anteriores a R2 sin esas huellas no se declaran equivalentes. Laboratorio añade navegación por teclado entre registros, instrucciones y memoria. Depuración permite copiar la instantánea de una pausa desde Variables.

La consola admite perfiles de lenguajes adicionales mediante **SDK y lenguajes → configuración de lenguajes**: un identificador, `extensions` y órdenes `run`, `check` o `build` expresadas como arrays de argumentos. Por ejemplo, un perfil puede asociar `.lua` con `["ruta/al/interprete", "${file}"]`. El intérprete debe estar instalado. No se ejecutan cadenas de shell. Se rechazan asociaciones ambiguas o que sustituyan extensiones integradas; comprobar o compilar exige la orden correspondiente. La ejecución usa los límites y cancelación comunes del IDE.

La compatibilidad de extensiones amplía DiagnosticCollection: colecciones independientes aunque compartan nombre, lotes con URI repetidos, iteración con URI tipados, arrays de solo lectura, clear/delete/dispose, getDiagnostics agregado y eventos onDidChangeDiagnostics agrupados. Diagnostic utiliza Error por defecto y expone DiagnosticTag. Se conservan las mejoras de R1 descritas a continuación.

Esta entrega amplía los flujos de proyecto y unifica las superficies de ayuda del editor. Mantiene las preferencias, los proyectos y los SDK opcionales ya preparados.

## Tipografía y densidad

Las pantallas de trabajo comparten cuatro niveles de texto: título de panel, contenido, descripción secundaria y metadatos. Se centralizan en unidades relativas, con tamaños de referencia de 18, 13, 12 y 11 píxeles al tamaño de texto habitual. Las cabeceras repetidas de marca se ocultan; los rótulos de tareas y categorías usan texto normal y espaciado natural. El código y la terminal conservan sus propias preferencias de fuente.

Apariencia incluye una vista previa de esos cuatro niveles junto a Densidad. Cómoda mantiene cabeceras de 52 píxeles, filas de 34 y controles de 38; Compacta usa 44, 28 y 32, respectivamente, sin reducir la letra. Las cabeceras laterales y del editor permanecen alineadas en ambos modos. La densidad guardada se incorpora al HTML inicial para evitar un cambio de tamaño durante el arranque. El diseño utiliza las coordenadas lógicas de la ventana, sin multiplicar las fuentes por la escala del dispositivo.

Proyecto, editor, terminal y Melody comparten altura de cabecera, márgenes laterales de 12 píxeles, iconos de título de 18 y botones de 32 píxeles en densidad cómoda o 28 en compacta, con iconos de 16. Sus controles mantienen el orden contraer, separar en otra ventana y más opciones. En el editor, la primera posición activa o restaura el modo de concentración. Las pestañas permanecen en la misma fila; las herramientas específicas y los espacios guardados siguen disponibles desde Más opciones. Melody conserva una acción directa para detener la respuesta. Los grupos acoplados mantienen ese mismo orden al cambiar de panel, sin duplicar sus editores ni conexiones. Los menús eligen espacio por encima o por debajo del botón para no taparlo y permitir cerrarlos desde él.

## Documentación y acciones del editor

Los paneles de documentación, diagnósticos, avisos de acciones y menús contextuales comparten márgenes, iconos, separadores y una superficie con 35 % de transparencia y texto opaco. Los submenús identifican su grupo mediante un título y su icono. La referencia muestra el símbolo, lenguaje, archivo y posición; ajusta su altura al contenido y permanece dentro de la ventana, también después de la animación de apertura. Incluye copia y preparación de una consulta en Melody, sin enviar automáticamente el contenido.

La documentación y los diagnósticos ofrecen **Abrir detalle**. Este panel permanece debajo del editor hasta cerrarlo y conserva el contenido al cambiar de archivo o mover el puntero. Muestra la instantánea completa tomada al abrirlo, incluidos los mensajes relacionados y los bloques de código. Permite copiar el contenido, devolver el foco al editor y cerrar con Escape desde el propio panel. La tarjeta flotante de diagnósticos conserva su paginación sin barras de desplazamiento.

La interfaz y Monaco componen los fondos de los temas de extensión de la misma forma. Se corrige el contraste insuficiente de números de línea, texto de campos, ayudas y sugerencias; los colores de sintaxis legibles de cada tema se conservan. Las cabeceras utilizan su propio fondo y primer plano declarados. La prueba con los paquetes instalados verifica 39 variantes, cambios de fuente, ventanas separadas y recarga sin perder el búfer pendiente.

Los atajos Ctrl+Alt+1/2/3 reconocen también la posición física de los dígitos en distribuciones como AZERTY y la tecla virtual cuando Windows omite el código físico. Se verificaron los tres atajos en la aplicación instalada, con el editor enfocado, sin insertar caracteres en el archivo. La entrada de caracteres mediante AltGr no cambia el tema.

## Proyecto y Melody

Proyecto ofrece siete estructuras por lenguaje. C separa `src/`, `include/*.h` y `tests/`; C++ utiliza `*.hpp`. Ambos incluyen CMake, presets Debug, pruebas CTest y una base de comandos de compilación. NASM usa `src/*.asm` e `include/*.inc`. Java sigue la estructura de Maven con clases, pruebas y recursos. Python utiliza un paquete en `src/`, `pyproject.toml`, pruebas y su entorno virtual cuando existe. Rust incluye Cargo, biblioteca pública, programa y pruebas de integración. nC conserva la estructura creada por `ncc package init` y su compilador real.

Los resultados se separan en `build/<lenguaje>/<programa-identificador>/`, con un descriptor de las fuentes, interfaces, destino y órdenes reales. Las fuentes existentes conservan sus rutas. Compilar Python genera `.pyc` sin ejecutar el programa. En Rust se detectan Cargo y rustc de la toolchain instalada aunque Rustup no tenga una versión predeterminada; no se cambia la selección global del equipo. Los planes revisados incluyen las cabeceras y módulos del proyecto para rechazar una ejecución si sus entradas han cambiado.

Las compilaciones de nC usan NCC y conservan su manifiesto y ejecutable nativos. Se corrige una regla de preparación que creaba además una cabecera C vacía para nC y Rust: las cabeceras automáticas quedan limitadas a C y C++. Los proyectos CMake generados para nC siguen invocando NCC y no dependen de una cabecera `.h`. Las cabeceras que ya existan en el proyecto se conservan.

Melody y Emma reciben la misma identificación de nC y su compilador NCC. Al consultar una fuente nC o nombrar el lenguaje, se adjunta una referencia compacta de su sintaxis oficial y la ruta detectada del compilador, sin ejecutar comandos ni leer archivos adicionales del proyecto. La referencia también llega a los planes de varios archivos y a los proveedores por cuenta, API y Ollama. Las respuestas del modelo siguen requiriendo revisión y comprobación con el compilador.

El puente de Emma respeta el identificador elegido en Zénit, anuncia sus modelos realmente disponibles y rechaza un modelo ausente en lugar de cargar otro. Reserva contexto para la documentación y la salida, con un máximo local de 32768 tokens y un error claro cuando la selección es demasiado extensa.

En Ajustes → Inteligencia artificial → Emma, Modelos locales incorpora Qwen3.8-27B-Uncensored Q4_K_M de JonathanColetti. Su descarga opcional utiliza el gestor reanudable de Zénit, una revisión fija del repositorio y verificación SHA-256. El GGUF no se incluye en el instalador ni cambia el modelo actual al descargarse. Elegirlo no carga el motor: la carga sucede al enviar la siguiente consulta y requiere memoria suficiente y una versión compatible de llama.cpp.

Proyecto, SDK, dependencias, máquinas y las acciones del Laboratorio comparten cinco pasos: elegir, configurar, revisar, ejecutar y consultar el resultado. Cada revisión muestra los parámetros reales de la tarea; cambiar la configuración la descarta. La ejecución se inicia expresamente desde esa revisión, y el estado final distingue errores de operaciones completadas. Las tareas de paquetes conservan la salida en directo y su cancelación.

Proyecto separa trabajar con un archivo de crear una plantilla. Ambos muestran la revisión y el resultado en la misma página; la ejecución conserva su recibo y la salida en Actividad reciente. SDK separa bases preparadas de paquetes opcionales. La biblioteca de máquinas organiza importar medios, crear máquinas y recuperar sesiones, muestra los requisitos que faltan y revisa recursos, checksum y archivos antes de modificar el proyecto. Abrir una consola significa conectarla; su proceso sigue mostrando su propio estado en la terminal.

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

El lanzador estable comprueba también la inscripción en Aplicaciones instaladas desde el contexto real del escritorio. Repara nombre, versión, rutas y visibilidad si Windows conserva una entrada anterior; utiliza la versión del payload seleccionado. Una inscripción correcta no se reescribe ni cambia su fecha de instalación. Se respeta la opción de no registrar la aplicación y un fallo del registro no impide abrir el proyecto.

## Extensiones

Los avisos informativos de instalación se agrupan en un recibo de compatibilidad. Las tarjetas mantienen identidad, descripción y acciones alineadas. La compatibilidad añade las factorías FileIsADirectory y FileNotADirectory y códigos FileSystemError reales. La matriz distingue las pruebas de comportamiento de una simple activación y queda ligada a versión y SHA-256 exactos.

La auditoría encontró 16 paquetes en el perfil de prueba. Quince se activaron; Jupyter sigue requiriendo el modelo de documentos notebook, no implementado. Su activación y sus kernels no se anuncian como compatibles.

## Organización del proyecto y pestañas temporales

El explorador permite seleccionar con Ctrl y Shift, arrastrar archivos y carpetas por lotes y guardar un orden manual por carpeta en el perfil local. Soltar cerca del borde superior o inferior de una fila cambia el orden; el centro de una carpeta mueve la selección dentro. La raíz del proyecto permite extraer archivos. Mantener un archivo arrastrado sobre otro durante 700 ms añade ese segundo archivo al arrastre, con un indicador de progreso.

Al arrastrar varias carpetas sobre otra se puede elegir entre moverlas dentro o fusionar sus contenidos. Los nombres repetidos se revisan y pueden conservarse con sufijos distintos. La aplicación nunca sustituye un archivo existente durante este flujo. El lote se comprueba de nuevo antes de aplicarlo; un fallo o una cancelación revierte los movimientos ya hechos. HILO coordina el trabajo sin crear procesos por archivo. Los búferes pendientes, la recuperación y los espacios guardados siguen las nuevas rutas. El archivo activo de Lantern y los recursos de una ejecución en curso requieren detener su ejecución antes de moverlos. Las referencias de CMake y otros archivos de configuración del proyecto no se reescriben automáticamente.

Arrastrar una pestaña abierta al centro de otra crea una carpeta temporal de pestañas. El grupo se puede renombrar con doble clic y deshacer con su icono de retroceso. Sus archivos permanecen en su ubicación original y los grupos se recuperan con la sesión. El editor comienza directamente con las pestañas, sin una identidad adicional de título e icono.

La selección del explorador permite preparar una consulta con varios archivos para Melody en su panel acoplado. El texto se revisa antes de enviarse. Las extensiones activas reciben eventos reales `workspace.onDidRenameFiles`, con URI tipados y documentos actualizados, para los movimientos del nuevo explorador.

Los entornos Lantern incorporan una comprobación del intérprete real y su aislamiento de paquetes. Las máquinas tienen una comprobación de QEMU, discos, medios de arranque, RAM y espacio disponible antes de arrancar; una comprobación no inicia otra máquina. Se mantienen los requisitos específicos de cada sistema invitado descritos arriba.

## Fluidez, ejecución y comprobación

Inicio mantiene la escena de Zénit y separa las acciones principales de los archivos recientes. Los accesos regresan al proyecto correspondiente; Actividad puede filtrar el proyecto actual sin borrar el historial. El explorador muestra la mano de agarre, cambia al arrastrar y desplaza el árbol al acercarse a sus bordes. Escape cancela el gesto y elimina su representación visual.

Melody incorpora **Contraprueba**, accesible desde Herramientas y memoria. Revisa las diferencias entre el archivo guardado y el búfer y ejecuta ambas variantes, en secuencia, sobre dos copias del mismo contexto del proyecto. Utiliza la misma entrada y compara salida y código de terminación. Conserva las fuentes, los hashes, las órdenes y el resultado; permite cancelar y preparar un mensaje de evidencia sin enviarlo automáticamente. Las copias no constituyen una máquina aislada: los programas conservan los permisos del usuario. Admite Este equipo y WSL; necesita las herramientas reales del lenguaje en el destino elegido.

Las consultas de solo lectura sobre archivos extensos preparan fragmentos numerados alrededor del cursor, diagnósticos y coincidencias con la pregunta. El mensaje identifica el contexto parcial y los rangos omitidos. No se permite sustituir todo el archivo desde una respuesta basada en ese contexto. La actualización visual de las herramientas de Melody se agrupa por fotograma y reutiliza el texto ya registrado del editor.

Lantern añade **Entrada repetible** y **Reglas de verificación**, configurables desde el engranaje del monitor. La entrada y su fin de archivo se repiten en cada revisión. Las reglas comprueban el código de salida y, opcionalmente, una salida exacta o un texto contenido; admiten un tiempo máximo. Se guardan por archivo. Cambiar las reglas de una sesión activa ofrece reiniciarla expresamente. Un fallo de la regla aparece separado del código de terminación real del programa y queda registrado en el historial.

La consola utiliza `run "ruta/archivo" -- argumentos`, `build "ruta/archivo"` y `check "ruta/archivo"` con el mismo motor y destino de ejecución del proyecto. Reconoce espacios, rutas relativas a su directorio y argumentos. Los lenguajes necesitan su runtime o compilador instalado/configurado; se verifican Python, C, C++, Java, NASM, Rust y nC. Durante una ejecución, `:eof` cierra la entrada. Cancelar una ejecución en cola la termina sin esperar a que se libere un trabajador y sin iniciar su proceso.

Laboratorio permite fijar una referencia de registros, filtrar por nombre o por valores cambiados y copiar el estado real del motor. Depuración filtra variables y resalta cambios entre pausas. Con el panel de depuración activo, F5 inicia o continúa, F10 avanza, F11 entra, Mayús+F11 sale y Mayús+F5 detiene; se respetan las capacidades del adaptador.

La compatibilidad con extensiones añade `languages.match` y aplica DocumentSelector a los proveedores: lenguaje, esquema, patrones y bases relativas. Una extensión no recibe un documento que no corresponde a su selector. También se corrige la pertenencia de URI a carpetas del proyecto y la resolución de rutas relativas. Esto amplía la compatibilidad comprobada, sin declarar paridad completa con VS Code.

Pruebas de esta ampliación: `tests/test_experience_055.py`, `tests/check_experience_055_ui.py`, `tests/test_focused_context.mjs` y `tests/test_extension_selectors.mjs`. La revisión visual usa proyectos y perfiles temporales; las llamadas a proveedores de IA externos no forman parte de esta prueba.

## Validación de la entrega

Pruebas específicas: `tests/test_project_workflows.py`, `tests/test_release_055.py`, `tests/test_extension_fs_errors.py`, `tests/test_project_organizer.py`, `tests/check_project_organizer_ui.py` y `tests/check_055_interface.py`. Se ejecutan sobre proyectos y perfiles temporales. Los recibos y capturas locales se guardan en `qa-output/055-*`. Las pruebas de discos y compilación usan herramientas reales disponibles en el SDK; una omisión de una prueba se registra como tal.


### R2 · refuerzo de herramientas y acabado

- Melody incorpora **Dossier de fallo**: fuentes consultadas, cambios del búfer, diagnósticos y última ejecución de Lantern. Identifica resultados anteriores por la huella del código. La consulta se prepara para revisión y no se envía automáticamente al proveedor.
- Lantern permite **guardar hasta seis casos por archivo**, recuperarlos al volver al proyecto y ejecutarlos después de revisar su plan.
- **Referencia de comportamiento** fija la salida completa y el código de una ejecución terminada. Las siguientes revisiones muestran coincidencia, cambio o entrada distinta. La referencia persiste en el proyecto y se puede quitar.
- El Laboratorio puede seguir la instrucción actual. Depuración puede fijar variables para compararlas entre pausas. El arrastre agrupa las mediciones y el movimiento en el ciclo de pantalla.
- Las terminales de extensiones respetan el perfil elegido y sus argumentos; `onDidChangeTerminalState` se emite al enviar los primeros datos aceptados.
- Se proporciona una compilación local identificada de nC Language 1.0.0-21v.zenit.1. Ejecuta ncc con argumentos estructurados y corrige la invocación de PowerShell externa. El compilador y las fuentes de los proyectos no se modifican. El VSIX se instala como actualización normal y se conserva una copia previa.

### R2 · cierre del servidor de GitLab y destinos revisados

- GitLab Duo: se implementan las sugerencias en línea desde el proveedor de la extensión hasta Monaco, con comprobación de versión del documento y descarte de respuestas obsoletas. Los mensajes de webviews pueden confirmar su inicio mientras el comando que los abrió está esperando; el transporte correlaciona cada respuesta por su identificador. Se verifica el servidor de lenguaje y el chat real por separado.
- Los comentarios de extensiones tienen controlador, hilos y actualización de contenido en una superficie propia del editor. El texto de las extensiones se muestra como texto, sin ejecutar HTML.
- Matriz y Contraprueba admiten WSL, además del equipo local. Conservan copias revisadas, la ejecución secuencial y la cancelación. El destino queda vinculado a la revisión. Un cambio de destino exige preparar otra revisión, sin recurrir al anfitrión.
- Los planes remotos incorporan Java, nC y los sufijos de lenguajes personalizados; compilar no debe iniciar el programa. NASM conserva su comprobación de arquitectura y ABI.
- SDK incorpora «Comprobar lenguaje y destino»: localiza las herramientas donde se ejecutará el archivo, separa compilador de adaptador DAP y prepara un diagnóstico revisable para Melody. Dossier de fallo incluye lenguaje, destino y entorno activo.
- Los casos de Lantern permiten editar su nombre y elegir salida exacta o texto contenido. La biblioteca de máquinas muestra motor, medios y sesiones en ejecución. Reabrir una consola existente reutiliza la máquina antes de comprobar RAM para un arranque nuevo.
- Un error en la limpieza de cancelación de un adaptador se registra y no interrumpe el trabajador de tareas ni deja dependencias esperando.

Pruebas específicas: `tests/test_closure_r2.py`, `tests/check_r2_wsl_review.py`, `tests/check_gitlab_duo_ui.py`, `tests/test_extension_inline_comments.mjs` y la prueba reentrante de `tests/test_extension_053.py`. La validación no envía consultas a proveedores de IA ni suplanta una licencia o cuenta GitLab. La integración Git 1.95.3 no ofrece el API opcional de detalles del historial solicitado por GitLab 7.2.5; este aviso no es un fallo de inicialización del servidor. La integración completa con VS Code continúa siendo parcial. SSH no sincroniza automáticamente las copias revisadas; el sistema y las imágenes de las máquinas virtuales deben prepararse por separado.


### R2 · integración de extensiones y terminales

- Se revisan los 18 paquetes instalados: 17 motores activados y un paquete de iconos declarativo. La matriz distingue estas pruebas de la compatibilidad completa.
- nC integra documentos virtuales, grafo del proyecto, tareas del compilador seleccionado y formato nfmt en Windows mediante una compilación de compatibilidad trazable 1.0.0-21v.zenit.2.
- Las funciones que una extensión registra después de activarse llegan al editor sin reiniciar su motor. Los grupos de configuración anidados conservan sus valores predeterminados.
- Cada shell puede ejecutar el archivo actual con entrada, salida, parada y estado propios. Las fases de compilación fallidas detienen el programa y las ejecuciones se limitan a una por terminal.
- Los cuadernos de Jupyter tienen celdas editables y un kernel Python local de Zénit, con variables por sesión, salida acotada, guardado nbformat y protección frente a modificaciones simultáneas del archivo. Los kernels remotos, magias y widgets no se dan por compatibles.
- QEMU se descubre también en Program Files y en las ubicaciones del instalador de Windows, sin exigir PATH ni una imagen Arch. SDK muestra qemu-system-x86_64 y qemu-img externos y permite volver a detectarlos.

### R2 · apariencia y variantes de nC

La integración carga `language-configuration.json` del paquete: parejas, cierre automático, comentarios e indentación. TextMate marca los tokens que admiten parejas equilibradas para que Monaco coloree correctamente los niveles anidados. Se conservan los tipos semánticos, sus modificadores, los selectores por lenguaje y la correspondencia `semanticTokenScopes`; las categorías sin estilo no eliminan el color léxico. Cambiar de tema actualiza también las categorías ya visibles.

La referencia visual seleccionada es la distribución JetBrains `nc-language-plugin-1.0.0.21v.zip`, SHA-256 `f8e18421f1707fb2db6270f3f694dccc083c37b6cc96489c93fb3b6823c759fb`. La adaptación local `1.0.0-21v.zenit.3` conserva sus seis SVG exactos para `.n`, `.nm`, `.nb`, `.nbb`, `.ncp` y `.nbo`. Las parejas de colores claro/oscuro se extraen del bytecode de `NcTextAttributes` distribuido, sin ejecutar IntelliJ en Zénit. El compilador y los servicios editoriales usan la integración nC actual; no se afirma compatibilidad binaria con las APIs de JetBrains.

El tema de iconos elegido se conserva para los demás lenguajes y se respeta el modo «sin iconos». `.init` mantiene su modo textual adicional con un icono de documento. `.nbo` textual usa su gramática de objeto IR; los archivos con bytes binarios siguen abriéndose en el editor hexadecimal. La comprobación real se encuentra en `tests/check_nc_appearance_ui.py` y los casos de integración en `tests/test_extension_language_appearance.mjs`. La procedencia de los recursos se conserva en `JETBRAINS-PROVENANCE.json` dentro del VSIX.

Los diagnósticos respetan el kit nativo o WSL elegido para la ejecución y la selección de capas del enrutador oficial de nC. El servicio nativo no se sustituye silenciosamente por WSL al fallar una herramienta auxiliar. La conversión de rutas a WSL emplea `--exec` y conserva separadores y espacios. Los analizadores de máquina/basal/primitive requieren `nc-sys-lsp` en su kit.

### R3 · integración actual de nC

La entrega se identifica como 0.5.5 R3 en el IDE, el instalador y los recursos de versión de Windows (0.5.5.3). Incluye la adaptación nC 1.0.0-21v.zenit.3 a partir de la distribución JetBrains elegida por el usuario: seis iconos originales, colores claro/oscuro, parejas e indentación y diagnóstico con el kit nativo o WSL seleccionado. Conserva los ajustes, proyectos y la recuperación de pestañas y texto pendiente. Las APIs internas de IntelliJ no se ejecutan en Monaco.

Se corrige una interrupción global de contribuciones: los lenguajes declarados sin sufijos, como GitHub Actions, se registran antes de aplicar su configuración. El catálogo completo de los 18 paquetes carga sus gramáticas, temas e iconos sin bloquear la apariencia de nC.

Al terminar la carga de iconos o cambiar de tema, las pestañas ya abiertas y las migas de navegación se actualizan junto al árbol. Se conserva la identidad de las pestañas, el contenido y los indicadores de cambios, sin repetir análisis del documento por un cambio visual.

### R3 · fiabilidad y medición del trabajo

La recuperación incluye los parches binarios pendientes, con su revisión original y la página hexadecimal abierta, además de los borradores de texto. Los parches permanecen en el perfil de recuperación y no escriben el archivo fuente. Un binario modificado, convertido a texto o eliminado se recupera en modo de conflicto: conserva los bytes pendientes para exportar y no permite guardarlos sobre otra revisión. Los espacios guardados contienen distribución y rutas; no duplican los parches ni los borradores. Se admiten hasta 64 KiB modificados por binario y 8 MiB de metadatos de parches por sesión. Tras recuperar, Deshacer/Rehacer opera sobre los cambios de bytes recuperados, sin reconstruir cada pulsación de la sesión anterior.

Lantern registra el contexto de fuentes y descriptores de compilación de su copia, las órdenes, el destino, el entorno seleccionado y la huella de la configuración del ejecutor. El dossier de Melody distingue una modificación del archivo principal de un cambio en una dependencia, un destino, un entorno o la configuración. Las revisiones antiguas sin contexto registrado se muestran sin verificar. La revisión es estática y acotada a 400 archivos y 6 MB; no prueba la reproducción de importaciones dinámicas, datos externos, variables de entorno ni instalaciones de herramientas. Alcanzar el límite impide declarar la evidencia vigente. No se envía el dossier al proveedor de IA automáticamente.

El análisis de referencias lee únicamente el texto que necesita, sin calcular las estadísticas editoriales de cada dependencia, y atiende a la cancelación entre archivos. HILO comparte las detecciones simultáneas y permite cancelar a quien espera sin interrumpir a los otros consumidores. Invalidar una detección descarta también el resultado del lector que la inició, además de los resultados de quienes esperaban. Sus contadores se consultan bajo demanda; HILO conserva su papel de motor interno.

Sistema y rendimiento incorpora **Informe de esta sesión**, también accesible desde la paleta de comandos. Separa el editor disponible, la recuperación de sesión, los catálogos y las detecciones opcionales; muestra la inicialización del servicio, reutilización de detecciones y ocupación del ejecutor. El informe no activa la lectura periódica de hardware ni ejecuta herramientas. Sus tiempos no incluyen el arranque completo del lanzador o de Windows y no constituyen una comparación con VS Code.

Pruebas de este bloque: `tests/test_reliability.py`, `tests/test_reliability.mjs` y `tests/check_reliability_ui.py`, sobre proyectos y perfiles temporales. La revisión visual cubre temas claro/oscuro, una ventana de 640 píxeles, recuperación de texto y bytes, conflicto con el disco y evidencia obsoleta por cambios en una dependencia.

### R3 · profundidad del editor

La búsqueda del proyecto consulta también los borradores de texto abiertos. El reemplazo literal conserva los filtros de carpeta, inclusión, exclusión, mayúsculas y palabra completa. Antes de aplicarlo se revisan los archivos afectados; cambiar un búfer o su revisión en disco invalida el conjunto. La revisión admite 64 archivos, 10 000 sustituciones y 4 MiB de texto, con archivos de hasta 1 MiB; alcanzar un límite de revisión exige reducir el ámbito. Los archivos omitidos por tamaño o codificación se indican. No se ofrece todavía búsqueda mediante expresiones regulares en el proyecto.

La navegación incorpora historial de posiciones con Alt+Izquierda y Alt+Derecha, símbolos con Ctrl+Mayús+O y búsqueda/reemplazo del proyecto con Ctrl+Mayús+H. Guardar como utiliza Ctrl+Mayús+S. Las definiciones toleran la diferencia de mayúsculas de la unidad de Windows sin aceptar rutas fuera del proyecto. Los menús muestran las funciones que anuncian los servicios activos.

El cliente LSP nativo incorpora referencias, declaraciones, implementaciones, definiciones de tipos, símbolos jerárquicos, resaltados de texto/lectura/escritura, plegado, formato, renombrado y acciones de código cuando el servidor las anuncia. Cada proveedor utiliza su propia sesión. Las acciones y los renombrados de texto, tanto nativos como de extensiones, pasan por una revisión de varios archivos. El último conjunto puede deshacerse con Ctrl+Z y rehacerse con Ctrl+Mayús+Z o Ctrl+Y mientras no haya modificaciones posteriores; los archivos de CoCo conservan su deshacer colaborativo. La revisión no guarda por sí misma: se mantienen las preferencias normales de guardado automático. El registro del conjunto es de la sesión actual. Las operaciones de creación, borrado y renombrado de recursos siguen su ruta específica de revisión de archivos.

Se corrige el cierre inmediato del cuadro F2: los controles interactivos permanecen dentro del árbol de foco de Monaco, también en editores divididos. Los diagnósticos y la documentación conservan su material transparente y su superficie propia, sin mezclarse con el código.

Git permite revisar las diferencias entre HEAD, índice y archivo guardado, y preparar o retirar un archivo del índice local. Utiliza un índice alternativo y el bloqueo de Git, comprueba revisiones y conserva los demás cambios preparados y los bytes de trabajo. Admite adiciones, borrados, renombrados e índices sin primer commit. El acceso existente al editor de conflictos se mantiene. Se requiere abrir la raíz del repositorio; este bloque no incorpora commits, sincronización remota ni preparación por fragmentos. Los binarios muestran tamaños, sin simular una comparación textual.

El explorador de pruebas permite revisar y repetir los casos fallidos de unittest y pytest, incluidos identificadores parametrizados. Se ejecutan los archivos guardados y se avisa de los borradores pendientes. Un cambio posterior de fuentes, dependencias, entorno o configuración marca el informe anterior y retira sus indicadores de resultado vigente. El descubrimiento AST y las huellas de fuentes se reutilizan mediante HILO; no se importa código al descubrir. Cargo y CTest mantienen la ejecución de sus suites; no se anuncia repetición individual para ellos.

«Funciones del lenguaje» distingue las capacidades anunciadas por los servicios activos de la comprobación del compilador, entorno, destino y adaptador de depuración. No garantiza que todos los lenguajes ofrezcan las mismas refactorizaciones ni que exista paridad completa con VS Code. La integración nativa se prueba con un servidor de protocolo controlado; la prueba real de nC usa la adaptación `1.0.0-21v.zenit.3`, su compilador y el renombrado en un editor dividido.

Validación: `tests/test_editor_depth.py`, `tests/test_editor_depth.mjs`, `tests/check_editor_depth_ui.py`, la ampliación de `tests/check_nc_appearance_ui.py` y la regresión de `tests/check_diagnostic_panel_ui.py`. Las pruebas utilizan proyectos, repositorios y perfiles temporales. La actualización de la instalación habitual conserva sus ajustes, proyectos y recuperación de sesión mediante una copia previa del perfil y la comprobación posterior del contenido.

## Trabajo entre equipos e investigación reproducible

CoCo recupera una conexión cuya primera respuesta se perdió y conserva las
peticiones de ejecución pendientes tras recargar el invitado. Crear y renombrar
archivos también admite reintentos sin repetir operaciones. Se comprueban permisos
actuales antes de aceptar una repetición. La salida compartida dispone de **Origen
de la ejecución**, con huellas, órdenes y vínculo al recibo de reconstrucción del
entorno; Melody puede recibir y explicar esta evidencia.

La reconstrucción de `.tern.zip` valida ruedas para el intérprete de destino,
rechaza inventarios desactualizados y vincula la instalación a los bytes revisados.
Comprueba las dependencias instaladas sin red y conserva un recibo. Los trabajos
se coordinan con HILO sin añadir un panel del motor ni bloquear el editor durante
el cálculo de huellas. Se mantienen la reutilización de compilaciones verificadas,
la prioridad de interacción y la cancelación de árboles del ejecutor existente.
QEMU detecta su aceleración disponible mediante inicialización, prueba breve del firmware y
confirmación QMP, con TCG como alternativa. El presupuesto previo al arranque
incluye RAM y CPU reservadas por las otras máquinas activas de Zénit.

Lantern conserva hasta 20 copias de fuentes de 128 kB para investigar revisiones,
fuera de la respuesta periódica de estado. **Localizar primer cambio** vuelve a
ejecutar entre 2 y 10 revisiones seleccionadas, dos veces cada una y en orden, sin
suponer que todos los cambios son monotónicos. Rechaza dependencias o configuración
incomparables y no atribuye una causa ante una salida inestable. Identifica el
primer resultado distinto entre las revisiones elegidas, no un commit culpable ni
un cambio histórico de herramientas.

**Reducir entrada fallida** elimina fragmentos de la entrada en copias del programa
revisado, conservando la misma firma de salida y código del fallo. Repite cada
candidato y se limita a 32 ensayos y 120 segundos; el informe indica si se agotó el
presupuesto. No garantiza un mínimo global ni reduce todavía el código fuente.
Ambos resultados pueden copiarse o prepararse como consulta a Melody; preparar la
consulta no la envía ni modifica el proyecto.

Este bloque se valida con fallos TCP inducidos, una ruta HTTPS pública desde la
misma estación, el conector real de VS Code y recorridos visuales de las funciones.
La prueba física LAN/Internet entre dos equipos sigue pendiente por falta de una
segunda estación. No amplía por sí sola la matriz de lenguajes, los adaptadores de
depuración ni toda la paridad de extensiones con VS Code.

## Continuidad de CoCo al reiniciar

El perfil conserva la sala, sus documentos CRDT, los permisos y las intenciones
antes de confirmar cambios y lanzar procesos. CoCo ofrece **Continuar sesión**
sin abrir conexiones ni ejecutar programas automáticamente. Un segundo backend
no puede recuperar una sala ya hospedada por otra instancia viva. Los reintentos
recuperan la identidad de la ejecución anterior; las ejecuciones sin resultado
confirmado se revisan antes de admitir otra intención para el mismo archivo.
Los procesos huérfanos se reconocen por PID y fecha de creación cuando ambos
quedaron registrados, y se pueden detener desde la revisión del anfitrión.

La recuperación conserva cambios externos en disco y permite consultar el origen
de una salida anterior. La nueva tarjeta de recuperación comparte la tipografía
y el espaciado de CoCo y adapta sus acciones al ancho de ventana. El conector
VS Code 0.2.2 conserva identidades al cambiar el endpoint de la sala y migra las
credenciales e intenciones de 0.2.1. Los límites de salida retenida, reconexión del
navegador entre dominios y resultados inciertos se detallan en `TEAM.md`.

## Profundidad de lenguajes y nC · R3

La adaptación nC 1.0.0-21v.zenit.4 conserva el origen JetBrains seleccionado y
corrige las definiciones, referencias, renombrados y símbolos que mezclaban
contenedores homónimos. Las refactorizaciones se revisan y se pueden deshacer en
el editor; se rechazan nombres en conflicto. La acción de cambiar a la extensión
de la familia correcta captura su documento y utiliza un WorkspaceEdit válido.
El evento de cambios de la API VS Code incluye su rango UTF-16 completo, evitando
el fallo del autoimportador al procesar las ediciones.

El explorador de pruebas reconoce los destinos CMake generados por Zénit y ofrece
una prueba de humo NCC por entrada main, con resultados asociados al archivo.
Cargo usa el compilador seleccionado. El puente de servidores de extensiones
expone renombrado y refactorizaciones de texto que antes omitía. Rust detecta el
servidor real de su toolchain y recibe las carpetas de trabajo mediante LSP.

Los recorridos de C, C++, Python, Rust y nC alto nivel se verifican con muestras
locales y herramientas reales. Java y NASM ensamblan/compilan, prueban y depuran,
pero su navegación y refactorización requieren JDT LS y asm-lsp, respectivamente,
que no están instalados en el equipo de esta comprobación. No se declara paridad
completa con VS Code, IntelliJ, todas las familias nC o todas las arquitecturas.

## R6 · entrega de las correcciones de lenguajes

La distribución solicitada se identifica como Zénit 0.5.5 R6 en el servicio, la
ventana, el instalador y los recursos de versión de Windows (0.5.5.6). Integra
las correcciones de profundidad de lenguajes comprobadas, incluida la adaptación
nC 1.0.0-21v.zenit.4 del plugin JetBrains seleccionado. El paquete mantiene el
formato ligero con Python incluido y los SDK externos configurados por separado.
La actualización conserva el perfil, la recuperación de sesión y los proyectos.

Lantern prepara ahora una revisión coherente con el archivo seguido y los otros
archivos de texto abiertos sin guardar. Una edición en una clase auxiliar también
invalida la revisión, aunque el archivo principal no cambie. La copia de ejecución
no guarda los originales; excluye binarios, secretos, archivos externos y salidas
generadas, y limita el conjunto de búferes a 200 archivos y 4 MiB.


### R6 · NCC y módulos del proyecto

Los fuentes nC generan un descriptor `ncc-build.json` y conservan su manifiesto
`ncc.package.json`. No generan cabeceras C ni CMake. Una raíz CMake intacta creada
por la antigua exportación de nC se archiva antes de retirarla; los CMake editados
y los proyectos mixtos permanecen intactos.

Las importaciones compactas `use <project:modulo>` se resuelven en una copia
privada, también cuando un módulo está junto al archivo principal. NCC comprueba
el proyecto antes de ejecutarlo. El enlace nativo se solicita expresamente al
compilador y comunica sus dependencias faltantes; la ejecución de proyecto no
certifica una sesión de depuración nativa multimódulo.

La adaptación `.zenit.7` mantiene los recursos del plugin JetBrains seleccionado.
F12 reconoce `modulo.contenedor.miembro`; los miembros de un contenedor local
respetan su ámbito al buscar referencias y renombrarlos. Las declaraciones
compactas y con llaves en otra línea conservan sus coordenadas UTF-16 originales.
Las importaciones no ocultan otras declaraciones escritas en su misma línea.
Rust carga la caché estándar cuando se necesita,
respetando las preferencias explícitas del usuario.

El enlazador de proyectos NCC detecta bibliotecas MSVC y Windows SDK completas
cuando `LIB` no está configurada. Omite toolsets más recientes que estén
incompletos y conserva una selección explícita del usuario. La detección se
limita al proceso de NCC: no cambia PATH, el registro ni las variables del sistema.

Se corrige la entrada interactiva de los proyectos nC en Windows. El proceso
NCC conserva la consola ConPTY que recibe las teclas, también en el panel
flotante, y los pasos de preparación no consumen la entrada del programa. La
consola de tareas y Lantern conservan la entrada por tubería, incluida la entrada
preparada y el cierre explícito de stdin.

Forge actualiza correctamente el árbol tras generar los archivos de compilación
por primera vez y continúa hasta abrir la terminal interactiva del programa.
Se verifica el enlace y la ejecución nativos de una muestra con dos módulos.

Los diagnósticos de módulos de nC pasan por NCC con una copia privada de los
búferes pendientes, incluidas las dependencias recuperadas de la sesión. Se
cancelan las comprobaciones obsoletas y se limitan a dos compiladores simultáneos.
El índice omite `.lumen`, entornos y resultados generados. El catálogo de ayudas
incluye las firmas publicadas por las 96 familias del NCC seleccionado; no
certifica que todas sus operaciones se hayan probado.

### R6 · renombrado nC comprobado y consultas cancelables

F2 puede proponer el renombrado de una función pública de un contenedor y de sus
llamadas explícitas `modulo.contenedor.funcion()` en fuentes `.n`/`.nc`. Utiliza
el analizador de la integración seleccionada para los ámbitos y las referencias;
NCC confirma la declaración pública con su AST y comprueba el proyecto anterior
y posterior en dos copias independientes. No ejecuta el programa para renombrar
ni guarda los originales. Los cambios pasan por la revisión de varios archivos
y pueden deshacerse y rehacerse como conjunto en la ventana actual.

Se rechazan colisiones, rutas de módulos ambiguas y proyectos que no pasan la
comprobación. La revisión caduca a los cinco minutos y se invalida si cambian
fuentes, búferes pendientes, dependencias locales, manifiesto, compilador
seleccionado o destino. Se limita a 200 fuentes de 128 kB, 4 MiB de fuentes,
64 archivos modificados, 1000 referencias y 16 entradas de proyecto; las
dependencias locales comprobadas admiten hasta 64 MiB. Requiere NCC local.
Esta función no representa un renombrado semántico general de todos los tipos,
aliases, llamadas dinámicas o familias de nC, ni añade depuración multimódulo.

Las consultas del editor a extensiones Node reciben un CancellationToken propio.
Al cambiar el texto, cancelar la petición en Monaco o retirar el proveedor, el
cliente descarta la respuesta pendiente y comunica la cancelación al motor.
Incluye consultas en cola y resolución diferida de sugerencias y acciones.
Las consultas siguen serializadas para conservar el documento de cada petición.
Un proveedor que ignore la señal retiene su turno hasta terminar o agotar el
tiempo máximo existente; no se promete interrumpir JavaScript arbitrario.
Las comprobaciones NCC del renombrado también cancelan sus procesos pendientes.

Una actualización de metadatos de la extensión, como una API opcional pendiente,
ya no retira los proveedores del editor si sus capacidades no han cambiado.
Esto evita que el cuadro F2 pierda el proveedor mientras se introduce el nombre.

Las pruebas utilizan perfiles y proyectos temporales: F12/F2, revisión, deshacer,
rehacer, conflictos con cambios pendientes y en disco, ejecución NCC con salida
42, aspecto de las siete modalidades nC y cancelación Monaco → HTTP → VSIX.
El VSIX y estos cambios de código se verifican por separado de la aplicación
instalada; no implican que el instalador habitual ya se haya sustituido.

## R7 · actualización desde Zénit

La revisión 0.5.5 R7 distribuye las correcciones comprobadas de nC, consultas de
extensiones, Melody, Lantern y coordinación de recursos. Se ofrece como Preview
de Windows x64 en Ajustes → Actualizaciones: primero se descarga y comprueba su
SHA-256; el usuario inicia la instalación y el IDE conserva su recuperación de
sesión, preferencias, proyectos y herramientas externas.

Incluye el paquete nC `1.0.0-21v.zenit.7`. En el primer arranque actualiza únicamente
la adaptación anterior cuya huella se ha incluido expresamente en el catálogo.
Conserva su configuración, su estado desactivado y las autorizaciones existentes
de un único paquete que coincidan con el grafo anterior. Las versiones propias,
los paquetes eliminados y los nuevos grafos de dependencias conservan la ruta
normal de elección y revisión. No se habilitan proyectos nuevos ni extensiones
que el usuario hubiera desactivado.
