# Zénit 0.5.3 Preview R9

Los temas de extensiones conservan controles legibles. Un borde de foco
transparente ya no se convierte en el color de los iconos; las selecciones,
campos, botones y cabecera usan pares de fondo/texto de su propia superficie.
Desactivar un tema restaura Día, Noche o Bosque sin dejar colores residuales.

Cada paquete presenta un único botón **Elegir tema**, con muestras de color,
búsqueda de variantes, selección por teclado y marca del tema aplicado.
Bearded Theme expone sus 64 variantes. Las tarjetas ya no se ensanchan al
mostrar veinte o más botones. Los avisos de cambio de tema se actualizan en
una sola notificación.

Los cambios se transmiten a las ventanas desacopladas. Ajustes conserva los
campos y el foco; solamente el tema efectivo aparece seleccionado. La
bienvenida adapta paisaje y botones a Noche/Bosque, manteniendo el canvas
Blender/Babylon/WebGL2 y deteniendo el render cuando se oculta.

Melody ofrece enlaces a las líneas mencionadas en sus consejos. Están ligados
al archivo y revisión que recibió el proveedor; un cambio retira las marcas
anteriores. Consultar sigue sin modificar el búfer. Las predicciones requieren
aceptación y los planes de archivos/proyectos conservan revisión y recuperación.

La integración de extensiones añade `ColorThemeKind`, `activeColorTheme` y
`onDidChangeActiveColorTheme` con estados y eventos reales. Distingue claro,
oscuro y las dos variantes de alto contraste declaradas por el paquete. Si el
tema no se puede cargar o sus contribuciones están desactivadas, informa del
tema de Zénit efectivo. No se calcula el tipo a partir del nombre comercial.

Validación de esta revisión:

- 288 pruebas Python: 283 correctas, 5 omisiones explícitas.
- 75 pruebas Node y 57 archivos JavaScript comprobados.
- 89 variantes reales: 20 Vira, 5 One Dark Pro y 64 Bearded Theme.
- 9 comprobaciones UI de temas; 12 de depuración/canales reales; 7 de
  archivos, Proyecto desacoplado y tres CMD/ConPTY; 19 de inicio/Melody/interfaz.
- 13 vistas de WebView2 nativo y 72 capturas en 24 combinaciones de
  resolución/escala; sin overflow global ni errores JS en los recorridos probados.

Las pruebas de consejos/proyectos usan un transporte de IA determinista
identificado. No miden la calidad de un modelo externo. Los colores de las
muestras provienen de la paleta resuelta; el editor conserva el tema original.

La compatibilidad global con VS Code sigue siendo parcial. OAuth integrado,
documentos binarios, filesystem virtual en todos los editores, visualizadores
y forwarding de puertos mantienen sus límites. No se acredita 90 % de toda
la API ni que cualquier extensión funcione.

Windows se entrega como instalador `.exe` y portable con manifiesto/SHA-256.
Esta revisión no reconstruye Linux/macOS ni añade firma/notarización.
Consulta [implementación](../IMPLEMENTATION_REPORT.md),
[comparación visual](../VISUAL_DIFF_REPORT.md) y [límites](../KNOWN_LIMITATIONS.md).

La distribución Windows publicada supera 15 comprobaciones nativas y 10 del runtime instalado; 94 archivos coinciden con el build. El perfil y los SDK existentes se conservan.
