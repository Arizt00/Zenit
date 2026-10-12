# Zénit 0.5.3 R10 · tema persistente y coloreado coherente

R10 parte de `335bbcc` (R9) y responde al fallo descrito por el usuario: el
editor vuelve al tema original y el coloreado queda incorrecto. La auditoría
reproduce el fallo con el paquete real Bearded Theme Solarized Light antes de
modificar su ruta de render. También continúa la mejora de interfaz/Melody y
la integración de formatos de temas de extensiones.

## Fallo reproducido y solución

Crear una división propagaba `theme: lumen-theme` desde las opciones iniciales
de la primera vista. Monaco comparte el servicio de temas: crear la segunda
vista cambiaba el tema de ambas. Actualizar fuentes/word wrap volvía a propagar
ese valor antiguo. R10 excluye el tema de las opciones que se transfieren entre
vistas y conserva los modelos y búferes. Un cambio de preferencias del editor
tampoco llama al tema nativo si hay una extensión seleccionada.

La prueba anterior registra `selected → lumen-extension-theme`,
`split/font/wrap → lumen-theme`. La prueba posterior conserva
`lumen-extension-theme` en selección, división, fuente, contribuciones, ajuste
de líneas y recarga. Verifica el mismo modelo y el color real de comentarios.
La auditoría anterior no se presenta como una prueba que pasaba.

## Arquitectura y archivos

| Área | Archivos | Resultado |
| --- | --- | --- |
| División/preferencias | `editor.js`, `app.js` | Las opciones locales de vista no sobrescriben el tema global. La preferencia externa y los modelos permanecen. |
| Sintaxis | `theme-tokens.js`, `textmate.js`, `editor.js`, `extension-theme.js` | Normaliza RGB corto/RGBA; compone alpha sobre el editor; conserva estilos sin foreground. TextMate y Monaco usan el mismo color efectivo. |
| Semántica/contraste | `theme-tokens.js`, `editor.js`, `preview.js` | Reglas simples de tipo/modificador y semanticHighlighting explícito; respeta las cuatro bases de Monaco, incluido hc-light/hc-black. |
| Recursos de tema | `backend/extensions.py` | Resuelve tokenColors en archivos .tmTheme/JSON locales, valida tipo/ruta/tamaño, conserva colores y semántica heredados. |
| Terminal | `theme-tokens.js`, `workbench.js` | Colores ANSI normales/brillantes y cursor/selección aportados por el tema; mantiene PTY, teclado y búfer. |
| Selector | `theme-picker.js`, `themes.css` | Filtra por tipo declarado; cuenta resultados reales, estado vacío y muestra la sintaxis efectiva con transparencia. |
| Melody | `melody-companion.js`, `melody.css` | Apartados basados en texto real; inserción explícita con chequeo de modelo/versión/cursor, Undo y sin guardar. Predicciones caducadas se retiran. |
| Inicio | `welcome.css` | Luz suave basada en el acento, animación CSS de 48 s y reglas existentes de pausa/reducir movimiento. Sin nuevo renderer. |
| Versión/build | `version.py`, `version.txt`, `setup.js`, `package.json` | Preview R10, nuevo módulo incluido y 58 comprobaciones sintácticas. |

Las reglas completas de TextMate permanecen en la gramática real. Monaco
lexical traduce solamente alias de categorías que puede representar; no se
finge soporte de todos los scopes contextuales. Semántica cubre selectores
simples de tipo/modificador, no lenguaje ni todos los comodines/ordenamientos.
El contrato y sus diferencias se contrastan con la
[guía oficial de temas](https://code.visualstudio.com/api/extension-guides/color-theme),
[guía de semántica](https://code.visualstudio.com/api/language-extensions/semantic-highlight-guide)
y el [servicio Standalone de Monaco](https://github.com/microsoft/vscode/blob/main/src/vs/editor/standalone/browser/standaloneThemeService.ts).

El loader no obtiene recursos remotos ni ejecuta el tema. Acepta hasta 3 MB por
recurso, herencia dentro del paquete y errores explícitos para XML/rutas/tipos
inválidos. Se conserva el límite de 128 variantes por paquete y 256 activas.

## Diseño y fidelidad

Se conservan spacing, radii, bordes, tipografía e iconos SVG compartidos. Los
nuevos filtros y acciones usan tokens semánticos; no crean una segunda estética.
El cuerpo de consejos sigue el scroll del panel y mantiene el composer visible.
El texto no estructurado tiene fallback íntegro; no se fabrican secciones.
Insertar usa el mismo lenguaje de botones y una acción deshacible.

Los ocho goldens originales permanecen intactos. Editor/Inicio conservan cinco
bounds dentro de 2 px, máximo observado 1.333 px. Las composiciones simplificadas
de Inicio/Laboratory/Debug siguen el brief posterior del usuario. Se incluyen
capturas, overlays y diffs actuales en [VISUAL_DIFF_REPORT](VISUAL_DIFF_REPORT.md).
El before/after de división usa el mismo proyecto y viewport. No hay porcentaje
inventado de fidelidad ni de paridad.

## Validación

- Python: 290 pruebas, 285 correctas y 5 omisiones explícitas.
- Node: 80 pasan; JavaScript: 58 archivos comprobados.
- Temas: 10 checks UI, 89 variantes reales de Vira/One Dark Pro/Bearded.
- Estabilidad: 6 pasos con Monaco real, dos vistas, modelo preservado y RGBA;
  xterm conserva ambos azules ANSI originales al cambiar fuente.
- TextMate/ASM: 7 checks con Oniguruma real, scopes/inyección, estado multilinea,
  reactivación, ejemplo x86-64 y controles en tres tamaños/tres ambientes.
- Inicio/Melody: 21 checks; shader, pausa, contexto WebGL, consejos de revisión,
  apartados reales y sugerencia explícita que se deshace en un paso.
- Debug/output: 12 checks con proceso Python y extensión Node reales.
- Archivos/panel/terminal: 7 checks, tres CMD/ConPTY, Proyecto desacoplado,
  creación/borrado y recuperación reales en workspace aislado.
- 13 vistas WebView2 nativas y 72 capturas en 24 combinaciones emuladas. Sin
  overflow global ni errores JS en estos recorridos. No cubre cada monitor físico.

El transporte de IA de QA es una fixture declarada. Se comprueba la entrega,
revisión y aplicación al búfer, no calidad/predicciones de modelos externos.
Las terminales, archivos, registros y valores de los motores son reales.

## Rendimiento y límites

Muestra nativa de bienvenida animada: CPU de render mediana
0.4 ms, p95 0.7 ms. Intervalo de frames
16.6 ms mediana, 25.0 ms p95. No hay long tasks
en esa muestra. No es tiempo GPU ni una garantía de 60 FPS en cada dispositivo.
Escenas ocultas tienen cero loops; modelos/canvas se conservan.

La compatibilidad global de VS Code sigue siendo parcial. OAuth integrado,
filesystem virtual completo, editores binarios, visualizadores y forwarding
siguen pendientes. No se acredita 90 % global. [KNOWN_LIMITATIONS](KNOWN_LIMITATIONS.md)
conserva esos límites y los de color/semántica propios de R10.

Los recibos de build/publicación/instalación se incorporan en
`tests/visual/evidence/windows-r10-*.json` después de ejecutar cada fase.
R10 entrega instalador/portable Windows; no reconstruye Linux/macOS ni firma.
El proceso anterior del usuario se conserva para no perder trabajo sin guardar.
