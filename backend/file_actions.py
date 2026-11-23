"""Explorer operations with workspace boundaries and a recoverable local trash."""
import json
import os
from pathlib import Path
import shutil
import time
import uuid
from .preferences import atomic_json

def target(ws, name, exists=True):
    result=ws.resolve(name,must_exist=exists)
    if result==ws.root or any(part in ('.git','.lumen') for part in result.relative_to(ws.root).parts):
        raise ValueError('Esta carpeta pertenece al sistema del proyecto.')
    for item in (result,*result.parents):
        if hasattr(item,'is_junction') and item.is_junction():raise ValueError('No se operan uniones de Windows.')
    return result

def perform(ws, body, before_move=None):
    operation=body.get('operation');name=body.get('path','')
    with ws.lock:
        if operation=='restore':
            ticket=body.get('ticket','')
            if not isinstance(ticket,str) or len(ticket)!=32 or any(c not in '0123456789abcdef' for c in ticket):raise ValueError('Identificador no válido.')
            folder=ws.private_dir('trash')/ticket
            from .uninstall import no_links
            no_links(folder);no_links(folder/'content');no_links(folder/'metadata.json')
            data=json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
            destination=target(ws,data['path'],False)
            if destination.exists():raise ValueError('Ya existe un archivo en la ubicación original.')
            destination.parent.mkdir(parents=True,exist_ok=True)
            directory=(folder/'content').is_dir()
            (folder/'content').rename(destination);(folder/'metadata.json').unlink();folder.rmdir()
            return {'path':data['path'],'directory':directory}
        source=target(ws,name,operation!='mkdir')
        if operation=='mkdir':source.mkdir();return {'path':name}
        if operation=='delete':
            ticket=uuid.uuid4().hex;folder=ws.private_dir('trash')/ticket
            if before_move:before_move(source,folder/'content')
            folder.mkdir()
            atomic_json(folder/'metadata.json',{'path':name,'deletedAt':time.time()})
            source.rename(folder/'content')
            return {'ticket':ticket,'path':name,'recoverable':True}
        if operation in ('rename','copy','move'):
            requested=body.get('destination','');destination=target(ws,requested,False)
            # resolve() normalizes the case of existing Windows files. Retain
            # the requested leaf so Main.py -> main.py actually changes its name.
            leaf=Path(requested).name
            if os.name=='nt' and (leaf.endswith((' ','.')) or any(c in leaf for c in '<>:"|?*') or leaf.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'{p}{i}' for p in ('COM','LPT') for i in range(1,10)]}):raise ValueError('Ese nombre no es válido en Windows.')
            destination=destination.parent/leaf
            same_entry=destination.exists() and source.samefile(destination)
            case_only=operation in ('rename','move') and os.name=='nt' and same_entry and str(source).casefold()==str(destination).casefold()
            if case_only and str(source)==str(destination):return {'path':name,'unchanged':True}
            if destination.exists() and not case_only:raise ValueError('Ya existe un archivo con ese nombre.')
            if not case_only and destination.is_relative_to(source):raise ValueError('Una carpeta no se puede mover dentro de sí misma.')
            if not destination.parent.is_dir():raise ValueError('La carpeta de destino no existe.')
            if operation=='copy':
                if source.is_dir():
                    for item in source.rglob('*'):target(ws,item.relative_to(ws.root).as_posix())
                    shutil.copytree(source,destination)
                else:shutil.copy2(source,destination)
            else:
                if before_move:before_move(source,destination)
                source.rename(destination)
            result={'path':destination.relative_to(ws.root).as_posix()}
            if operation in ('rename','move'):result['oldPath']=source.relative_to(ws.root).as_posix()
            return result
        raise ValueError('Operación de archivo desconocida.')
