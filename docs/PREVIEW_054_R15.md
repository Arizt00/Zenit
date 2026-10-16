# Zénit 0.5.4 R15

R15 corrige el destino de las ejecuciones y añade una primera implementación
funcional de trabajo en equipo. No se afirma paridad completa con VS Code.

Los espacios de trabajo comparten un icono de ventana con dos áreas, un selector
con identidad propia, acciones alineadas y controles que se adaptan al ancho
del editor. El mismo icono aparece en la vista previa de configuración. Las
herramientas se abren con una transición breve que respeta movimiento reducido.
Assembly agrupa ejemplos, entrada y destinos en una sección plegable. Los
resultados se consultan en pestañas de salida, registros, instrucciones y memoria,
según los datos que publique el motor. Al cambiar al espacio ASM, la consola
abierta se aparta para dar espacio al código; vuelve al regresar al otro espacio.

- Ejecutar conserva su icono y etiqueta durante el cambio a Detener. En una
  ventana externa, la terminal local recibe su ejecución; «Usar terminal de
  Zénit» envía las siguientes ejecuciones a la ventana principal. Se retiró la
  adopción automática de tareas y terminales de otras ventanas. La transferencia
  explícita de una terminal existente sigue disponible.
- Ejecutar utiliza una PTY real, también para Java con `System.console()`.
  Distintos editores pueden ejecutar archivos a la vez. Hay seis terminales
  activas como máximo, salida acotada e historial retirado progresivamente. La
  compilación y las tareas con tuberías usan entre uno y cuatro trabajadores,
  según CPU, y hasta dieciséis tareas pendientes. Los paquetes de Hilo conservan
  su cola independiente.
- Los tres puntos cierran su propio menú al pulsarlos de nuevo. Los menús
  quedan separados de su cabecera y los submenús se distribuyen con espacio
  entre niveles. En ventanas estrechas se ocultan niveles anteriores; flecha
  izquierda permite volver. Las extensiones muestran su nombre e identidad
  visual. Se actualizaron los iconos de contraer y dejar flotante.
- Ajustes deja espacio antes de Perfiles de terminal, el distintivo del sistema
  y las acciones situadas tras una lista. La esfera CSS anterior permanece
  oculta mientras se carga el cristal. Babylon se inicia cuando la interfaz está
  preparada y el cristal es visible. El arranque ya no espera a un análisis
  completo del proyecto; Comprobar proyecto sigue disponible manualmente.
  El servidor local admite ráfagas de conexiones de varias ventanas para evitar
  perder importaciones de la interfaz mientras el equipo está compilando.
- La revisión de un VSIX presenta autor, descripción y vistas basadas en sus
  colores e iconos reales. Los planes con dependencias conservan esas vistas.
  Aplicar un paquete de apariencia selecciona sus recursos, sin necesitar
  ejecutar su motor únicamente para aplicar los iconos.

La capa de extensiones utiliza ahora `vscode-uri` oficial. Se incorporaron
`TimelineItem`, información del entorno como `isNewAppInstall`, decoraciones
reales de Monaco con ciclo de vida, grupos de pestañas, casillas de TreeView,
proveedores de identidad de sesión, enlaces de terminal, manejadores URI y
SecretStorage respaldado por el almacén seguro del sistema. Las variantes de
decoración avanzadas y la integración de shell mediante OSC todavía no tienen
cobertura completa.

La auditoría de los diez paquetes instalados logró activar nueve. Prettier
produjo ediciones reales. GitHub Actions sigue requiriendo un proveedor de
autenticación de GitHub: no se generan sesiones ni tokens ficticios. Activación
no equivale a certificar todas las funciones de cada paquete.

Co-Code (CoCo) mantiene los cambios concurrentes con Yjs/Yrs, guarda exclusivamente en
el anfitrión y permite ejecutar allí cuando este lo activa. Incluye deshacer
local, presencia, puntos de control en memoria y una consulta explícita de los
cambios a Melody. La consulta utiliza el proveedor configurado; no cambia ni
acelera por sí misma el modelo remoto. Hilo también conserva temporalmente el
inventario de aportaciones de extensiones para evitar lecturas repetidas.

CoCo separa crear y unirse mediante pestañas. Los modos de conexión tienen
tarjetas alineadas con iconos, y el permiso de guardar y ejecutar se configura
aparte. La invitación y los estados de conexión conservan su espacio propio.
CoCo incorpora los modos Este equipo, Red local e Internet. Dos estaciones
pueden editar la misma sala y ejecutar en el entorno del anfitrión. Para
Internet, Hilo prepara un conector Cloudflare verificado y una dirección HTTPS
temporal; su estado y los reintentos aparecen en CoCo. Un fallo de transporte
conserva el búfer. Este servicio temporal está orientado a desarrollo y pruebas,
sin garantía de disponibilidad; consulte sus límites en TEAM.md.

