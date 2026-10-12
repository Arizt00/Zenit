# Zénit 0.5.3 R8 · depuración, ventanas, terminales y Melody

Esta revisión parte de `dab665d` (R7). Responde a la petición de simplificar
Depuración, mejorar inicio/Melody, continuar la compatibilidad de extensiones,
añadir proyectos/archivos a Melody y corregir Proyecto desacoplado y la entrada
al alternar terminales. Los servicios existentes y goldens originales se conservan.

## Cambios y arquitectura

| Área | Archivos principales | Resultado real |
| --- | --- | --- |
| Depuración | `debug-workspace.js`, `debug-workspace.css`, `studio.js`, `lantern.js` | Un inspector seleccionado; controles compactos; puntos de interrupción por archivo; input solo en estados compatibles. Reapertura mantiene el nodo. |
| Lantern | `lantern.js`, `debug.css` | Vista compacta en el inspector; conserva Live, Lens y adaptadores. Retirado el layout anterior y sus reglas muertas. |
| Proyecto fuera de Zénit | `desktop-workflows.js`, `shell.css`, `windows.css` | El contenedor nativo usa columna, cabecera arriba y árbol debajo. Acciones originales se trasladan a la cabecera. |
| Terminales | `app.js`, `workbench.js`, `product-ui.js` | Terminal vuelve a la PTY seleccionada; tareas usan consola explícita. Foco inmediato sin temporizador de 80 ms; ajuste de geometría en un frame con comprobación de sesión. Sesiones repetidas se distinguen por número. |
| Melody activo | `melody-companion.js`, `melody.css` | Oculta la bienvenida mientras hay ayuda, conserva nodos; consejo real en margen de Monaco, retirado al cambiar versión/modelo. Predicciones siguen requiriendo aceptación. |
| Melody archivos/proyectos | `melody_files.py`, `providers.py`, `platform_services.py`, `melody-files.js/css`, `ai-intent.js` | Plan JSON validado, revisión por ruta/contenido, batch a disco con recuperación, rollback y Deshacer. La petición sin archivo activo ya no se rechaza por comparar null con cadena vacía. |
| Inicio | `studio.js`, `welcome.css` | Escena proporcional a altura, paisaje con luz/composición CSS y profundidad por puntero limitada a ±4/±3 px. No hay un loop permanente para seguir el puntero. |
| Salida de extensiones | `extension_ui.cjs`, `extension_api.cjs`, `extension_host.cjs`, `extension_services.py`, `extension-output.js/css`, `extension-services.js` | Selector, texto real, clear/show/hide, copia, LogLevel y evento real. IDs independientes por bridge de dependencia. Off suprime los cinco métodos de log. |

Depuración usa `/platform/debug` y los motores existentes Python/Node/Java/DAP.
Su polling cesa al ocultarla y no reescribe elementos cuyo valor sigue igual.
Limpiar la salida borra el visor, no el transcript real del motor. Un error de
puntos de interrupción permanece junto al formulario.

Melody archivos separa petición, propuesta y aplicación. El job está ligado a la
carpeta; revisión produce un ticket de diez minutos y hashes del contenido previo.
Aplicar comprueba todo el plan antes de escribir. Se conservan backups y manifiesto
en `.lumen/melody`, se crean las carpetas necesarias, y las escrituras usan temp
y reemplazo en el mismo directorio. Un fallo revierte las operaciones ya hechas.
Deshacer verifica hashes posteriores y búferes compartidos para no pisar trabajo
nuevo. Los eventos actualizan vistas limpias de otras ventanas; un búfer modificado
se conserva. No hay ejecución de instrucciones del modelo como código de shell.

Los planes son relativos al workspace y solo texto UTF-8. Se bloquean rutas
externas, symlinks/junctions, secretos, repositorio interno y dependencias. Crear
no sobrescribe. Borrar no acepta carpetas. El proveedor/modelo existente y sus
permisos siguen siendo los de Melody; no se añade un modelo ni nuevas credenciales.

## Diseño y revisión visual

Las superficies usan los tokens de `tokens.css`: escala de 2–64 px,
`radius-control/card/panel`, border, surface/editor, text/secondary y accent.
Nuevas hojas específicas sustituyen las antiguas reglas de Debug. La comparación
original de esa pantalla queda documentada como composición anterior, porque el
usuario pidió reducirla. Inicio/Editor conservan sus bounds principales.

