# Comparación visual · Zénit 0.5.3 R13

Se conserva la matriz histórica de referencia/componente y se añaden las últimas
capturas solicitadas, sin estirarlas ni convertir resultados en nuevos goldens.

| Captura señalada | Corrección real | Verificación |
| --- | --- | --- |
| Editor con menú grande | Menú DOM/Shadow DOM de 360×337 px en la prueba, filas ≤30 px, SVG temáticos | Captura y acciones reales de Monaco |
| Extensiones | Hero de menor altura, iconos y tarjeta más ligera, miniatura del tema instalado, VSIX visible | Catálogo, variante One Dark Pro Darker, inspector real |
| Consejos y conversación | Tablas, encabezados, listas, código y enlaces con jerarquía tipográfica | Texto QA delimitado, copia exacta, rechazo de HTML ejecutable |
| Perfil | Dos columnas; diálogo 680×452 px en 1672×917 | Zoom, crop WebP real, nombre y persistencia |
| Inicio oscuro | Color por tema, profundidad/iluminación y órbita refinada | Canvas de Blender/Babylon retenido; reduced-motion y pausa |

Las dos capturas QA que el usuario volvió a adjuntar se guardan en
`tests/visual/issue-references/r13`. Su comparación overlay/diff contra R13 está
en `tests/visual/comparisons/r13`; se pide evolución respecto a esas imágenes,
por lo que una diferencia menor no significa automáticamente mejor diseño.

Los siete overlays/diffs de las referencias originales están en
`tests/visual/comparisons`. La portada de la referencia inicial fue sustituida
por el encargo posterior de inicio minimalista a pantalla completa. Las imágenes
originales permanecen intactas. El catálogo y el perfil se compactan por la petición
posterior; no se presenta ese cambio de proporción como coincidencia píxel a píxel.

13 vistas nativas y 72 capturas de escala/resolución están verificadas. Sin errores
JS no controlados ni overflow global en estos recorridos; los cinco límites de
composición principales cumplen 2 px. Persisten diferencias de material, tipografía,
contenido de proyectos y datos reales. No se certifica fidelidad perfecta ni 90 %
de paridad VS Code. Consulta `KNOWN_LIMITATIONS.md`.

La muestra de animación nativa presenta intervalos de frame variables y no garantiza
60 FPS. Los datos medidos figuran en `IMPLEMENTATION_REPORT.md`.
