# Co-Code · CoCo

Abre **CoCo** en la parte superior derecha de Zénit o desde la paleta de comandos.
Abre un archivo de texto y crea un equipo para compartir su búfer, incluidos los
cambios que aún no has guardado. El servicio permanece apagado hasta entonces.

La invitación permite editar los archivos que el anfitrión comparte. Elige el
alcance antes de crear la sesión:

| Modo | Conexión entre estaciones |
| --- | --- |
| Este equipo | Otras instancias de Zénit o IDEs en el mismo ordenador. Solo escucha en la interfaz local. |
| Red local | Otros ordenadores de tu red privada, mediante la dirección del anfitrión. El cortafuegos debe permitir esa conexión; Zénit no cambia sus reglas. |
| Internet | Equipos en redes distintas mediante una dirección HTTPS temporal de Cloudflare. Hilo prepara el conector y la invitación aparece cuando el enlace está listo. |

En todos los modos se comparte la misma sesión, con un único búfer por archivo
y el entorno de ejecución del anfitrión. Cada participante puede usar Zénit o
un conector compatible. La estación anfitriona debe permanecer abierta y
conectada. No se necesitan privilegios de administrador ni un servicio de
Windows.

Internet descarga `cloudflared` 2026.10.1 de su publicación oficial, verifica
su SHA-256 y lo conserva en el perfil de Zénit. La preparación automática admite
Windows x64 y Linux x64/ARM64. No requiere una cuenta de Cloudflare. El tráfico
pasa por Cloudflare: HTTPS no significa cifrado de extremo a extremo entre
participantes. Terminar la sesión detiene el conector y revoca la invitación.
Si el enlace falla, «Reintentar conexión de Internet» conserva el mismo búfer y
la misma sala; comparte la nueva invitación para reconectar las estaciones.

Este transporte utiliza [Quick Tunnels de Cloudflare](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/),
orientados a desarrollo y pruebas, sin garantía de disponibilidad. El proveedor
admite hasta 200 peticiones en curso, que no equivalen a 200 participantes. La
dirección cambia al reiniciar el enlace. Para trabajo permanente se puede usar
una red privada entre estaciones con el modo Red local; R15 no incluye un
servidor propio de encuentro ni sesiones persistentes en la nube.

«Permitir guardar y ejecutar en mi equipo» autoriza esas acciones a los
participantes. Los procesos usan las herramientas y el entorno del anfitrión.
Los invitados no necesitan instalar esas dependencias. Una ejecución activa por
archivo se comparte entre los participantes: pulsar Ejecutar al mismo tiempo
recupera el mismo trabajo, sin duplicar su proceso. Los archivos distintos pueden
ejecutarse de forma independiente dentro de la cola acotada del anfitrión. Los
clientes publican un identificador por intención y conservan ese identificador al
reintentar una petición; la sala recuerda las últimas 128 intenciones. La salida
se observa también desde los demás clientes, con cursores independientes que
leen el mismo trabajo. Los cambios de texto se
fusionan mediante CRDT; los cambios externos en disco requieren revisión antes
de guardar. La sesión conserva el texto compartido si detecta ese conflicto.

Puedes entrar desde otra instancia de Zénit con la invitación completa. También
puedes abrirla en un navegador con Monaco integrado. La invitación deja de
funcionar cuando el anfitrión termina la sesión. Los participantes inactivos se
retiran del listado tras 45 segundos.

Los conectores se descargan desde «Conectar desde otra IDE» en CoCo:

| Editor | Uso | Verificación de R15 |
| --- | --- | --- |
| VS Code | Instala el VSIX y ejecuta «Co-Code: unirme con una invitación». Los archivos `zenit-team:` se editan en el editor nativo; Guardar escribe en el anfitrión. | Probado en VS Code 1.141.2 con perfil temporal: edición Unicode concurrente, guardado y ejecución. |
| Antigravity u otro editor compatible con VSIX/API de VS Code | Instala el mismo VSIX si el producto admite esas API. | No se ejecutó una prueba dentro de Antigravity. |
| JetBrains 2025.2 o posterior, con JCEF | Instala el ZIP desde disco y abre la herramienta «Co-Code». Introduce la invitación y conecta. Usa un editor Monaco dentro de esa herramienta. | Compilado con JDK 21 y SDK oficial 252.28539.108. El cliente integrado pasó las pruebas de navegador; queda pendiente probar el plugin dentro de JetBrains. |

El conector JetBrains no enlaza todavía el Document nativo del IDE. Si JCEF no
está disponible, ofrece abrir el cliente del navegador. Los conectores no se
instalan automáticamente en otros editores.

No hay un límite fijo de personas en el producto. La memoria, CPU y red del
anfitrión determinan la capacidad real; se probó el registro de 81 participantes,
no una carga ilimitada de editores. Una sesión admite hasta 32 archivos de
500 KB cada uno y hasta 8 MB de texto total. La interfaz inicial comparte el
archivo actual; el anfitrión puede añadir otros archivos abiertos con
«Compartir archivo actual» sin cambiar la sala ni reemplazar los búferes que ya
se están editando. Los presupuestos de petición y estado CRDT evitan crecimiento
sin control. La sincronización envía cambios incrementales y reduce su frecuencia
cuando la ventana está oculta o la conexión falla.

