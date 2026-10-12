# Límites reales · reconstrucción visual de Zénit

1. **Fidelidad visual:** los siete bounds principales de Welcome/Editor cumplen
   la tolerancia de 2 px, pero no se verifica esa tolerancia para cada detalle.
   Las caústicas, refracción, iluminación y facetas 3D no coinciden exactamente
   con las imágenes. La ilustración de Laboratory y algunos iconos locales
   tampoco son los mismos assets de la referencia. Las diferencias por pantalla
   están en `VISUAL_DIFF_REPORT.md`; no se declara igualdad total por parecido.
2. **Datos reales:** fechas de recientes, rutas, orden del árbol, Git, modelos,
   versiones, diagnósticos, terminales y compatibilidad pueden diferir del golden.
   Las pruebas abren archivos reales de un proyecto temporal, compilan Java y
   ejecutan ASM. No copian salidas de las referencias para hacer coincidir pixels.
3. **Golden masters:** hay ocho referencias originales. ASM, paleta, Melody
   aislada y Proyecto flotante se verifican como regresiones; no tienen una
   referencia independiente que permita certificar comparación directa.
4. **Rendimiento:** la ausencia de mutaciones/layout/paint en reposo se midió
   durante dos segundos con movimiento desactivado. No prueba todos los equipos
   ni todos los estados. Se mide CPU del renderer; el tiempo GPU no se mide.
   Las muestras de rAF no certifican FPS de pantalla. La GPU puede caer al
   fallback CSS si WebGL no está disponible. La recuperación tras pérdida de
   contexto no se ha forzado en este recorrido.
5. **Responsive:** 24 combinaciones pasan en emulación de escala de Edge. La
   captura nativa utiliza Windows/WebView2 al 150 % con viewport cliente fijado
   por CDP. No representa una prueba física de cuatro DPI en cada sistema,
   monitor o combinación de GPU. El overflow interno con scroll sigue permitido.
6. **VS Code:** continúa siendo una implementación parcial. No se garantiza
   cualquier plugin, webview, gestor de tareas, API de terminal, depurador,
   WorkspaceEdit o semántica de insignias de VS Code. La ampliación funcional
   se pausó durante esta corrección visual. Los estados parciales siguen visibles.
7. **Toolchains:** detectar una ruta no equivale a certificar todas sus funciones.
   Docker CLI no aporta por sí solo un motor de contenedores. El adaptador ASM
   actual no publica flags, aunque sí registros, instrucciones y memoria reales.
   Tampoco se distribuyen «todas las dependencias posibles» de Python/Java ni
   todas las versiones históricas de compiladores.
8. **Máquinas y sistemas:** las limitaciones anteriores de imágenes de macOS,
   Windows 7, firma/notarización y distribución macOS permanecen. Esta fase no
   descargó nuevas imágenes ni añadió capacidades de virtualización.
9. **Texto y temas:** las comparaciones se realizan con fuentes del equipo de
   pruebas. Antialiasing y preferencias explícitas de fuente/interlineado pueden
   cambiar el resultado. Se verificaron pares concretos de contraste de los
   tres temas base, no todos los contenidos de webviews ni todas las extensiones.
10. **Forge:** se comparó el panel flotante del producto con el cuerpo de la
    ventana de referencia. Hay además captura del modo desacoplado real. Los
    controles de acoplamiento y la decoración del sistema operativo tienen
    diferencias; no se dibujaron botones de ventana falsos para ocultarlas.

Los paquetes públicos R6 previos no se consideran automáticamente reconstruidos
por este cambio de código. Los resultados de empaquetado/instalación, cuando se
ejecuten, se registran por separado con su procedencia.
