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
