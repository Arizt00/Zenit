# Implementación · Zénit 0.5.3 Preview R12

## Corrección solicitada de la voz de Emma

R11 seleccionaba `moss-approved` mediante authorizedVoiceDirectory. La aplicación
Emma actual selecciona su asistente mediante assistantVoice('emma'), que resuelve
la identidad nueva preparada el 4 de octubre y elegida por el usuario con Qwen.
R12 utiliza ese mismo selector y mantiene sus validaciones de identidad y hashes.
No modifica Emma, sus referencias ni sus parámetros de voz.

Archivos funcionales: `backend/emma_voice_bridge.mjs`, `backend/melody_voice.py`.
El bridge exige la identidad nueva de Emma, disponibilidad del motor Qwen y
coincidencia del motor en la respuesta terminada. Falta de voz/modelo o una
identidad distinta devuelve un error; no cae silenciosamente en MOSS ni una
voz de sistema. El audio sigue siendo local, autenticado, no-store, cancelable
y limitado a 2500 caracteres de prosa. Se conservan los controles de R11.

Se actualizan versión/instalador a R12 y el test del player para comprobar la
duración real del WAV de entrada, sin fijarla al audio antiguo. Tres tests Node
nuevos verifican identidad nueva, ausencia de fallback e igualdad del motor.
Los 85 tests Node pasan. Siete tests Python relacionados con voz/configuración
pasan; 14 comprobaciones UI de voz/tema se repiten con el nuevo audio. No se
repite la matriz completa de R11, porque la composición de UI no cambia aquí.

Generación Qwen real: 4.24 s a 24000 Hz,
pico 0.531, cero muestras saturadas. Tiempo medido de esta petición:
37.28 s. No se declara voz instantánea ni calidad
perceptual validada para todos los textos. Las pruebas UI reutilizan ese WAV
real y un fixture explícito de IA; no evalúan un proveedor externo.

Se elige la voz nueva local ya preparada, como autorizó el usuario. No se activa
una voz online ni se solicitan/copían credenciales. OpenAI ofrece integración de
voz mediante su API de audio; no se afirma que estas voces sean idénticas a la
selección de ChatGPT ni se conecta una cuenta sin configurar ese servicio.

Evidencia: `tests/visual/evidence/r12-*`,
`tests/visual/current/melody-new-voice.png`. Los resultados de R11 siguientes
son históricos y siguen describiendo la implementación conservada.

---

# Implementación · Zénit 0.5.3 Preview R11

## Cambios y causas verificadas

R11 continúa sobre `27f3067a927f0ced1ef93198f6d0ef10a077fb8d` (R10).
La ventana del usuario comprobada al empezar era R10 y tenía One Dark Pro Darker.
R10 había corregido el reinicio global de Monaco al copiar `theme` en un editor
dividido. R11 comprueba esa corrección con One Dark Pro y Bearded Solarized Light.
No se atribuye al usuario una causa que no se haya reproducido.

Se corrigen tres problemas adicionales: la barra mostraba el tema base en lugar
del efectivo; el arranque/reload podía mostrar colores nativos hasta recibir las
contribuciones; pasar a un tema nativo guardaba primero el borrado del tema de
extensión, creando un estado intermedio. Ahora se restaura una instantánea de
colores validada antes del CSS, se esperan las contribuciones antes de resolver
el tema y ambos ajustes se guardan en una única operación. Respuestas antiguas
de contribuciones no reemplazan el estado de una petición más reciente.
Un tema ausente se comunica con un error explícito y fallback nativo.

## Arquitectura y archivos

- `web/src/theme-cache.js`, `theme-init.js`, `extension-theme.js`, `web/index.html`:
  bootstrap clásico previo al CSS, whitelist de tokens y colores hex; no URLs,
  CSS arbitrario, credenciales ni datos de proyecto en la instantánea.
- `web/src/app.js`, `workbench.js`: controles del tema efectivo y actualización
  atómica de preferencias; modelos, foco y canvases existentes se conservan.
- `backend/extension_api.cjs`, `extension_runtime.py`, `extension_services.py`:
  `workspace.getConfiguration('workbench').get/has/inspect/update('colorTheme')`
  consulta y modifica el perfil real. Eventos de configuración y color llegan al
  host Node. Solo Global está implementado; Workspace/WorkspaceFolder se rechazan.
- `backend/melody_voice.py`, `emma_voice_bridge.mjs`, `emma_voice_worker.py`:
  trabajos locales limitados y cancelables, usando la voz MOSS aprobada existente
  de Emma y decodificación continua. PCM mono de 16 bits se convierte en WAV.
  El audio reside en memoria y se entrega por una ruta autenticada `no-store`.
- `web/src/melody-voice.js`, `melody-companion.js`, `workbench.js`,
  `web/design/melody-voice.css`: Escuchar respuesta/consejo/selección; pausa,
  reanudación y parada. Un consejo invalidado detiene su lectura. No hay lectura
  automática, envío adicional de código ni cambios de archivo al escuchar.
- `web/src/product-ui.js`, `web/design/melody.css`, `icons.js`: una fila compacta
  de herramientas permite ver las cuatro acciones de Melody a 1672×917. Voz y
  pausa usan la misma cuadrícula SVG de 24 unidades. Los controles usan tokens
  existentes de espaciado, radio, borde, superficies y texto, sin `transition:all`.
- `preferences.py`, `server.py`, `platform_services.py`, `packaging/lumen.spec`:
  configuración independiente de la voz y empaquetado de los bridges; la voz
  puede usarse aunque el proveedor de análisis sea otro. No se incluyen referencias
  privadas ni modelos de Emma en el instalador público.

## Verificación real

