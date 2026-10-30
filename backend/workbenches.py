"""Bounded, atomic workbench recovery and named spaces, stored outside projects."""
from __future__ import annotations
import copy,hashlib,json,threading,time
from pathlib import Path
from .preferences import atomic_json

MAX_TEXT=2*1024*1024
class Workbenches:
 def __init__(self,features):
  self.features=features;self.directory=features.prefs.directory/'workbenches';self.directory.mkdir(exist_ok=True);self.lock=threading.RLock();self.cache={}
 def _path(self,ws):return self.directory/(hashlib.sha256(str(ws.root).encode()).hexdigest()[:32]+'.json')
 def _read(self,ws):
  key=str(ws.root)
  if key not in self.cache:
   try:
    file=self._path(ws)
    if file.stat().st_size>32*MAX_TEXT:raise ValueError('Workbench too large')
    value=json.loads(file.read_text(encoding='utf-8'))
    if not isinstance(value,dict) or value.get('schema')!=1 or value.get('workspace')!=key or not isinstance(value.get('spaces'),list) or value.get('session') is not None and not isinstance(value['session'],dict):raise ValueError('Invalid workbench')
   except (OSError,ValueError,TypeError):
    # Preserve malformed recovery for inspection instead of overwriting it.
    if file.is_file():
     try:file.rename(file.with_suffix('.corrupt-'+str(time.time_ns())+'.json'))
     except OSError:pass
    value={'schema':1,'workspace':key,'session':None,'spaces':[],'target':'local'}
   self.cache[key]=value
   while len(self.cache)>16:self.cache.pop(next(iter(self.cache)))
  return self.cache[key]
 def _write(self,ws,data):
  data['updated']=time.time();atomic_json(self._path(ws),data);self.cache[str(ws.root)]=data
 def snapshot(self,ws):
  with self.lock:return copy.deepcopy(self._read(ws))
 def _document(self,ws,item):
  if not isinstance(item,dict):raise ValueError('Documento no válido.')
  path=item.get('path')
  if not isinstance(path,str) or not path or len(path)>2048:raise ValueError('Ruta de sesión no válida.')
  if Path(path).is_absolute():
   if not ws.trusted:raise PermissionError('Autoriza el proyecto para recuperar archivos externos.')
   path=str(Path(path).resolve())
  else:ws.resolve(path,must_exist=False)
  result={'path':path,'dirty':item.get('dirty') is True}
  if item.get('kind')=='binary':
   result['kind']='binary'
   if result['dirty']:
    from .binary_recovery import normalize
    result['binary']=normalize(item.get('binary'))
    result['dirty']=bool(result['binary']['patches'])
  elif result['dirty']:
   text=item.get('content')
   if not isinstance(text,str) or len(text.encode('utf-8'))>MAX_TEXT:raise ValueError('El búfer de recuperación admite hasta 2 MiB.')
   result['content']=text
  revision=item.get('revision')
  if revision is not None and (not isinstance(revision,str) or len(revision)>100):raise ValueError('Revisión inválida.')
  result['revision']=revision
  for key,maximum in [('line',10000000),('column',1000000),('scrollTop',100000000),('scrollLeft',1000000)]:
   value=item.get(key,1 if key in ('line','column') else 0)
   if type(value) not in (int,float) or not 0<=value<=maximum:raise ValueError('Posición de editor inválida.')
   result[key]=int(value)
  return result
 def _session(self,ws,raw):
  if not isinstance(raw,dict):raise ValueError('Sesión no válida.')
  docs=raw.get('documents',[])
  if not isinstance(docs,list) or len(docs)>48:raise ValueError('La sesión admite 48 archivos.')
  docs=[self._document(ws,x) for x in docs]
  if len({x['path'] for x in docs})!=len(docs):raise ValueError('Documento repetido.')
  if sum(len(x.get('content','').encode()) for x in docs)>4*MAX_TEXT:raise ValueError('La recuperación admite 8 MiB de texto sin guardar.')
  if sum(len(json.dumps(x.get('binary',{}))) for x in docs)>4*MAX_TEXT:raise ValueError('La recuperación admite 8 MiB de parches binarios.')
  paths={x['path'] for x in docs};active=raw.get('active')
  layout=raw.get('layout')
  if layout is not None and (not isinstance(layout,dict) or len(json.dumps(layout))>10000):raise ValueError('Distribución no válida.')
  style=raw.get('style','general')
  if style not in ('general','web','data','design','assembly'):raise ValueError('Estilo no válido.')
  panes=raw.get('panes',[])
  if not isinstance(panes,list) or len(panes)>2:raise ValueError('División no válida.')
  groups=raw.get('tabGroups',[]);clean=[];grouped=set()
  if not isinstance(groups,list) or len(groups)>24:raise ValueError('Grupos de pestañas no válidos.')
  for group in groups:
   if not isinstance(group,dict) or not isinstance(group.get('id'),str) or len(group['id'])>80 or not isinstance(group.get('name'),str) or len(group['name'])>60 or not isinstance(group.get('paths'),list) or len(group['paths'])>48:raise ValueError('Grupo temporal no válido.')
   if any(not isinstance(p,str) for p in group['paths']):raise ValueError('Ruta de grupo no válida.')
   members=list(dict.fromkeys(p for p in group['paths'] if p in paths and p not in grouped));grouped.update(members)
   if members:clean.append({'id':group['id'],'name':group['name'],'paths':members})
  return {'documents':docs,'active':active if active in paths else (docs[0]['path'] if docs else None),'layout':layout,'style':style,'panes':[p for p in panes if p in paths],'axis':'vertical' if raw.get('axis')=='vertical' else 'horizontal',
          'tabGroups':clean,'activeTabGroup':raw.get('activeTabGroup') if raw.get('activeTabGroup') in {g['id'] for g in clean} else None}
 def checkpoint(self,ws,body):
  session=self._session(ws,body.get('session'))
  auxiliary=body.get('auxiliary') is True
  shared_paths=body.get('shared',[])
  if not isinstance(shared_paths,list) or len(shared_paths)>48 or any(not isinstance(p,str) for p in shared_paths):raise ValueError('Búferes compartidos no válidos.')
  with self.lock:
   data=copy.deepcopy(self._read(ws));old=data.get('session') or {}
   if auxiliary:
    docs={x['path']:x for x in old.get('documents',[])}
    for doc in session['documents']:docs[doc['path']]=doc
    session={**old,'documents':list(docs.values())[-48:]}
   # The document hub is authoritative for edits received from another window.
   remote={x['path']:x for x in self.features.buffers.snapshot()['buffers']}
   for doc in session['documents']:
    shared=remote.get(doc['path'])
    if shared and doc.get('kind')!='binary' and doc['path'] in shared_paths:
     doc['dirty']=not shared['saved'];doc['revision']=shared.get('revision')
     if doc['dirty']:doc['content']=shared['text']
     else:doc.pop('content',None)
   session=self._session(ws,session)
   if data.get('session')!=session:data['session']=session;self._write(ws,data)
   return {'saved':True,'documents':len(session['documents'])}
 def discard(self,ws,path,recursive=False):
  affected=lambda name:name==path or recursive and name.startswith(path+'/')
  with self.lock:
   data=copy.deepcopy(self._read(ws));session=data.get('session')
   if session:
    session['documents']=[x for x in session['documents'] if not affected(x['path'])]
    session['panes']=[x for x in session.get('panes',[]) if not affected(x)]
    if affected(session.get('active') or ''):session['active']=next((x['path'] for x in session['documents']),None)
    for group in session.get('tabGroups',[]):group['paths']=[p for p in group['paths'] if not affected(p)]
    session['tabGroups']=[g for g in session.get('tabGroups',[]) if g['paths']]
    if session.get('activeTabGroup') not in {g['id'] for g in session['tabGroups']}:session['activeTabGroup']=None
    self._write(ws,data)
   return {'removed':True}
 def save_space(self,ws,body):
  name=body.get('name')
  if not isinstance(name,str) or not name.strip() or len(name)>60 or any(ord(c)<32 for c in name):raise ValueError('El nombre debe tener entre 1 y 60 caracteres.')
  session=self._session(ws,body.get('session'))
  for doc in session['documents']:
   doc.pop('content',None);doc.pop('binary',None);doc['dirty']=False
  with self.lock:
   data=copy.deepcopy(self._read(ws));spaces=[x for x in data['spaces'] if x['name'].casefold()!=name.strip().casefold()]
   if len(spaces)>=12:raise ValueError('Puedes guardar hasta 12 espacios por proyecto.')
   spaces.append({'name':name.strip(),'session':session,'updated':time.time()});data['spaces']=spaces;self._write(ws,data)
   return self.snapshot(ws)
 def delete_space(self,ws,name):
  with self.lock:
   data=copy.deepcopy(self._read(ws));data['spaces']=[x for x in data['spaces'] if x['name']!=name];self._write(ws,data);return self.snapshot(ws)
 def set_target(self,ws,target,options=None):
  with self.lock:
   data=copy.deepcopy(self._read(ws));data['target']=target;data['targetOptions']=options or {};self._write(ws,data)
 def relocate(self,ws,remap):
  with self.lock:
   data=copy.deepcopy(self._read(ws))
   for session in [data.get('session'),*[s.get('session') for s in data.get('spaces',[])]]:
    if not session:continue
    for document in session.get('documents',[]):document['path']=remap(document['path'])
    session['active']=remap(session['active']) if session.get('active') else None
    session['panes']=[remap(p) for p in session.get('panes',[])]
    for group in session.get('tabGroups',[]):group['paths']=[remap(p) for p in group['paths']]
   self._write(ws,data)
 def clear(self):
  with self.lock:self.cache.clear()
