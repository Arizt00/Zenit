# Zénit 0.5.3 R9 · temas legibles, selección y sincronización

Esta revisión parte de `ec1b980` (R8). Corrige el error de los temas mostrado
en las capturas del usuario, la fila de variantes que desbordaba las tarjetas
y la aplicación de colores en ventanas desacopladas. Continúa las mejoras de
inicio/Melody y acredita nuevos contratos de extensiones con pruebas reales.

## Arquitectura y archivos

| Área | Archivos | Comportamiento |
| --- | --- | --- |
| Resolución de temas | `web/src/extension-theme.js` | Solo acepta colores hex. Compone alpha sobre la superficie, elige un acento visible y normaliza los pares que fallan contraste. Mantiene el tema original de Monaco. Retirar el tema limpia sus tokens y restaura el ambiente elegido. |
| Sistema de diseño | `web/design/tokens.css`, `shell.css`, `catalogue.css`, `dialogs.css`, `welcome.css` | Pares de cabecera, rail, campo, botón, selección y chips; halo de cabecera/selección sin blanco fijo; overlay acorde al tema. Layout de tarjetas acotado con acciones que pueden envolver. |
| Selector | `web/src/theme-picker.js`, `web/design/themes.css`, `workbench.js` | Una acción por paquete, búsqueda, muestras de la paleta resuelta, teclado y tema efectivo marcado. No crea canvas ni carga otro editor. |
| Sincronización | `platform_services.py`, `extension-services.js`, `workbench.js` | Eventos de preferencias/contribuciones actualizan otras ventanas. Escrituras serializadas y epochs evitan aplicar una respuesta anterior. Ajustes actualiza controles y texto existentes, conserva nodos/foco y no reconstruye una búsqueda por un evento repetido. |
| API de color | `extension_services.py`, `extension_runtime.py`, `extension_api.cjs` | Estado inicial real, cuatro ColorThemeKind y evento al cambiar identidad/tipo. Un recurso inválido, paquete desactivado o contribuciones desactivadas informa del tema nativo efectivo. |
| Variantes | `extensions.py` | Hasta 128 por paquete y 256 activas con aviso al exceder límites. Bearded Theme carga sus 64 variantes; el antiguo límite silencioso de 30 queda eliminado. |
| Avisos | `web/src/app.js`, `workbench.js` | Reutiliza una notificación al cambiar rápidamente de tema; otros avisos mantienen su contrato. |
| Consejos | `melody-companion.js`, `melody.css` | Hasta seis referencias de línea válidas, navegación a Monaco y marca ligada a revisión/modelo. Al analizar, cambiar archivo o recibir un error retira el consejo anterior. |
| Bienvenida | `welcome.css` | Paisaje más tenue en Noche/Bosque, colores legibles y botones de su paleta. Conserva la esfera Blender/Babylon/WebGL2, su canvas y las reglas de pausa/reducir movimiento. |
| Distribución | `version.py`, `version.txt`, `setup.js`, `package.json` | Revisión R9 y comprobación sintáctica del nuevo selector. Instalador, desinstalador y producto mantienen la marca Zénit. |

