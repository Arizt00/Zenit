"""Unsaved buffers shared by native windows, with optimistic conflict detection."""
import threading


class Buffers:
    def __init__(self):self.lock=threading.RLock();self.items={}
    def snapshot(self):
        with self.lock:return {'buffers':[dict(x) for x in self.items.values()]}
    def document(self,ws,path):
        """Hydrate a child from disk metadata and its current unsaved buffer."""
        from pathlib import Path
        from .workspace import Workspace
        if not isinstance(path,str) or not path or '\x00' in path:raise ValueError('Ruta no válida.')
        external=Path(path).is_absolute()
        if external:path=str(Path(path).resolve())
        with self.lock:remote=dict(self.items[path]) if path in self.items else None
        if external:
            if not ws.trusted or remote is None:raise PermissionError('Abre el archivo en la sesión antes de separarlo.')
            target=Path(path);reader=Workspace(target.parent,ws.native);name=target.name
        else:target=ws.resolve(path,must_exist=False);reader=ws;name=path
        if target.exists():
            item=reader.open_file(name);item['path']=path
        elif remote is not None:
            item={'path':path,'name':target.name,'content':remote['text'],'revision':None,'newline':'LF','bom':False,'transient':True}
        else:raise FileNotFoundError('No se encuentra el archivo o un búfer compartido abierto.')
        return {'file':item,'buffer':remote}
    def update(self, ws, body):
        path=body.get('path')
        from pathlib import Path
        if isinstance(path,str) and Path(path).is_absolute():
            if not ws.trusted:raise PermissionError('Proyecto no autorizado.')
            path=str(Path(path).resolve())
        else:ws.resolve(path,must_exist=False)
        text=body.get('text');expected=body.get('sequence',0)
        if not isinstance(text,str) or len(text)>2_000_000:raise ValueError('El búfer compartido admite hasta 2 MB.')
        if type(expected) is not int:raise ValueError('Revisión inválida.')
        revision=body.get('revision')
        if revision is not None and (not isinstance(revision,str) or len(revision)>100):raise ValueError('Revisión de archivo inválida.')
        with self.lock:
            old=self.items.get(path)
            if old and expected!=old['sequence']:return {'conflict':True,'buffer':dict(old)}
            if not old and len(self.items)>=200:raise ValueError('Límite de 200 búferes compartidos.')
            result={'path':path,'text':text,'sequence':(old['sequence'] if old else 0)+1,'saved':body.get('saved') is True,'revision':revision}
            self.items[path]=result
            return {'buffer':dict(result),'conflict':False}
    def clear(self):
        with self.lock:self.items.clear()
