# Investigaciones verificables con Melody y Lantern

La investigación conserva por separado la evidencia registrada, la interpretación de Melody y los cambios propuestos. Prepararla no ejecuta órdenes ni modifica archivos. Una respuesta del modelo es una hipótesis hasta comprobarla.

## Recorrido de uso

1. Abre **Investigar resultado** desde las herramientas de Melody, un resultado terminado del explorador de pruebas o el detalle de una ejecución en **Actividad → Resultados y cambios**.
2. Revisa el resultado y su procedencia: prueba o ejecución, revisión de fuentes, descriptores de dependencias, compilador o intérprete, entorno y destino.
3. Lee las fuentes capturadas y selecciona cuáles podrá consultar Melody. La vista previa muestra la petición y el contexto que se enviarán al proveedor configurado. No se adjuntan la conversación anterior ni el archivo actual del editor como contexto adicional.
4. Cuando exista una prueba previa aprobada con la misma selección y una captura disponible, inspecciona las diferencias y reproduce esa revisión. Un resultado antiguo sin fuentes conservadas se identifica como tal; no se le atribuye la revisión actual.
5. Revisa las órdenes de Lantern, la entrada y el límite de tiempo antes de ejecutar. Se realizan dos ensayos secuenciales en copias desechables. El informe conserva las órdenes, códigos de salida, huellas, extractos y resultados individuales de pruebas.
6. Revisa la hipótesis y los fragmentos de la propuesta de Melody. Puedes excluir fragmentos, probar únicamente los seleccionados y después revisar su aplicación. Los fragmentos rechazados permanecen excluidos al volver de la reproducción.
7. Aplicar cambia los búferes mediante el sistema de ediciones revisadas; el guardado respeta tus preferencias habituales. **Restaurar conjunto revisado** utiliza el recibo de deshacer de esta investigación en la ventana actual. Se rechaza una aplicación o restauración que ya no coincida con las fuentes esperadas o cuyo recibo haya sido sustituido por otra operación.

La restauración del conjunto depende del recibo de edición de la ventana y no está disponible después de reiniciar. La investigación, sus fuentes y sus ensayos sí se conservan en el proyecto.

Los resultados distinguen expresamente las pruebas aprobadas de un fallo reproducido en dos ensayos. Un código cero con salida coincidente tampoco se presenta como una suite de aserciones aprobada. Si una propuesta nueva llega durante la reproducción, al terminar se añaden las observaciones al registro vigente sin sobrescribir esa propuesta.

## Qué demuestra la evidencia

Cada ejecución o prueba nueva conserva una captura anterior a su inicio. La cadena puede abrir fuentes, posiciones y nombres de pruebas que realmente se hayan registrado. No inventa una función causante, una instrucción de máquina, memoria o registros cuando el adaptador no aporta esa información.

Una diferencia respecto de una prueba anterior aprobada es una candidata a investigar. Dos ensayos coincidentes son observaciones repetidas; no demuestran causalidad ni determinismo general. Si el programa modifica sus fuentes durante el ensayo, no se encuentra un resultado de pruebas válido o la preparación no termina, el informe marca la reproducción como incompleta.

Se conservan las huellas de los ejecutables y de los adaptadores externos identificados en las órdenes. Los descriptores de dependencias se vinculan a la revisión. Las versiones efectivamente instaladas de todos los paquetes, bibliotecas dinámicas y servicios externos no se congelan. No se presenta esa información como verificada.

## Reproducción y límites

