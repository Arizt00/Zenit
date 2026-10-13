# Paridad comprobada · Zénit 0.5.4 R4

R4 amplía flujos concretos, sin atribuir un porcentaje global de API VS Code.

| Área | Comprobación real | Límite |
|---|---|---|
| Ventanas | Editor a tamaño completo; terminal inferior, arrastre/teclado, desacoplar y reintegrar | La distribución del IDE y del editor exterior tiene estructura distinta |
| Sincronización | Búferes, guardado, tema, fuente, perfil, árbol y salida de tareas en ambos sentidos | Las ediciones concurrentes incompatibles se conservan y requieren resolver el conflicto |
| Terminal | Teclado CMD/ConPTY entre principal, editor, terminal separado y Forge; sesión persiste al cerrar una vista | No equivale a toda la integración de shells de VS Code |
| Forge | Entorno del archivo, preparación/compilación y ejecución PTY; Java real con System.console() y entrada | Depende de las herramientas instaladas/configuradas; Python y C/GDB mantienen sus acciones específicas |
| Búsqueda | Casos/palabras, glob de inclusión/exclusión, carpeta/tipo, línea y columna UTF-16, teclado | Texto literal, hasta 200 resultados visibles; no añade expresiones regulares ni reemplazo masivo |
| Melody | Plan de sesión con recuperación y comparación Monaco; preguntas directas y subjuntivo | Planes con límites de R3; las pruebas de generación usan transporte controlado |
| Temas/iconos | Regresiones sobre variantes reales y Material; sincronización entre ventanas | Product Icon Themes y compatibilidad universal aún pendientes |

La voz Qwen de Emma, consejos y predicciones existentes se conservan. No se
entrena otro modelo ni se certifica la calidad de sus respuestas. Los ámbitos
completos de configuración, OAuth integrado y CustomDocument binario continúan
pendientes. Véase [KNOWN_LIMITATIONS](../KNOWN_LIMITATIONS.md).
