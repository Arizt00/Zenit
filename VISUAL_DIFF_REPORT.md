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
| editor | [Golden](tests/visual/references/editor.png) · [Resultado](tests/visual/current/editor.png) · [Overlay](tests/visual/comparisons/editor-overlay.png) · [Diff](tests/visual/comparisons/editor-diff.png) | 7.18 | 0.747 | app/editor/docking/product-ui + shell.css. Orden del árbol/tabs, minimapa, rama Git y runtime dependen del proyecto. Antialiasing e iconos tienen diferencias. |
| search | [Golden](tests/visual/references/search.png) · [Resultado](tests/visual/current/search.png) · [Overlay](tests/visual/comparisons/search-overlay.png) · [Diff](tests/visual/comparisons/search-diff.png) | 5.90 | 0.758 | studio + pages.css. Ilustración local y filtros funcionales tienen diferencias menores de iconos/tipo. El estado vacío se conserva. |
| settings | [Golden](tests/visual/references/settings.png) · [Resultado](tests/visual/current/settings.png) · [Overlay](tests/visual/comparisons/settings-overlay.png) · [Diff](tests/visual/comparisons/settings-diff.png) | 9.76 | 0.608 | workbench/controls + pages.css. Texto de seguridad y categorías avanzadas conservan información real. Blur y rasterizado varían por host. |
| extensions | [Golden](tests/visual/references/extensions.png) · [Resultado](tests/visual/current/extensions.png) · [Overlay](tests/visual/comparisons/extensions-overlay.png) · [Diff](tests/visual/comparisons/extensions-diff.png) | 9.82 | 0.536 | workbench/preview + catalogue/dialogs.css. Paquetes, versiones, estados y compatibilidad son reales. No se copia la insignia Compatible del golden si no corresponde. |
| laboratory | [Golden](tests/visual/references/laboratory.png) · [Resultado](tests/visual/current/laboratory.png) · [Overlay](tests/visual/comparisons/laboratory-overlay.png) · [Diff](tests/visual/comparisons/laboratory-diff.png) | 11.17 | 0.466 | foundation-ui + catalogue.css. Ilustración local, algunas marcas y detalles inferiores difieren. Las rutas son reales; Ruta local no se sustituye por Incluido. |
| debug | [Golden](tests/visual/references/debug.png) · [Resultado](tests/visual/current/debug.png) · [Overlay](tests/visual/comparisons/debug-overlay.png) · [Diff](tests/visual/comparisons/debug-diff.png) | 8.82 | 0.540 | studio/lantern + debug.css. Se preservan Live, Lens y Multi-Language. Estado/stack/variables dependen del motor; no se rellenan para imitar la imagen. |
| forge | [Golden](tests/visual/references/forge.png) · [Resultado](tests/visual/current/forge.png) · [Overlay](tests/visual/comparisons/forge-overlay.png) · [Diff](tests/visual/comparisons/forge-diff.png) | 9.63 | 0.480 | desktop-workflows/docking + windows.css. Marco y controles de acoplamiento difieren de la decoración OS. Contexto, ruta, herramientas y salida pertenecen al proyecto real. |

## Bienvenida vigente

El usuario sustituyó la bienvenida de dos columnas por una escena mínima y
después pidió que ocupara toda la ventana. La referencia original se conserva
intacta como historial; no se utiliza para declarar un pixel diff aprobado de
la composición nueva. El objetivo vigente está en `tests/visual/welcome-brief.json`.

[Resultado de bienvenida](tests/visual/current/welcome.png) ·
[Perfil y recientes](tests/visual/current/profile-activity.png) ·
[Referencia mínima posterior](tests/visual/references/welcome-minimal.png).

La geometría Blender de dos paredes, el material óptico y la órbita son
renderizados en vivo. El fondo vectorial de montañas no es el raster de la
referencia. La iluminación, el tamaño de escena y las facetas mantienen
diferencias; no se declara una reproducción óptica perfecta.

Los 5 bounds de Editor/Bienvenida pasan con desviación máxima
de 1.333 px. No se extrapola ese resultado a todos los detalles de las otras
vistas. Los materiales y assets mantienen las diferencias descritas arriba.

Regresiones sin golden independiente: [ASM](tests/visual/current/asm.png),
[Melody](tests/visual/current/melody.png), [paleta](tests/visual/current/palette.png),
[Proyecto flotante](tests/visual/current/floating-project.png).
También se incluye [Forge desacoplado](tests/visual/current/forge-detached.png).

Las inspecciones geométricas y de estilo están en `tests/visual/current/inspection.json`.
El estado de conservación de campos/canvas/modelos, los errores JS y el resultado
ASM real están en los JSON de esa carpeta. Esta corrección generó 72 capturas
de Editor/Melody/Bienvenida en 24 combinaciones de resolución y escala.
La matriz anterior de 312 capturas no se presenta como una nueva ejecución.
Se incluyen el resumen JSON y
muestras seleccionadas en `tests/visual/responsive`.

Este informe registra resultados y diferencias; no certifica equivalencia total
con las ocho imágenes ni paridad total con VS Code.
