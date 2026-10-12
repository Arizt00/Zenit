# Zénit 0.5.3 Preview R8

Depuración concentra la sesión en un inspector: Variables, Pila, Salida o Lantern.
El archivo, puntos de interrupción y errores se conservan al cambiar de vista.
La entrada al programa aparece solamente si el motor la admite y está ejecutando.

Proyecto desacoplado usa una cabecera superior y un árbol de ancho completo.
Las terminales conservan la sesión seleccionada al volver desde «Terminal»;
el selector distingue sesiones de la misma shell y devuelve el foco al teclado.
La consola de tareas permanece accesible por su entrada explícita.

Melody puede proponer crear, actualizar o borrar archivos y un proyecto completo.
Prueba peticiones como:

- «Crea un proyecto Python en una carpeta calculadora, con README y pruebas».
- «Crea el archivo src/utilidades.py con funciones para validar entradas».
- «Borra el archivo prueba_temporal.py».

El proveedor devuelve un plan; «Revisar archivos» muestra las rutas y contenidos.
Aplicar escribe en disco, conserva una copia de recuperación y ofrece Deshacer.
Un borrado debe estar solicitado en la petición. Los planes no ejecutan comandos
ni instalan dependencias. Se validan rutas, conflictos y cambios sin guardar.
Admiten hasta 60 archivos y 400000 bytes propuestos dentro del proyecto abierto.
Las consultas normales y la ayuda en tiempo real siguen sin modificar el disco.

La ayuda activa de Melody ocupa una tarjeta compacta y ofrece una marca de consejo
ligada a la revisión de Monaco. Una edición posterior retira el consejo anterior.
El inicio conserva Blender/Babylon/WebGL2 y añade profundidad suave al paisaje.

La integración de extensiones añade canales de salida seleccionables y niveles
de registro reales, incluido Off. Cambiar el nivel emite onDidChangeLogLevel;
padre y dependencias tienen identificadores de canal independientes.
La compatibilidad global con VS Code continúa siendo parcial: no se acredita 90 %.

Validación: 285 pruebas Python (280 pasan, 5 omisiones explícitas), 71 Node,
12 comprobaciones de Debug/output, 7 de archivos/panel/terminal, 17 de interfaz
y ayuda; 13 vistas nativas y 72 capturas en 24 combinaciones de resolución/escala.
La generación de proyectos se prueba con transporte de IA determinista, sin
certificar la calidad de ningún modelo externo.

Windows se entrega como instalador `.exe` y portable, con manifiesto/SHA-256.
Los paquetes Linux/macOS y firma/notarización no se reconstruyen en esta revisión.
Consulta [implementación](../IMPLEMENTATION_REPORT.md), [comparación visual](../VISUAL_DIFF_REPORT.md)
y [límites reales](../KNOWN_LIMITATIONS.md).

El Windows publicado supera 15 comprobaciones nativas y 7 comprobaciones del runtime instalado; 92 archivos coinciden con el build.
