# Arranque, máquinas y recorridos de lenguaje

El informe de rendimiento se abre desde Hardware o desde la paleta con
«Informe de esta sesión». Muestra dos relojes independientes: los hitos de la
interfaz y los intervalos del servicio medidos con `perf_counter`. Los intervalos
pueden estar anidados y no se suman. El lanzador y Windows quedan fuera del reloj
del backend. Consultar el informe no arranca herramientas ni máquinas.

Los servicios de máquinas, paquetes, voz, depuración, pruebas, CoCo y entornos
se construyen en su primer uso. Cerrar el IDE o cambiar de proyecto sólo detiene
los que llegaron a iniciarse. La vista de destinos lee los perfiles guardados;
descubre WSL al abrir su selector, o al recuperar un destino WSL ya seleccionado.
El inventario de Forge se carga al abrir Forge.

## QEMU

La prueba de aceleración y el arranque del invitado comparten la configuración de
CPU: CPU predeterminada para WHPX, `host` para KVM/HVF y `max` para TCG. La prueba
de firmware no adjunta discos ni certifica un sistema invitado completo. Si falla,
el informe conserva el motivo y explica la selección de TCG. Se reutiliza durante
un máximo de 60 segundos y se invalida al cambiar el ejecutable.

La plantilla Arch generada usa caché `writeback`, respetando los flush del invitado
y el apagado ACPI/QMP. Los invitados importados conservan `writethrough`. No se
cambian opciones de seguridad o de virtualización de Windows. Véanse las
[opciones de QEMU](https://qemu-project.gitlab.io/qemu/system/invocation.html)
y la [documentación de WHPX](https://www.qemu.org/docs/master/system/whpx.html).

Cada petición registra la comprobación de recursos, lanzamiento de terminal,
proceso QEMU, conexión serie, primera salida y los prompts observados. Un prompt
ausente queda pendiente; la conexión de terminal no se anuncia como arranque
completo. Los informes no guardan el texto de la terminal.

## Comprobar un lenguaje

En las funciones del lenguaje del editor, abre «Recorridos comprobables», o busca
«Lenguajes: comprobar recorridos y referencia nC» en la paleta.

«Comprobar muestra» prepara un proyecto temporal con espacios en la ruta. Usa las
herramientas configuradas en Este equipo y los perfiles estándar de Zénit; no
ejecuta comandos personalizados ni modifica el proyecto del usuario. Los seis
pasos son abrir, definición, renombrado, compilar/ejecutar, pruebas y depurar.
La depuración exige una pausa con pila y un segundo paso observable. Para ASM y
nC la muestra incluye una prueba de humo, identificada como tal; no sustituye
una suite de aserciones del proyecto. La tarea se puede cancelar desde el informe
o desde Tareas. Las herramientas que faltan y las respuestas fallidas se muestran
por separado. Un cambio de configuración, ejecutable o extensión caduca el recibo.

La referencia nC se extrajo del ZIP JetBrains `nc-language-plugin-1.0.0.21v.zip`
elegido por el usuario, SHA-256
`f8e18421f1707fb2db6270f3f694dccc083c37b6cc96489c93fb3b6823c759fb`.
La matriz conserva las seis familias `.n`, `.nb`, `.nbb`, `.nm`, `.nbo` y `.ncp`,
las declaraciones y las acciones del plugin, su equivalente nativo/adaptado o su
ausencia. El parser PSI de IntelliJ no se ejecuta en Monaco. La procedencia de
los iconos/colores no equivale a certificar todas las funciones semánticas.

## Validación de este cambio

- Cinco procesos independientes por versión, perfiles vacíos y cachés del SO
  posiblemente calientes: mediana de inicialización del servicio 91,644 →
  16,048 ms; recorrido completo de backend 278,413 → 181,389 ms. No son tiempos
  de apertura de la ventana ni una comparación con otros editores.
- Arranque real de Arch con WHPX, escritura en un overlay QCOW2 propio, guardado
  de `.tern`, segundo arranque y lectura del archivo; apagados correctos.
- C, C++, Python y nC: seis pasos comprobados con herramientas reales.
- Java: compilación, prueba y depuración comprobadas; JDT LS falta en este equipo.
- NASM x86-64: ensamblado, ejecución, humo y depuración comprobados; falta asm-lsp
  para verificar definición y renombrado.
- Rust: seis pasos comprobados tras instalar rust-analyzer/rust-src en la
  toolchain estable existente. La detección prefiere el ejecutable real frente
  al proxy de rustup y el proceso LSP conserva sus herramientas hermanas en PATH.
  El cliente anuncia carpetas de trabajo y responde workspace/workspaceFolders.
  La muestra se abre en el destino Cargo real, no en un módulo huérfano.

Los recibos son locales y repetibles. No certifican todas las arquitecturas ni
un proyecto arbitrario, y tampoco una estación remota o toda la API de VS Code.

## Profundidad de lenguajes · nC adaptado 1.0.0-21v.zenit.4

El origen visual sigue siendo el ZIP JetBrains indicado arriba. La adaptación
local añade navegación, referencias, renombrado y esquema por ámbitos, usando
las declaraciones del parser de la integración elegida. Dos contenedores pueden
usar el mismo nombre sin mezclar sus variables; los parámetros y bloques locales
ocultan los nombres exteriores. El renombrado rechaza colisiones, comentarios,
cadenas y miembros cualificados que no pueda vincular de forma segura. No es un
índice semántico global ni certifica todas las familias de bajo nivel.

La corrección rápida de migración de extensión captura la ruta del documento que
la solicitó. No depende del documento consultado más recientemente por otro
proveedor. WorkspaceEdit emite el rango completo UTF-16 del texto anterior, para
que la autoimportación no falle al recibir una edición de la extensión.

El puente LSP de extensiones expone renombrado y refactorizaciones con ediciones
de texto para su revisión y deshacer conjuntos en Monaco. No descarta en silencio
operaciones de recursos o acciones que requieren comandos adicionales: se
deshabilitan con una explicación o se remiten al perfil LSP nativo.

El explorador reconoce los directorios CMake generados bajo build/<lenguaje>/… y
permite elegir el destino cuando existen varios. CTest recorre sus subdirectorios
una sola vez. Cargo utiliza el rustc seleccionado. NCC ofrece una comprobación
de humo por referencia main, con orden revisable, resultado por archivo y
caducidad al cambiar las fuentes. ncc test valida parser, tipos, contratos y
ejecuta main; el éxito no equivale a una suite de aserciones ni a verificar la
semántica de cualquier programa.
