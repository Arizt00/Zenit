# Zénit 0.5.3 R7 · interfaz y Melody

R7 continúa desde `5e76eff`. La petición posterior del usuario simplifica
Laboratory y mejora el fondo del inicio; las referencias originales permanecen
intactas. Se conservan servicios reales, Monaco, PTY, Forge, Lantern, Assembly,
proveedores de IA y contratos de extensiones de R6.

## Qué cambió

| Área | Archivos | Resultado |
| --- | --- | --- |
| Laboratory | `web/src/foundation-ui.js`, `web/design/laboratory.css` | Cinco secciones accesibles, filtro de herramientas y detalles plegables. Los formularios permanecen montados al navegar y añadir SSH solo actualiza la lista. |
| Limpieza visual | `catalogue.css`, `design.css` | Retiradas 544 líneas de reglas del laboratorio anterior; un módulo propio usa la escala global de tokens. Se elimina el cambio de altura de la cabecera global al abrir Laboratory. |
| Terminal | `foundation-ui.js` | Maven, Gradle, Bash, Docker y máquinas usan la terminal integrada. Forge se abre mediante su entrada explícita. Las excepciones se muestran junto a la acción. |
| Datos de máquinas | `foundation-ui.js` | Núcleos y memoria se leen del perfil real. Un perfil inactivo no habilita Detener. Una consola ya adjunta se reutiliza. |
| Inicio | `studio.js`, `welcome.css`, `welcome-crystal-landscape.png` | Paisaje atmosférico propio, niebla y cristal con movimiento lento. Se conservan pantalla completa, dos acciones, perfil/recientes y esfera de Blender/Babylon/WebGL2. |
| Botones | `tokens.css` | Transición de presión, foco y sombras acotadas; brillo interior suave. Sin transition:all. |
| Melody | `melody-companion.js`, `melody.css`, `app.js` | Revisar, Explicar y Próximo paso usan el contexto real. La selección viaja al proveedor existente. Predicciones ligadas al cursor y revisión; peticiones duplicadas no generan trabajos simultáneos. |
| Distribución | `version.py`, `version.txt`, `setup.js`, `publish_native_release.py` | Revisión R7 reconocible por el actualizador; versiones nativas coherentes y publicación exige las 15 comprobaciones nativas vigentes. |

## Arquitectura y comportamiento

Laboratory monta una hoja y cinco tabpanels. La navegación modifica visibilidad,
aria-selected y tabIndex, sin rehacer formularios. ArrowLeft/Right y Home/End
navegan las pestañas. Los endpoints `/foundation`, `/languages` y `/machines`
siguen siendo la fuente de datos. Las rutas se identifican como base de Zénit,
ruta del sistema o no detectada: no se confunden con una ejecución satisfactoria.

Crear .venv usa el runner real; el resto de acciones abre una terminal PTY. Se
conservan el control de confianza, errores reales y estándares configurados. No
se sustituye el motor Docker por resultados de demostración.

El paisaje es un PNG local generado con la herramienta integrada image_gen.
El prompt completo y su procedencia están en `design/welcome-background.json`.
No contiene texto ni una esfera prerenderizada. La esfera conserva la malla de
dos paredes creada en Blender y el shader vivo de Babylon. El paisaje y la luz
usan transform/opacity; se pausan al ocultar la bienvenida, minimizar la ventana
o desactivar/reducir movimiento. La visibilidad usa un listener con limpieza.

Melody conserva consentimiento por sesión, proveedor/modelo y límite de 12
consultas, mínimo 20 segundos entre ellas, búfer máximo de 64.000 caracteres.
Los enfoques ajustan el prompt, la selección y los diagnósticos reales. No son
modelos nuevos entrenados ni una evaluación de calidad de IA externa.

Una predicción pendiente se cancela al mover el cursor; los consejos se invalidan
al cambiar contenido, proveedor, proyecto o enfoque. Un clic de predicción que
coincide con una revisión se encola una sola vez y conserva su cursor. Los
controles quedan encima de la respuesta para no moverse al recibir texto. Una
sugerencia válida de hasta ocho líneas entra en Monaco y requiere Tab; no guarda
el archivo. Los ejemplos de transporte de las pruebas están identificados como
fixtures, no como respuestas de un proveedor real.

## Tokens y rendimiento

