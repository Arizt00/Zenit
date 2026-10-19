# Zénit 0.5.4 R17 — flujos de proyecto comprobables

R17 amplía la R16 corregida. Conserva su recuperación de sesión, espacios por
proyecto, destino común y deshacer de cambios de extensiones.
El cierre nativo espera la captura final sin bloquear el hilo de WebView2, de
modo que la última pulsación puede recuperarse incluso al cerrar inmediatamente.

## Lantern y entornos reproducibles

Los nuevos `.tern` usan el esquema 2: versión e implementación exactas de Python,
dependencias fijadas, plataforma, destino y pasos de preparación declarativos.
Los descriptores anteriores siguen abriéndose. La exportación `.tern.zip` incluye
ruedas disponibles con sus hashes y un informe de recursos ausentes. Reunir ruedas
desde PyPI es una acción explícita. Reconstruir comprueba las huellas y utiliza
`pip --no-index --require-hashes` en un entorno nuevo, sin sustituir otro existente.

Las máquinas virtuales se exportan detenidas mediante `qemu-img convert` a un
QCOW2 independiente de la imagen base, con su semilla. La reconstrucción crea otra
identidad. Se exige la versión indicada de QEMU; el hipervisor y el intérprete se
incorporan con el SDK, no se inventan dentro del descriptor. La prueba de
portabilidad valida un disco real sin sistema invitado; no certifica el arranque
de todas las imágenes y sistemas operativos.

## Melody, pruebas y Git

Los planes de varios archivos muestran los archivos consultados y diferencias
antes de aplicar. El recibo conserva el conjunto, su restauración y el registro
de las pruebas ejecutadas. **Probar cambios** presenta las órdenes y permite
ejecutar la suite; no interpreta órdenes arbitrarias de la respuesta de la IA.
No se restaura un conjunto mientras sus pruebas siguen en marcha.

El explorador descubre pruebas Python sin importar el proyecto. Ejecuta unittest
o pytest y enlaza resultados a las líneas reales. La cobertura es opcional y
requiere `coverage` en el entorno del proyecto. Cargo y CTest utilizan sus
herramientas instaladas y sus informes reales; las preparaciones son trabajos
dependientes. Las marcas de resultado se retiran si los archivos consultados
cambian. No se confunde una activación de herramientas con una suite aprobada.

El editor de conflictos lee las tres etapas reales del índice Git. Muestra nuestro
contenido, el resultado editable y el contenido entrante; la base está disponible
para consulta. Recupera borradores, permite deshacer aceptar un lado y conserva una
copia anterior antes de guardar. Marcar resuelto prepara únicamente el archivo
seleccionado; no crea commits. Comprueba que ni el índice ni el búfer ni el archivo
cambiaron durante la revisión. Los conflictos binarios no se convierten en texto.

## Co-Code / CoCo

Las nuevas sesiones usan el protocolo 2. El anfitrión puede compartir el árbol del
proyecto, abrir documentos, crear y renombrar archivos y revisar diferencias y
operaciones. Se excluyen credenciales, enlaces y carpetas de dependencias o
generadas. Los binarios aparecen identificados y no se editan como texto compartido.

Cada participante entra en lectura; el anfitrión asigna edición o edición y
ejecución. La credencial de reconexión pertenece a esa estación. Renombrar conserva
la identidad CRDT, incluso si otra persona todavía tiene actualizaciones con la
ruta anterior. Los cambios pendientes se mantienen durante cortes de red y los
clientes web recuperan su estado CRDT local al recargar. Esto no sustituye una
copia del proyecto ni recupera automáticamente un anfitrión cuyo proceso terminó.

Todas las ejecuciones compartidas permanecen en el anfitrión. Los reintentos usan
identidades de petición; un reintento antiguo no vuelve a lanzar un proceso aunque
su resultado haya salido de la caché. Una ejecución activa del mismo documento se
comparte. La cola, los documentos, las actualizaciones y los recursos de sesión
tienen presupuestos de memoria; no existe un límite fijo de personas.

