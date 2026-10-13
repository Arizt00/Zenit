# Implementación · Zénit 0.5.4 R2

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