ColorThemeKind respeta los tipos declarados por la extensión, no una inferencia
del nombre comercial. Vira llama a algunas variantes «High Contrast» pero las
declara `vs-dark`: el host informa Dark. Se prueban además temas de fixture
`hc-black` y `hc-light` con un host Node real. El contrato de referencia es el
[archivo oficial de API de VS Code](https://github.com/microsoft/vscode/blob/main/src/vscode-dts/vscode.d.ts).

## Tokens y causa del fallo

Vira declara `focusBorder` con alpha cero. El código anterior lo reutilizaba
como acento y ocultaba iconos. One Dark Pro aporta bordes oscuros/translúcidos,
tampoco adecuados para texto de botones. El foco y el acento ahora se resuelven
por separado; los foreground se verifican sobre su fondo efectivo.

Los nuevos roles son `button-start/end/text`, `field-text/muted`,
`chrome-text/secondary/accent`, `rail-text/secondary/accent`,
`canvas-text/secondary/accent`, `soft-text/secondary`, `chrome-halo`,
`selection-halo`, `positive-bg/text` y `overlay`. Comparten los spacing/radii/motion existentes.
Los pares de texto/control resueltos usan mínimo 4.5:1 y foco 3:1. No se promete
que cada píxel de cada tema cumpla estas métricas: los límites de composición,
texturas y del editor original permanecen explícitos.

## Interfaz y validación visual

Se preservan los ocho goldens originales. Los cambios solicitados después para
Inicio, Laboratory y Debug se documentan como composiciones vigentes diferentes.
Las vistas actuales, overlays y diffs están en [VISUAL_DIFF_REPORT](VISUAL_DIFF_REPORT.md).
Editor/Inicio conservan cinco bounds principales dentro de 2 px; la desviación
máxima observada es 1.333 px. Ese resultado no equivale a fidelidad global.

El selector y los temas de las capturas del error se revisan con 89 variantes
reales: 20 Vira, 5 One Dark Pro y 64 Bearded. Los siete pares medidos pasan 4.5:1;
las tarjetas conservan sus bounds y el mismo modelo Monaco. La ventana Proyecto
recibe el tema y Ajustes retiene campos/foco. No se compara directamente por
píxeles una captura del proyecto del usuario a otro viewport/proyecto de QA.

## Pruebas de R9

- Python: 288 pruebas, 283 correctas y 5 omisiones explícitas.
- Node: 75 pasan; JavaScript: 57 archivos comprobados.
- Temas: 9 comprobaciones UI con los tres paquetes reales, persistencia,
  teclado, contraste, ventanas y ausencia de errores JS.
- ColorThemeKind: 3 pruebas con extensión Node real; estado inicial, tipos,
  identidad, evento/objeto actual y fallback al desactivar o invalidar recursos.
- Debug/output: 12 comprobaciones; Python real calcula 42 al avanzar, canales
  Node reales, nivel de registro y cero mutaciones en muestras inactiva/pausada.
- Archivos/panel/terminal: 7 comprobaciones; tres CMD ConPTY reciben teclado,
  Proyecto se distribuye en columna y los archivos creados/borrados se restauran.
- Inicio/Melody: 19 comprobaciones, shader vivo, pausa/contexto WebGL, ambientes,
  referencias de líneas, revisiones, selección real y aceptación de predicción.
- 13 vistas WebView2 nativas; 72 capturas en 24 combinaciones de resolución/escala
  emulada. Sin overflow global ni errores JS en esos recorridos. No representa
  una prueba física de cada monitor/DPI o de Linux/macOS.

La generación y los consejos UI usan transporte determinista identificado.
No se acredita calidad de modelos externos ni predicciones siempre correctas.
Se conservan terminales, Monaco, proveedores, planes revisados de archivos,
Lantern Live/Lens/adaptadores y los motores reales de Debug de R8.

## Rendimiento

La muestra WebView2 de bienvenida animada registra CPU de render mediana
0.4 ms y p95 0.6 ms. Intervalo observado
de frames: 20.8 ms mediana, 29.2 ms p95.
No hay long tasks en esa muestra. No es tiempo GPU ni una garantía de 60 FPS.
El canvas oculto tiene cero render loops; cambiar ambientes conserva el mismo
canvas. Repetir preferencias no reaplica el tema ni crea más engines.

## Límites y distribución

La paridad de VS Code sigue siendo parcial. No hay una matriz global suficiente
para acreditar 90 %. Los contratos añadidos cumplen los escenarios probados;
OAuth integrado, filesystem virtual completo, documentos binarios, visualizadores
y forwarding de puertos siguen pendientes. [KNOWN_LIMITATIONS](KNOWN_LIMITATIONS.md)
conserva esos límites y los de las revisiones anteriores.

Los recibos del build, publicación, instalación y verificación del helper
congelado se incorporan en `tests/visual/evidence/windows-r9-*.json` después
de ejecutar cada paso. R9 prepara instalador/portable Windows con SHA-256.
Esta entrega no reconstruye Linux/macOS ni añade firma/notarización.
