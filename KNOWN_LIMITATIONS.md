# Límites reales · Zénit 0.5.3 R6

1. **Paridad VS Code:** sigue siendo parcial. La activación real de siete de ocho
   paquetes probados no mide cobertura global ni garantiza todos sus comandos.
   No existe todavía una matriz suficiente para declarar 90 % de toda su API.
2. **Autenticación:** se admiten proveedores aportados por extensiones; faltan
   los brokers OAuth integrados de GitHub/Microsoft y persistencia completa de
   grants. GitHub Pull Requests permanece bloqueado sin su proveedor conectado.
3. **Virtual filesystem:** se despachan operaciones reales de proveedores. Falta
   integración completa de modelos, guardado, WorkspaceEdit y ventanas auxiliares
   para todos los esquemas virtuales. Un URI virtual no se convierte en una ruta local.
4. **Custom editors:** CustomTextEditor usa un documento real y webview. Documentos
   binarios CustomDocument con save/undo/backup completos no están implementados.
5. **Debug/puertos:** existen registros y dispatch de visualizadores y atributos
   de puertos. No hay UI automática completa de árboles de visualización, todos
   los when clauses ni transporte universal de forwarding de puertos.
6. **Eventos de archivos:** willCreate/Rename/Delete aplica al host iniciador de
   WorkspaceEdit. No se difunde todavía a cada host para todas las operaciones de
   UI, terminal o disco. El contrato no se anuncia como equivalencia global.
7. **Entorno/output/status:** faltan applyAtShellIntegration, todos los selectores
   glob, selector completo de canales y control UI de LogLevel. Mutaciones de
   entorno se aplican al crear nuevos procesos, no a shells que ya estaban abiertas.
8. **Language model API:** se registran e invocan herramientas explícitas. No hay
   broker universal de modelos de extensiones ni acceso automático a credenciales
   de Melody. Ninguna herramienta inventa tokens, modelos o resultados.
9. **Melody:** la calidad de consejos/predicciones depende del proveedor conectado.
   La nueva ayuda es opcional, hasta 12 consultas por sesión/3 por minuto, máximo
   64.000 caracteres por búfer. Las sugerencias mayores de ocho líneas no se
   presentan como inline completion. El transporte UI se verificó con una fixture;
   no es un benchmark de IA externa. No se certifican predicciones correctas.
10. **Cristal/fidelidad:** la geometría viene de Blender y el material se anima
    en Babylon/WebGL2; no es Cycles ni una simulación óptica físicamente exacta.
    Los campos de luz, facetas de montañas e iconos tienen diferencias descritas
    en VISUAL_DIFF_REPORT. La bienvenida de dos columnas fue sustituida por el
    brief posterior del usuario, conservando sus ocho goldens originales intactos.
11. **Rendimiento:** las mediciones son muestras locales de CPU del renderer. No
    se midió tiempo GPU ni se garantiza la misma tasa en cada equipo/monitor.
    Recuperación de contexto y reducir movimiento se comprobaron en Edge con
    SwiftShader; la captura nativa comprobó WebGL2 con Intel/ANGLE. No cubre toda
    combinación de GPU, controlador o backend. No se afirma animación perfecta.
12. **Responsive:** 24 combinaciones de resolución/escala emulada. La captura
    WebView2 usa el host al 150 % y un viewport CDP. Faltan pruebas físicas de
    todos los DPI en varios monitores y de la misma UI en Linux/macOS.
13. **Toolchains/VM:** detección de ruta no certifica cada herramienta. Docker CLI
    necesita un daemon; no se distribuyen todas las dependencias ni compiladores
    históricos. El adaptador ASM no publica todos los flags. Los límites previos
    de imágenes macOS/Windows 7, licencias y virtualización permanecen.
14. **Arranque/captura nativos:** ya se habían observado timeouts antes del
    bootstrap de ventanas web. En esta fase una captura CDP de bienvenida también
    agotó el tiempo al compartir carga con otras pruebas; recorridos posteriores
    secuenciales completaron. La causa no está demostrada y no se considera cerrada
    solo porque las repeticiones pasan. Se conserva instrumentación de recursos.
15. **Distribución:** esta entrega prepara Windows desde el código actual. No
    reconstruye aquí Linux/macOS ni firma/notariza esos paquetes. Los binarios
    públicos anteriores de GitHub no se sobrescriben ni se etiquetan como nuevos.
    El nuevo Windows se publica como asset alternativo UI-10ca227 dentro de R6,
    con su propio manifiesto, verificación y SHA-256. Como conserva la revisión,
    no se ofrece como actualización de versión automática: su instalación es manual.

Los estados de compatibilidad parcial siguen visibles. Las pruebas no sustituyen
datos del usuario por salidas, diagnósticos, versiones o respuestas de IA inventados.
