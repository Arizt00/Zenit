# Zénit · corrección de interfaz y evolución · 0.5.3 R6

Esta entrega continúa desde `a5c6601` y aplica las instrucciones posteriores al
primer rediseño. La bienvenida anterior de dos columnas fue sustituida por la
composición mínima solicitada y después extendida a toda la ventana. Monaco,
terminales reales, Lantern, Laboratory, extensiones y proveedores de Melody
siguen conectados a los servicios del producto. No son capturas dentro de HTML.

## Cambios y arquitectura

| Área | Archivos principales | Resultado |
| --- | --- | --- |
| Inicio | `studio.js`, `welcome.css`, `welcome-mountains.svg` | Escena a pantalla completa, dos acciones reales, perfil detrás de un clic y fondo con luz lenta. |
| Perfil | `studio.js`, `dialogs.css` | Nombre/avatar y hasta 20 archivos recientes reales, ordenados por fecha; abre archivos de otras carpetas con control de cambios no guardados. |
| Proyecto nuevo | `backend/projects.py`, `server.py`, `app.js` | Crea y abre una carpeta vacía real, sin sobrescribir otro proyecto; valida rutas y nombres reservados. |
| Cristal | `tools/build_crystal.py`, `design/zenit-crystal.blend`, `glass.js`, `zenit-crystal.mesh.*` | Geometría de Blender, dos paredes, material óptico animado, órbita y carga verificada por SHA-256. |
| Terminal / Forge | `desktop-workflows.js`, `docking.js`, `shell.css` | Abrir Terminal no activa el dashboard de Forge por una preferencia antigua. Forge conserva su ventana y su integración explícita. |
| Redimensionado | `docking.js`, `shell.css` | El contenedor deja de recortar los separadores exteriores. Arrastrar izquierda, derecha e inferior modifica el tamaño real. |
| Pestañas | `app.js` | Actualización por clave: conserva botones al editar/activar archivos, mantiene foco y webview tabs, y anima nuevas pestañas solo con opacity. |
| Contraste | `tokens.css`, `extension-theme.js` | Texto secundario más legible, eliminación de saturación/blur heredados en paneles ordinarios y corrección de pares ilegibles de temas externos. |
| Melody | `melody-companion.js`, `workbench.js`, `melody.css`, `app.js` | Ayuda opcional sobre el búfer actual y predicción solicitada expresamente dentro de Monaco. |
| Extensiones | `extension_host.cjs`, `extension_api.cjs`, `extension_services.*`, módulos `extension_auth/environment/filesystem/language_tools/ports/ui.cjs` | Más contratos reales de VS Code, detallados abajo. |

### Blender, Babylon y WebGL2

Blender 5.0.1 genera una esfera de pared exterior y otra interior: 6.050 vértices
y 12.096 triángulos por pared, 24.192 triángulos en conjunto. Se conserva el
archivo `.blend` editable y el generador reproducible. Un formato binario pequeño
exporta posiciones, normales e índices; Babylon aplica esos datos mediante
VertexData. El navegador no necesita instalar Blender.

El material de ejecución es un ShaderMaterial propio: Fresnel, doble borde,
reflejos, desplazamiento cromático y lente con render target. Los campos pastel
se desplazan lentamente y la órbita cambia de inclinación sin deformar la esfera.
No se presenta como un render Cycles ni como una reproducción física exacta del
material Blender. El checksum, los rangos de índices, las normales y la separación
de las paredes tienen pruebas. CSS conserva un fallback identificable.

El motor limita su dibujo a 60 actualizaciones por segundo, conserva canvas y
contexto, detiene el bucle al ocultarse y respeta reducir movimiento. La prueba
fuerza una pérdida de contexto y comprueba su recuperación en el mismo canvas.
El fondo de inicio usa transform/opacity del compositor, no timers permanentes
ni cambios geométricos del layout. Se pausa también al ocultarse.

### Melody contigo

La acción «Ayuda en tiempo real», o la petición «Ayúdame en tiempo real mientras escribo», muestra el proveedor/modelo y autoriza una sesión
acotada: hasta 12 consultas, separadas por al menos 20 segundos. Solo se envía el
búfer activo de hasta 64.000 caracteres y diagnósticos actuales, mediante el mismo
AIRouter y las mismas credenciales/proveedores existentes. No se envía todo el
proyecto ni se crea una respuesta de demostración.

El cambio de carpeta, proveedor o modelo invalida la sesión. Editar durante una
respuesta la cancela; una respuesta que llega después de detenerse se descarta.
La consulta normal y la edición en vivo detienen la ayuda para evitar competencia.
Los consejos se muestran como propuestas: no escriben ni guardan archivos.

«Sugerir siguiente código» solicita hasta ocho líneas. Una respuesta compatible
se publica mediante un InlineCompletionsProvider real, ligada al modelo, revisión
y cursor. Tab la acepta con el mecanismo de Monaco y la edición queda en el
búfer con undo. La edición en vivo previa conserva su permiso por archivo,
control de conflictos y suspensión de autoguardado. Las pruebas de transporte de
esta nueva UI usan una fixture explícita: no evalúan la calidad de un modelo externo.

### Contratos de extensiones ampliados

- `import 'vscode'` en ESM utiliza los hooks síncronos de Node 24, junto con el
  require CJS existente. Comparten la identidad de API por extensión y dependencia.
- StatusBarItem, LanguageStatusItem, OutputChannel y LogOutputChannel publican
  estado y salida reales, con actualización, limpieza y disposición.
- environmentVariableCollection conserva mutaciones por extensión y ámbito;
  se aplican al entorno real al crear terminales, incluidas las terminales normales.
