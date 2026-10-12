# Zénit 0.5.3 Preview R10

Corrige el fallo por el que el editor volvía al tema original al dividirlo o
cambiar sus preferencias. La segunda vista de Monaco heredaba el nombre del
tema usado al arrancar, y lo aplicaba a todas las vistas. Ahora crear una
división o sincronizar sus opciones conserva el tema seleccionado, los modelos
y los cambios sin guardar. La regresión se reproduce antes del arreglo y se
verifica después con Bearded Theme Solarized Light.

El coloreado admite valores cortos y transparencia en comentarios y otras
reglas. La transparencia se compone sobre el fondo real del editor, en Monaco
y TextMate. Los estilos que no aportan un color también se conservan. Se
añaden reglas semánticas básicas de tipo/modificador y las bases de alto
contraste de Monaco. La terminal utiliza los 16 colores ANSI del tema cuando
están declarados, junto al cursor y la selección propios de la terminal.

Los temas pueden referenciar un archivo `.tmTheme` local en el paquete. Se
conservan reglas heredadas de color y semántica; los recursos fuera del paquete,
remotos o inválidos producen un error explícito. Esta capacidad no requiere
iniciar código de la extensión.

El selector distingue temas claros, oscuros y de alto contraste según su
declaración, muestra el número real de resultados y un estado vacío. Sus
muestras de sintaxis incluyen los comentarios con transparencia. El fondo
animado del inicio incorpora el acento del tema y conserva las reglas de pausa
y movimiento reducido.

Melody organiza las respuestas que traen Observación, Razón, Próximo paso y
Prueba sin inventar ni sustituir contenido. Las respuestas libres siguen
visibles como texto. **Insertar sugerencia** aplica una continuación vigente
al búfer actual, no la guarda y se deshace en un paso. Un cambio de revisión,
modelo o cursor retira la sugerencia anterior. Los proveedores y sus permisos
se conservan; no se anuncia una mejora medida de los modelos externos.

Validación: 290 pruebas Python (285 correctas y 5 omisiones), 80 Node,
58 comprobaciones sintácticas, 10 checks de temas con 89 variantes reales,
6 pasos de estabilidad del editor y prueba ANSI de xterm, 7 checks de
TextMate/ASM, 21 de inicio/Melody, 12 de Debug/output y 7 de
archivos/panel/terminal. Se incluyen 13 vistas nativas y 72 capturas en
24 combinaciones emuladas de resolución/escala.

La compatibilidad global de VS Code sigue siendo parcial. Las reglas semánticas
de lenguaje, comodines/modificadores complejos, todos los scopes en el
tokenizador lexical de Monaco y los demás límites de R9 siguen pendientes.
No se acredita 90 % global ni ausencia universal de flicker.

Windows se prepara como instalador `.exe` y portable con manifiesto/SHA-256.
No se reconstruyen aquí Linux/macOS ni se añade firma/notarización.
Consulta [implementación](../IMPLEMENTATION_REPORT.md),
[comparación visual](../VISUAL_DIFF_REPORT.md) y [límites](../KNOWN_LIMITATIONS.md).
