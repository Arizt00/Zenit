"""Explicit hex patches, source rebuilds and native/Java execution, without shells."""
import base64
import hashlib
import os
from pathlib import Path
import re
import shutil
import struct
import tempfile
import threading
import time
import uuid
from .binary_view import read_binary,revision
from .workspace import ConflictError
from .preferences import atomic_json

MAX_EDIT_SIZE=1_073_741_824


def java_name(file):
    """Read this_class from the JVM constant pool; do not guess package names."""
    if file.stat().st_size>16_000_000:raise ValueError('La clase Java es demasiado grande.')
    raw=file.read_bytes();cursor=10;pool={};index=1
    try:
        if raw[:4]!=b'\xca\xfe\xba\xbe':raise ValueError('No es una clase Java.')
        count=struct.unpack_from('>H',raw,8)[0]
        while index<count:
            tag=raw[cursor];cursor+=1
            if tag==1:
                size=struct.unpack_from('>H',raw,cursor)[0];cursor+=2;pool[index]=raw[cursor:cursor+size].decode('utf-8');cursor+=size
            elif tag==7:pool[index]=struct.unpack_from('>H',raw,cursor)[0];cursor+=2
            elif tag in (3,4,9,10,11,12,17,18):cursor+=4
            elif tag in (5,6):cursor+=8;index+=1
            elif tag in (8,16,19,20):cursor+=2
            elif tag==15:cursor+=3
            else:raise ValueError('Etiqueta JVM desconocida.')
            index+=1
        name=pool[pool[struct.unpack_from('>H',raw,cursor+2)[0]]]
        if not isinstance(name,str) or not re.fullmatch(r'[\w$/]+',name):raise ValueError('Nombre JVM inválido.')
        return name
    except (IndexError,KeyError,struct.error,UnicodeError):raise ValueError('La clase Java está incompleta o dañada.') from None