Se incluyen capturas, overlays y diffs. La revisión nativa utiliza WebView2 real
a 150 % con viewport CDP 1672×917. La matriz emula seis resoluciones y cuatro
escalas; no se presenta como una prueba física de cada monitor/DPI. Las vistas
coincidentes y diferencias están en VISUAL_DIFF_REPORT, sin porcentaje inventado.

## Validación

- Python: 285 pruebas, 280 pasan y 5 se omiten por capacidades/dependencias.
- Node: 71 pruebas pasan; incluye cuatro contratos nuevos de OutputChannel.
- Debug/output: 12 comprobaciones con Python y extensión Node reales. Pausa,
  pasos y resultado 42; cero mutaciones en muestras inactiva/pausada sin cambios.
- Archivos/panel/terminal: 7 comprobaciones. Tres CMD ConPTY reciben teclado;
  alternar y pulsar Terminal mantiene entrada. Proyecto desacoplado corregido.
  Un plan crea tres archivos, borra uno solicitado y restaura todo al deshacer.
- Transacciones: ocho pruebas de recuperación, límites, permisos, stale hashes,
  búferes sin guardar, excepciones de escritura y cambios posteriores.
- Interfaz/companion: 17 comprobaciones, incluida pausa de render, contexto WebGL,
  marca de consejo, revisión de Monaco y aceptación de predicción.
- Prettier real: 13 pruebas de integración de extensiones pasan; se mantiene
  formato de búfer sin guardar y contrato ESM/CJS.
- Visual: 13 vistas nativas, cinco bounds principales dentro de 2 px y 72
  capturas de Editor/Melody/Inicio en 24 combinaciones sin overflow global/errores JS.

El transporte de IA de las pruebas UI es una fixture identificada. No acredita
que un proveedor externo genere proyectos correctos. Las terminales y archivos
de estas pruebas son reales en un workspace y perfil aislados.

## Rendimiento y límites

En la captura nativa, la bienvenida animada registra CPU de render WebGL mediana
0.4 ms y p95 0.6 ms. El intervalo observado de frames es 29.2 ms mediana y
54.1 ms p95; no son 60 FPS garantizados ni tiempo GPU. No se observan long tasks
en esa muestra. Las superficies ocultas no tienen loops de render activos.

No se certifica ausencia de flicker universal ni paridad 90 %. OAuth integrado,
filesystem virtual en todos los editores, documentos binarios, visualizadores,
forwarding de puertos y eventos globales siguen pendientes. Las nuevas capacidades
de salida cumplen los contratos probados, no toda la API de VS Code.

Distribución nativa, publicación e instalación se registran con sus recibos en
`tests/visual/evidence/windows-r8-*.json` una vez verificadas. Los límites de
paquetes, firma y plataformas están en KNOWN_LIMITATIONS.

## Distribución verificada de R8

El build procede de `91357f2a22a7ef0ebc52b72f2b97d172d85827ba` y está publicado
en [GitHub](https://github.com/Arizt00/Zenit/releases/tag/v0.5.3-preview.8).
Instalador Windows: 112964092 bytes; portable: 70750040 bytes. Los cinco assets
conservan el digest SHA-256 confirmado por GitHub, sin reemplazar releases anteriores.

El paquete supera 15 comprobaciones nativas. Instalado en `app-0.5.3-R8`, los
92 archivos de frontend/assets/bridges coinciden byte por byte con el source del
build. Siete comprobaciones del helper congelado validan render, pausa de escenas,
Laboratory, Debug y creación/borrado/recuperación de archivos reales. No hay
peticiones de IA al iniciar la ayuda desactivada.

La instalación conserva R7, los cuatro archivos de perfil comprobados y el índice
del SDK compartido, sin reinstalar Java/C++/Python. La ventana R7 del usuario
permanece abierta. El actualizador R7 selecciona R8 y el SHA correcto de la
respuesta real de GitHub; no se repite la descarga durante esta comprobación.
Estos resultados y sus límites están en `tests/visual/evidence/windows-r8-*.json`.
