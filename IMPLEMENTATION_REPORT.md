# Implementación · Zénit 0.5.4 R4

Distribución R4: Windows reconstruido y verificado con 15 comprobaciones del
paquete y 21 de la instalación congelada. El lanzador estable y los dos accesos
directos resuelven `app-0.5.4-R4`; se conservan los archivos de perfil, versiones
anteriores y el índice/selección del SDK compartido. La instalación compara 112
archivos de fuente/recursos. Se publica instalador, portable y tres ficheros de
verificación/SHA-256, con sus cinco digests remotos comprobados. Los ejecutables
continúan sin firma digital. Linux/macOS no se reconstruyen en esta entrega.

R4 corrige el cierre de menús y la entrada del terminal entre ventanas. Añade
búsqueda con posiciones exactas, editor exterior completo con controles de
ejecución y terminal inferior separable, sincronización de cambios y tareas,
evento de perfil/árbol y ejecución Forge mediante los entornos existentes.
Las órdenes explícitas de Melody admiten más formas y comparación Monaco.

[PREVIEW_054_R4](docs/PREVIEW_054_R4.md) describe el alcance y
[VSCODE_PARITY_054_R4](docs/VSCODE_PARITY_054_R4.md) sus límites.
Validación R4: 325 pruebas Python (320 pasan, 5 omitidas), 102 Node,
65 archivos con análisis de sintaxis y 90 comprobaciones de interfaz en siete
suites. Se usa CMD/ConPTY real y Java real con consola y lectura de entrada.
Las pruebas de propuestas/consejos de IA usan fixtures explícitos.

Las secciones que siguen conservan evidencia histórica de R3/R2.

# Implementación · Zénit 0.5.4 R3

R3 añade el fondo de foto real y difuminada a Tu perfil, sincronizado con el
recorte. Conserva la composición de Mi actividad aceptada por el usuario y mejora
el foco, los materiales y las estrellas discretas de Inicio. No sustituye la foto
local ni cambia la geometría Blender existente.

Melody recibe contexto de los archivos nombrados y revisiones capturadas antes
de la generación. Se corrige también la conexión ausente entre su host y Studio,
que impedía publicar correctamente los búferes de la sesión. La aplicación
directa respeta la preferencia de omitir confirmaciones rutinarias. Conserva
recuperación atómica, formatos originales, deshacer del disco y texto previo
sin guardar; cambios posteriores cancelan la aplicación. Los binarios se pueden
borrar por orden explícita, con copia de sus bytes. Rutas externas requieren
pertenecer a los documentos abiertos. No se envían credenciales al modelo.

El alcance nuevo se recoge en [PREVIEW_054_R3](docs/PREVIEW_054_R3.md) y
[VSCODE_PARITY_054_R3](docs/VSCODE_PARITY_054_R3.md). La generación de planes usa
fixtures deterministas en QA; no se certifica capacidad universal del proveedor.
Las secciones siguientes conservan la evidencia histórica de R2.

Validación R3: 317 pruebas Python (312 pasan, 5 omitidas), 101 pruebas Node,
64 comprobaciones de sintaxis JavaScript y 69 comprobaciones de interfaz en
seis recorridos. Se capturaron 15 vistas del WebView2 real al 150 % de escala
Windows; los cinco límites de composición medidos quedan dentro de 2 px CSS.
Las evidencias y capturas de prueba están en `tests/visual/evidence/054-r3-*`
y `tests/visual/current/054-r3`. La imagen privada del usuario no se añade a Git.

R2 reconstruye Inicio y Mi actividad con las referencias posteriores del usuario,
sus correcciones de material y la última petición de alineación y tipografía.
Corrige también causas concretas de apertura y persistencia de paneles.

## Mi actividad

Hoja de 1104 px en dos columnas. Identidad centrada: avatar 88 px, nombre 20 px,
descripción 13 px. La cabecera reutiliza exactamente la foto local del avatar,
ampliada, desenfocada y desvanecida. Sin foto hay un ornamento CSS sin añadir
otro contexto WebGL. Los recuentos proceden del historial real.

La tarjeta «Lo último que abriste» muestra el archivo y proyecto reales. Continuar
abre ese búfer y cambia de carpeta cuando corresponde. Pestañas y búsqueda
comparten una barra. Nombres, rutas y fechas tienen columnas estables y texto
legible. Tres filas caben completas en el viewport de referencia; historiales
largos conservan scroll sin barras visibles. Se mantienen filtro, Ctrl+F,
flechas/Home/End/Enter, Archivos/Proyectos, estado Abierto y menú por fila.
Quitar del historial no borra el archivo. Escape/Tab cierran el menú y devuelven
el foco sin cerrar la hoja. Recorte y guardado local de la foto permanecen.

## Inicio y animación

Inicio ocupa el viewport con el paisaje nocturno reconstruido de la referencia,
composición medida a 1672×941 y acciones reales. El cristal usa la geometría
Blender existente y Babylon/WebGL2; se ajustan iridiscencia, transparencia y órbita
del material principal. Melody conserva su material. Movimiento reducido y
superficies ocultas detienen las animaciones. La identidad nocturna de la portada
no cambia con el tema del editor. VISUAL_DIFF_REPORT.md distingue las diferencias
medidas de una supuesta igualdad de píxel o simulación óptica perfecta.

## Apertura

- waitForNativeBridge reconoce WebView2, Qt y el marcador desktop del servicio.
  Monaco carga después de la API nativa. Se reprodujo una inyección tardía que
  dejaba pywebview.domJSON sin registrar por el conflicto UMD/AMD. Seis ciclos
  con retraso artificial de 3 s conservan DOM nativo y módulo AMD Java real.
- El HTML incorpora el tema inicial del perfil. Un origen loopback nuevo recibe
  el tema antes del módulo de aplicación. El cache rechaza una identidad ajena.
- Bootstrap independiente con fases/fallos y Reintentar, incluso si no carga app.js.
- Lanzador estable Zenit.exe en la raíz: resuelve el payload activo del manifiesto
  y recupera la revisión completa más reciente si el manifiesto no es válido.
  Escritorio/Inicio apuntan a él; solo se migran pins propiedad de esta instalación.
- persistedLayout excluye ocultaciones temporales por separación nativa. Ventanas
  auxiliares no escriben la distribución principal. Se respetan paneles ocultos
  deliberadamente y la opción de restauración, sin resetear el perfil del usuario.

## Barras y Melody

DOM, Monaco y xterm ocultan sus barras, conservando rueda, teclado y trackpad;
no se sustituye overflow:auto por overflow:hidden. Los webviews independientes
de extensiones conservan su propio CSS.

Editar el modelo real caduca consejo, marca y voz asociada. Se comprueba con
Monaco y reproducción del WAV Qwen de Emma ya verificado; el transporte de
texto/audio se identifica como fixture. No se entrena ni se evalúa otro modelo.

## Evidencia

Cifras finales en tests/visual/evidence/054-r2-tests.json. Capturas QA en
 tests/visual/current/054-r2 y comparaciones en tests/visual/comparisons/054-r2.
Se conservan los ocho goldens originales. La captura nativa usa WebView2 y
CapturePreviewAsync al DPI Windows 150 %, sin emular coordenadas de clic;
conserva PNG físicos y copias a escala CSS. Los timeouts CDP observados se
registran como límites, sin atribuirles una causa universal.

R2 conserva los contratos de iconos, extensiones, terminales, Debug y Melody de
R1. docs/VSCODE_PARITY_054_R2.md y KNOWN_LIMITATIONS.md describen los pendientes.
No existe una medición que permita certificar 90 % global de VS Code.