El conector VS Code 0.2 usa el mismo protocolo, incluye selección de archivos del
proyecto y acciones de creación y renombrado. JetBrains utiliza su editor CoCo
integrado, servido por el anfitrión. Las sesiones anteriores mantienen el protocolo
1 para compatibilidad con conectores antiguos. Se han probado interfaces separadas,
VS Code real, la interfaz de red local y un túnel HTTPS público desde este equipo;
no son una prueba con dos ordenadores físicos.

## Orquestación y compilaciones

HILO sigue siendo el motor interno. La interfaz **Tareas** permite revisar trabajos,
dependencias, prioridades y cancelación. No instala servicios ni inicia sondeos
generales de hardware. CPU y memoria corresponden a los procesos propios observados.
Las compilaciones C/C++ se reutilizan solo si coinciden órdenes, entorno, compilador,
fuentes, cabeceras, entradas del enlazador y artefactos. El programa vuelve a
ejecutarse; la caché no reutiliza su salida ni omite pruebas.

## Máquina y binarios

El inspector ELF32/64 y PE32/32+ lee secciones y símbolos con límites de tamaño y
revisión. Los símbolos pueden faltar en archivos que se distribuyen sin esa tabla.
La comparación muestra intervalos de hasta 64 KiB y grupos de diferencias, incluidos
cambios de tamaño; permite avanzar por el archivo sin cargarlo entero.

LLDB/DAP expone registros reales junto a la pila. La consulta de memoria y
desensamblado comprueba la identidad de la pausa antes y después de cada operación.
Al avanzar se invalidan los datos anteriores. **Paso atrás** solo se habilita si el
motor anuncia `supportsStepBack`; no se simula retroceso en LLDB sin ese soporte.
La edición, copia anterior, recompilación y ejecución binaria de R16 se mantienen.

## Extensiones y SDK

Los comandos de los submenús conservan sus iconos declarados y disponen de iconos
por acción cuando la extensión no los declara. Se corrigieron la carga de metadatos
grandes de GitLens y el proveedor de autenticación GitHub que impedía activar GitHub
Actions. Las credenciales requieren conexión explícita y consentimiento por extensión.

La revisión instalada corrigió además la apertura de vistas web al activar GitLab
y GitLens: registrar un proveedor ya no crea pestañas ni tapa el archivo recuperado.
La vista se resuelve al solicitar su apertura y puede cerrarse y abrirse de nuevo.
El clic en una pestaña de archivo devuelve el editor sin descartar el búfer.
También se enlazaron los comandos de enfoque de árboles, incluidos los declarados
antes de crear su proveedor. GitLens ya no termina su proceso al solicitar uno de
esos árboles; la interfaz abre la vista correspondiente o indica que el proveedor
todavía no está registrado. Los paneles con `preserveFocus` respetan el editor activo.

La matriz `config/extension-compatibility.json` vincula pruebas a ID, versión y
SHA-256 exactos. **Ver pruebas verificadas** distingue activación, comportamiento
comprobado y capacidades sin certificar. EditorConfig se prueba con opciones reales
de Monaco; Even Better TOML con formato, símbolos y Ctrl+Z. No se declara paridad
total con VS Code ni se comprueban funciones remotas mediante cuentas ficticias.

El instalador ligero conserva el runtime Python necesario. Las herramientas de
lenguaje se distribuyen como paquetes SDK opcionales con manifiesto y hashes por
archivo; se incorporan desde **Laboratorio → SDK**. Las bases ya preparadas pueden
reutilizarse sin descargarlas. Desactivar una base no borra sus archivos.

Las pruebas de esta entrega usan proyectos y perfiles temporales. Los informes de
la compilación y la comprobación instalada acompañan a los artefactos de entrega.
