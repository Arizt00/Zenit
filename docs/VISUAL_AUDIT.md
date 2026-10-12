# Auditoría previa · reconstrucción visual de Zénit

Base examinada: `2d1bffa`, 377 archivos versionados y 208 archivos de código,
estilos, HTML y construcción. Se recorrieron los módulos frontend/backend,
runtime nativo C/C++/ASM, PyInstaller, instalador/desinstalador, assets, pruebas
y persistencia. No se modificó el producto antes de capturar la base.

La interfaz real se ejecutó con Monaco y API Python en Edge y en WebView2 nativo.
El recorrido aislado usa archivos de código generados para pruebas; no simula
resultados de IA, hardware, compiladores o extensiones. Las referencias se
conservan con sus dimensiones y SHA-256 en el artefacto de auditoría.

| Referencia | Componente real | Diferencia previa | Responsables | Intervención |
| --- | --- | --- | --- | --- |
| 1 · Editor/Melody | Monaco, DockManager, terminal, proveedores | Explorador demasiado ancho; pestañas agrupadas incluso con dos archivos; barra extra; controles dispersos; esfera/bienvenida pequeñas | app, editor, preview, studio, docking | Geometría compartida, overflow menus, pestañas planas por defecto, Melody estable |
| 2 · Inicio | Studio, perfil y recientes reales | Una sola hoja exterior; hero más bajo; esfera sin contraste; botones pequeños | studio, glass, lenon | Dos hojas y proporciones de referencia; escena visible con pausa fuera de pantalla |
| 3 · Buscar | API search y resultados reales | Encabezado y filtros incompletos; estado vacío se elimina al borrar | studio, workspace/server | Filtros reales, relevancia y estado vacío persistente |
| 4 · Ajustes | Preferences/schema y hoja modal | Cada categoría elimina contenido/navegación y foco; aplicar una preferencia repinta toda la aplicación | workbench, controls | Hoja y categorías conservadas, actualizaciones por dominio |
| 5 · Forge | DesktopWorkflows, PTY y procesos reales | Varias capas de estilos; acciones sin jerarquía común | desktop-workflows, workbench | Ventana, terminal y acciones del mismo sistema |
| 6 · Laboratory | Foundation y máquinas | Hero y tarjetas genéricos; «incluido» solamente por existencia del archivo | foundation-ui, foundation | Detección ejecutable verificable; tarjetas e iconos locales |
| 7 · Debug | Debugger/DAP y Lantern | Controles densos, salida de Lantern excesiva | studio, lantern, debugger | Bloques de referencia y monitor compacto; controles reales |
| 8 · Extensiones | Open VSX/VSIX y hosts | Hero, acciones y estados demasiado grandes | workbench, extension-installer | Catálogo refinado y menú de gestión, conservando compatibilidad parcial |
| Sin imagen propia · ASM/Proyecto flotante/paleta | Simulación, DockManager, palette | Necesitan coherencia con las ocho referencias | assembly-workbench, docking, app | Mismo sistema; se validan como regresiones, sin afirmar comparación directa inexistente |

La base carga 14 CSS (278.257 bytes, 344 declaraciones `!important`). No se
encontró `transition: all` en esas hojas. Hay versiones sucesivas del mismo
selector y dos implementaciones del cristal, de las que solo glass.js está
conectada al producto actual. Los archivos históricos se conservan como fuentes
de migración y para superficies independientes; ya no se cargan en el IDE.
El parser elimina las reglas de los componentes sustituidos antes de generar
`web/design/support.css`. El producto utiliza `web/design.css` como único punto
de entrada, con tokens y propietarios separados por superficie.

Flicker medido: alternar Apariencia → General destruye `#settings-content` y
`.settings-navigation`. Guardar cualquier preferencia reaplica tema/Monaco,
terminales y Lantern. El estado del footer reconstruye HTML cada 500 ms;
Lantern reasigna texto/atributos en cada poll aunque su estado no cambie.
Los observers de selects recorren todos los campos ante cambios ajenos.

Los SDK y datos de usuario están fuera del frontend. Las pruebas usan un perfil
temporal; la instalación conservará preferencias, credenciales, proyectos y SDK.
El render WebGL se mide; no se presupone una tasa de 60 FPS.

## Medidas del perfil canónico

Área cliente: 1672 × 917. La barra nativa de 24 px se excluye únicamente al
comparar; no se estiran capturas para hacer coincidir el viewport.

| Región | x/y | Anchura/altura | Presentación |
| --- | --- | --- | --- |
| Proyecto | 90 / 71 | 263 / 800 | Cabecera 50, filas 34, radio 16, borde 1 |
| Editor | 363 / 71 | 867 / 578 | Tabs 49, breadcrumbs 32, Monaco 14/19 |
| Terminal | 363 / 657 | 867 / 214 | Cabecera 42, texto monoespaciado, tab con línea fina |
| Melody | 1241 / 71 | 417 / 800 | Título 22, cuerpo 14, esfera ≈144, acciones 58, compositor 104 |
| Inicio lateral | 18 / 73 | 405 / 824 | Avatar 156, saludo 44, botón 60, radio 20 |
| ZÉNIT / GLASS | 436 / 73 | 1218 / 478 | Display 64, cuerpo 20, lente ≈300, seis cristales |
| Recientes | 436 / 565 | 1218 / 332 | Título 18, filas 55, blanco, borde 1 |

`tests/visual/geometry.json` contiene los bounds del control automático.
`inspection.json` registra por pantalla bounds, padding, gap, tipografía,
radios, bordes, fondos, color, opacidad, blur y sombra del producto ejecutándose.
Las ocho referencias originales y sus hashes están en `tests/visual/goldens.json`.
El informe de diferencias separa medidas verificadas, materiales y datos reales.


## Corrección posterior desde a5c6601

La bienvenida de dos columnas queda como historial; el usuario la sustituyó por
una escena mínima y después pidió pantalla completa y perfil con un clic.
El target vigente se registra en tests/visual/welcome-brief.json. Se inspeccionaron
Studio/Docking/Glass/Preview y el host de extensiones antes de aplicar la corrección.

| Síntoma | Causa/contrato comprobado | Solución y prueba |
| --- | --- | --- |
| Terminal abre Forge | La preferencia hacker.enabled restaurada habilitaba el dashboard al entrar en la consola | Forge solo por acción explícita o ventana Forge; QA abre Terminal con la preferencia antigua activa |
| Separadores no reciben arrastre | overflow:hidden en dock-slot recortaba el handle situado fuera del panel | overflow visible en slot y recorte en dock-content; hit test y drag de tres handles |
| Pestañas cambian DOM al editar | innerHTML reconstruía los tabs en cada cambio de firma | Nodos por clave, cambio de estado y fade únicamente; QA conserva la identidad del botón |
| Esfera y bienvenida insuficientes | Card restringida y geometría solo procedural | Fullscreen; dos paredes creadas en Blender, shader y órbita en Babylon; hash y recuperación de contexto |
| Captura lavada | No se reprodujo su causa exacta en el perfil del usuario | Contraste reforzado, eliminación de saturación heredada y guardas de temas; no se afirma una causa probada |
| Prettier no encuentra vscode | Entrada ESM fuera del interceptor require CJS | Hooks ESM reales sobre Node 24; formato real de Prettier en proyecto aislado |
| Consejos durante escritura | Necesita grant, cancelación, versión y cuota independientes del stream de edición | CompanionSession, inline provider de Monaco y test de transporte explícitamente simulado |

Las métricas, capturas y diferencias vigentes están en los informes de la raíz.
