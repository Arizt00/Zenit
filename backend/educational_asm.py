"""Real RARS/MARS CLI adapters; guest instructions stay in their CPU engines."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
from .runtime_paths import find_tool
from .terminals import child_environment

ENGINES={
    'rars':{'label':'RARS · RISC-V educativo','architectures':('riscv32','riscv64'),'step':True},
    'mars':{'label':'MARS · MIPS educativo','architectures':('mips',),'step':False},
}
RARS_EXAMPLE='.data\nmessage: .asciz "RARS: 7 + 5 = "\n.text\n.globl main\nmain:\nla a0, message\nli a7, 4\necall\nli t0, 7\naddi a0, t0, 5\nli a7, 1\necall\nli a7, 10\necall\n'
MARS_EXAMPLE='.data\nmessage: .asciiz "MARS: 7 + 5 = "\n.text\n.globl main\nmain:\nla $a0, message\nli $v0, 4\nsyscall\nli $t0, 7\naddiu $a0, $t0, 5\nli $v0, 1\nsyscall\nli $v0, 10\nsyscall\n'
ENGINES['rars']['examples']={a:[{'label':'Consola educativa · 7 + 5','source':RARS_EXAMPLE}] for a in ('riscv32','riscv64')}
ENGINES['mars']['examples']={'mips':[{'label':'Consola educativa · 7 + 5','source':MARS_EXAMPLE}]}

def engine_path(engine):
    root=Path(__file__).resolve().parents[1]/'tools/simulators'
    data=json.loads((root/'SOURCE.json').read_text(encoding='utf-8'))[engine]
    path=root/data['file']
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=data['sha256']:
        raise ValueError('El motor '+engine.upper()+' no coincide con el paquete verificado. Reinstala esta versión de Zénit.')
    return path

def bounded_run(argv,stdin,cwd):
    with tempfile.TemporaryFile() as input_file:
        input_file.write(stdin.encode('utf-8'));input_file.seek(0)
        process=subprocess.Popen(argv,stdin=input_file,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=cwd,env=child_environment(),creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        parts=[[],[]];size=0;lock=threading.Lock();overflow=threading.Event()
        def read(stream,index):
            nonlocal size
            try:
                while chunk:=stream.read(8192):
                    with lock:
                        size+=len(chunk)
                        if size>2000000:
                            overflow.set()
                            if process.poll() is None:process.kill()
                            break
                        parts[index].append(chunk)
            finally:stream.close()
        readers=[threading.Thread(target=read,args=(stream,i),daemon=True) for i,stream in enumerate((process.stdout,process.stderr))]
        for thread in readers:thread.start()
        try:process.wait(timeout=12)
        except subprocess.TimeoutExpired:
            process.kill();process.wait(timeout=3);raise ValueError('La simulación superó 12 segundos. Reduce las instrucciones o revisa la entrada.') from None
        finally:
            for thread in readers:thread.join(timeout=3)
        if overflow.is_set():raise ValueError('La salida simulada supera 2 MB; el motor se ha detenido.')
        return process.returncode,*[b''.join(chunks).decode('utf-8','replace') for chunks in parts]

def simulate(body,ws):
    engine=body['engine'];info=ENGINES[engine];architecture=body.get('architecture')
    if architecture not in info['architectures']:raise ValueError('El motor no admite esta arquitectura.')
    steps=body.get('steps',10000)
    if type(steps) is not int or not (1 if info['step'] else 32)<=steps<=10000:raise ValueError('Límite de instrucciones no válido para este motor.')
    java=find_tool('java')
    if not java:raise ValueError('Prepara Java para utilizar RARS o MARS. Los motores de CPU están incluidos en Zénit.')
    source=body['source'];stdin=body.get('stdin','')
    if not isinstance(stdin,str) or len(stdin.encode())>65536:raise ValueError('La entrada simulada admite hasta 64 KiB.')
    registers=['a0','a1','a7','sp','t0','t1','t2','s0','s1','ra'] if engine=='rars' else ['$v0','$v1','$a0','$a1','$sp','$t0','$t1','$t2','$s0','$s1','$ra']
    with tempfile.TemporaryDirectory(prefix='zenit-educational-asm-') as temporary:
        root=Path(temporary);name=body.get('path') or 'buffer.asm'
        if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Usa un archivo del proyecto en el laboratorio.')
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(source,encoding='utf-8')
        # Includes mirror only files explicitly referenced by the source. The
        # entire project, dependencies and credentials are never copied here.
        pending=[(name,source)];seen={Path(name).as_posix()};total=0
        while pending:
            current,text=pending.pop()
            for match in re.finditer(r'^\s*\.include\s+"([^"\r\n]+)"',text,re.M):
                relative=Path(current).parent/match.group(1)
                file=ws.resolve(relative.as_posix());relative=file.relative_to(ws.root)
                if relative.as_posix() in seen:continue
                seen.add(relative.as_posix())
                if len(seen)>32 or file.stat().st_size>131072:raise ValueError('Las dependencias de simulación superan su presupuesto de memoria.')
                with file.open('rb') as stream:raw=stream.read(131073)
                total+=len(raw)
                if len(raw)>131072 or total>2000000:raise ValueError('Las dependencias de simulación superan su presupuesto de memoria.')
                copied=root/relative;copied.parent.mkdir(parents=True,exist_ok=True);copied.write_bytes(raw);pending.append((relative.as_posix(),raw.decode('utf-8-sig')))
        argv=[java,'-Xmx128m','-Djava.awt.headless=true','-jar',str(engine_path(engine)),'nc','me','sm','ic','ae2','se3']
        if architecture=='riscv64':argv.append('rv64')
        argv.extend([str(steps),*registers,str(target)])
        code,output,diagnostic=bounded_run(argv,stdin,target.parent);diagnostic=diagnostic.replace(str(root),'<búfer>')
        if code:return {'status':'error','error':diagnostic[:12000],'output':output[:65536]}
        values=dict(re.findall(r'(?m)^(\$?\w+)\s+(0x[0-9a-fA-F]+)\s*$',diagnostic))
        counts=re.findall(r'(?m)^\s*(\d+)\s*$',diagnostic)
        return {'engine':engine,'architecture':architecture,'status':'paused' if 'maximum step limit' in diagnostic else 'complete','executed':int(counts[-1]) if counts else None,'pc':None,'registers':values,'instructions':[],'memory':'','output':output[:65536],'diagnostic':diagnostic[:12000],'error':'','note':'CPU simulada por '+info['label']+'. Los servicios educativos del motor pueden usar archivos; no es un aislamiento de seguridad. PC y traza de instrucciones no están publicados por este adaptador CLI.'}
