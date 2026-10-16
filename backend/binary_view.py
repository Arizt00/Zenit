"""Paged byte inspection and optimistic revision stamps without full-file reads."""
import base64
import hashlib
from pathlib import Path


def revision(path):
    info=path.stat()
    return hashlib.sha256(str((info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)).encode()).hexdigest()


def read_binary(path: Path, name: str, offset=0, count=512):
    if type(offset) is not int or offset < 0 or type(count) is not int or not 1 <= count <= 4096:
        raise ValueError('Offset must be positive and count between 1 and 4096 bytes.')
    if not path.is_file():
        raise ValueError('Select a file.')
    stamp=revision(path)
    with path.open('rb') as stream:
        size = stream.seek(0, 2)
        if offset > size:
            raise ValueError('Offset is beyond the end of the file.')
        stream.seek(0); magic = stream.read(16)
        stream.seek(offset); raw = stream.read(count)
    signatures = [(b'MZ', 'PE executable'), (b'\x7fELF', 'ELF executable'),
                  (b'\xca\xfe\xba\xbe', 'Java class / universal Mach-O'),
                  (b'\x89PNG', 'PNG image'), (b'PK\x03\x04', 'ZIP container'),
                  (b'%PDF', 'PDF document'), (b'\x00asm', 'WebAssembly'),
                  (b'\xff\xd8\xff', 'JPEG image')]
    kind = next((label for prefix, label in signatures if magic.startswith(prefix)), 'Binary data')
    if stamp!=revision(path):raise ValueError('El archivo cambió mientras se leía. Vuelve a abrirlo.')
    return {'path': name, 'kind': 'binary', 'content': '', 'size': size, 'offset': offset,'revision':stamp,
            'count': len(raw), 'data': base64.b64encode(raw).decode('ascii'),
            'format': kind, 'readOnly': size>1_073_741_824}
