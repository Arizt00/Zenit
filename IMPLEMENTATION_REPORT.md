# Reconstrucción visual de Zénit · 0.5.3 R6

Se reconstruyó la presentación del producto real sobre la revisión `2d1bffa`.
Monaco, xterm/ConPTY, los procesos de compilación, los proveedores de Melody,
Lantern, Open VSX/VSIX, los hosts de extensiones y los motores de depuración
siguen conectados a sus servicios originales. No se sustituyeron por pantallas
estáticas ni salidas inventadas. La ampliación funcional de paridad quedó pausada
por la instrucción de corrección visual.

## Arquitectura y archivos

- `web/index.html` carga un único punto de entrada: `web/design.css`.
- `web/design/tokens.css` centraliza espaciado, radios, superficies, texto,
  selección, estados, borde, sombras, cristal y duraciones.
- `shell.css`, `welcome.css`, `melody.css`, `pages.css`, `catalogue.css`,
  `debug.css`, `windows.css`, `workspaces.css` y `dialogs.css` poseen la
  presentación de sus componentes. Se formatearon para poder mantenerlos.
- `tools/migrate_visual_styles.py` analiza los catorce CSS históricos y elimina
  las reglas de las superficies sustituidas. Genera `support.css` para controles
  auxiliares y vistas avanzadas, con la procedencia registrada en `migration.json`.
  Esos catorce archivos ya no se cargan en el IDE; siguen disponibles para las
  superficies independientes y como fuentes de migración.
- `product-ui.js` reorganiza botones existentes y sus handlers en menús compactos.
  Añade el selector de sesiones reales de terminal, el acceso a proveedor/modelo
  de Melody y la barra contextual de breadcrumbs. Las acciones originales siguen
  accesibles. `app.js` instala y limpia este módulo.
- `studio.js`, `workbench.js` y `lantern.js` conservan nodos y limitan las
  actualizaciones a cambios de estado. Las categorías de Ajustes retienen sus
  campos, desplazamiento y foco; sus etiquetas no comparten IDs duplicados.
- `docking.js` conserva paneles al reparentarlos. Se corrigió la reapertura de
  Melody en el cajón de ventanas estrechas y la capa que interceptaba clics.
- `desktop-workflows.js` monta el editor y los estilos de trabajo desacoplados
  en el contenedor nativo visible, conservando sus modelos. El parser de CSS
  distingue un nombre de clase completo de prefijos como `workspace-profile-*`,
  para no eliminar por accidente los contratos de las herramientas de datos.
- `editor.js` mantiene Monaco, minimapa y edición dividida. El interlineado
  predeterminado pasa a 1,35 en `backend/preferences.py`: 14 px de letra y 19 px
  de línea. Las preferencias explícitas del usuario conservan su valor.
- `glass.js` mantiene escenas Babylon/WebGL2, lente refractiva con render target,
  Fresnel, doble reflejo de pared, iluminación pastel en movimiento, seis cristales
  facetados, órbita, luz ambiental y sombra óptica. Los canvases se conservan y
  las escenas ocultas pausan su bucle. CSS queda como fallback cuando falla WebGL.
- `controls.js`, `preview.js` y `monaco-overlays.js` evitan rescaneos completos
  del DOM ante mutaciones ajenas. La terminal ajusta tamaño solo si cambia.
- `foundation-ui.js` utiliza detección real y marcas locales de lenguajes. Los
  archivos de `assets/languages` incluyen procedencia y aviso de licencias.
  «Ruta local» identifica detección de un ejecutable; no promete que Docker tenga
  un daemon funcionando ni que cada SDK haya pasado una prueba completa.

## Sistema de diseño

La escala de espacio es 2, 4, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48 y 64 px.
Los radios principales son 10/14/16/20 px. Los bordes son de 1 px. El blanco
`#ffffff` se combina con fondo `#f8f9ff`, selección `#f0ebff`, acento `#6b43f5`,
texto `#10133c` y secundario `#6473a9`. El cristal usa alpha 0,88 sin aplicar
opacidad al texto. Las duraciones son 120/180/240 ms, sobre propiedades concretas.
No se añadió `transition: all`.