El botón de copiar invitación deja 16 px bajo el campo y comparte la animación
de Forge: icono al reposar, etiqueta al pasar el cursor y contracción tras pulsar.
El cierre impide arrancar nuevos servidores de lenguaje mientras retira los
existentes, también cuando había un inicio en curso.

CoCo reutiliza una ejecución activa por archivo ante órdenes simultáneas y
conserva el identificador de petición en los reintentos de red. Los demás
participantes pueden observar esa salida sin iniciar otro proceso. El anfitrión
añade archivos a la misma sala sin reemplazar las ediciones en curso. El menú
de tres puntos de una extensión ya no se interpreta como navegación al editor,
incluidas las vistas Lista, Tarjetas y Compacta.

Lantern conserva sus entornos Python y máquinas QEMU por sesión, con opción de
retenerlos mediante `.tern`. Co-Code comparte el entorno de ejecución del
anfitrión y su intérprete Python seleccionado. No crea un contenedor duplicado
en cada ordenador ni convierte automáticamente una VM en destino de ejecución.

Consulte [Co-Code](TEAM.md) para usar los conectores y conocer sus límites.

## Edición de binarios

El visor hexadecimal permite sustituir bytes, deshacer/rehacer y conservar los
cambios al navegar entre páginas o pestañas. Guardar comprueba la revisión y los
bytes originales, escribe un archivo temporal y conserva una copia anterior en
`.lumen/binary-backups`. Retiene las últimas tres copias por archivo. Los cambios
externos o un fallo de compilación no sustituyen el archivo original. También
puedes exportar un parche JSON con los offsets y bytes originales/nuevos.

Se editan archivos de hasta 1 GiB con hasta 64 KiB de sustituciones por guardado;
no se insertan ni eliminan bytes. Los archivos mayores conservan la inspección
por páginas. El IDE no interpreta las estructuras de cada formato ni modifica
firmas digitales o checksums internos por ti.

Recompilar pide un fuente C, C++, ASM, Rust, Go, Java o nC. Emplea la toolchain y
las dependencias del proyecto, compila en una carpeta independiente y sustituye
el artefacto seleccionado solo cuando tiene éxito. Admite ejecutables, clases y
JAR Java y objetos/bibliotecas C/C++. Requiere el SDK apropiado. Recompilar una
clase sustituye esa clase; los proyectos Java con otras clases dependientes
necesitan mantener sus artefactos relacionados actualizados. No reconstruye
fuentes a partir de un ejecutable ni equivale a descompilarlo.

Ejecutar usa una PTY propia y los argumentos indicados, con el mismo destino de
ventana que los archivos de texto. En Windows admite PE ejecutables y Java
clases/JAR; los ELF se ejecutan en Linux con permiso de ejecución. Los archivos
de datos, objetos y DLL requieren un programa anfitrión y se indican como tales.
CoCo comparte por ahora archivos de texto; los parches binarios no se fusionan
mediante CRDT.

## Assembly: motor simulado, equipo y máquina virtual

Laboratorio ASM permite elegir el motor y filtra sus arquitecturas. LLVM/Unicorn
admite x86 de 32 y 64 bits, ARM32, ARM64 y RISC-V32/64. RARS 1.6 añade el entorno
educativo RISC-V32/64 con sus servicios de consola; MARS 4.5 incorpora MIPS32.
Los dos JAR originales están incluidos y verificados por SHA-256; requieren
Java detectado en el equipo. Se admiten dependencias `.include` dentro del
proyecto, entrada del programa y salida real del motor. No se afirma soporte
para todas las ISA existentes: el catálogo se amplía mediante adaptadores y
toolchains concretos, sin presentar un compilador universal.

La simulación tiene límites de 10.000 instrucciones, 128 MiB de heap Java,
12 segundos y 2 MB de salida. Paso reinicia RARS o Unicorn hasta la instrucción
seleccionada; MARS usa ejecución acotada completa y no expone paso en este
adaptador. PC, traza y memoria no publicados por los CLI educativos se indican
como no disponibles. Sus servicios de archivo pueden acceder al sistema con
los permisos del usuario: simular una CPU no equivale a aislar código no fiable.