Deshacer revierte tus propias operaciones de la sesión. Los puntos de control
retienen hasta cuatro instantáneas de texto en memoria, de hasta 2 MB cada una;
solo el anfitrión restaura y restaurar no escribe automáticamente en disco.
«Revisar cambios con Melody» envía el antes/después al proveedor de IA que ya
tengas configurado, únicamente cuando pulsas esa acción.

## Prueba entre estaciones

`tools/check_coco_station.py` prepara una sesión exclusivamente con dos archivos
de prueba. En el anfitrión:

```powershell
python tools/check_coco_station.py host --mode lan --exchange qa-output/coco-lan
```

Copia `invitation.json` de esa carpeta al segundo equipo y ejecuta allí:

```powershell
python tools/check_coco_station.py join --invitation-file invitation.json --report peer-report.json
```

Repite con `--mode internet` en el anfitrión y conecta el segundo equipo desde
otra red. Los informes comprueban la misma sala, dos archivos con ediciones
Unicode, guardado en el anfitrión y ocho intenciones concurrentes que convergen
a un único proceso por archivo. Repetir las peticiones después de completar los
trabajos debe devolver sus identificadores originales. La sesión de prueba se
cierra automáticamente al terminar o al agotar el tiempo de espera.

El script necesita las dependencias Python del proyecto. También puede
ejecutarse con `zenit-python.exe --python-child <ruta-al-script> ...` desde una
instalación de Zénit, usando su runtime incluido. Por defecto rechaza ejecutarse
como invitado en la misma estación. `--allow-same-station` permite comprobar el
verificador localmente, pero marca explícitamente que no valida dos equipos.
Identidades de sistema distintas tampoco acreditan por sí solas dos máquinas
físicas. La prueba entre dos equipos queda pendiente cuando no se dispone del
segundo equipo; no debe sustituirse por dos procesos locales ni una VM y
presentarse como comprobación física.

Para reconstruir los archivos de instalación de los conectores:

```powershell
python tools/build_team_integrations.py
```

El build valida las huellas de las fuentes y del JAR JetBrains precompilado.
Para recompilar ese JAR se requiere JDK 21 y el SDK oficial fijado por el script:

```powershell
python tools/build_team_integrations.py --jetbrains
```

## Reconexión y operaciones con respuesta perdida

Los clientes Zénit, navegador/JCEF y el conector VS Code 0.2.1 generan su
credencial antes de la primera sincronización. El anfitrión conserva sólo su
huella. Si la primera respuesta se pierde, el reintento recupera al mismo
participante y sus permisos. Los clientes anteriores que esperan una credencial
generada en el servidor siguen admitidos, con su limitación ante ese primer corte.
Zénit conserva hasta 16 identidades de conexión por proyecto en su perfil local.
La recuperación descrita más abajo sobrevive al cierre del anfitrión y al
reinicio de su backend; requiere continuar la sesión desde CoCo.
El navegador conserva la identidad en sessionStorage de la pestaña y VS Code usa
su almacén de secretos. La invitación no se copia en los registros de ejecución.

Las peticiones de ejecución sin confirmar se guardan antes de enviarlas y
recuperan su mismo identificador al recargar la pestaña. En VS Code se conservan
en el estado del espacio de trabajo. Los identificadores se vinculan al documento
y al participante. Una respuesta perdida después de finalizar el programa no
autoriza otra ejecución. La creación y el renombrado incorporan identificadores
de operación y comprueban que el reintento conserva la misma petición; un cambio
de permisos se valida incluso al repetir una operación ya procesada. Los registros
son acotados: los identificadores expulsados se rechazan sin volver a actuar.
El transporte admite hasta 16 peticiones POST simultáneas, independientemente del
número de participantes. Las peticiones adicionales reciben 503 para reintentar;
esto limita los cuerpos y respuestas retenidos en memoria durante conexiones
lentas. Los recursos del editor se sirven por su ruta independiente.

**Origen de la ejecución** muestra el SHA-256 del archivo guardado antes de
iniciar, las órdenes del anfitrión, el entorno reconstruido cuando existe un
recibo y la coincidencia con el archivo, el búfer compartido y la configuración
actuales. Se comprueba si cambió el tamaño o fecha de las herramientas registradas;
esa comprobación no verifica todos sus bytes. Melody
puede explicar ese informe. Se conserva evidencia de las últimas 128 ejecuciones
en el perfil de recuperación; no congela el resto del proyecto, los ejecutables de las herramientas,
las variables ni los datos externos. La huella de salida corresponde a la
consola retenida, cuyo límite se indica en el informe.

La validación de desarrollo utiliza `tests/test_coco_recovery.py` con un relay TCP
real que introduce latencia y pierde respuestas de conexión, ejecución y cambios
del árbol. `tests/check_coco_internet_ui.py` recorre el endpoint HTTPS público con
dos respuestas de ejecución perdidas y una recarga del invitado. Ambos se ejecutan
en una estación: comprueban los fallos y el transporte, pero no dos redes o dos
máquinas físicas. `tests/check_team_vscode.py --r17` comprueba el conector dentro
de VS Code real con un perfil desechable. El JAR JetBrains sirve el cliente web;
su IDE no se ha vuelto a validar en este bloque.

