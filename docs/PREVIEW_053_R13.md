# Zénit 0.5.3 Preview R13

Refina la portada, el perfil, el catálogo, los menús de Monaco y la conversación
de Melody. El renderer de respuestas muestra tablas, títulos y código con copia
exacta; no ejecuta HTML del proveedor. El menú conserva sus acciones reales.
Los paquetes de temas muestran una miniatura calculada de la variante instalada.

Cuatro comandos habituales de extensiones abren el selector de temas, comandos,
archivos y ajustes, esperando confirmación del renderer. Se mantienen las
correcciones de persistencia/coloreado del tema y la voz nueva Qwen de Emma de R12.

Validación: 297 tests Python (292 pasan, 5 omisiones explícitas), 88 Node, 62 checks
de sintaxis, 13 vistas nativas y 24 casos de escala/resolución (72 capturas), sin
overflow global. Terminales ConPTY, Debug Python y servicios Node reales siguen
funcionando en las pruebas. Las pruebas UI de IA son fixtures identificadas.

Paridad VS Code parcial; no se certifica 90 %. La animación tiene frame times
variables; no se garantizan 60 FPS. La voz local puede tardar decenas de segundos.
Esta entrega Windows no certifica builds nuevos de Linux/macOS.

Detalles: [implementación](../IMPLEMENTATION_REPORT.md),
[comparación visual](../VISUAL_DIFF_REPORT.md), [límites](../KNOWN_LIMITATIONS.md).