«Ejecutar en este equipo» utiliza la toolchain nativa, el ABI y la terminal de
Zénit, sin motor simulado. El código educativo RISC-V/MIPS ya no se envía a NASM
por la extensión `.asm`. Los perfiles personalizados de compilación conservan
prioridad. «Máquinas de Lantern» abre la creación y restauración de entornos
`.tern`, incluida la VM Arch x86-64 cuando su base QEMU/imagen está preparada.
Otras máquinas existentes pueden conectarse por SSH. Esta revisión no instala
imágenes de todas las arquitecturas ni arranca kernels en el sistema anfitrión.

## Diagnósticos y preparación de programas nativos

Los errores y advertencias se leen en una tarjeta flotante bajo el código,
con un 35 % de transparencia en el material y texto opaco. La tarjeta no tiene
scroll: separa los diagnósticos y los textos extensos en partes consecutivas,
con flechas, acceso por teclado y copia del mensaje íntegro. La apertura y el
cierre usan animaciones breves; respetan movimiento reducido. `Ctrl+K Ctrl+I`
abre el diagnóstico del cursor. Las explicaciones de selección conservan
la ubicación de Melody elegida por el usuario.

La ejecución nativa estándar de C/C++ exporta `CMakeLists.txt`, una cabecera
inicial `.h`/`.hpp` y los intermediarios del compilador, además del ejecutable
en `.lumen/run/<programa-id>/`. Las descripciones CMake por fuente están en
`.lumen/native/`; conservan los argumentos y dependencias configurados y se
pueden reconstruir con CMake/Ninja. Los CMake y cabeceras existentes no se
sobrescriben y el fuente no se modifica para incluir la cabecera.

Para `.n`/`.nc`, ncc compila una vez con `build-native --no-run` y se ejecuta
el artefacto producido; se crea `ncc.package.json` si no existía. Rust requiere
`rustc` detectado y genera `Cargo.toml` si falta. Las cabeceras C de nC/Rust son
plantillas opcionales de interoperabilidad: no inventan declaraciones ni
convierten tipos del lenguaje a una ABI C. Los perfiles personalizados conservan
prioridad. Las comprobaciones de sintaxis y las copias temporales de Lantern
no crean estos archivos en el proyecto del usuario.

El menú contextual del explorador añade **Guardar** y **Guardar como…** para el archivo elegido. Las pestañas comparten un único controlador de menú, corrigiendo el cierre inmediato por doble activación y conservando Reabrir pestaña cerrada. El botón izquierdo mantiene la apertura normal; el derecho abre las acciones.

## NASM para Linux y Windows

El laboratorio detecta `.asm` NASM y ofrece **NASM + Unicorn**, x86/x86-64 y
un selector de destino **Linux · ELF** o **Windows · PE/COFF**. `BITS 32` y
`; Sistema: Linux`/`; Sistema: Windows` orientan la selección inicial; las
selecciones manuales se mantienen durante esa sesión para cada archivo.
NASM ensambla realmente ELF32/ELF64 o Win32/Win64 y LLVM enlaza la imagen antes
de cargarla en Unicorn. Los ejemplos, las instrucciones, los registros, el
código de salida y el paso a paso corresponden al destino elegido.

El adaptador de Linux implementa `exit` y `write` sobre stdout/stderr dentro
del simulador, con un máximo de 64 KiB. Windows admite programas de CPU y el
retorno de `main`; DLL externas, WinAPI y servicios no implementados requieren
el ejecutor nativo o una máquina virtual. No se reenvían llamadas del invitado
al sistema anfitrión. El laboratorio no incluye un kernel completo.

El ejecutor nativo de NASM conserva el formato y ABI del archivo, valida la
sintaxis sin enlazar cuando solo se comprueba, usa CRT para `main` y admite
`_start` explícito (Linux sin CRT, Windows con `ExitProcess`). Un destino Linux
en un equipo Windows se dirige al laboratorio, Linux/WSL o una VM en lugar de
intentar enlazarlo como `WinMain`. Las toolchains nativas de 32 bits se configuran
por separado; el laboratorio simula ambas anchuras sin requerirlas.

El selector visible **Simulación / Máquina real** cambia la acción principal del
laboratorio. En Máquina real se guarda el archivo, se ensambla y se ejecuta en
una terminal propia mediante el mismo ejecutor nativo de Zénit, sin lanzar
también la simulación. El paso a paso permanece reservado al motor simulado.
Cambiar el destino invalida los resultados de la ejecución anterior.

El laboratorio separado carga el archivo indicado por su ventana y el búfer
compartido actual, incluidos los cambios sin guardar. No vuelve a abrir el
archivo de inicio del proceso principal, que puede haberse borrado o cambiado.
Si el archivo abierto ya no existe en disco, el búfer compartido sigue disponible
para editar y simular; permanece marcado sin guardar hasta que se conserve.