- La reproducción está implementada para el destino **local**. Se puede inspeccionar evidencia de otros destinos, pero no ejecutar una reproducción remota desde esta función.
- Las fuentes capturadas se restauran en una copia. Se comprueba que los datos, el entorno seleccionado, la configuración de herramientas y sus huellas siguen coincidiendo con lo revisado antes de iniciar procesos.
- La entrada interactiva anterior no se registra; debe introducirse de nuevo. Cada ensayo admite hasta 16 KiB de entrada y 60 segundos.
- Las copias tienen los permisos del usuario; no constituyen un sandbox del sistema operativo. Se revisan las órdenes antes de ejecutarlas.
- Se capturan hasta 400 fuentes, 128 kB por fuente y 8 MiB de texto total; también se registran huellas de hasta 2000 archivos de datos, con un presupuesto agregado de 32 MiB. Una captura que alcance sus límites no se ofrece como reproducción completa.
- Se excluyen `.git`, `.lumen`, archivos `.env*`, claves conocidas y los directorios omitidos por la preparación del proyecto. Hay que revisar las fuentes seleccionadas antes de enviarlas a un proveedor.
- Cada consulta admite de 1 a 8 fuentes, hasta 48000 caracteres de fuentes y 64000 de contexto total. El informe completo permanece local.
- Las propuestas se limitan a fuentes existentes de la captura, hasta 32 archivos, 128 kB de contenido final por archivo y 512 kB de texto original y propuesto en conjunto. El modelo no puede introducir órdenes ejecutables en la propuesta.
- Se conservan hasta 16 investigaciones y seis grupos de ensayos por investigación. Los resultados guardan extractos acotados y huellas completas de salida o comportamiento. Cada registro tiene un presupuesto de 4 MiB.
- Se retienen 24 capturas no referenciadas, además de las protegidas por las investigaciones conservadas y sus revisiones de referencia. Los registros residen en `.lumen/investigations/`; no contienen una copia de todo el entorno instalado.

## HILO como motor interno

HILO mantiene una cola breve para las acciones de archivos y una cola de mantenimiento para las tareas largas. Una investigación en segundo plano no ocupa la vía de mover o deshacer archivos. No se añade un panel técnico de HILO al editor.

Los procesos de herramientas registrados por Runner y las ejecuciones gestionadas en PTY comparten un presupuesto de núcleos y memoria. `hardware.toolCores` usa por defecto la mitad de los núcleos disponibles y `hardware.toolMemoryMB` usa 4096 MiB. La afinidad limita el conjunto de CPU utilizado por las herramientas cuando el sistema la admite; no limita la afinidad del editor. Los procesos de fondo tienen menor prioridad.

La memoria es RSS agregada, muestreada cada 250 ms: no es una cuota dura del sistema operativo. Al rebasarla se cancela primero trabajo de fondo. El seguimiento identifica los procesos por PID y momento de creación y conserva descendientes observados para cancelarlos aunque se separen del padre. Se mantienen los mecanismos existentes de cancelación por árbol o grupo.

El alcance no incluye automáticamente cualquier orden escrita en una shell, cada servidor de lenguaje, cada motor externo de IA o cualquier máquina virtual. Los límites y fallos de medición se indican en el estado interno de recursos. El observador de recursos arranca al registrar trabajo y deja de muestrear al quedar inactivo.

Los lanzadores de máquinas utilizan las reservas de CPU/RAM y el apagado ordenado de su subsistema. No se registran como una herramienta genérica que pueda ser cancelada por árbol antes de cerrar el disco. Al quedar inactivo el observador de herramientas, el consumo vuelve a cero y los límites mostrados siguen las preferencias actuales.

La reutilización de compilaciones C/C++ conserva sus comprobaciones de fuentes, cabeceras declaradas por el compilador, entradas del enlazado, herramientas, argumentos, entorno y artefactos. Cambiar una de esas entradas invalida el resultado reutilizado. No se reutiliza una reproducción como si hubiera sido ejecutada de nuevo.

## Verificación de desarrollo

`tests/test_investigations.py` prueba capturas, una regresión real, propuestas por fragmentos, cambios de datos y herramientas, binarios C, rutas y revisión de pruebas. `tests/check_investigations_ui.py` conecta resultados reales, repeticiones, selección de fragmentos, aplicación y restauración, además de comprobar estilos claro, oscuro y ventana reducida. La respuesta del modelo utilizada en esa prueba visual es una fixture controlada; los programas y las pruebas de reproducción sí se ejecutan realmente.

`tests/test_resource_budget.py` y `tests/test_interactive_priority.py` verifican el presupuesto, los descendientes, la afinidad del editor y la separación entre acciones interactivas y mantenimiento. Los resultados de la entrega se recopilan en `qa-output/research-acceptance.json`.
