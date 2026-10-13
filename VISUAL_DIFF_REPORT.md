# Comparación visual · Zénit 0.5.4 R3

Tu perfil añade el mismo recurso fotográfico del avatar como portada ampliada,
difuminada y desvanecida, con recorte sincronizado y material claro/oscuro.
Mi actividad mantiene el diseño, centrado y tamaños aceptados. Inicio conserva
la referencia nocturna con estrellas discretas y estados de foco más visibles.

`tests/test_session_profile_ui.py` comprueba igualdad del canvas de portada con
el recorte real, zoom/arrastre, cancelación, WebP persistido y viewports de
1672×917, 1366×768, 800×600 y 640×360. Las imágenes de QA usan una foto geométrica
de prueba, identificada como fixture; no se publica la foto privada del usuario.
Las medidas de diferencia de R2 que siguen son históricas, no una nueva medición
de igualdad de píxeles para R3.

Inicio se ajusta a la referencia nocturna de 1672x941. Mi actividad sigue las
correcciones posteriores: cabecera de perfil, identidad centrada, ultimo archivo
y barra compacta de historial. Mantiene datos reales; las capturas son QA.

| Vista | MAE (0-255) | SSIM por bloques |
| --- | ---: | ---: |
| welcome | 5.032 | 0.9576 |
| activity | 10.873 | 0.6630 |

Las cifras no equivalen a un porcentaje de acabado. Overlays/diferencias en
tests/visual/comparisons/054-r2. Los ocho goldens iniciales permanecen intactos.

Hay 13 vistas nativas WebView2 a DPI Windows 150 %, con PNG fisicos
conservados y copias CSS de 1672x917. Se redimensiona el host real, sin emular
coordenadas de clic. Los cinco pilares geometricos pasan la tolerancia de 2 px.
La captura usa [CapturePreviewAsync](https://learn.microsoft.com/en-us/dotnet/api/microsoft.web.webview2.core.corewebview2.capturepreviewasync); se observaron timeouts CDP intermitentes, registrados en los limites.

La matriz de 24 casos/72 capturas emula resolucion/escala en Edge; no sustituye
pruebas fisicas en todos los monitores. La hoja de actividad se comprueba en
cuatro viewports, incluyendo 640x360, sin overflow global. Rueda/teclado siguen
funcionando con las barras ocultas. Avatar/fondo usan la misma imagen local.

En la muestra nativa de 3 s hubo 180 renders de la esfera, CPU mediana 0.5 ms y p95 0.7000000029802322 ms; no se midio tiempo GPU. Las superficies ocultas tienen cero bucles. No se garantiza una tasa universal ni animacion perfecta.
