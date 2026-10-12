# Implementación · Zénit 0.5.4 R1

## Resultado

0.5.4 R1 conecta los temas de iconos instalados con el explorador, las pestañas y las
vistas de archivos. Refina Mi actividad, Ajustes, Extensiones, acceso a proveedores
y Debug. Corrige la decoración de los menús que Monaco añade a un ShadowRoot ya
existente. La confianza se recuerda por carpeta y existe un modo directo para
evitar confirmaciones rutinarias. Monaco, PTY, proveedores, Open VSX/VSIX, DAP/LSP,
Lantern y Laboratory siguen siendo servicios reales.

La revisión no acredita todavía el 90 % global de VS Code. Tampoco afirma que
se haya entrenado un modelo nuevo o que las predicciones de Melody sean perfectas.
Los informes y capturas distinguen ejecución real, recursos instalados y fixtures.

## Iconos y paridad

- `appearance.iconTheme`: automático, Zénit, sin iconos o identidad instalada.
  Selector con búsqueda, teclado y previsualizaciones de recursos del paquete;
  acceso desde Apariencia y desde la propia tarjeta de la extensión.
- Asociaciones por nombre, extensión múltiple, padre directo y lenguaje;
  carpetas, raíces, expansión, mapas específicos, light/highContrast y twisties.
  Los cambios de iconos no crean eventos falsos de ColorThemeKind.
- SVG y raster locales; fuentes WOFF/WOFF2/TTF/OTF con FontFace, tamaño heredado,
  peso/estilo permitidos y liberación al cambiar de conjunto. Recursos de hasta
  512 KB por imagen, 2 MB por fuente y 8 MB por tema; 4000 definiciones y 5 temas
  por paquete. Los SVG pueden reutilizar geometría con referencias internas `#id`;
  se rechazan scripts, entidades, recursos externos y rutas fuera del paquete.
- Material Icon Theme real: 1251 definiciones cargadas y
  0 recursos rechazados. Se comprueba expansión de carpeta con dos SVG
  distintos, selección persistente y restauración tras recargar; no se inicia
  el host de Material para aplicar sus contribuciones declarativas.
- `workbench.iconTheme` global usa el id de declaración de VS Code: lectura,
  propiedad directa, has/inspect/update, null para quitar iconos y undefined para
  restaurar automático. Los eventos `onDidChangeConfiguration` reflejan cambios.
- `workbench.action.selectIconTheme` abre el selector real y espera acuse del
  renderer, como selectTheme/showCommands/quickOpen/openSettings. Se prueban
  los cinco comandos desde una extensión Node real.

