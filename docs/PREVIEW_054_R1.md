# Zénit 0.5.4 R1

Los temas de iconos instalados ahora cambian archivos, carpetas y raíces, con
expansión, variantes, selección persistente y fuentes locales. Material se
comprueba directamente; no exige arrancar su host. workbench.iconTheme y el
comando selectIconTheme se conectan a la configuración y selector reales.

Mi actividad se reconstruye en dos columnas con perfil, Archivos/Proyectos, grupos temporales, estado real de búfer abierto y búsqueda por teclado.
Ajustes muestra el tema efectivo y conserva nodos/foco; Extensiones, Debug,
menús de Monaco y acceso a proveedores comparten controles más ligeros.

La confianza se recuerda por carpeta. Modo directo evita las confirmaciones
rutinarias de acciones solicitadas; revocar una carpeta sigue teniendo prioridad.
Se mantienen los conflictos, cambios sin guardar y planes revisables de Melody.
La voz nueva de Emma/Qwen y la ayuda en tiempo real permanecen conectadas.

Validación: 304 pruebas Python (299 pasan, 5 omisiones), 95 JavaScript,
63 checks de sintaxis, 13 vistas nativas, 24 casos/72 capturas de responsive,
89 variantes de tema y 94 checks UI. Hay PTY, debugger y servicios Node reales.
Los recorridos de IA usan fixtures explícitas; no se inventan resultados de modelos.

Paridad VS Code parcial, sin atribuir 90 %. Product Icon Themes, brokers OAuth,
custom editors binarios y cobertura universal de extensiones siguen pendientes.
No se garantiza 60 FPS ni se reconstruyen Linux/macOS.

Detalles: [implementación](../IMPLEMENTATION_REPORT.md),
[comparación](../VISUAL_DIFF_REPORT.md), [límites](../KNOWN_LIMITATIONS.md),
[matriz de paridad](VSCODE_PARITY_054_R1.md).

Distribución Windows verificada: 15 checks nativos y 15 del runtime instalado; 107 archivos coinciden con el build. El tema de color y los SDK se conservan; modo directo y Material quedan seleccionados por petición del usuario.
