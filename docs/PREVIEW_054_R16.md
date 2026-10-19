# Zénit 0.5.4 R16 — coherencia y rendimiento

R16 incorpora espacios guardados por proyecto, recuperación duradera y un destino
común de ejecución. HILO deja de ser una herramienta visible: es el núcleo del
backend, **Hyper Integrated Logic Orchestrator / Orquestador lógico hiperintegrado**.

## HILO y rendimiento

El registro de subsistemas valida sus dependencias y cierra los consumidores antes
que los servicios de los que dependen. Coordina runners, SDK, runtimes, destinos,
búferes, terminales, LSP, depuración, Lantern, entornos, Melody, voz, extensiones,
descargas, actualizaciones y CoCo. Un fallo de limpieza queda registrado y no
impide cerrar los demás servicios. Los cambios de SDK invalidan la detección y
retiran los LSP para que se vuelvan a descubrir.

La cola de mantenimiento conserva un trabajador, 24 pendientes y hasta 64 registros.
La identidad de las operaciones incluye el proyecto. Las ventanas comparten una
sola detección simultánea por clave, con caché acotada e invalidación por generación;
la ejecución interactiva no espera en esa cola. Los índices SDK se reutilizan según
ruta, fecha y tamaño. Lantern evita leer y analizar de nuevo checkpoints JSON sin
cambios. Melody pausa su animación de texto en ventanas ocultas y retoma la última
respuesta al volver. Estas mejoras no constituyen un porcentaje de rendimiento ni
un benchmark de velocidad de los proveedores IA.

No hay panel, comando ni sondeo frontend de HILO. Las antiguas rutas `/hilo` se
mantienen como compatibilidad interna. Las operaciones específicas de Lantern y
SDK consultan `/operations` mientras una operación propia está en marcha.

## Espacios y recuperación

El icono de espacios junto a las pestañas abre **Espacios de trabajo**. También está
disponible en la paleta. Se guardan paneles, tamaños, pestañas, estilo y división
por proyecto, hasta 12 espacios. Abrir un espacio conserva los documentos con
cambios pendientes. Un espacio de una vista elimina una división anterior.

La recuperación guarda texto sin guardar, revisión original, pestaña activa,
posiciones, desplazamientos y orden de las vistas. Vive en el perfil local, bajo
`workbenches/`, fuera de los proyectos y del almacenamiento ligado al puerto del
navegador. Las ventanas externas escriben el mismo búfer; el hub conserva la
versión más reciente. Al cerrar una ventana nativa se captura también la última
edición, sin esperar al temporizador de recuperación.

Los archivos fuente nunca se guardan por recuperar una sesión. Si cambiaron en
disco, se conserva el texto recuperado y su revisión original para activar la
resolución de conflictos al guardar. Un archivo de recuperación malformado se
conserva como `.corrupt-<fecha>.json` antes de iniciar otro. Los binarios conservan
sus funciones de guardado explícito; la recuperación no serializa sus bytes.
Límites: 48 documentos, 2 MiB por búfer modificado y 8 MiB de texto total. El ajuste
**General · Recuperar sesión** permite desactivar la restauración automática.

Se unifican alturas de cabeceras y espaciado de acciones; los controles respetan el
ancho disponible. Las consultas de Melody desde Forge, Lantern, laboratorio y
herramientas conservan su posición actual. Recuperar pestañas no convierte una
cancelación interna de Monaco en una pantalla falsa de fallo de arranque.

La revisión visual posterior iguala las tres cabeceras a 52 px, incluida Melody.
En un explorador estrecho, las acciones secundarias pasan al menú de tres puntos
sin desaparecer: abrir una ventana externa por debajo de 270 px y crear archivo
por debajo de 235 px. El editor de binarios reúne edición y ejecución en una fila
cuando cabe; en vistas estrechas utiliza iconos con nombres accesibles y conserva
al menos 160 px para la tabla hexadecimal. Estos cambios responden al ancho del
panel, también en divisiones y ventanas independientes.

## Destino común

El selector superior guarda un destino por proyecto y lo comparte entre ventanas:

- **Este equipo** usa el runtime y el intérprete del proyecto.
- **WSL** muestra distribuciones detectadas y convierte rutas Windows a `/mnt/...`.
- **SSH** usa una estación configurada y una carpeta remota absoluta.

Los planes de ejecución/comprobación de archivos usan ese destino, incluidos los
planes solicitados por CoCo en el anfitrión. El selector no copia archivos a SSH:
deben estar guardados y presentes en la carpeta de esa estación. Los compiladores
y las dependencias deben existir en el destino. Los comandos se construyen como
argumentos y se escapan para el shell remoto.

Un destino eliminado o una combinación no implementada produce un mensaje; no
se ejecuta silenciosamente en el equipo local. DAP, checkpoints cooperativos y
los modos de Forge para búfer Python/GDB/binarios siguen siendo locales. Las
máquinas QEMU sin SSH mantienen su consola, pero no se anuncian como destinos de
archivos. La planificación WSL/SSH se comprueba con fixtures; no acredita una
prueba entre dos equipos físicos o redes distintas.

## SDK modular

**Laboratorio · SDK** permite activar una carpeta preparada con `tool-index.json`,
incorporar un ZIP de componentes o dejar de usar una base sin borrarla. La
importación verifica plataforma, lista exacta de archivos, SHA-256, rutas y
límites, incluso al reutilizar una copia preparada. Los paquetes se extraen en una
carpeta temporal del perfil y se activan después de verificarse. No ejecuta las
herramientas durante la importación ni modifica el SDK original.

Para producir un componente desde una base preparada:

```powershell
python tools/package_sdk.py --component nasm --output dist/sdk/Zenit-SDK-nasm-Windows-x64.zip
```

El exportador admite los componentes presentes en el índice: Python, GCC, LLVM,
nC, NASM, Java, Node, Bash, Docker, QEMU, imágenes, Maven y Gradle. No descarga
componentes ausentes ni cambia sus licencias. La construcción admite una base
mínima y componentes opcionales:

```powershell
python tools/build_desktop.py --installer --require-assets --sdk-components python,nasm
```

Python es obligatorio. La distribución estándar mantiene Python/GCC/LLVM/nC/NASM
para conservar las capacidades anteriores. No se ha creado un servicio remoto de
descarga de componentes.

## Extensiones y validación

Se corrigen los contratos de Position/Range/Selection de VS Code: coordenadas no
negativas, rangos ordenados, selecciones invertidas, sobrecargas y operaciones
sobre rangos. SemanticTokensBuilder acepta esas mismas instancias. Esto amplía
compatibilidad real; no equivale a paridad completa ni garantiza todas las
extensiones. Referencia del contrato: [VS Code API](https://code.visualstudio.com/api/references/vscode-api).

Las pruebas incluyen backend de orquestación/recuperación/destinos/SDK, integración
de ventanas, SDK NASM real, tres temas y tres tamaños, cierre nativo inmediato,
diagnósticos, CoCo y edición/ejecución de binarios. Los fixtures remotos y los
transportes IA deterministas se distinguen de ejecución y conexiones reales.
Los informes de esta construcción están bajo `qa-output/r16-*` y la verificación
del paquete acompaña sus manifiestos en `dist/`.