- Autenticación admite proveedores registrados por extensiones, cuentas,
  sesiones y consentimiento por consumidor. No inventa OAuth ni access tokens.
- CustomTextEditorProvider abre documentos en webviews reales; las operaciones
  de webview se serializan y esperan la creación del panel antes de continuar.
- FileSystemProvider despacha lecturas, escrituras, stat, directorios y recursos
  virtuales; readonly y operaciones entre proveedores fallan explícitamente.
- Varios proveedores de configuración de depuración se conservan por tipo. Hay
  registro y despacho de visualizadores de depuración y atributos de puertos.
- Herramientas aportadas por extensiones pueden registrarse e invocarse de forma
  explícita, con cancelación y sus mensajes de confirmación.
- onWillCreate/Rename/DeleteFiles del host iniciador puede aportar ediciones de
  texto a la misma transacción WorkspaceEdit. No se anuncia difusión global completa.

La auditoría de ocho paquetes instalados activa siete. Prettier 12.4.0 produce
una edición real de formato; Maven registra 38 comandos y seis proveedores;
Markdown Preview Enhanced, Pyrefly, Python Debugger, Container Tools y Material
Icon Theme también activan. GitHub Pull Requests queda bloqueado por el proveedor
GitHub no conectado. **Activación de 7/8 paquetes no significa 90 % de paridad con
VS Code**, ni certifica cada comando. La evidencia declara capabilityCertification=false.

## Diseño y validación

Se mantienen los tokens centralizados de espaciado, radios, estados, tipografía,
bordes y duraciones. Día usa blanco/lavanda con texto `#10133c`, secundario
`#53638e` y acento `#6b43f5`. Los iconos de controles pertenecen a la misma familia
SVG local; los logos de lenguajes/extensiones proceden de sus recursos reales.
No se introdujo transition:all ni opacidad sobre el texto.

- Suite Python completa: 275 pruebas ejecutadas, cinco omitidas por requisitos
  del entorno. Después se verificó además el contrato del nuevo asset Blender.
- JavaScript: 62 pruebas pasan, incluidas nueve de cancelación, revisión, cuota y
  permisos de la ayuda; ESM, formato de Prettier, filesystem y servicios tienen
  13 pruebas de integración nuevas dentro de la suite Python.
- Recorrido de corrección: 14 comprobaciones con inicio, perfil, pérdida de WebGL,
  reducir movimiento, pestañas conservadas, tres separadores, ayuda, aceptación
  de inline suggestion, proyecto nuevo y ausencia de errores JS. Transporte de
  IA simulado e identificado expresamente, no respuesta de un proveedor real.
- Recorridos R5/R6 previos: siete y ocho comprobaciones de tres temas, terminales,
  guardado Unicode, código en vivo con permiso y desinstalación sobre un destino
  desechable. Los resultados se conservan como ejecuciones separadas.
- Capturas de 13 vistas en WebView2 real al 150 % del host, viewport cliente
  1672×917 fijado por CDP. Referencias originales intactas; overlays y diffs de
  siete vistas. La bienvenida posterior se valida por su brief y geometría.
- Matriz de seis resoluciones y cuatro escalas emuladas: 24 casos y 72 capturas
  nuevas de Editor/Melody/Inicio. No representa 24 cambios físicos de DPI de Windows.

En una muestra nativa de tres segundos del inicio animado se recogieron 182
draws, CPU mediana 0,5 ms y p95 0,8 ms por frame del motor, sin long tasks ni
mutaciones DOM. Son medidas locales de CPU, no tiempo GPU ni una garantía de
60 FPS de pantalla. El perfil completo está en `tests/visual/current`.

## Entrega y límites

Los reports visuales, capturas, datos de rendimiento y contratos están incluidos
en el repositorio. La comprobación del instalador reconstruido y de la instalación
local se registra por separado en `tests/visual/evidence`. Los paquetes públicos
anteriores no se presentan como builds de estos cambios. Consulte
`KNOWN_LIMITATIONS.md` para capacidades parciales y distribución por plataforma.

`packaging/lumen.spec` incluye todos los módulos extension_*.cjs que Node carga
dinámicamente. El recorrido del paquete comprueba sus bytes contra el código,
la integridad de la geometría Blender y el módulo de creación de proyectos, junto
con los catorce contratos nativos anteriores (quince comprobaciones en total).


## Windows construido, instalado y publicado

Build de producto: `10ca2270c23ee8bccbe06e48529fa03c7b1dfc57`. El instalador
Windows y el portable se publicaron como assets alternativos `UI-10ca227` en la
release R6, con manifiesto, quince comprobaciones nativas y SHA-256. GitHub devolvió
digests iguales a los archivos locales. Los assets anteriores permanecen intactos.

La instalación local se actualizó y conservó una copia recuperable de su payload
anterior, cuatro archivos del perfil y las selecciones Java/C++/Python del SDK.
El frozen helper instalado detectó trece herramientas y ejecutó el ejemplo
x86-64 con 36 instrucciones: RAX/RBX = 55, RCX = 0 y RDX = 110. No se reconstruyó
ni rehasheó por completo el SDK compartido.

Se compararon 27 archivos entre fuente, bundle e instalación. Otra comprobación
abrió la UI instalada con perfil desechable: bienvenida a pantalla completa,
geometría Blender, WebGL2, material avanzando, límite configurado de 60 dibujos,
ayuda de Melody desactivada sin peticiones IA y pausa de la esfera al entrar al
editor. Son cuatro comprobaciones adicionales, sin modificar los datos del usuario.

Evidencia: `tests/visual/evidence/windows-crystal-*.json`. El build mantiene la
revisión R6: se instala manualmente y no se presenta como actualización de versión
automática. Linux/macOS no se reconstruyeron para esta corrección.
