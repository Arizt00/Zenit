# Límites reales · Zénit 0.5.4 R3

R3 amplía Melody a archivos nombrados y documentos abiertos de la sesión, con
deshacer de disco/búfer. Los planes siguen acotados a 60 archivos y 400000 bytes
de texto; borrados individuales hasta 32 MiB, copia del lote hasta 64 MiB.
El contexto de texto total no supera 64000 caracteres. No se ejecutan comandos
de un plan, no se borran directorios y no se modifica .git/.lumen. Credenciales
y binarios se omiten del contexto enviado al proveedor. El botón de deshacer
pertenece a la sesión actual; las copias de recuperación sí quedan en disco.
Los tests de planes prueban el flujo real con un transporte determinista, no la
calidad del modelo. Los límites anteriores que siguen continúan vigentes, salvo
la descripción histórica de Melody restringida a archivos limpios/de texto.

1. **Paridad VS Code:** sigue siendo parcial. La activación real de siete de ocho
   paquetes probados no mide cobertura global ni garantiza todos sus comandos.
   No existe todavía una matriz suficiente para declarar 90 % de toda su API.
2. **Autenticación:** se admiten proveedores aportados por extensiones; faltan
   los brokers OAuth integrados de GitHub/Microsoft y persistencia completa de
   grants. GitHub Pull Requests permanece bloqueado sin su proveedor conectado.
3. **Virtual filesystem:** se despachan operaciones reales de proveedores. Falta
   integración completa de modelos, guardado, WorkspaceEdit y ventanas auxiliares
   para todos los esquemas virtuales. Un URI virtual no se convierte en una ruta local.
4. **Custom editors:** CustomTextEditor usa un documento real y webview. Documentos
   binarios CustomDocument con save/undo/backup completos no están implementados.
5. **Debug/puertos:** existen registros y dispatch de visualizadores y atributos
   de puertos. No hay UI automática completa de árboles de visualización, todos
   los when clauses ni transporte universal de forwarding de puertos.
6. **Eventos de archivos:** willCreate/Rename/Delete aplica al host iniciador de
   WorkspaceEdit. No se difunde todavía a cada host para todas las operaciones de
   UI, terminal o disco. El contrato no se anuncia como equivalencia global.
7. **Entorno/output/status:** R8 incorpora selector de canales, clear, hide/show,
   niveles Off/Trace/Debug/Info/Warning/Error y onDidChangeLogLevel reales. Faltan applyAtShellIntegration, todos los selectores
   glob y preferencias globales persistentes de nivel de registro. Mutaciones de
   entorno se aplican al crear nuevos procesos, no a shells que ya estaban abiertas.
8. **Language model API:** se registran e invocan herramientas explícitas. No hay
   broker universal de modelos de extensiones ni acceso automático a credenciales
   de Melody. Ninguna herramienta inventa tokens, modelos o resultados.
9. **Melody:** la calidad de consejos/predicciones depende del proveedor conectado.
   La nueva ayuda es opcional, hasta 12 consultas por sesión/3 por minuto, máximo
   64.000 caracteres por búfer. Las sugerencias mayores de ocho líneas no se
   presentan como inline completion. El transporte UI se verificó con una fixture;
   no es un benchmark de IA externa. No se certifican predicciones correctas.
10. **Cristal/fidelidad:** la geometría viene de Blender y el material se anima
    en Babylon/WebGL2; no es Cycles ni una simulación óptica físicamente exacta.
    El paisaje es un asset raster generado localmente, no un terreno 3D simulado. Los campos de luz e iconos tienen diferencias descritas
    en VISUAL_DIFF_REPORT. La bienvenida de dos columnas fue sustituida por el
    brief posterior del usuario, conservando sus ocho goldens originales intactos.
11. **Rendimiento:** las mediciones son muestras locales de CPU del renderer. No
    se midió tiempo GPU ni se garantiza la misma tasa en cada equipo/monitor.
    Recuperación de contexto y reducir movimiento se comprobaron en Edge con
    SwiftShader; la captura nativa comprobó WebGL2 con Intel/ANGLE. No cubre toda
    combinación de GPU, controlador o backend. No se afirma animación perfecta.
