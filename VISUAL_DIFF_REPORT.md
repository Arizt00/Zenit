# Comparación visual · 0.5.4 R1

Se conserva cada referencia original. La portada a pantalla completa y las
mejoras de actividad/ajustes/debug siguen las instrucciones posteriores del
usuario. No se mide esta evolución como una copia de una composición antigua.

## Ciclo realizado

Auditar contratos y CSS → implementar → ejecutar el producto → capturar → revisar
→ corregir → volver a capturar. Se detectaron el campo de búsqueda con dos bordes
y los grupos de Apariencia cuadrados; se corrigieron sus selectores sin recrear
la ventana. La prueba de inserciones tardías cubre el menú de Monaco dentro de
su ShadowRoot. La captura nativa se hizo con WebView2 y ANGLE/Intel; las pruebas
de contexto perdido usan Edge/SwiftShader.

## Resultados y límites

Hay 13 vistas nativas, más capturas de Material, selector, actividad, cuenta,
temas, terminales y Markdown. Se validan 24 casos de viewport/DPI emulado (72
capturas) sin overflow global. Los cinco pilares geométricos conservan la
tolerancia de 2 px. No se alteran `tests/visual/references` ni se deforman capturas
para mejorar una cifra. Las capturas privadas de los proyectos del usuario no
se añaden al repositorio.

Las comparaciones de evolución se guardan en `tests/visual/comparisons/054-r1`.
Actividad usa la última captura aportada por el usuario, con el perfil y archivos
QA; las otras vistas usan capturas QA de R13. MAE es error medio de canal en 0–255;
SSIM representa bloques de luminancia. Fechas, contenido y distribución pueden
variar; la nueva actividad es una evolución solicitada. Ninguna
métrica equivale a un porcentaje de acabado o de paridad.

| Vista | MAE | SSIM por bloques |
| --- | ---: | ---: |
| extensions | 6.377 | 0.6981 |
| activity | 2.795 | 0.8328 |
| debug | 1.554 | 0.9205 |
| welcome | 0.053 | 0.9985 |

Extensiones mantiene la identidad de la hoja y reduce su cabecera. Ajustes usa
el tema efectivo y un tamaño menor. Actividad elimina rutas dominantes y añade
filtro y agrupación. Debug conserva sus nodos y reorganiza el espacio vacío.
Inicio conserva el shader vivo y mejora el control principal; no se presenta
como un nuevo paisaje tridimensional. Existen diferencias de contenido, óptica,
iconos oficiales, tipografía y estados respecto a las referencias originales.
No se certifica todavía correspondencia visual perfecta.

Evidencia: `tests/visual/evidence/054-r1-tests.json`, `054-r1-icons-ui.json`,
`054-r1-geometry.json`, `054-r1-matrix.json` y `tests/visual/current`.
Los frame times están en IMPLEMENTATION_REPORT.md; no se declaran 60 FPS constantes.
