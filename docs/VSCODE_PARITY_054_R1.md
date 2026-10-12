# Paridad verificada · 0.5.4 R1

No hay denominador medido de toda la API de VS Code; no se asigna un 90 %.
Esta matriz diferencia contratos conectados de áreas todavía parciales.

| Área | Evidencia actual | Pendiente relevante |
| --- | --- | --- |
| File Icon Themes | Material instalado, archivos/carpetas/raíces, variantes, font TTF real, selección/reload | Iconos por defecto de contribuciones de lenguaje, Product Icon Themes |
| Configuración | workbench.colorTheme/iconTheme global, lectura/inspect/update y eventos | Ámbitos de carpeta/workspace completos y sincronización de cuenta |
| Comandos UI | selectTheme/selectIconTheme/showCommands/quickOpen/openSettings, extensión Node → backend → renderer → acuse | Inventario global y argumentos de todos los comandos |
| Editor/lenguajes | Monaco/TextMate/semántica, split, completado/diagnósticos/ediciones reales, LSP | Compatibilidad universal con APIs y proveedores de todas las extensiones |
| Marketplace | Open VSX, VSIX, dependencias, activar/desactivar/reinstalar, hosts Node y estados reales | No se garantiza ejecución completa de cada paquete de VS Code |
| Terminales | ConPTY, varios CMD con teclado, shells/perfiles, salida/estado de extensiones | Todos los IME, programas TUI, shell integration y entorno en shells existentes |
| Debug | Python real paso/variables/stack; DAP/JDI según adaptador; niveles de logs reales | Visualizadores/puertos/when clauses y forwarding universales |
| Workspace | Búferes, guardado, conflictos, cambios de recursos y rollback; confianza duradera | Difusión universal de eventos a todos los hosts y esquemas virtuales |
| Custom editors/auth | CustomTextEditor/webview y proveedores de auth registrables | Documentos binarios con undo/backup completo; brokers GitHub/Microsoft integrados |
| Melody | Proveedores existentes, planes revisables, consejos vinculados a revisión y voz Emma nueva | Broker universal para Language Model API y benchmark externo de calidad |

Los temas de archivos siguen las [asociaciones documentadas por VS Code](https://code.visualstudio.com/api/extension-guides/file-icon-theme).
Las limitaciones de ámbitos, recursos y APIs permanecen visibles en la UI y en
KNOWN_LIMITATIONS.md. Una contribución declarativa no necesita activar un host;
instalar una extensión ejecutable no equivale a certificar todas sus funciones.