## Continuar después de reiniciar el anfitrión

CoCo guarda la sala y los estados CRDT completos, sus identificadores de documento,
alias, puntos de control, permisos y credenciales de reconexión verificadas. Los
cambios aceptados se confirman después de la transacción local. Los sondeos sin
cambios no vuelven a escribir los documentos. El estado reside en
`co-code/recovery.sqlite3`, dentro del perfil, y no dentro del proyecto ni de su
exportación `.tern`. Windows cifra los datos con DPAPI para el usuario actual;
POSIX limita los permisos del directorio y del archivo. Copiar el perfil a otro
usuario de Windows no traslada esas credenciales.

Al abrir CoCo después de un cierre aparece **Continuar sesión**. No se abre un
puerto ni se ejecuta código hasta que el anfitrión continúa expresamente en un
proyecto autorizado. **Descartar recuperación** pide confirmación antes de
eliminar la copia compartida; conserva los archivos guardados. **Terminar
conexión** en el anfitrión revoca la invitación y elimina su recuperación. Cerrar
el IDE o cambiar de proyecto conserva el punto de recuperación.

El anfitrión intenta reutilizar el mismo puerto local o LAN. Si está ocupado
elige otro y muestra una invitación nueva. Internet vuelve a preparar su enlace
HTTPS, cuya dirección puede cambiar. Zénit y el conector VS Code **0.2.2** conservan
la identidad por la credencial de la sala, incluso si cambia esa dirección. El
conector migra credenciales e intenciones pendientes de 0.2.1. Un navegador está
limitado por el almacenamiento de su origen: una dirección HTTPS diferente abre
otro origen y puede requerir entrar como una estación nueva y volver a conceder
permisos. No se anuncia reconexión automática de esa pestaña entre dominios.

Antes de iniciar un programa se registra su identidad y la intención que lo
solicitó. Si el backend desaparece entre esa reserva y la confirmación final, la
ejecución queda **interrumpida o sin resultado confirmado**. Repetir su intención
recupera ese mismo registro, sin ejecutar otra vez. Las operaciones de creación y
renombrado también reservan su intención antes de tocar el árbol; una operación
ambigua tras un corte requiere revisar los archivos, y su reintento no vuelve a
modificarlos. Un bloqueo por proyecto impide que dos backends vivos recuperen la
misma sala simultáneamente.

Se conservan las colas finales de consola de las últimas 16 ejecuciones, con hasta
100 000 caracteres cada una. Las ejecuciones activas guardan la última salida
observada, como máximo una vez por segundo; un corte abrupto puede perder salida
posterior a ese punto. Los identificadores y las huellas de intenciones siguen
teniendo presupuestos separados y nunca se expulsan para autorizar un reintento
antiguo. El resultado recuperado permite consultar su origen y señala si cambió
el archivo, el búfer, la configuración o las herramientas.

CoCo no vuelve a conectar la entrada/salida de un proceso huérfano ni inventa su
código de salida. Cuando conoce su PID y la fecha de creación comprueba ambos
antes de ofrecer **Detener proceso anterior**, incluyendo sus hijos. En los demás
casos exige **Confirmar interrupción** al anfitrión antes de admitir una intención
nueva para ese archivo. Esto implica revisar un resultado incierto; confirmar no
demuestra que un programa cuyo arranque no llegó a registrarse haya terminado.
Los cambios externos en disco se señalan y no se sobrescriben al recuperar.

Si un borrador de texto recuperado por el editor difiere de la sala, Zénit guarda
una copia local cifrada antes de sincronizarlo. **Revisar borrador** permite leer
y copiar esa versión; no la aplica sobre los cambios de los demás participantes.
Estas copias privadas no se publican en CoCo y sobreviven también a terminar la
sala. Se eliminan expresamente desde su revisión. Se admiten hasta 128 copias y
8 MB por proyecto; al alcanzar el límite se conserva el editor sin sustituir su
texto. La garantía cubre el último punto de recuperación confirmado, no teclas
que no llegaron a guardarse antes de un cierre abrupto.

El origen de una ejecución recuperada compara también las fuentes y descriptores
locales consultados, la configuración de ejecución y los archivos METADATA/RECORD
del entorno Python del proyecto, dentro de presupuestos de lectura. No verifica
todos los bytes de paquetes instalados ni las dependencias Python globales.

`tests/test_coco_persistence.py` recrea aplicaciones, pierde confirmaciones de
renombrado, comprueba permisos y cierres explícitos, e incluye un cierre abrupto
de un backend en otro proceso con un programa que sobrevive. El recorrido visual
`tests/check_coco_persistence_ui.py` comprueba la recuperación, los conflictos, la
confirmación de interrupciones y el origen de resultados en perfiles temporales.
Estas pruebas siguen realizándose en una sola estación física.