Las referencias definen la composición del perfil canónico de pruebas. La tabla
de `VISUAL_DIFF_REPORT.md` identifica cada imagen, captura y diferencia. Los
temas oscuro/bosque y los temas instalados conservan sus mapas reales. Las
comparaciones de contraste verifican pares especificados de texto y sintaxis;
no certifican accesibilidad completa de todas las extensiones o webviews.

## Validación

- Auditoría y capturas de la base antes de editar, en Edge y WebView2 real.
- Capturas sucesivas con revisión de overlays y diferencias, sin reemplazar los
  golden masters por resultados generados.
- Ocho referencias originales con SHA-256, 12 vistas de regresión y una captura
  adicional de Forge desacoplado en `tests/visual`.
- Siete regiones principales de Editor/Welcome verificadas con tolerancia de
  2 px. La mayor desviación nativa fue 1,333 px. Este control no representa una
  certificación de cada elemento ni de equivalencia de materiales.
- Matriz completa: seis resoluciones físicas, escalas 100/125/150/200 %, 24 casos,
  sin overflow horizontal global ni errores JavaScript. Se abrió Melody y se
  verificó que su compositor quedara dentro de la ventana. Son escalas emuladas
  de Edge; no se cambió la configuración de DPI de Windows 24 veces.
- 257 pruebas Python previas de la base funcional: 252 pasaron, cinco omitidas.
  Después del cambio del interlineado, 56 pruebas de plataforma: 54 pasaron,
  dos omitidas. Tres contratos nuevos protegen hashes, tamaños y UTF-8 de los
  golden tests. Cincuenta pruebas JavaScript y comprobaciones de sintaxis pasan.
- Recorridos R5/R6: siete y ocho comprobaciones respectivamente, con terminales,
  tres temas, temas instalados tras reiniciar, host de extensión real, guardado
  Unicode, errores Java, edición en vivo con permiso y conservación del archivo
  original. El transporte de IA de esa prueba se simula explícitamente; no se
  presenta como una respuesta de un modelo real.
- La captura del editor ejecuta Java realmente en ConPTY. El ejemplo x86-64
  ejecuta 36 instrucciones en CPU emulada y termina con RAX = `0x37` (55).

## Rendimiento y flicker

Se eliminó un fallo de animación: desactivarla dejando duración 0,01 ms mantenía
infinito el blink de xterm. Ahora se detiene. También se evitaron setters iguales,
reaplicación de tema sin cambios y reconstrucciones periódicas del footer.

En WebView2 nativo, dos segundos de reposo con movimiento desactivado produjeron
cero mutaciones, tareas largas, layouts, recálculos de estilo y paints. Con
movimiento activado, la escena visible sigue renderizando; la de Welcome oculta
tiene cero bucles. Las medidas de rAF y CPU del renderer están en los JSON de
rendimiento. No equivalen a FPS de monitor ni a tiempo GPU. No se afirma 60 FPS.
Es un muestreo acotado, no una garantía universal de ausencia de flicker.

## Reproducción

Instala `requirements-visual.txt` junto al entorno normal de desarrollo y usa:

```powershell
python tools/visual_capture.py --native --output build/visual
python tools/visual_compare.py --captures build/visual --output build/visual-diffs
python tools/visual_validate.py build/visual
python tools/visual_capture.py --matrix --all-views --output build/visual-matrix
python tools/visual_validate.py build/visual-matrix --matrix
python -m unittest tests.test_visual_contract -v
node --run check
node --test tests/*.mjs
```

El runner crea un proyecto y perfil temporales. `--installed-from` permite copiar
paquetes de una instalación para revisar el catálogo, sin claves ni autorizaciones
de ejecución. Las APIs de QA se inyectan únicamente en el runner; no se exponen
en la aplicación distribuida. Las capturas del repositorio documentan su contexto.

## Límites de la entrega

La composición principal está verificada; el material 3D, la escena decorativa
del laboratorio y algunos detalles de iconos/tipografía mantienen diferencias
con las imágenes. La comparación no constituye un certificado de igualdad
píxel a píxel. `KNOWN_LIMITATIONS.md` registra estas diferencias y los límites
funcionales conservados. La reconstrucción visual no certifica paridad total
con VS Code ni el funcionamiento de cualquier extensión descargada.
