# Implementación · Zénit 0.5.3 Preview R13

## Resultado y alcance

Esta revisión continúa las correcciones de R11/R12 y trabaja sobre las capturas
del editor, catálogo, conversación, perfil y portada. Mantiene Monaco, terminales
PTY, Open VSX/VSIX, proveedores de Melody, Lantern, Laboratory y depuración reales.
No sustituye estas funciones por una maqueta. Las referencias originales quedan
intactas; las dos últimas capturas aportadas se conservan por separado para comparar
la evolución solicitada. No certifica el 90 % de toda la API de VS Code.

## Componentes y archivos

| Cambio | Archivos funcionales | Contrato conservado |
| --- | --- | --- |
| Menú compacto, SVG coherentes y mismo aspecto en DOM/Shadow DOM | `web/src/monaco-overlays.js`, `web/src/icons.js`, `web/design/support.css` | Acciones y navegación de Monaco; paneles reales |
| Respuestas y consejos con títulos, listas, tablas, enlaces y código | `web/src/assistant-markdown.js`, `web/src/app.js`, `web/src/melody-companion.js`, `web/design/assistant-markdown.css`, `web/design/melody.css` | Texto real, copia exacta, revisión de edición, referencias de línea y lectura |
| Perfil en dos columnas | `web/src/studio.js`, `web/design/profile.css` | Arrastre, zoom, crop normalizado, WebP de 512 px, nombre y guardado local |
| Catálogo más ligero y miniatura del tema real | `web/src/workbench.js`, `web/design/catalogue.css` | Estado/compatibilidad, filtro, dependencias, VSIX, host y selector de variantes |
| Atmósfera de inicio por tema y refinamiento óptico | `web/design/welcome.css`, `web/src/glass.js` | Canvas persistente, Blender/Babylon/WebGL2, movimiento limitado y pausa |
| Cuatro comandos de extensiones confirmados por la interfaz | `backend/extension_services.py`, `web/src/extension-services.js` | Node real → backend → UI → respuesta; timeout/error si no se abre |
| Integración y metadatos R13 | `web/design.css`, `backend/version.py`, `packaging/version.txt`, `packaging/lumen.spec`, `web/src/setup.js`, `package.json` | Build e instalador identifican la revisión correcta |

Se retiran los estilos de perfil duplicados de `support.css`; el perfil tiene una
única hoja específica. El menú de Monaco inyecta una única definición tanto en el
documento como en los ShadowRoots; los glifos son decorativos y no sustituyen los
handlers del editor. El observer actúa al aparecer menús, sin reconstruir el
workbench en cada frame. Las animaciones respetan la preferencia global y reduced-motion.

## Sistema visual

Se reutilizan `web/design/tokens.css`: espacios 2/4/6/8/10/12/16/20/24/32 px,
radios de control/tarjeta/panel/hoja, superficies, texto, estados, bordes, sombras
y duración rápida/normal/lenta. Perfil, tablas, bloques de código y controles del
catálogo usan estos tokens. Las dimensiones del crop y la miniatura son geometría
del componente. Los valores del shader representan el material, no espaciado CSS.

La portada combina el fondo existente con una máscara dependiente del tema y
campos luminosos discretos. La esfera conserva la doble pared de Blender y su
renderizado Babylon; se ajustan el peso del color, el reflejo estrellado y la órbita.
No se presenta un paisaje raster como terreno 3D ni el shader como óptica físicamente exacta.

## Paridad de extensiones

`workbench.action.selectTheme`, `workbench.action.showCommands`,
`workbench.action.quickOpen` y `workbench.action.openSettings` abren el control real
correspondiente. Esperan hasta 12 s a la confirmación del renderer. La ausencia de
temas, un comando desconocido, falta de respuesta o proyecto sin confianza se
rechazan. Abrir el selector no equivale a aplicar un tema; la selección sigue
perteneciendo al usuario. Los controles globales pertenecen al workbench principal; las ventanas auxiliares no abren ni confirman la misma petición por duplicado. Tres tests Node adicionales verifican la propiedad de la petición y el rechazo de un control fallido. No se anuncia un resultado de compilación o depuración.

## Melody y la voz vigente

El renderer usa nodos de texto y elementos DOM; no ejecuta HTML del proveedor ni
carga imágenes. Solo admite enlaces http/https con noopener. El código conserva
sus espacios al copiarse. Las tablas pueden desplazarse dentro del panel. Los
consejos estructurados usan el mismo renderer; las predicciones siguen limitadas
a ocho líneas y a la revisión/cursor actuales, con aceptación explícita y Deshacer.

Se mantiene la nueva voz Qwen de Emma seleccionada en R12 mediante
`assistantVoice('emma')`, con verificación de identidad y sin fallback silencioso
a la antigua MOSS. La generación real de R12 produjo 4,24 s de audio en 37,28 s;
R13 vuelve a verificar el player con ese WAV, sin recargar el modelo ni copiar las
referencias privadas. La voz online de OpenAI no se activa en esta entrega.

## Validación

297 tests Python ejecutados: 292 pasan y 5 se omiten explícitamente. Pasan los
91 tests Node y los 62 controles de sintaxis. `tests/test_assistant_markdown.mjs`
comprueba preservación de contenido y fences; `tests/test_ui_command_ack.py`
verifica confirmación, error, timeout y confianza. El test nuevo de interfaz
`tests/test_ui_refinement_r13.py` utiliza una extensión Node real, un tema instalado,
un avatar QA generado y texto de prueba identificado; no mide calidad de IA externa.

- refinement: 11 comprobaciones, sin errores JS no controlados.
- correction: 21 comprobaciones, sin errores JS no controlados.
- voice-ui: 14 comprobaciones, sin errores JS no controlados.
- themes: 10 comprobaciones, sin errores JS no controlados.
- files-ui: 7 comprobaciones, sin errores JS no controlados.
- debug-output: 12 comprobaciones, sin errores JS no controlados.
- textmate: 7 comprobaciones, sin errores JS no controlados.

Las 13 vistas nativas usan WebView2 y DesktopAPI reales. Las cinco regiones de
geometría mayor quedan dentro de 2 px de tolerancia. La matriz repite seis tamaños
de 1280×720 a 3840×2160 y escalas 100/125/150/200 %: 24 casos, 72 capturas, sin
overflow global. Es emulación de escala de Edge, no un cambio del DPI del sistema.
Las pruebas de terminales usan tres sesiones ConPTY reales; las de Debug ejecutan
Python real y comprueban cero mutaciones DOM en estados idle/paused sin cambios.

## Rendimiento medido

WebView2 nativo, ventana QA: 101 muestras en 3.00 s; intervalo mediano 29.10 ms, p95 45.80 ms, máximo 75.10 ms. CPU del render Babylon: mediana 0.60 ms, p95 0.90 ms. No se registran long tasks ni eventos de pérdida de contexto en esa muestra. No es una garantía de 60 FPS.

El muestreo inactivo de dos segundos registra cero mutaciones, cero render loops
activos y cero long tasks. Los modelos, canvas y número de motores se conservan
al recorrer las vistas. El efecto se pausa al quedar oculto o reducir el movimiento.
Más detalle: `tests/visual/current/performance*.json`, `stability.json` y los recibos
de `tests/visual/evidence/r13-*.json`. Los diffs son diagnósticos de imagen, no una
puntuación de fidelidad o cobertura API.