Las reglas de asociación se contrastaron con la [documentación oficial de
File Icon Theme](https://code.visualstudio.com/api/extension-guides/file-icon-theme).
La matriz de cobertura y pendientes está en `docs/VSCODE_PARITY_054_R1.md`.

## Permisos y persistencia

`backend/permissions.py` guarda decisiones locales con escritura atómica en
`workspace-permissions.json`. Usa la ruta resuelta y normalizada, almacenada como
SHA-256: una autorización solo afecta a esa carpeta exacta. No escribe decisiones
en el proyecto. Reiniciar o volver a la carpeta conserva la elección. Revocar
detiene los servicios y prevalece incluso sobre el modo directo.

`security.confirmRoutineActions=false` evita avisos adicionales para acciones
solicitadas: ejecución, LSP, iniciar motores, consultas/edición en vivo de Melody,
ayuda en tiempo real, cierre de terminal y borrado a papelera/desinstalación. La
sesión de consejos continúa desactivada al arrancar; solo comienza al solicitarla.
La revisión de planes de archivos y los bloqueos por cambios sin guardar/conflictos
siguen funcionando. La preferencia predeterminada del producto es confirmaciones;
en la instalación del usuario se activa modo directo por su petición explícita.

## Interfaz y arquitectura

| Superficie | Cambio verificable |
| --- | --- |
| Mi actividad | Hoja de 800 px en dos columnas: identidad local, recuentos reales, Archivos/Proyectos con teclado, filtro/Ctrl+F, grupos temporales, indicador Abierto basado en los modelos reales y acceso directo al archivo/proyecto. |
| Ajustes | Hoja máxima de 960×740, navegación compacta, grupos redondeados, tema efectivo visible y selector de iconos. Las categorías conservan nodos, foco y scroll. |
| Extensiones | Cabecera de 136 px, tarjetas finas y acción Elegir iconos solo en paquetes que aportan iconThemes. Mantiene búsqueda, revisión, estados reales, VSIX y gestión de hosts. |
| Debug | Título funcional de 26 px y zona de estado vacía delimitada. Mantiene controles, breakpoints, variables, pila, salida y estado real del debugger. |
| Acceso a proveedores | Cabecera identificada, estado separado, botones compactos y detalles plegables. El acceso continúa mediante el cliente oficial; no se inventa un login propio ni se inicia sesión durante las pruebas. |
| Monaco | Observador por ShadowRoot, decoración de inserciones tardías y liberación de observadores al retirar el host; misma familia SVG. |
| Inicio | Acción Abrir proyecto con icono coherente y jerarquía más definida; permanece a pantalla completa, con el mismo paisaje, geometría Blender y material Babylon/WebGL2. |
| Melody | Conserva Markdown, selección real, planes/undo, revisión vinculada a versión/cursor, sugerencias aceptadas explícitamente y la voz nueva Qwen de Emma. |

Se reutilizan los tokens centrales `space-*`, radius-control/card/sheet, border,
surface/field/glass, accent/text/secondary, motion-fast y focus. No hay opacity
aplicada al texto ni transition:all nueva. Se editan las hojas canónicas;
`icon-themes.css` y `accounts.css` agrupan los estilos de sus componentes.

Archivos principales: `backend/permissions.py`, `preferences.py`, `server.py`,
`platform_services.py`, `extensions.py`, `extension_services.py`,
`extension_runtime.py`, `extension_api.cjs`; `web/src/file-icon-theme.js`,
`icons.js`, `theme-picker.js`, `workbench.js`, `extension-services.js`, `app.js`,
`studio.js`, `accounts.js`, `monaco-overlays.js`, `debug-workspace.js`,
`melody-companion.js`, `preview.js`, `explorer-menu.js`; `web/design/` y
`design.css`; pruebas `test_workspace_permissions.py`, `test_extension_icon_theme.py`,
`test_file_icon_theme.mjs`, `test_ui_icons_permissions_r14.py` y el recorrido
de comandos existente. Versiones y empaquetado se incrementan a 0.5.4 R1.

## Validación

- 304 pruebas Python: 299 pasan y 5 omisiones explícitas. 95 pruebas JavaScript,
  63 comprobaciones de sintaxis. Nuevas verificaciones de recursos locales,
  prioridad de asociaciones, fuentes, configuración Node y confianza duradera.
- 94 comprobaciones UI: {"icons-ui": 12, "refinement": 11, "correction": 21, "voice-ui": 14, "themes": 10, "files": 7, "debug": 12, "textmate": 7}.
- Se prueban 89 variantes de color, persistencia, split, ventanas auxiliares,
  foco y selección, además de Material y una TTF local real.
- Tres terminales CMD ConPTY siguen recibiendo teclado; la separación de Proyecto
  conserva encabezado y árbol; los planes de Melody crean/borran/recuperan archivos
  reales con un transporte de modelo explícitamente identificado como fixture.
- Debug Python calcula `answer = 42` al avanzar; la salida y niveles de logs
  pertenecen a una extensión Node real. Inactivo/pausado: cero mutaciones en las
  muestras. No se sustituyen diagnósticos ni salidas por texto de demo.
- 13 vistas nativas WebView2 y 24 combinaciones de resolución/escala emulada,
  72 capturas. Sin overflow global ni errores JS. Los pilares de composición
  conservan la tolerancia de 2 px; los ocho goldens originales no se modifican.
- Se reproducen los 4.24 s del WAV generado por la identidad nueva Emma/Qwen en
  R12. Esto comprueba controles y reproducción, no una nueva generación ni la
  calidad de otros proveedores. No se conecta una suscripción ChatGPT a una API.

Los fallos encontrados durante esta iteración se corrigieron y volvieron a
comprobar: borde doble del buscador de actividad, grupos sin esquinas en Apariencia,
decoración tardía de menús y SVG de Material que reutilizaban paths locales.

## Rendimiento medido

Muestra nativa de inicio: 3001.1 ms, 225
intervalos rAF, mediana 12.5 ms, p95
16.8 ms, máximo 33.3 ms.
CPU de render WebGL p95 0.60 ms; sin long tasks
observadas. Un loop visible y cero loops para la esfera oculta. En la muestra
inactiva de 2 s no hay mutaciones ni dibujo. Estos valores no equivalen a tiempo
GPU o a una garantía de 60 FPS en cada equipo; no se reclama animación perfecta.

## Distribución

Se prepara build Windows 0.5.4 R1 con manifiesto/SHA-256, validación del runtime
congelado e instalación junto al payload anterior. El recibo de distribución
verificada se añade después de publicar e instalar. No se reconstruyen aquí
Linux/macOS. Límites completos: `KNOWN_LIMITATIONS.md`.


## Distribución verificada · 0.5.4 R1

El build procede de `521d4428fab46787945e544dd7af6eb1dd9bfbbf` y se publica en
[GitHub](https://github.com/Arizt00/Zenit/releases/tag/v0.5.4-preview.1).
Instalador: 113118365 bytes; portable:
70878607 bytes. Los cinco assets tienen SHA-256
confirmado por GitHub y las releases anteriores se conservan.

Se superan 15 comprobaciones del paquete nativo y 15 del helper instalado.
Los 107 archivos de frontend/assets/bridges coinciden con el build. El
runtime instalado carga los 1251 iconos Material, conserva el tema en el
Monaco dividido y verifica revocación persistente incluso en modo directo.
Melody no envía consultas al arrancar; su nueva voz Emma se sigue resolviendo.

`app-0.5.4-R1` conserva el payload anterior, los cuatro archivos de perfil
comprobados y el índice/selecciones del SDK. Tras comprobar esa conservación,
se cambian únicamente dos preferencias solicitadas: modo directo y selección
de Material Icon Theme. El tema de color, proveedor y conexión de voz quedan
conservados. No se cierran ventanas previas ni se descartan búferes. Esas
ventanas seguirán usando su revisión anterior hasta abrir el nuevo runtime.

La respuesta real de GitHub permite al actualizador 0.5.3 R13 seleccionar
0.5.4 R1 con el SHA correcto. Los recibos están en
`tests/visual/evidence/windows-054-r1-*.json`.
