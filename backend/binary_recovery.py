"""Validate pending byte patches without reading or modifying a project file."""
import base64
import binascii

MAX_PATCH_BYTES = 65536
MAX_OFFSET = 2**53 - 1


def normalize(raw):
    if not isinstance(raw, dict):
        raise ValueError('Recuperación binaria no válida.')
    revision = raw.get('revision')
    if not isinstance(revision, str) or not revision or len(revision) > 100:
        raise ValueError('La recuperación binaria necesita su revisión original.')
    patches = raw.get('patches')
    if not isinstance(patches, list) or len(patches) > MAX_PATCH_BYTES:
        raise ValueError('Demasiados grupos de bytes pendientes.')
    result = []; end = 0; total = 0
    for patch in patches:
        if not isinstance(patch, dict):
            raise ValueError('Parche binario no válido.')
        offset = patch.get('offset')
        if type(offset) is not int or not end <= offset <= MAX_OFFSET:
            raise ValueError('Los parches deben estar ordenados y no solaparse.')
        values = []
        for key in ('before', 'after'):
            value = patch.get(key)
            if not isinstance(value, str) or len(value) > 5464:
                raise ValueError('Cada grupo admite hasta 4096 bytes.')
            try:
                decoded = base64.b64decode(value, validate=True)
            except (ValueError, binascii.Error) as error:
                raise ValueError('Bytes de recuperación no válidos.') from error
            if not 1 <= len(decoded) <= 4096:
                raise ValueError('Cada grupo admite entre 1 y 4096 bytes.')
            values.append(decoded)
        if len(values[0]) != len(values[1]) or offset + len(values[0]) > MAX_OFFSET:
            raise ValueError('El parche no puede cambiar el tamaño del binario.')
        total += len(values[0]); end = offset + len(values[0])
        if total > MAX_PATCH_BYTES:
            raise ValueError('La recuperación admite hasta 64 KiB modificados por binario.')
        result.append({'offset': offset, **{key: base64.b64encode(value).decode('ascii') for key, value in zip(('before', 'after'), values)}})
    position = raw.get('offset', 0)
    if type(position) is not int or not 0 <= position <= MAX_OFFSET:
        raise ValueError('Posición binaria no válida.')
    return {'revision': revision, 'patches': result, 'offset': position}
