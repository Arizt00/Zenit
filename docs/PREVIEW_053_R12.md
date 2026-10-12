# Zénit 0.5.3 · Preview R12

Corrige la selección de voz solicitada: Melody usa la nueva voz de Emma preparada
el 4 de octubre y seleccionada por el usuario con Qwen, mediante el mismo catálogo
que usa la aplicación Emma. R11 había enlazado la referencia MOSS anterior.

La identidad, disponibilidad y motor se verifican; si falta la voz nueva, se
muestra un error sin volver a la antigua. Se conservan Escuchar, pausa,
reanudación, parada, selección, consejos y tratamiento local del audio.
No se copian referencias privadas ni se descargan modelos; no se activa un
servicio online o una API de pago en esta corrección.

Generación real: 4,24 s de audio a 24 kHz, cero muestras saturadas; 37,28 s de
preparación/generación en esta petición. No se declara voz instantánea.
85 tests Node, siete Python relacionados y 14 comprobaciones de voz/tema pasan.
Los demás cambios de interfaz y límites de VS Code de R11 se conservan.

[Implementación](../IMPLEMENTATION_REPORT.md) · [Límites](../KNOWN_LIMITATIONS.md)
· [Comparación visual](../VISUAL_DIFF_REPORT.md).
