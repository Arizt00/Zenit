"""Bounded evidence of the source context and destination of a Lantern run.

This is a conservative static context, not an assertion that dynamic imports,
external data, environment variables or tool installations were reproduced.
"""
import hashlib
import json
from .change_footprint import footprint,sha


def runtime_signature(runtimes):
    return hashlib.sha256(json.dumps(runtimes.config,sort_keys=True).encode()).hexdigest()


def context(workspace, path, content, obsolete=None):
    # The interactive executor admits larger buffers than the static dossier.
    # Evidence limits must never become new restrictions on program execution.
    if len(content.encode('utf-8'))>128000:
        return {'files':[{'path':path,'sha256':sha(content)}],'limited':True,
                'scope':'El archivo principal supera el límite de análisis estático; se conserva su huella, sin verificar sus dependencias.'}
    analysis = footprint(workspace, {'path': path, 'content': content},obsolete=obsolete)
    return {'files': analysis['consulted'], 'limited': analysis['limited'],
            'scope': 'Fuentes y descriptores locales revisados; hasta 400 archivos y 6 MB. No incluye datos externos, variables de entorno ni dependencias instaladas.'}


def compare(recorded, consulted):
    if not recorded:
        return {'status': 'unknown', 'changed': [], 'notice': 'Esta ejecución no registró su contexto; vuelve a comprobarla.'}
    old = {row['path']: row['sha256'] for row in recorded['files']}
    current = {row['path']: row['sha256'] for row in consulted['files']}
    changed = sorted(path for path in old.keys() | current.keys() if old.get(path) != current.get(path))
    status = 'changed' if changed else 'limited' if recorded['limited'] or consulted['limited'] else 'matched'
    return {'status': status, 'changed': changed[:40], 'changedCount': len(changed),
            'notice': {'changed': 'El contexto de fuentes cambió después de esta ejecución.',
                       'limited': 'Coincide el contexto revisado, pero la revisión alcanzó su límite.',
                       'matched': 'Coinciden las fuentes y descriptores revisados. Los datos externos y las herramientas pueden haber cambiado.'}[status],
            'scope': recorded['scope']}
