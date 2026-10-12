# Comparación visual · Zénit

Referencias originales: 1672 × 941. Resultado: WebView2 real, área cliente
1672 × 917, host Windows al 150 %, viewport fijado por CDP. Solo se recortan
los 24 px de título de la referencia. No hay estirado de la captura.

La revisión combina bounds, overlay 50 %, diff de píxeles y revisión humana.
MAE usa la escala de canales 0–255. SSIM es una comparación de luminancia
reducida por bloques. Ninguna de estas cifras es un porcentaje de fidelidad
ni produce automáticamente una marca de pantalla terminada.

| Vista | Referencia / resultado | MAE | SSIM por bloques | Componentes / diferencias conocidas |
| --- | --- | ---: | ---: | --- |
| editor | [Golden](tests/visual/references/editor.png) · [Resultado](tests/visual/current/editor.png) · [Overlay](tests/visual/comparisons/editor-overlay.png) · [Diff](tests/visual/comparisons/editor-diff.png) | 7.30 | 0.729 | app/editor/docking/product-ui + shell.css. Orden del árbol/tabs, minimapa, rama Git y runtime dependen del proyecto. Antialiasing e iconos tienen diferencias. |
| search | [Golden](tests/visual/references/search.png) · [Resultado](tests/visual/current/search.png) · [Overlay](tests/visual/comparisons/search-overlay.png) · [Diff](tests/visual/comparisons/search-diff.png) | 5.96 | 0.757 | studio + pages.css. Ilustración local y filtros funcionales tienen diferencias menores de iconos/tipo. El estado vacío se conserva. |
| settings | [Golden](tests/visual/references/settings.png) · [Resultado](tests/visual/current/settings.png) · [Overlay](tests/visual/comparisons/settings-overlay.png) · [Diff](tests/visual/comparisons/settings-diff.png) | 9.75 | 0.608 | workbench/controls + pages.css. Texto de seguridad y categorías avanzadas conservan información real. Blur y rasterizado varían por host. |
| extensions | [Golden](tests/visual/references/extensions.png) · [Resultado](tests/visual/current/extensions.png) · [Overlay](tests/visual/comparisons/extensions-overlay.png) · [Diff](tests/visual/comparisons/extensions-diff.png) | 9.81 | 0.543 | workbench/preview + catalogue/dialogs.css. Paquetes, versiones, estados y compatibilidad son reales. No se copia la insignia Compatible del golden si no corresponde. |
| laboratory | [Golden](tests/visual/references/laboratory.png) · [Resultado](tests/visual/current/laboratory.png) · [Overlay](tests/visual/comparisons/laboratory-overlay.png) · [Diff](tests/visual/comparisons/laboratory-diff.png) | 10.91 | 0.373 | foundation-ui + laboratory.css. El usuario pidió simplificar la vista en R7: cinco secciones persistentes sustituyen el hero y la cuadrícula completa. El golden original se conserva como historial; no es el objetivo vigente de esta pantalla. Las rutas no certifican ejecuciones. |
| debug | [Golden](tests/visual/references/debug.png) · [Resultado](tests/visual/current/debug.png) · [Overlay](tests/visual/comparisons/debug-overlay.png) · [Diff](tests/visual/comparisons/debug-diff.png) | 9.05 | 0.497 | debug-workspace/lantern + debug-workspace.css. El usuario pidió simplificar Depuración en R8: un inspector seleccionado sustituye los cuatro bloques y el hero de Lantern. Se conserva el golden anterior como historial. Live, Lens, motores y valores siguen siendo reales. |
| forge | [Golden](tests/visual/references/forge.png) · [Resultado](tests/visual/current/forge.png) · [Overlay](tests/visual/comparisons/forge-overlay.png) · [Diff](tests/visual/comparisons/forge-diff.png) | 9.72 | 0.476 | desktop-workflows/docking + windows.css. Marco y controles de acoplamiento difieren de la decoración OS. Contexto, ruta, herramientas y salida pertenecen al proyecto real. |

## Bienvenida vigente

El usuario sustituyó la bienvenida de dos columnas por una escena mínima y
después pidió que ocupara toda la ventana. La referencia original se conserva
intacta como historial; no se utiliza para declarar un pixel diff aprobado de
la composición nueva. El objetivo vigente está en `tests/visual/welcome-brief.json`.

[Resultado de bienvenida](tests/visual/current/welcome.png) ·
[Perfil y recientes](tests/visual/current/profile-activity.png) ·
[Referencia mínima posterior](tests/visual/references/welcome-minimal.png).

