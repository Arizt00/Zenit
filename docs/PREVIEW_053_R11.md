# Zénit 0.5.3 · Preview R11

Melody incorpora lectura de respuestas, consejos y selección con la voz aprobada
de Emma, controles de pausa/reanudación/parada y decodificación continua.
La voz utiliza la instalación local existente de Emma; los modelos y referencias
privadas no se incluyen en el instalador público. Se activa con Escuchar, sin
lecturas automáticas ni modificación de archivos. Límite: 2500 caracteres de
prosa, español, una generación a la vez; la generación real de prueba tardó 61 s.

One Dark Pro y Bearded conservan sus colores al dividir el editor, modificar
preferencias y recargar. El tema efectivo se muestra en la barra y sus colores
se restauran antes del CSS. Cambiar al tema nativo guarda los dos ajustes juntos.
Un tema no disponible produce un aviso explícito.

La API `workbench.colorTheme` de las extensiones consulta y actualiza el perfil
Global real. Targets de workspace todavía se rechazan. Las cuatro acciones de
Melody caben con una fila de herramientas compacta; los nuevos iconos comparten
la familia SVG de Zénit. Monaco, ConPTY, Lens, DAP/LSP, webviews y proveedores
existentes se conservan.

Verificación: 294 tests Python (5 skips), 82 Node, 89 variantes de tema,
14 checks nuevos de voz/tema, 13 vistas nativas y 72 capturas de resolución/escala.
La voz se genera con MOSS real; las pruebas de interacción usan un fixture de IA.
No se certifica un 90 % global de VS Code ni calidad universal de los modelos.

[Implementación](../IMPLEMENTATION_REPORT.md) · [Comparación visual](../VISUAL_DIFF_REPORT.md)
· [Límites](../KNOWN_LIMITATIONS.md).