12. **Responsive:** 24 combinaciones de resolución/escala emulada. La captura
    WebView2 usa el host al 150 % y un viewport CDP. Faltan pruebas físicas de
    todos los DPI en varios monitores y de la misma UI en Linux/macOS.
13. **Toolchains/VM:** detección de ruta no certifica cada herramienta. Docker CLI
    necesita un daemon; no se distribuyen todas las dependencias ni compiladores
    históricos. El adaptador ASM no publica todos los flags. Los límites previos
    de imágenes macOS/Windows 7, licencias y virtualización permanecen.
14. **Arranque/captura nativos:** ya se habían observado timeouts antes del
    bootstrap de ventanas web. En esta fase una captura CDP de bienvenida también
    agotó el tiempo al compartir carga con otras pruebas; recorridos posteriores
    secuenciales completaron. La causa no está demostrada y no se considera cerrada
    solo porque las repeticiones pasan. Se conserva instrumentación de recursos.
15. **Distribución:** R10 prepara un instalador y portable Windows con revisión
    propia, manifiesto y SHA-256. No reconstruye aquí Linux/macOS ni firma/notariza
    los paquetes. Las releases anteriores se conservan. El actualizador reconoce
    la nueva revisión; la instalación se elige después de guardar el trabajo.

Los estados de compatibilidad parcial siguen visibles. Las pruebas no sustituyen
datos del usuario por salidas, diagnósticos, versiones o respuestas de IA inventados.

## Límites específicos de R7

- Laboratory detecta rutas; no ejecuta todos los compiladores al abrirse. Las acciones muestran sus respuestas reales en la terminal. Maven/Gradle comprueban su versión; no sustituyen el gestor completo de tareas de las extensiones.
- El paisaje de inicio tiene movimiento de composición y luz CSS; la esfera conserva su render WebGL2 independiente. No se garantiza 60 FPS en cada GPU o pantalla.
- Revisar, Explicar y Próximo paso ajustan el contexto y las instrucciones enviadas al proveedor existente. No hay un nuevo modelo predictivo entrenado ni una evaluación externa de calidad.
- No se añaden nuevas APIs de VS Code en R7. Los límites de compatibilidad anteriores siguen vigentes.

## Límites específicos de R8

- Los planes de Melody admiten hasta 60 archivos UTF-8 y 400000 bytes propuestos, dentro del proyecto abierto. Un proyecto completo se genera en una subcarpeta. No incluye ejecución de comandos, instalación de paquetes, binarios, borrado recursivo de carpetas ni edición de secretos o dependencias instaladas.
- Aplicar exige revisar el plan concreto. Los cambios externos y los búferes sin guardar bloquean la operación. Hay rollback frente a excepciones de escritura y copias persistentes en `.lumen/melody`; no es una transacción resistente a caídas del sistema. Deshacer desde el chat requiere la misma sesión y archivos que no hayan cambiado; las copias permanecen disponibles después de reiniciar.
- La generación UI usa un transporte de prueba explícito. Se acredita la creación/borrado/recuperación de archivos, no que cualquier modelo produzca un proyecto correcto ni que sus dependencias compilen.
- Depuración conserva los nodos al cerrar/reabrir y al cambiar inspector. Los muestreos inactivo y pausado sin cambios producen cero mutaciones; no certifican ausencia de flicker en cada motor, GPU o recorrido.
- El error de selección/entrada se verifica con tres sesiones CMD ConPTY y teclado real del navegador. No cubre todos los programas TUI, shells WSL ni todos los IME.
- No se declara 90 % global de VS Code. Las áreas pendientes 1–8 conservan sus límites; cada avance se acredita con contratos y pruebas concretos.


## Límites específicos de R9

