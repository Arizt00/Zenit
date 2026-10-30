"""Bounded replacement previews and revision checks; never writes source files."""
import fnmatch
import hashlib
import re
import threading
import time
import uuid
from pathlib import Path
from .workspace import ConflictError

MAX_FILE = 1024*1024
MAX_TOTAL = 4*1024*1024


def matches(path, patterns):
    return any(fnmatch.fnmatchcase(path.lower(), p.lower()) or
               '/' not in p and fnmatch.fnmatchcase(Path(path).name.lower(), p.lower()) or
               p.startswith('**/') and fnmatch.fnmatchcase(path.lower(), p[3:].lower()) for p in patterns)


class EditorChanges:
    def __init__(self):
        self.plans = {}; self.lock = threading.RLock()

    def revisions(self, ws, body):
        rows = body.get('documents')
        if not isinstance(rows, list) or len(rows)>64:raise ValueError('Revisa hasta 64 archivos por conjunto de cambios.')
        changed=[]
        for row in rows:
            if not isinstance(row,dict) or not isinstance(row.get('path'),str) or not isinstance(row.get('revision'),str):raise ValueError('Documento sin revisión guardada.')
            try:
                file=ws.resolve(row['path'])
                if not file.is_file() or file.stat().st_size>2*MAX_FILE:raise ValueError('Archivo no disponible.')
                value=hashlib.sha256(file.read_bytes()).hexdigest()
            except (OSError,ValueError):value=None
            if value!=row['revision']:changed.append(row['path'])
        if changed:raise ConflictError('Cambió en disco: '+', '.join(changed[:5])+'. Vuelve a revisar los cambios.')
        return {'valid':True}

    def search(self,ws,body):
        query=body.get('query','');buffers=body.get('buffers',[]);values={};total=0
        if not isinstance(query,str) or len(query)>200 or not isinstance(buffers,list) or len(buffers)>48:raise ValueError('Consulta de búsqueda no válida.')
        for row in buffers:
            if not isinstance(row,dict) or not isinstance(row.get('content'),str):raise ValueError('Búfer de búsqueda no válido.')
            path=ws.resolve(row.get('path','')).relative_to(ws.root).as_posix();size=len(row['content'].encode());total+=size
            if size>MAX_FILE or total>MAX_TOTAL:raise ValueError('La búsqueda admite 1 MiB por búfer y 4 MiB en conjunto.')
            values[path]=row['content']
        results=ws.search(query,content=True,folder=body.get('folder',''),case=body.get('case') is True,word=body.get('word') is True,include=body.get('include',''),exclude=body.get('exclude',''),file_type=body.get('type',''),limit=201,buffers=values)
        return {'results':results[:200],'truncated':len(results)>200}

    def preview(self, ws, body):
        if not ws.trusted:raise PermissionError('Autoriza el proyecto para revisar reemplazos.')
        query=body.get('query');replacement=body.get('replacement','')
        if not isinstance(query,str) or not 1<=len(query)<=200 or not isinstance(replacement,str) or len(replacement)>4096:raise ValueError('Busca entre 1 y 200 caracteres; el reemplazo admite 4096.')
        if '\0' in query or '\0' in replacement:raise ValueError('El reemplazo de texto no admite bytes nulos.')
        buffers=body.get('buffers',[])
        if not isinstance(buffers,list) or len(buffers)>48:raise ValueError('Demasiados búferes abiertos.')
        overrides={};total=0
        for row in buffers:
            if not isinstance(row,dict) or not isinstance(row.get('content'),str):raise ValueError('Búfer no válido.')
            name=row.get('path','');file=ws.resolve(name);name=file.relative_to(ws.root).as_posix()
            total+=len(row['content'].encode())
            if total>MAX_TOTAL or len(row['content'].encode())>MAX_FILE:raise ValueError('Los búferes de reemplazo admiten 1 MiB por archivo y 4 MiB en conjunto.')
            overrides[name]=row
        folder=body.get('folder','');scope=ws.resolve(folder).relative_to(ws.root).as_posix() if folder else ''
        if scope=='.':scope=''
        def patterns(key):
            value=body.get(key,'')
            if not isinstance(value,str) or len(value)>1024:raise ValueError('Filtro no válido.')
            return [('*'+p if p.startswith('.') else p) for p in (p.strip().replace('\\','/') for p in value.split(',')) if p][:32]
        include=patterns('include');exclude=patterns('exclude')
        pattern=re.compile((r'(?<!\w)' if body.get('word') else '')+re.escape(query)+(r'(?!\w)' if body.get('word') else ''),0 if body.get('case') else re.I)
        rows=[];budget=0;occurrences=0;skipped=0;limited=False
        for name in ws.files():
            if scope and not name.startswith(scope+'/'):continue
            if include and not matches(name,include) or matches(name,exclude):continue
            if body.get('type'):
                from .change_footprint import SUFFIXES
                code=Path(name).suffix.lower() in SUFFIXES
                if code!=(body['type']=='code'):continue
            try:
                file=ws.resolve(name)
                if file.stat().st_size>MAX_FILE:skipped+=1;continue
                raw=file.read_bytes()
                if b'\0' in raw:continue
                saved=raw.decode('utf-8-sig').replace('\r\n','\n');revision=hashlib.sha256(raw).hexdigest()
                override=overrides.get(name)
                if override and override.get('revision')!=revision:raise ConflictError('El archivo cambió en disco: '+name)
                before=override['content'] if override else saved
            except (OSError,UnicodeError):skipped+=1;continue
            budget+=len(raw)
            if budget>16*MAX_FILE:limited=True;break
            count=sum(1 for _ in pattern.finditer(before))
            if not count:continue
            after=pattern.sub(lambda _:replacement,before)
            if before==after:continue
            if len(rows)>=64 or occurrences+count>10000 or sum(len(x['before'].encode())+len(x['after'].encode()) for x in rows)+len(before.encode())+len(after.encode())>MAX_TOTAL:
                limited=True;break
            occurrences+=count;rows.append({'path':name,'before':before,'after':after,'revision':revision,'count':count,'buffer':bool(override)})
        plan={'id':uuid.uuid4().hex,'workspace':str(ws.root),'created':time.monotonic(),'files':rows,'limited':limited,'skipped':skipped,'occurrences':occurrences}
        with self.lock:
            self.plans={k:v for k,v in self.plans.items() if time.monotonic()-v['created']<600}
            self.plans[plan['id']]=plan
            for key in list(self.plans)[:-8]:self.plans.pop(key)
        return {k:v for k,v in plan.items() if k not in ('workspace','created')}

    def verify(self,ws,body):
        with self.lock:plan=self.plans.get(body.get('plan'))
        if not plan or plan['workspace']!=str(ws.root) or time.monotonic()-plan['created']>600:raise ValueError('El reemplazo caducó. Revisa de nuevo la búsqueda.')
        if plan['limited']:raise ValueError('La revisión alcanzó su límite. Reduce el ámbito antes de reemplazar.')
        return self.revisions(ws,{'documents':[{'path':r['path'],'revision':r['revision']} for r in plan['files']]})
