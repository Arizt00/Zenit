# Zénit 0.5.4 R15

R15 corrige el destino de las ejecuciones y añade una primera implementación
funcional de trabajo en equipo. No se afirma paridad completa con VS Code.

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