Laboratory consume las escalas globales de espacio, radios, tipografía, colores,
superficies y motion de `tokens.css`. Iconos de acciones pertenecen a la familia
SVG local; las marcas de lenguajes usan assets locales. La página antigua y sus
reglas responsivas se retiran, en lugar de apilar una segunda implementación.

En WebView2, el inicio animado se midió durante unos tres segundos: cero tareas
largas, cero mutaciones DOM, cero eventos de layout y paint, un único bucle para
la esfera visible; CPU del render mediana 0,5 ms y p95 0,7 ms. El editor inactivo
durante dos segundos tuvo cero mutaciones, layouts, paints y recálculos de
estilos. Los datos están en `tests/visual/current/performance*.json`. Son muestras
locales sobre Intel/ANGLE, no una garantía de FPS o consumo en todos los equipos.

## Validación

- Python: 277 pruebas ejecutadas, 272 satisfactorias y 5 omitidas; cero fallos.
- JavaScript: 66 pruebas satisfactorias, incluidas 13 de intención/sesión de
  Melody; 53 archivos pasan comprobación de sintaxis.
- Laboratory: nueve comprobaciones, con SDK real, terminal Maven, persistencia
  C99/SSH, filtro/teclado, tres resoluciones y tres temas, simulación ASM y
  resultados invalidados al editar sin modificar el archivo en disco.
- UI: quince comprobaciones de pantalla completa, perfil, pausas de animación,
  recuperación WebGL, pestañas persistentes, terminal sin Forge, tres separadores,
  composer visible, selección enviada y aceptación explícita de código en Monaco.
- Capturas WebView2 de las trece vistas principales. 72 capturas adicionales de
  Editor/Melody/Welcome cubren 24 combinaciones: seis resoluciones de 1280×720 a
  3840×2160 y escalas 100/125/150/200 %, mediante emulación de dispositivo de Edge.
  Cero overflow global y errores JS; no se presenta como un cambio de DPI físico.
- Los cinco bounds principales de Editor/Welcome pasan con tolerancia de 2 px;
  desviación máxima 1,333 px. Overlays/diffs de siete vistas se conservan para
  revisión, sin convertir MAE/SSIM en un porcentaje de fidelidad.

Evidencias específicas: `tests/visual/evidence/r7-*.json`,
`tests/visual/current`, `tests/visual/responsive/r7-*` y
`tests/visual/comparisons`. Laboratory tiene una composición nueva solicitada
por el usuario; su golden original no se modifica para reducir el diff.

## Límites

No se añaden nuevas APIs de VS Code en esta revisión. La compatibilidad sigue
siendo parcial y no existe una medición suficiente para declarar 90 % global.
Los siete paquetes activados en la auditoría anterior no garantizan todos sus
objetivos. Se conservan los límites de OAuth, CustomDocument, filesystem virtual,
visualizadores y broker de modelos descritos en KNOWN_LIMITATIONS.md.

El paisaje es raster con movimiento de composición, no un terreno 3D simulado.
La esfera no certifica exactitud óptica perfecta. Linux/macOS requieren su propia
construcción y verificación; esta máquina Windows no certifica nuevos binarios
de esas plataformas.


## Entrega Windows verificada

Producto construido desde `86ff19abb7b488d0f43b7fc3eec764f7c72fc993`. El `.exe`
y el portable R7 se publicaron en GitHub con manifiesto, SHA-256 y quince
comprobaciones del paquete nativo. GitHub devolvió digests idénticos a los locales.

La instalación creó `app-0.5.3-R7`, mantuvo la carpeta de R6 y no interrumpió su
proceso abierto. Cuatro archivos de perfil, índice de extensiones e índice/selecciones
Java/C++/Python del SDK permanecieron iguales. El SDK compartido se reutilizó.
Se comprobaron 86 archivos entre fuente, bundle y copia instalada. Cinco pruebas
adicionales abrieron la UI instalada con perfil desechable: assets idénticos,
esfera viva WebGL2, ayuda desactivada sin consultas IA, pausa al entrar al editor
y cinco secciones reales de Laboratory con una sola visible.

El selector de actualizaciones de R6, aplicado a la respuesta real de GitHub,
detectó R7 y su hash correcto. No se repitió la descarga de 113 MB ni se modificaron
los ajustes del usuario. Los recibos están en `tests/visual/evidence/windows-r7-*.json`.
Windows es la plataforma construida/publicada para R7 en esta entrega.
