"""Bounded static references for a reviewed buffer, without executing project code."""
import ast,difflib,hashlib,re
from pathlib import PurePosixPath

SUFFIXES={'.py','.c','.h','.cc','.cpp','.hpp','.java','.rs','.n','.nc','.nm','.nb','.nbb','.ncp','.nbo','.init','.asm','.s','.inc','.js','.ts','.mjs'}
BUILD_FILES={'CMakeLists.txt','Cargo.toml','Cargo.lock','package.json','package-lock.json','pyproject.toml','requirements.txt','pom.xml','build.gradle','build.gradle.kts','settings.gradle','settings.gradle.kts','ncc.package.json','ncc.lock'}
def sha(text):return hashlib.sha256(text.encode()).hexdigest()

def references(text,path):
 result=[]
 if path.endswith('.py'):
  try:
   for node in ast.walk(ast.parse(text)):
    if isinstance(node,ast.Import):result.extend(a.name for a in node.names)
    if isinstance(node,ast.ImportFrom):
     prefix='.'*node.level+(node.module or '');result.append(prefix)
     result.extend(prefix+('.' if prefix and not prefix.endswith('.') else '')+a.name for a in node.names if a.name!='*')
  except SyntaxError:pass
 else:
  result.extend(re.findall(r'(?:#\s*include|%include|\bimport|\bfrom)\s*["<\']([^"\'>]+)',text))
  result.extend(re.findall(r'(?m)^\s*(?:import\s+(?:static\s+)?|use\s+)([\w.:]+)',text))
  result.extend(re.findall(r'(?m)^\s*(?:pub\s+)?mod\s+(\w+)\s*;',text))
 return list(dict.fromkeys(r for r in result if r))[:100]

def resolve_reference(ref,source,paths,suffix_index=None):
 name=ref.replace('::','/').removeprefix('crate/').removeprefix('self/')
 if source.endswith('.py'):
  level=len(name)-len(name.lstrip('.'));name=name.lstrip('.').replace('.','/')
  if level:
   parent=PurePosixPath(source).parent
   for _ in range(level-1):parent=parent.parent
   name=(parent/name).as_posix()
 elif source.endswith('.java'):name=name.replace('.','/')
 variants={name,*[name+s for s in SUFFIXES],name+'/__init__.py',name+'/mod.rs'}
 local={(PurePosixPath(source).parent/v).as_posix() for v in variants}
 exact=sorted((local|variants)&set(paths))
 if exact:return exact
 if suffix_index is not None:return sorted({p for variant in variants for p in suffix_index.get(variant,[])})
 return [p for p in paths if any(p.endswith('/'+v) for v in variants)]

def footprint(ws,body,*,obsolete=None):
 if not ws.trusted:raise PermissionError('Autoriza el proyecto antes de analizar sus referencias.')
 path=body.get('path','');saved=ws.read(path);content=body.get('content',saved['content'])
 if not isinstance(content,str) or len(content.encode())>128000:raise ValueError('Huella de cambio admite un búfer de hasta 128 kB.')
 texts={};skipped=0;total=0;files=ws.files()
 for name in files:
  if obsolete and obsolete():
   from concurrent.futures import CancelledError
   raise CancelledError()
  if PurePosixPath(name).suffix.lower() not in SUFFIXES and PurePosixPath(name).name not in BUILD_FILES:continue
  try:
   file=ws.resolve(name);size=file.stat().st_size
   if len(texts)>=400 or size>128000 or total+size>6_000_000:skipped+=1;continue
   # Reference analysis needs source text, not per-file editor statistics.
   # A bounded read also tolerates a file growing after its stat.
   with file.open('rb') as stream:raw=stream.read(128001)
   if len(raw)>128000 or b'\0' in raw:skipped+=1;continue
   text=raw.decode('utf-8-sig').replace('\r\n','\n')
  except (ValueError,UnicodeError,OSError):skipped+=1;continue
  texts[name]=text;total+=len(text.encode())
 texts[path]=content;paths=set(texts);edges={};unresolved={};suffix_index={}
 for name in paths:
  parts=name.split('/')
  for i in range(len(parts)):suffix_index.setdefault('/'.join(parts[i:]),set()).add(name)
 for name,text in texts.items():
  edges[name]=set();unresolved[name]=[]
  for ref in references(text,name):
   matches=resolve_reference(ref,name,paths,suffix_index)
   if matches:edges[name].update(p for p in matches if p!=name)
   else:unresolved[name].append(ref)
 affected={};front={path}
 for depth in range(1,5):
  next_level={name for name,refs in edges.items() if name!=path and name not in affected and refs&front}
  for name in next_level:affected[name]=depth
  front=next_level
  if not front:break
 rows=[{'path':p,'depth':d,'test':bool(re.search(r'(^|/)(tests?|test_[^/]+)|(?:Test|_test)\.',p))} for p,d in sorted(affected.items(),key=lambda item:(item[1],item[0]))]
 changed=[];a=saved['content'].splitlines();b=content.splitlines()
 for tag,i,j,k,l in difflib.SequenceMatcher(None,a,b).get_opcodes():
  if tag!='equal':changed.append({'savedStart':i+1,'savedLines':j-i,'bufferStart':k+1,'bufferLines':l-k})
 return {'path':path,'savedSha256':sha(saved['content']),'bufferSha256':sha(content),'changedRanges':changed[:100],
  'dependencies':sorted(edges[path])[:80],'affected':rows[:80],'unresolved':unresolved[path][:40],
  'consulted':[{'path':name,'sha256':sha(text)} for name,text in texts.items()], 'skippedFiles':skipped,
  'limited':skipped>0 or len(rows)>80,'notice':'Referencias estáticas orientativas, hasta cuatro niveles. Las importaciones dinámicas, macros y configuración de compilación pueden añadir relaciones no detectadas. No se han ejecutado pruebas.'}