La geometría Blender de dos paredes, el material óptico y la órbita son
renderizados en vivo. R10 conserva el paisaje de cristal generado y servido
localmente, con luz, movimiento CSS y profundidad de hasta 4 px al mover el puntero. El usuario pidió mejorar
el fondo y simplificar Laboratory. No se declara reproducción óptica perfecta.

Los 5 bounds de Editor/Bienvenida pasan con desviación máxima
de 1.333 px. No se extrapola ese resultado a todos los detalles de las otras
vistas. Los materiales y assets mantienen las diferencias descritas arriba.

R10: 24 combinaciones de resolución/escala validadas sin overflow global ni errores JS. Depuración se comprueba además a 1280×720, 1366×768 y 1920×1080.

Regresiones sin golden independiente: [ASM](tests/visual/current/asm.png),
[Melody](tests/visual/current/melody.png), [paleta](tests/visual/current/palette.png),
[Proyecto flotante](tests/visual/current/floating-project.png).
También se incluye [Forge desacoplado](tests/visual/current/forge-detached.png).

Correcciones posteriores sin golden independiente: [Proyecto desacoplado](tests/visual/current/project-detached.png),
[varias terminales reales](tests/visual/current/multiple-terminals.png) y [revisión de archivos de Melody](tests/visual/current/melody-file-review.png).

## Temas e interfaz de R10

[Selector](tests/visual/current/theme-picker.png) · [Vira Graphene High Contrast](tests/visual/current/vira-graphene-high-contrast.png) · [One Dark Pro Mix](tests/visual/current/one-dark-pro-mix.png) · [Proyecto con tema sincronizado](tests/visual/current/detached-theme.png).

Las capturas del error de R8 del usuario y el proyecto QA difieren en resolución y contenido; no se declara un pixel diff comparable entre ellas. La comprobación funcional usa 89 variantes reales, siete pares de color con contraste mínimo 4.5:1, ausencia de overflow y conservación del modelo Monaco. Los 64 temas Bearded se cargan completos. Un selector por paquete sustituye las filas de variantes.

[Inicio Noche](tests/visual/current/welcome-dark.png) · [Inicio Bosque](tests/visual/current/welcome-forest.png). Se conserva el mismo canvas animado. El cambio de ambiente y sus botones son comprobados por la UI, no por un nuevo golden inventado.

[Regresión de tema antes](tests/visual/current/theme-split-before.png) · [División corregida](tests/visual/current/theme-split-fixed.png) · [Overlay](tests/visual/comparisons/theme-split-overlay.png) · [Diff](tests/visual/comparisons/theme-split-diff.png). Se conserva el mismo proyecto/viewport. El informe JSON registra que antes Monaco vuelve a lumen-theme y después conserva lumen-extension-theme en los seis pasos, con el comentario RGBA compuesto correctamente.

[Consejo organizado de Melody](tests/visual/current/melody-advice-sections.png). El texto proviene de una fixture explícita; no evalúa la calidad de un modelo externo. La inserción se verifica sobre el búfer real y se deshace en un paso.

Las inspecciones geométricas y de estilo están en `tests/visual/current/inspection.json`.
El estado de conservación de campos/canvas/modelos, los errores JS y el resultado
ASM real están en los JSON de esa carpeta. Esta corrección generó 72 capturas
de Editor/Melody/Bienvenida en 24 combinaciones de resolución y escala.
La matriz anterior de 312 capturas no se presenta como una nueva ejecución.
Se incluyen el resumen JSON y
muestras seleccionadas en `tests/visual/responsive`.

Este informe registra resultados y diferencias; no certifica equivalencia total
con las ocho imágenes ni paridad total con VS Code.

## R11 · Melody y temas efectivos

[One Dark Pro estable](tests/visual/current/one-dark-stable.png) · [Melody hablando](tests/visual/current/melody-speaking.png).

La fila de archivos/ayuda ocupa una sola línea y las cuatro acciones caben a 1672×917. La voz utiliza iconos de la familia SVG y tokens existentes; no cambia la altura de los paneles. El player usa texto legible sobre la superficie efectiva y controles de pausa/parada.

14 comprobaciones de voz/tema verifican selección, autenticación, audio real de Emma reproducido, pausa/reanudación, cancelación, persistencia del tema y cambio nativo atómico. La captura de conversación usa un fixture de IA; el WAV procede de MOSS real y esa generación se registra aparte. No se presenta el texto del fixture como respuesta de un proveedor real.

R11 repite 13 vistas nativas y 24 combinaciones de escala/resolución (72 capturas). Las imágenes de referencia permanecen intactas. La restauración de colores se verifica antes de recibir las contribuciones; el control de tema muestra la variante efectiva.

No se certifica equivalencia óptica perfecta ni cobertura del 90 % de VS Code. Los límites específicos del material, contenido y otras pantallas siguen descritos en las filas anteriores.
