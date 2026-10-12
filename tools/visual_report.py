"""Build a review document from actual comparisons, without a pass-by-similarity gate."""
import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DETAILS = {
    'editor': ('app/editor/docking/product-ui + shell.css', 'Orden del árbol/tabs, minimapa, rama Git y runtime dependen del proyecto. Antialiasing e iconos tienen diferencias.'),
    'search': ('studio + pages.css', 'Ilustración local y filtros funcionales tienen diferencias menores de iconos/tipo. El estado vacío se conserva.'),
    'settings': ('workbench/controls + pages.css', 'Texto de seguridad y categorías avanzadas conservan información real. Blur y rasterizado varían por host.'),
    'extensions': ('workbench/preview + catalogue/dialogs.css', 'Paquetes, versiones, estados y compatibilidad son reales. No se copia la insignia Compatible del golden si no corresponde.'),
    'laboratory': ('foundation-ui + laboratory.css', 'El usuario pidió simplificar la vista en R7: cinco secciones persistentes sustituyen el hero y la cuadrícula completa. El golden original se conserva como historial; no es el objetivo vigente de esta pantalla. Las rutas no certifican ejecuciones.'),
    'debug': ('debug-workspace/lantern + debug-workspace.css', 'El usuario pidió simplificar Depuración en R8: un inspector seleccionado sustituye los cuatro bloques y el hero de Lantern. Se conserva el golden anterior como historial. Live, Lens, motores y valores siguen siendo reales.'),
    'forge': ('desktop-workflows/docking + windows.css', 'Marco y controles de acoplamiento difieren de la decoración OS. Contexto, ruta, herramientas y salida pertenecen al proyecto real.'),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--comparisons', type=Path, default=ROOT / 'tests/visual/comparisons')
    args = parser.parse_args()
    data = json.loads((args.comparisons / 'comparison.json').read_text(encoding='utf-8'))
    lines = ['# Comparación visual · Zénit', '',
             'Referencias originales: 1672 × 941. Resultado: WebView2 real, área cliente',
             '1672 × 917, host Windows al 150 %, viewport fijado por CDP. Solo se recortan',
             'los 24 px de título de la referencia. No hay estirado de la captura.', '',
             'La revisión combina bounds, overlay 50 %, diff de píxeles y revisión humana.',
             'MAE usa la escala de canales 0–255. SSIM es una comparación de luminancia',
             'reducida por bloques. Ninguna de estas cifras es un porcentaje de fidelidad',
             'ni produce automáticamente una marca de pantalla terminada.', '',
             '| Vista | Referencia / resultado | MAE | SSIM por bloques | Componentes / diferencias conocidas |',
             '| --- | --- | ---: | ---: | --- |']
    cards = []
    for screen, (components, limitations) in DETAILS.items():
        value = data['screens'][screen]
        links = f'[Golden](tests/visual/references/{screen}.png) · [Resultado](tests/visual/current/{screen}.png) · [Overlay](tests/visual/comparisons/{screen}-overlay.png) · [Diff](tests/visual/comparisons/{screen}-diff.png)'
        lines.append(f'| {screen} | {links} | {value["meanMAE"]:.2f} | {value["lumaBlockSSIM"]:.3f} | {components}. {limitations} |')
        cards.append(f'<section><h2>{html.escape(screen)}</h2><p>{html.escape(limitations)}</p><div class="comparison"><img class="reference" src="references/{screen}.png" alt="Referencia original"><img class="actual" src="current/{screen}.png" alt="Captura real"><i></i></div><label>Referencia / resultado <input type="range" min="0" max="100" value="50" aria-label="Superposición {screen}"></label><p><a href="comparisons/{screen}-overlay.png">Overlay 50 %</a> · <a href="comparisons/{screen}-diff.png">Diferencias</a></p></section>')
    geometry = json.loads((ROOT / 'tests/visual/current/geometry-verification.json').read_text(encoding='utf-8'))
    max_delta = max(abs(x) for check in geometry['checks'] for x in check['delta'])
    lines += ['', '## Bienvenida vigente', '',
              'El usuario sustituyó la bienvenida de dos columnas por una escena mínima y',
              'después pidió que ocupara toda la ventana. La referencia original se conserva',
              'intacta como historial; no se utiliza para declarar un pixel diff aprobado de',
              'la composición nueva. El objetivo vigente está en `tests/visual/welcome-brief.json`.', '',
              '[Resultado de bienvenida](tests/visual/current/welcome.png) ·',
              '[Perfil y recientes](tests/visual/current/profile-activity.png) ·',
              '[Referencia mínima posterior](tests/visual/references/welcome-minimal.png).', '',
              'La geometría Blender de dos paredes, el material óptico y la órbita son',
              'renderizados en vivo. R10 conserva el paisaje de cristal generado y servido',
              'localmente, con luz, movimiento CSS y profundidad de hasta 4 px al mover el puntero. El usuario pidió mejorar',
              'el fondo y simplificar Laboratory. No se declara reproducción óptica perfecta.', '',
              f"Los {len(geometry['checks'])} bounds de Editor/Bienvenida pasan con desviación máxima",
              f'de {max_delta:.3f} px. No se extrapola ese resultado a todos los detalles de las otras',
              'vistas. Los materiales y assets mantienen las diferencias descritas arriba.', '',
              'R10: 24 combinaciones de resolución/escala validadas sin overflow global ni errores JS. Depuración se comprueba además a 1280×720, 1366×768 y 1920×1080.', '', 'Regresiones sin golden independiente: [ASM](tests/visual/current/asm.png),',
              '[Melody](tests/visual/current/melody.png), [paleta](tests/visual/current/palette.png),',
              '[Proyecto flotante](tests/visual/current/floating-project.png).',
              'También se incluye [Forge desacoplado](tests/visual/current/forge-detached.png).', '',
              'Correcciones posteriores sin golden independiente: [Proyecto desacoplado](tests/visual/current/project-detached.png),',
              '[varias terminales reales](tests/visual/current/multiple-terminals.png) y [revisión de archivos de Melody](tests/visual/current/melody-file-review.png).', '',
              '## Temas e interfaz de R10', '',
              '[Selector](tests/visual/current/theme-picker.png) · [Vira Graphene High Contrast](tests/visual/current/vira-graphene-high-contrast.png) · [One Dark Pro Mix](tests/visual/current/one-dark-pro-mix.png) · [Proyecto con tema sincronizado](tests/visual/current/detached-theme.png).', '',
              'Las capturas del error de R8 del usuario y el proyecto QA difieren en resolución y contenido; no se declara un pixel diff comparable entre ellas. La comprobación funcional usa 89 variantes reales, siete pares de color con contraste mínimo 4.5:1, ausencia de overflow y conservación del modelo Monaco. Los 64 temas Bearded se cargan completos. Un selector por paquete sustituye las filas de variantes.', '',
              '[Inicio Noche](tests/visual/current/welcome-dark.png) · [Inicio Bosque](tests/visual/current/welcome-forest.png). Se conserva el mismo canvas animado. El cambio de ambiente y sus botones son comprobados por la UI, no por un nuevo golden inventado.', '',
              '[Regresión de tema antes](tests/visual/current/theme-split-before.png) · [División corregida](tests/visual/current/theme-split-fixed.png) · [Overlay](tests/visual/comparisons/theme-split-overlay.png) · [Diff](tests/visual/comparisons/theme-split-diff.png). Se conserva el mismo proyecto/viewport. El informe JSON registra que antes Monaco vuelve a lumen-theme y después conserva lumen-extension-theme en los seis pasos, con el comentario RGBA compuesto correctamente.', '',
              '[Consejo organizado de Melody](tests/visual/current/melody-advice-sections.png). El texto proviene de una fixture explícita; no evalúa la calidad de un modelo externo. La inserción se verifica sobre el búfer real y se deshace en un paso.', '',
              'Las inspecciones geométricas y de estilo están en `tests/visual/current/inspection.json`.',
              'El estado de conservación de campos/canvas/modelos, los errores JS y el resultado',
              'ASM real están en los JSON de esa carpeta. Esta corrección generó 72 capturas',
              'de Editor/Melody/Bienvenida en 24 combinaciones de resolución y escala.',
              'La matriz anterior de 312 capturas no se presenta como una nueva ejecución.',
              'Se incluyen el resumen JSON y',
              'muestras seleccionadas en `tests/visual/responsive`.', '',
              'Este informe registra resultados y diferencias; no certifica equivalencia total',
              'con las ocho imágenes ni paridad total con VS Code.']
    lines += ['', '## R11 · Melody y temas efectivos', '',
              '[One Dark Pro estable](tests/visual/current/one-dark-stable.png) · [Melody hablando](tests/visual/current/melody-speaking.png).', '',
              'La fila de archivos/ayuda ocupa una sola línea y las cuatro acciones caben a 1672×917. La voz utiliza iconos de la familia SVG y tokens existentes; no cambia la altura de los paneles. El player usa texto legible sobre la superficie efectiva y controles de pausa/parada.', '',
              '14 comprobaciones de voz/tema verifican selección, autenticación, audio real de Emma reproducido, pausa/reanudación, cancelación, persistencia del tema y cambio nativo atómico. La captura de conversación usa un fixture de IA; el WAV procede de MOSS real y esa generación se registra aparte. No se presenta el texto del fixture como respuesta de un proveedor real.', '',
              'R11 repite 13 vistas nativas y 24 combinaciones de escala/resolución (72 capturas). Las imágenes de referencia permanecen intactas. La restauración de colores se verifica antes de recibir las contribuciones; el control de tema muestra la variante efectiva.', '',
              'No se certifica equivalencia óptica perfecta ni cobertura del 90 % de VS Code. Los límites específicos del material, contenido y otras pantallas siguen descritos en las filas anteriores.']
    (ROOT / 'VISUAL_DIFF_REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    review = '''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Zénit · revisión visual</title><style>
    body{font:15px/1.5 system-ui;color:#10133c;background:#f8f9ff;margin:32px auto;padding:0 24px;max-width:1440px}section{margin:32px 0;padding:24px;background:white;border:1px solid #e9eafa;border-radius:16px}p{color:#6473a9}h1,h2{font-weight:600}.comparison{position:relative;aspect-ratio:1672/917;overflow:hidden;border:1px solid #dedbfc}.comparison img{position:absolute;width:100%;height:auto;left:0;top:0}.comparison .reference{top:-2.61723%}.actual{clip-path:inset(0 0 0 50%)}.comparison i{position:absolute;left:50%;height:100%;width:1px;background:#6b43f5}input{width:280px;max-width:60%;vertical-align:middle}a{color:#6b43f5}</style><h1>Referencia ↔ Zénit ejecutándose</h1><p>Capturas reales. El deslizador revela el resultado sin modificar las referencias. Las diferencias por datos y materiales se describen por vista.</p>'''
    review += ''.join(cards) + '<script>document.querySelectorAll("input").forEach(input=>input.oninput=()=>{const section=input.closest("section");section.querySelector(".actual").style.clipPath="inset(0 0 0 "+input.value+"%)";section.querySelector("i").style.left=input.value+"%";});</script></html>'
    (ROOT / 'tests/visual/review.html').write_text(review, encoding='utf-8')


if __name__ == '__main__':
    main()
