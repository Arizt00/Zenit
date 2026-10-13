# Zénit 0.5.4 · Preview R4

El editor exterior ocupa toda su ventana y coloca el terminal debajo del código.
Su cabecera incluye Ejecutar, Terminal, Usar terminal de Zénit y Volver a Zénit.
Ctrl J lo oculta o recupera; el separador admite arrastre y teclado. El terminal
puede salir a otra ventana y volver al editor sin terminar la shell. Al elegir
el terminal principal, el exterior se oculta y la sesión continúa en Zénit.

Se comprueban edición y guardado en ambas direcciones, temas, fuente y perfil,
además de creación y borrado en los exploradores. Las tareas comparten su salida
entre las ventanas. Los cambios simultáneos incompatibles conservan los búferes
y muestran el conflicto; no se impone una sobrescritura silenciosa.

Se corrige el menú de Proyecto que permanecía abierto al pulsar fuera: los
anclajes por coordenadas no tienen contains/focus. El cierre funciona sobre
Monaco, con Escape y al cambiar de ventana. Las entradas tienen foco visible,
separadores y atajos. Las apariciones duran 180 ms, con opacidad y desplazamiento,
sin escalar tipografía; se respeta movimiento reducido y cancelación.

Búsqueda añade mayúsculas, palabra completa, inclusión/exclusión, carpeta y tipo.
Los filtros se aplican antes de los 200 resultados, con aviso de truncamiento.
Cada línea coincidente abre su primera columna UTF-16, incluso tras emoji.
Los resultados se agrupan por archivo y conservan consulta/filtros al reabrir.
Se navega con flechas y Enter; Ctrl Shift F abre la búsqueda.

El terminal principal acepta teclado con un editor exterior abierto. La vista
activa gobierna el tamaño PTY y se filtran respuestas de identificación de
ConPTY que CMD interpretaba como parte de la orden. Forge incorpora Ejecutar
archivo mediante el entorno configurado y una terminal real, además de Python
desde el búfer y C/GDB. Se comprueba Java real con System.console(), lectura de
entrada y salida por ConPTY. Los archivos absolutos deben estar abiertos en la
sesión para ejecutar o separar; no se amplía el acceso a otras rutas.

Melody reconoce preguntas directas y órdenes en subjuntivo sobre archivos.
La revisión incluye una comparación real de Monaco, con modelos que se liberan
al cerrar. Continúan recuperación, deshacer, contexto de sesión y protección de
revisiones. Inicio, Mi actividad y Tu perfil mantienen su diseño y portada real
difuminada, con regresiones de temas e iconos Material. La voz Qwen de Emma y la
ayuda en tiempo real existentes se conservan; no se entrena una nueva voz/modelo.

Validación y paquetes se detallan en [IMPLEMENTATION_REPORT](../IMPLEMENTATION_REPORT.md)
y [VISUAL_DIFF_REPORT](../VISUAL_DIFF_REPORT.md). La generación de planes usa
respuestas controladas y no acredita calidad universal de un proveedor. La
[paridad con VS Code](VSCODE_PARITY_054_R4.md) sigue siendo parcial; se explican
los [límites](../KNOWN_LIMITATIONS.md). Esta entrega reconstruye Windows.