- Se prueban 89 variantes de tres paquetes y los pares de color de los controles definidos. No se garantiza que cada tema de Open VSX o toda textura/transparencia mantenga contraste sin ajuste. La interfaz corrige colores ilegibles; Monaco conserva la configuración original del tema.
- La carga admite 128 variantes por paquete y 256 temas activos en total. Si se exceden estos límites aparece un error de contribución; no se anuncia que todas las variantes estén cargadas. La previsualización representa la paleta resuelta, no una captura completa de cada motor de editor.
- ColorThemeKind/eventos cubren los cuatro tipos y cambios reales de identidad, incluso entre dos temas del mismo tipo. No equivalen a toda la configuración, semántica TextMate, altas definiciones de contraste ni todas las API de temas de VS Code.
- Los enlaces de Melody se extraen de referencias a líneas válidas del texto devuelto, hasta seis por consejo. No verifican la corrección técnica del consejo. Caducan al cambiar el modelo/revisión; no editan ni borran archivos.
- La bienvenida nocturna usa la misma imagen y canvas, con composición CSS adaptada. Las muestras WebView2 de render CPU, frames y long tasks no certifican 60 FPS, tiempo GPU ni ausencia universal de flicker. Las ventanas del usuario no se reinician automáticamente.


## Límites específicos de R10

- El tema se conserva al crear una división y actualizar sus preferencias; seis recorridos reproducibles y las ventanas nativas probadas acreditan ese arreglo. No se garantiza que cada acción de una extensión o cada evento del sistema operativo conserve el tema.
- Colores RGB/RGBA se normalizan y componen sobre el editor real. Monaco/TextMate mantienen el color original del tema; no se impone el ajuste de contraste de la interfaz a todos los tokens. Algunos temas eligen comentarios deliberadamente tenues.
- .tmTheme y reglas JSON referenciadas son locales al paquete y tienen un límite de 3 MB por recurso. No se descargan archivos de sintaxis remotos. Se conserva el límite de herencia existente.
- Los scopes contextuales completos necesitan una gramática TextMate. El tokenizador lexical integrado de Monaco solamente traduce alias de categorías comunes. La capa semántica cubre selectores simples de tipo/modificador; lenguaje, comodines y todas las permutaciones de modificadores siguen pendientes.
- Los apartados de Melody solo organizan texto recibido. No verifican sus conclusiones ni inventan apartados ausentes. Insertar sugerencia exige el mismo modelo, versión y posición; se aplica al búfer y es deshacible, no guarda ni ejecuta. La calidad del modelo externo no se evalúa con las fixtures.
- La luz del fondo de inicio sigue siendo composición CSS sobre un asset local. Render/perfilado son muestras del host; no certifican 60 FPS en todos los equipos ni ausencia universal de flicker.


## R11 · voz y temas (histórico; voz sustituida en R12)

- Voz de Melody: requiere la instalación local original de Emma con la identidad
  MOSS aprobada. No se redistribuyen modelos ni referencias privadas; no hay
  fallback silencioso a una voz de sistema. Español, 2500 caracteres de prosa,
  bloques de código omitidos, una generación simultánea. La prueba real tardó
  61 s para 6,88 s de voz. La calidad no se extrapola a todos los textos.
- La configuración `workbench.colorTheme` está integrada para Global. Los targets
  Workspace/WorkspaceFolder se rechazan; el resto de getConfiguration conserva
  sus límites existentes. Nombres ambiguos requieren un identificador instalado.
- El cache de colores evita el fallback visible al recargar un tema ya renderizado.
  Al iniciar por primera vez no existe cache: se espera la contribución real.
- Análisis y predicciones de Melody conservan contexto y control de revisión,
  pero no han pasado un benchmark de calidad de todos los proveedores externos.


## R12 · voz vigente

La voz vigente es la nueva identidad de Emma elegida el 4 de octubre con Qwen.
Sustituye la selección MOSS de R11; el adaptador no vuelve a la anterior si falla.
Requiere la instalación local preparada de Emma y el modelo Qwen; los modelos y
referencias privadas no se redistribuyen. Español, 2500 caracteres de prosa,
bloques de código omitidos y un trabajo simultáneo. La petición real de prueba
tardó 37,28 s para 4,24 s de voz: todavía no es instantánea. La voz online de
OpenAI no se activa en esta revisión. Se mantienen los demás límites de R11.


## R13 · alcance añadido

