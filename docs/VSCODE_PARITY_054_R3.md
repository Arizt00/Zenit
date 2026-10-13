# Paridad comprobada · 0.5.4 R3

La paridad se describe por comportamiento probado, sin un porcentaje global.

| Área | Comportamiento comprobado | Límite |
|---|---|---|
| Archivos de Melody | Crear un proyecto, editar por nombre, usar búferes sin guardar, aplicar y deshacer transacciones | Plan completo de texto; hasta 60 operaciones. La generación se prueba con transporte controlado |
| Contexto de sesión | Archivo nombrado distinto del activo y rutas externas de archivos abiertos | No acceso general a rutas externas no abiertas; credenciales sin texto adjunto |
| Historial y edición | Recuperación del disco y del búfer, rechazo de revisiones posteriores, BOM/CRLF | Deshacer por recibo en la sesión actual; copias locales persistentes |
| Terminal | Tres sesiones CMD/ConPTY, cambiar sesión y volver a Terminal conserva teclado y salida independiente | No equivalencia universal de shell integration |
| Temas | 89 variantes reales, selección, recarga y sincronización entre ventanas, Monaco conserva su modelo | No todas las extensiones o APIs de temas |
| Iconos | Material real, carpetas y archivos, persistencia y temas TTF | Product Icon Themes aún pendientes |
| Ayuda y voz | Consejos/predicciones por revisión del código y audio Emma que caduca al editar | No se entrenó otro modelo; reproducción del WAV Qwen real existente |

Los ámbitos completos de configuración, OAuth integrado, CustomDocument binario
y la compatibilidad universal de APIs continúan pendientes. Véase
[KNOWN_LIMITATIONS.md](../KNOWN_LIMITATIONS.md).
