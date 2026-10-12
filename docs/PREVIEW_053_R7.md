# Zénit 0.5.3 · Preview R7

R7 simplifica Laboratory, añade un paisaje propio al inicio y mejora la
coordinación de la ayuda de Melody. Conserva Monaco, terminales PTY, Lantern,
Assembly, Forge, proveedores de IA y capacidades reales de extensiones.

- Laboratory tiene cinco secciones: Lenguajes, Proyecto, Assembly, Contenedores
  y Máquinas. Los formularios permanecen montados al navegar; añadir una conexión
  SSH actualiza solo la lista de máquinas. Filtro y pestañas admiten teclado.
- Las herramientas muestran rutas detectadas y su procedencia. No se anuncia
  que un motor Docker funcione solamente porque exista su cliente.
- Las acciones habituales de Laboratory abren la terminal integrada. Forge
  conserva su entrada y ventana explícitas.
- La bienvenida ocupa toda la ventana. Un paisaje local de cristal, niebla y
  luz pastel acompaña la esfera viva de Blender/Babylon/WebGL2. Movimiento lento,
  pausa al ocultarse y compatibilidad con reducir movimiento.
- Los botones comparten presión suave, foco visible y luz interior discreta.
- Melody ofrece Revisar, Explicar y Próximo paso. Explicar utiliza la selección
  real; las predicciones pertenecen al cursor y revisión actuales. Cambiar de
  cursor durante la generación invalida una continuación antigua.
- Una petición explícita de predicción puede esperar a la revisión en curso;
  varios clics no crean generaciones simultáneas. Los controles se mantienen
  encima de la respuesta para evitar que se muevan al recibir texto.
- La ayuda sigue siendo opcional: hasta 12 consultas por sesión, mínimo 20
  segundos entre solicitudes, máximo 64.000 caracteres del búfer activo. Los
  consejos requieren revisión; una sugerencia de Monaco se acepta con Tab.

El instalador Windows y el portable se publican en la
[release R7](https://github.com/Arizt00/Zenit/releases/tag/v0.5.3-preview.7).
Los ejecutables de esta preview no están firmados. La revisión distinta permite
que R6 reconozca la actualización en GitHub si sus ajustes de actualización
están habilitados; la descarga conserva verificación SHA-256.

Esta entrega no certifica paridad completa ni un porcentaje global de cobertura
de VS Code. La calidad de los consejos depende del proveedor/modelo conectado.
Las verificaciones de la UI de IA emplean un transporte de prueba identificado;
no constituyen una evaluación de la inteligencia del modelo.

Linux y macOS no se presentan como reconstruidos localmente en Windows. Su
pipeline y sus verificaciones nativas siguen disponibles; los binarios de esta
entrega y su estado real se documentan en IMPLEMENTATION_REPORT.md.