- Se implementan cuatro comandos de apertura de controles con confirmación real.
  Esto no supone equivalencia de todos los comandos del workbench, de sus argumentos
  ni del inventario getCommands. Abrir el selector no significa que se aplique un tema.
- Markdown cubre títulos, fences, tablas, listas simples, citas, énfasis y enlaces
  http/https. No es un parser CommonMark completo: faltan listas anidadas, tablas con
  todas las alineaciones y construcciones avanzadas. HTML e imágenes no se ejecutan.
- Los checks de Melody usan fixtures UI explícitas. No se ha mejorado ni certificado
  la calidad de todos los proveedores, predicciones ni la tasa de acierto de consejos.
- La esfera continúa siendo un shader artístico con geometría Blender; los intervalos
  de frame observados no son 60 FPS estables. El paisaje sigue siendo raster y la
  emulación de escalas no sustituye pruebas de cada monitor/driver/DPI del sistema.
- La voz vigente sigue siendo Qwen de Emma, con sus dependencias locales y latencia
  de generación de R12. No se conecta una suscripción de ChatGPT a su API de audio.


## 0.5.4 R1 · alcance añadido

- Un intento de recarga en la herramienta de captura WebView2 agotó los 45 s
  de espera de ready. Se añadió diagnóstico de errores/estado y se repitió la
  captura completa con éxito, sin cambiar delays del producto. No se pudo
  atribuir una causa a ese intento; las muestras exitosas no prueban ausencia
  universal de fallos de arranque o recarga en todos los equipos.

- Los temas de archivos funcionan con asociaciones y recursos locales; Product
  Icon Themes para toda la iconografía del workbench no están implementados.
  Falta la herencia completa de iconos aportados por lenguajes y showLanguageModeIcons.
  Los SVG no cargan recursos externos; fuentes/definiciones grandes se limitan.
- workbench.iconTheme admite el perfil global. No hay override por carpeta o
  workspace; una selección ausente conserva la preferencia y usa un fallback
  visible. Los cinco comandos UI no equivalen al inventario completo de VS Code.
- El modo directo evita permisos rutinarios solicitados, no bypasses de
  credenciales, conflictos, búferes sin guardar o revisiones de planes de archivos.
  La revocación explícita siempre tiene prioridad. Nuevas instalaciones conservan
  confirmaciones por defecto; se activa directo en este equipo por petición del usuario.
- La hoja de acceso usa el cliente oficial de cada proveedor, no un servicio
  propio de autenticación de Zénit. Se revisa el diseño sin iniciar sesión ni
  probar las prestaciones de cuentas externas durante la regresión visual.
- La nueva voz Qwen de Emma, los consejos y predicciones conservan los límites
  documentados de R12/R13. No se implementa aquí voz de ChatGPT por suscripción
  ni un nuevo motor predictivo. No se certifica 90 % global de VS Code.


## 0.5.4 R2 · alcance añadido

- Se corrige una carrera UMD/AMD reproducida con WebView2. Los ciclos comprobados
  no certifican todas las cargas/drivers. Un Retry de la prueba de módulos agotó
  30 s; la repetición instrumentada pasó. Se conserva el diagnóstico de arranque.
- Capturas CDP nativas agotaron su tiempo de forma intermitente; la auditoría
  final usa CapturePreviewAsync y conserva sus PNG físicos. No acredita la causa
  universal de esos bloqueos. Un muestreo corto Edge/SwiftShader no avanzó el
  material; el recorrido completo repetido y el perfilado nativo sí lo hicieron.
- Se migran accesos propios. Abrir un exe anterior a R2 directamente por su ruta
  antigua sigue abriendo ese exe; no se modifican binarios antiguos ni enlaces ajenos.
- La portada reconstruida, reflejos artísticos, fuentes y escalado producen
  diferencias de píxel. Mi actividad sigue las correcciones posteriores de diseño;
  no sustituye datos reales por los archivos/avatar de las pruebas.
- Barras ocultas en DOM, Monaco y xterm; los webviews independientes de extensiones
  conservan su propio CSS. Voz Emma, predicciones y APIs mantienen límites R12/R1.
