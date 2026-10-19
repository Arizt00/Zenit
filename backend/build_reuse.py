"""Conservative C/C++ build reuse: compiler depfiles, linker inputs and output hashes."""
import hashlib,json,os,re,shlex,threading,time,weakref
from pathlib import Path
from .preferences import atomic_json

_locks=weakref.WeakValueDictionary();_guard=threading.Lock()

def digest(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>512*1024**2:raise ValueError('Entrada de compilación no reutilizable.')
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def depnames(text):
    if os.name!='nt':return shlex.split(text,posix=True)
    # MinGW emits native Windows paths while escaping spaces with a backslash.
    names=[];word='';i=0
    while i<len(text):
        char=text[i]
        if char=='\\' and i+1<len(text) and text[i+1] in ' \t#:\\':word+=text[i+1];i+=2;continue
        if char.isspace():
            if word:names.append(word);word=''
        else:word+='/' if char=='\\' else char
        i+=1
    if word:names.append(word)
    return names

class BuildCommands(list):
    def __init__(self,commands,reuse):super().__init__(commands);self.build_reuse=reuse
    def __getitem__(self,key):
        value=super().__getitem__(key)
        if isinstance(key,slice) and (key.start or 0)==0 and (key.step or 1)==1 and value:return BuildCommands(value,self.build_reuse)
        return value

class BuildReuse:
    def __init__(self,ws,source,target,depfile,command):
        self.ws=ws;self.source=source;self.target=target;self.depfile=depfile;self.command=command;self.trace=set();self.started=0
        identity=hashlib.sha256(str(target).encode()).hexdigest();self.record=ws.private_dir('build-cache')/(identity+'.json')
        with _guard:self.lock=_locks.setdefault(str(self.record),threading.Lock())
    def signature(self,environment):return hashlib.sha256(json.dumps([self.command,sorted(environment.items())],ensure_ascii=False).encode()).hexdigest()
    def read(self):
        try:
            if self.record.is_symlink() or self.record.stat().st_size>2000000:return None
            value=json.loads(self.record.read_text(encoding='utf-8'))
            if value.get('schema')==1 and isinstance(value.get('inputs'),dict) and isinstance(value.get('outputs'),dict) and len(value['inputs'])<=4096 and len(value['outputs'])<=64:return value
        except (OSError,ValueError,AttributeError):pass
        return None
    def hit(self,environment):
        self.started=time.time_ns();self.trace.clear();record=self.read()
        if not record or not self.target.is_file() or record.get('signature')!=self.signature(environment):return False
        if str(self.source) not in record['inputs'] or str(self.target) not in record['outputs']:return False
        try:
            return all(digest(Path(path))==expected for path,expected in {**record['inputs'],**record['outputs']}.items())
        except (OSError,ValueError):return False
    def output(self,line):
        text=line.strip();candidate=Path(text)
        if not candidate.is_absolute():candidate=self.ws.root/candidate
        # GNU ld -t emits actual object/archive paths. Keep diagnostics visible.
        try:
            if text and candidate.is_file() and candidate.suffix.lower() in ('.o','.obj','.a','.so','.dll','.dylib'):
                self.trace.add(candidate.resolve());return ''
        except OSError:pass
        return line
    def save(self,environment):
        try:
            if not self.depfile.is_file() or self.depfile.stat().st_size>1000000:return
            text=self.depfile.read_text(encoding='utf-8').replace('\\\n','');parts=re.split(r'(?<!\\):\s',text,maxsplit=1)
            if len(parts)!=2:return
            dependencies=[(self.ws.root/name).resolve() for name in depnames(parts[1])]
            if not dependencies or len(dependencies)>4090:return
            inputs={self.source.resolve(),Path(self.command[0]).resolve(),*dependencies,*[p for p in self.trace if not p.is_relative_to(self.target.parent)]}
            # A changed SDK index invalidates compiler, runtime and linker versions together.
            for parent in Path(self.command[0]).parents:
                marker=parent/'tool-index.json'
                if marker.is_file():inputs.add(marker);break
            if any(not path.is_file() or path.stat().st_mtime_ns>self.started for path in inputs):return
            outputs=[p for p in self.target.parent.iterdir() if p.is_file() and not p.is_symlink()]
            if len(outputs)>64 or self.target not in outputs:return
            atomic_json(self.record,{'schema':1,'signature':self.signature(environment),'inputs':{str(p):digest(p) for p in inputs},'outputs':{str(p):digest(p) for p in outputs}})
        except (OSError,ValueError,KeyError):return