class BinaryTools:
    def __init__(self,features):
        self.features=features;self.lock=threading.RLock();self.builds={};self.settings=features.prefs.directory/'binary-builds.json'
        try:self.sources=__import__('json').loads(self.settings.read_text(encoding='utf-8'))
        except (OSError,ValueError):self.sources={}
        if not isinstance(self.sources,dict):self.sources={}
    def scope(self,name):
        self.features._trusted();ws=self.features.app.workspace
        if isinstance(name,str) and Path(name).is_absolute():
            from .extension_services import file_path
            file=file_path(name);ws=self.features.extension_services.file_workspace(file);return ws,file.name,file
        return ws,name,ws.resolve(name)
    def key(self,file):return os.path.normcase(str(file))
    def info(self,name):
        ws,path,file=self.scope(name);stem=file.stem.split('$')[0]
        sources=[p for p in ws.files() if Path(p).stem==stem and Path(p).suffix.lower() in ('.c','.cpp','.cc','.cxx','.rs','.go','.java','.n','.nc','.s','.asm')]
        chosen=self.sources.get(self.key(file),'')
        if chosen not in sources and chosen and ws.resolve(chosen,must_exist=False).is_file():sources.insert(0,chosen)
        try:self.run_plan(ws,path);can_run=True;reason=''
        except (ValueError,OSError) as error:can_run=False;reason=str(error)
        return {'sources':sources,'source':chosen if chosen in sources else sources[0] if len(sources)==1 else '', 'canRun':can_run,'runReason':reason,'revision':revision(file)}
    def assert_revision(self,file,expected):
        if not expected or revision(file)!=expected:raise ConflictError('El binario cambió en disco. Tus cambios se conservan; vuelve a abrirlo antes de guardar.')
    def replace(self,ws,file,expected,write):
        with self.lock,ws.lock:
            origin=self.features.app.workspace
            self.assert_revision(file,expected)
            if file.stat().st_size>MAX_EDIT_SIZE:raise ValueError('El guardado binario admite archivos de hasta 1 GiB.')
            fd,temp=tempfile.mkstemp(prefix='.'+file.name+'.zenit-',dir=file.parent)
            try:
                with os.fdopen(fd,'w+b') as output:write(output);output.flush();os.fsync(output.fileno())
                self.assert_revision(file,expected)
                directory=ws.private_dir('binary-backups')/hashlib.sha256(str(file).encode()).hexdigest()[:16];directory.mkdir(exist_ok=True)
                backup=directory/(time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]+'-'+file.name);shutil.copy2(file,backup)
                self.assert_revision(file,expected)
                if self.features.app.workspace is not origin or not origin.trusted:raise ConflictError('El proyecto cambió antes de guardar el binario.')
                shutil.copymode(file,temp);os.replace(temp,file)
                # Only our own generated backups in this checked directory are retired.
                for old in sorted(directory.iterdir(),key=lambda p:p.stat().st_mtime_ns)[:-3]:
                    if re.fullmatch(r'\d{8}-\d{6}-[a-f0-9]{8}-'+re.escape(file.name),old.name) and old.is_file() and not old.is_symlink() and old.resolve().parent==directory.resolve():old.unlink()
                return {'backup':str(backup),'revision':revision(file)}
            finally:
                if os.path.exists(temp):os.unlink(temp)
    def save(self,body):
        ws,path,file=self.scope(body.get('path'));patches=body.get('patches')
        if not isinstance(patches,list) or not 1<=len(patches)<=65536:raise ValueError('Selecciona entre uno y 65536 bytes modificados.')
        if any(not isinstance(p,dict) or type(p.get('offset')) is not int for p in patches):raise ValueError('Parche binario inválido.')
        validated=[];end=0;total=0
        for item in sorted(patches,key=lambda p:p.get('offset',-1)):
            offset=item.get('offset');before=item.get('before');after=item.get('after')
            if type(offset) is not int or offset<end or not isinstance(before,str) or not isinstance(after,str) or max(len(before),len(after))>180000:raise ValueError('Parche binario inválido o solapado.')
            before=base64.b64decode(before,validate=True);after=base64.b64decode(after,validate=True);total+=len(after);end=offset+len(after)
            if not after or len(before)!=len(after) or end>file.stat().st_size or total>65536:raise ValueError('Los parches sustituyen hasta 64 KiB sin cambiar el tamaño del archivo.')
            validated.append((offset,before,after))
        def write(output):
            with file.open('rb') as original:shutil.copyfileobj(original,output,1_048_576)
            for offset,before,after in validated:
                output.seek(offset)
                if output.read(len(before))!=before:raise ConflictError('Los bytes originales ya no coinciden. Se conserva el archivo en disco.')
                output.seek(offset);output.write(after)
        result=self.replace(ws,file,body.get('revision'),write);page=read_binary(file,body['path'],int(body.get('offset',0)));return {**page,**result,'saved':True}
    def run_plan(self,ws,path,args=None):
        file=ws.resolve(path);args=args or []
        if not isinstance(args,list) or len(args)>64 or any(not isinstance(x,str) or len(x)>4096 or '\x00' in x for x in args):raise ValueError('Argumentos binarios inválidos.')
        with file.open('rb') as stream:magic=stream.read(4096)
        suffix=file.suffix.lower()
        if magic.startswith(b'MZ'):
            if os.name!='nt':raise ValueError('Este ejecutable PE requiere Windows.')
            try:
                position=struct.unpack_from('<I',magic,60)[0]
                if magic[position:position+4]!=b'PE\0\0':raise ValueError('Cabecera PE dañada.')
                flags=struct.unpack_from('<H',magic,position+22)[0]
                if flags&0x2000:raise ValueError('Una biblioteca DLL necesita un programa anfitrión; no se ejecuta como aplicación.')
            except struct.error:raise ValueError('Cabecera PE incompleta.') from None
            return [str(file),*args]
        if magic.startswith(b'\x7fELF'):
            if not __import__('sys').platform.startswith('linux'):raise ValueError('Este ELF requiere Linux o una máquina Linux de Lantern.')
            if not os.access(file,os.X_OK):raise ValueError('El archivo no tiene permiso de ejecución.')
            return [str(file),*args]
        if suffix=='.class' and magic.startswith(b'\xca\xfe\xba\xbe'):
            name=java_name(file);root=file.parent
            for part in reversed(name.split('/')[:-1]):
                if root.name!=part:raise ValueError('La clase no está en la carpeta de su paquete Java.')
                root=root.parent
            return [self.features.runtimes.executable('java'),'-cp',str(root),name.replace('/','.'),*args]
        if suffix=='.jar' and magic.startswith(b'PK'):return [self.features.runtimes.executable('java'),'-jar',str(file),*args]
        raise ValueError('Este formato contiene datos o necesita un programa anfitrión. Ejecutar admite PE de Windows, ELF en Linux y clases/JAR de Java.')
    def build(self,body):
        ws,path,file=self.scope(body.get('path'));source=body.get('source');original=self.key(file)
        self.assert_revision(file,body.get('revision'));source_file=ws.resolve(source)
        if source_file==file:raise ValueError('El origen debe ser código fuente, no el propio binario.')
        with self.lock:
            for ident,item in self.builds.items():
                job=self.features.app.runner.jobs.get(ident)
                if item['file']==file and job and not job.done:raise ValueError('Este binario ya se está recompilando.')
            from .runtimes import language
            lang=language(source);suffix=file.suffix.lower()
            if lang not in ('c','cpp','asm','rust','go','java','nc'):raise ValueError('Elige código C, C++, ASM, Rust, Go, Java o nC.')
            if suffix in ('.class','.jar') and lang!='java':raise ValueError('Una clase o JAR se recompila desde Java.')
            if suffix not in ('.class','.jar') and lang=='java':raise ValueError('Para Java el destino debe ser una clase o JAR.')
            plan=self.features.runtimes.plan(ws,source,debug=lang=='nc');commands=plan['commands'] if lang=='nc' else plan['commands'][:-1]
            if not commands:raise ValueError('El perfil no ofrece una compilación separada de la ejecución.')
            artifact=Path(plan['target']);previous=artifact if lang=='java' else artifact.parent;folder=ws.private_dir('binary-build')/uuid.uuid4().hex;folder.mkdir()
            commands=[[str(folder/Path(arg).relative_to(previous)) if isinstance(arg,str) and Path(arg).is_absolute() and Path(arg).is_relative_to(previous) else arg for arg in command] for command in commands]
            artifact=folder if lang=='java' else folder/artifact.name
            if lang=='java':
                package=re.search(r'^\s*package\s+([\w.]+)\s*;',source_file.read_text(encoding='utf-8-sig'),re.M);qualified=(package.group(1)+'.' if package else '')+source_file.stem
                if suffix=='.jar':
                    jar=Path(self.features.runtimes.executable('java')).with_name('jar.exe' if os.name=='nt' else 'jar')
                    if not jar.is_file():raise ValueError('El JDK necesita su herramienta jar para generar este archivo.')
                    output=artifact.with_suffix('.jar');commands.append([str(jar),'--create','--file',str(output),'--main-class',qualified,'-C',str(artifact),'.']);artifact=output
                else:artifact=artifact/Path(*qualified.split('.')[:-1])/file.name
            elif suffix in ('.o','.obj','.dll','.so','.dylib'):
                if lang not in ('c','cpp'):raise ValueError('Los objetos y bibliotecas de esta acción usan C o C++.')
                command=commands[-1];artifact=artifact.with_suffix(suffix);command[command.index('-o')+1]=str(artifact)
                command.insert(1,'-c' if suffix in ('.o','.obj') else '-dynamiclib' if suffix=='.dylib' else '-shared')
                if suffix in ('.so','.dylib'):command.insert(1,'-fPIC')
            result=self.features.app.runner.start(commands,ws.root,timeout=120)
            self.builds[result['job']]={'file':file,'workspace':ws,'path':body['path'],'revision':body['revision'],'artifact':artifact,'origin':self.features.app.workspace.root}
            self.sources[original]=source;atomic_json(self.settings,self.sources);return result
    def finish(self,body):
        self.features._trusted();identity=body.get('job');item=self.builds.get(identity);job=self.features.app.runner.jobs.get(identity)
        if not item or not job:raise ValueError('Compilación binaria no encontrada.')
        if not job.done:raise ValueError('La compilación sigue en curso.')
        if item['origin']!=self.features.app.workspace.root:raise PermissionError('El proyecto cambió.')
        if job.code!=0:raise ValueError('La compilación falló. El binario anterior sigue intacto.')
        artifact=item['artifact']
        if not artifact.is_file() or artifact.stat().st_size>MAX_EDIT_SIZE:raise ValueError('No se generó un artefacto válido para este destino.')
        def write(output):
            with artifact.open('rb') as source:shutil.copyfileobj(source,output,1_048_576)
        result=self.replace(item['workspace'],item['file'],item['revision'],write);del self.builds[identity]
        return {**read_binary(item['file'],item['path']),**result,'saved':True}