294 tests de Python: 289 aprobados y 5 omitidos por requisitos del entorno.
82 tests Node aprobados; 61 archivos JavaScript comprobados sintácticamente.
Se prueban 89 variantes reales, siete pares de contraste de texto, y los seis
pasos de estabilidad de Bearded con los 16 colores ANSI originales en xterm.
Una extensión Node real prueba lectura/escritura de colorTheme, cuatro tipos
de tema y rechazo de temas inexistentes o targets todavía no implementados.

14 comprobaciones nuevas de voz/tema/UI: One Dark Pro al dividir y cambiar
preferencias; colores conservados antes de cargar contribuciones; transición
nativa atómica; cuatro acciones visibles; reproducción, pausa, reanudación,
parada, selección, autenticación y tamaños de escritorio. El player reutiliza
un WAV generado en la comprobación MOSS real; el proveedor de IA es un fixture
explícito. Esa prueba no evalúa la calidad del modelo de análisis.

La generación real MOSS produjo 6,88 s de audio a 24 kHz, pico 0,729 y cero
muestras saturadas. Esa generación tardó 61,03 s en este equipo. No se presenta
como voz instantánea, ni como evaluación perceptual de todos los textos.
Se mantuvo el mismo procesamiento continuo aprobado para el vídeo anterior.

También pasan 21 comprobaciones de bienvenida/Monaco/Melody, 12 de depuración
y output real, 7 de archivos/paneles/ConPTY y 7 de TextMate/ASM. Se ejecutan 13
vistas de WebView2 y 24 combinaciones de resolución/escala con 72 capturas.
Los cinco bounds principales pasan dentro de 2 px. Las referencias originales
se conservan; overlay/diff no equivale a fidelidad perfecta ni a paridad de API.

Los informes y JSON están en `tests/visual/evidence/r11-*`; capturas y overlays
en `tests/visual/current` y `tests/visual/comparisons`. `VISUAL_DIFF_REPORT.md`
describe diferencias por pantalla. La matriz es emulación de escala en Edge;
la captura nativa usa Windows al 150 %, sin cambiar la escala del usuario.

## Límites

No existe evidencia para certificar 90 % global de VS Code. OAuth integrado,
esquemas virtuales, CustomDocument y otras APIs siguen pendientes según
`KNOWN_LIMITATIONS.md`. Se amplía un contrato concreto, sin afirmar que todos
los plugins funcionan. La mejora de análisis/predicción se prueba en su contrato
de contexto/revisión/aceptación; no se certifica calidad de proveedores externos.

Voz: utiliza una instalación local existente y validada de Emma/MOSS, en español.
No descarga modelos, referencias privadas ni voces alternativas. Sin ese motor,
con memoria insuficiente o ante un fallo, muestra el error real. Hasta 2500
caracteres de prosa por lectura, sin bloques de código, un trabajo de generación
a la vez. La reproducción tiene controles explícitos y libera su blob al parar.


## Distribución verificada de R11

El build procede de `2b6e6581f7163154c02d9c676a68919bb7dcfe99` y está publicado en
[GitHub](https://github.com/Arizt00/Zenit/releases/tag/v0.5.3-preview.11).
Instalador: 113074595 bytes; portable:
70847109 bytes. Los cinco assets tienen SHA-256
confirmado por GitHub; no se sustituyen releases anteriores.

Se superan 15 comprobaciones del paquete nativo y 12 del helper instalado.
Los 101 archivos de frontend/assets/bridges coinciden byte por byte con el
build. La comprobación instalada usa un Vira real en perfil QA aislado:
contraste, 20 variantes, y evento ColorThemeKind recibido por una extensión
Node real. Además verifica render/pausa, Laboratory, Debug y recuperación
de archivos. El consentimiento de IA sigue desactivado al iniciar.

`app-0.5.3-R11` conserva el payload R10, los cuatro archivos de perfil
comprobados y el índice/selecciones del SDK, sin reinstalar Java/C++/Python.
La respuesta real de GitHub permite al actualizador R10 seleccionar R11 con
el SHA correcto. No se repite la descarga al comprobar el descubrimiento.
Después se añade únicamente `ai.voiceDirectory` para conectar la voz solicitada; las demás preferencias conservan sus valores. No se copian referencias ni se carga el modelo al configurar. Los recibos completos están en `tests/visual/evidence/windows-r11-*.json`.


## Distribución verificada de R12

El build procede de `dc61080b115167c8c117ce07dbef5085820166d0` y está publicado en
[GitHub](https://github.com/Arizt00/Zenit/releases/tag/v0.5.3-preview.12).
Instalador: 113074837 bytes; portable:
70846820 bytes. Los cinco assets tienen SHA-256
confirmado por GitHub; no se sustituyen releases anteriores.

Se superan 15 comprobaciones del paquete nativo y 12 del helper instalado.
Los 101 archivos de frontend/assets/bridges coinciden byte por byte con el
build. La comprobación instalada usa un Vira real en perfil QA aislado:
contraste, 20 variantes, y evento ColorThemeKind recibido por una extensión
Node real. Además verifica render/pausa, Laboratory, Debug y recuperación
de archivos. El consentimiento de IA sigue desactivado al iniciar.

`app-0.5.3-R12` conserva el payload R11, los cuatro archivos de perfil
comprobados y el índice/selecciones del SDK, sin reinstalar Java/C++/Python.
La respuesta real de GitHub permite al actualizador R11 seleccionar R12 con
el SHA correcto. No se repite la descarga al comprobar el descubrimiento.
Después se añade únicamente `ai.voiceDirectory` para conectar la voz solicitada; las demás preferencias conservan sus valores. No se copian referencias ni se carga el modelo al configurar. Los recibos completos están en `tests/visual/evidence/windows-r12-*.json`.
