"""Create a local project folder without overwriting an existing project."""
from pathlib import Path
import re

def create_project(parent, name):
    if not isinstance(parent, str) or not isinstance(name, str):
        raise ValueError('Indica la carpeta y el nombre del proyecto.')
    name = name.strip()
    if not name or len(name) > 100 or re.search(r'[<>:"/\\|?*\x00-\x1f]', name) or name.endswith(('.', ' ')) or name in ('.', '..'):
        raise ValueError('El nombre del proyecto no es válido.')
    if name.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *[f'COM{i}' for i in range(1,10)], *[f'LPT{i}' for i in range(1,10)]}:
        raise ValueError('Ese nombre está reservado por el sistema.')
    folder = Path(parent).expanduser().resolve(strict=True)
    if not folder.is_dir():
        raise ValueError('Selecciona una carpeta existente.')
    target = folder / name
    target.mkdir(exist_ok=False)
    return {'path': str(target), 'created': True}
