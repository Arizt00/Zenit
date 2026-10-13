# Zénit 0.5.4 · Preview R3

Tu perfil reutiliza la foto real del avatar como fondo ampliado, difuminado y
desvanecido. La portada sigue el recorte durante zoom y arrastre, y desaparece al
quitar la imagen. Guardar mantiene el WebP local; cancelar conserva el perfil.
La hoja tiene materiales y controles coherentes con Mi actividad, cuya identidad
centrada, tipografía y distribución aceptadas se conservan.

Inicio mantiene el paisaje y cristal Blender/Babylon de la referencia. Añade
estrellas sutiles y mejores estados de foco y botones; movimiento reducido,
preferencia de animaciones y ocultación pausan los efectos.

Melody reconoce órdenes como «Modifica main.py», «Borra prueba.asm» y «Crea un
proyecto». Recibe el contenido actual de los archivos nombrados, incluido el texto
sin guardar y los archivos externos abiertos en la sesión. La orden captura sus
revisiones antes de generar la respuesta. Una edición posterior impide aplicarla.
En modo directo la orden explícita se aplica con recuperación y deshacer, sin
otra confirmación rutinaria. El modo de revisión sigue disponible.

Deshacer restaura el contenido original del disco y el búfer previo sin guardar.
Se preservan BOM y CRLF en actualizaciones. El borrado explícito también admite
binarios con copia exacta; no borra directorios ni ejecuta comandos del modelo.
Crear un proyecto sigue limitado a 60 archivos y 400000 bytes de texto. Cada
archivo borrado admite hasta 32 MiB, con hasta 64 MiB de recuperación por lote.
La IA no recibe contenido de credenciales; .git y .lumen quedan fuera del plan.

Temas, iconos Material, terminales independientes, ayuda en tiempo real y voz Qwen
de Emma se han comprobado como regresiones. Las pruebas de generación de planes
usan una respuesta controlada y no acreditan la calidad de un proveedor real.

[Implementación](../IMPLEMENTATION_REPORT.md), [evidencia visual](../VISUAL_DIFF_REPORT.md),
[paridad](VSCODE_PARITY_054_R3.md) y [límites](../KNOWN_LIMITATIONS.md) documentan el
alcance. Preview Windows sin firma; no se anuncia 90 % global de compatibilidad.
