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
| welcome | [Golden](tests/visual/references/welcome.png) · [Resultado](tests/visual/current/welcome.png) · [Overlay](tests/visual/comparisons/welcome-overlay.png) · [Diff](tests/visual/comparisons/welcome-diff.png) | 7.89 | 0.803 | studio/glass + welcome.css. Caústicas, reflexión, forma de facetas y brillo no idénticos. Fechas reales y acción de sesión dependen del host. |
| editor | [Golden](tests/visual/references/editor.png) · [Resultado](tests/visual/current/editor.png) · [Overlay](tests/visual/comparisons/editor-overlay.png) · [Diff](tests/visual/comparisons/editor-diff.png) | 7.01 | 0.750 | app/editor/docking/product-ui + shell.css. Orden del árbol/tabs, minimapa, rama Git y runtime dependen del proyecto. Antialiasing e iconos tienen diferencias. |
| search | [Golden](tests/visual/references/search.png) · [Resultado](tests/visual/current/search.png) · [Overlay](tests/visual/comparisons/search-overlay.png) · [Diff](tests/visual/comparisons/search-diff.png) | 5.76 | 0.760 | studio + pages.css. Ilustración local y filtros funcionales tienen diferencias menores de iconos/tipo. El estado vacío se conserva. |
| settings | [Golden](tests/visual/references/settings.png) · [Resultado](tests/visual/current/settings.png) · [Overlay](tests/visual/comparisons/settings-overlay.png) · [Diff](tests/visual/comparisons/settings-diff.png) | 9.75 | 0.606 | workbench/controls + pages.css. Texto de seguridad y categorías avanzadas conservan información real. Blur y rasterizado varían por host. |
| extensions | [Golden](tests/visual/references/extensions.png) · [Resultado](tests/visual/current/extensions.png) · [Overlay](tests/visual/comparisons/extensions-overlay.png) · [Diff](tests/visual/comparisons/extensions-diff.png) | 9.60 | 0.540 | workbench/preview + catalogue/dialogs.css. Paquetes, versiones, estados y compatibilidad son reales. No se copia la insignia Compatible del golden si no corresponde. |
| laboratory | [Golden](tests/visual/references/laboratory.png) · [Resultado](tests/visual/current/laboratory.png) · [Overlay](tests/visual/comparisons/laboratory-overlay.png) · [Diff](tests/visual/comparisons/laboratory-diff.png) | 10.86 | 0.472 | foundation-ui + catalogue.css. Ilustración local, algunas marcas y detalles inferiores difieren. Las rutas son reales; Ruta local no se sustituye por Incluido. |
| debug | [Golden](tests/visual/references/debug.png) · [Resultado](tests/visual/current/debug.png) · [Overlay](tests/visual/comparisons/debug-overlay.png) · [Diff](tests/visual/comparisons/debug-diff.png) | 8.67 | 0.545 | studio/lantern + debug.css. Se preservan Live, Lens y Multi-Language. Estado/stack/variables dependen del motor; no se rellenan para imitar la imagen. |
| forge | [Golden](tests/visual/references/forge.png) · [Resultado](tests/visual/current/forge.png) · [Overlay](tests/visual/comparisons/forge-overlay.png) · [Diff](tests/visual/comparisons/forge-diff.png) | 9.89 | 0.484 | desktop-workflows/docking + windows.css. Marco y controles de acoplamiento difieren de la decoración OS. Contexto, ruta, herramientas y salida pertenecen al proyecto real. |

Los siete bounds principales de Welcome/Editor pasan con desviación máxima
de 1,333 px. No se extrapola ese resultado a todos los detalles de las otras
vistas. Los materiales y assets mantienen las diferencias descritas arriba.

Regresiones sin golden independiente: [ASM](tests/visual/current/asm.png),
[Melody](tests/visual/current/melody.png), [paleta](tests/visual/current/palette.png),
[Proyecto flotante](tests/visual/current/floating-project.png).
También se incluye [Forge desacoplado](tests/visual/current/forge-detached.png).

Las inspecciones geométricas y de estilo están en `tests/visual/current/inspection.json`.
El estado de conservación de campos/canvas/modelos, los errores JS y el resultado
ASM real están en los JSON de esa carpeta. Las 312 capturas de la matriz de escala
se generaron en la carpeta de auditoría local; se incluyen el resumen JSON y
muestras seleccionadas en `tests/visual/responsive`.

Este informe registra resultados y diferencias; no certifica equivalencia total
con las ocho imágenes ni paridad total con VS Code.
