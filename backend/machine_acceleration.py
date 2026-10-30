"""On-demand QEMU accelerator detection without a guest disk or guest OS."""
from functools import lru_cache
import json,os,platform,socket,subprocess,tempfile,time,threading
from pathlib import Path

FLAGS=0x08000000 if os.name=='nt' else 0
DETECTION_LOCK=threading.RLock()

def cpu_arguments(accelerator):
    # WHPX uses the hypervisor's CPU. Forcing TCG's synthetic max model can
    # fail in firmware with Unexpected VP exit code 4 on supported hosts.
    return [] if accelerator=='whpx' else ['-cpu','host' if accelerator in ('kvm','hvf') else 'max']

def qmp_status(connection):
    connection.settimeout(1)
    with connection.makefile('rb') as stream:
        greeting=json.loads(stream.readline(65536))
        if 'QMP' not in greeting:raise ValueError('QEMU no confirmó el protocolo de control.')
        status=None
        for name in ('qmp_capabilities','cont','query-status','quit'):
            # Initialization alone misses WHPX failures in firmware. Exercise only
            # the supplied BIOS, with no disk, NIC, guest OS or user program.
            if name=='query-status':time.sleep(.8)
            connection.sendall((json.dumps({'execute':name,'id':name})+'\n').encode())
            for _ in range(16):
                response=json.loads(stream.readline(65536))
                if response.get('id')==name:
                    if 'error' in response:raise ValueError(str(response['error'])[:400])
                    if name=='query-status':status=response.get('return')
                    break
            else:raise ValueError('QEMU no confirmó la orden de control.')
        return status

def probe(qemu,accelerator):
    # TCP QMP also works with Windows GUI-subsystem builds whose stdio is absent.
    with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    argv=[qemu,'-machine','q35,hpet=off','-accel',accelerator,*cpu_arguments(accelerator),'-m','64','-nodefaults','-nic','none','-display','none','-serial','none','-monitor','none','-qmp',f'tcp:127.0.0.1:{port},server=on,wait=off','-S']
    process=None
    with tempfile.TemporaryFile() as errors:
        try:
            process=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=errors,creationflags=FLAGS)
            deadline=time.monotonic()+5;status=None
            while process.poll() is None and time.monotonic()<deadline:
                try:connection=socket.create_connection(('127.0.0.1',port),timeout=.15)
                except OSError:time.sleep(.05);continue
                with connection:status=qmp_status(connection)
                break
            ready=isinstance(status,dict) and status.get('status')=='running' and status.get('running') is True
            if ready:process.wait(timeout=2)
            errors.seek(0);reason=errors.read(4096).decode('utf-8','replace')[-600:]
            return {'name':accelerator,'available':ready,'reason':'' if ready else reason or 'QEMU no confirmó la ejecución del firmware.'}
        except (OSError,ValueError,subprocess.TimeoutExpired) as error:
            errors.seek(0);detail=errors.read(4096).decode('utf-8','replace')[-600:]
            return {'name':accelerator,'available':False,'reason':detail or str(error)[:600]}
        finally:
            if process and process.poll() is None:process.kill();process.wait(timeout=3)

@lru_cache(maxsize=8)
def _detect(qemu,modified,size,system,machine,epoch):
    started=time.perf_counter()
    try:
        result=subprocess.run([qemu,'-accel','help'],capture_output=True,timeout=5,creationflags=FLAGS)
        supported=[line.strip() for line in result.stdout.decode('utf-8','replace').splitlines() if line.strip() in ('tcg','whpx','kvm','hvf')]
    except (OSError,subprocess.TimeoutExpired):supported=[]
    preferred='tcg';checks=[]
    hardware={'Windows':'whpx','Linux':'kvm','Darwin':'hvf'}.get(system)
    if hardware in supported and machine.lower() in ('amd64','x86_64','x64'):
        check=probe(qemu,hardware);checks.append(check)
        if check['available']:preferred=hardware
    return {'preferred':preferred,'supported':supported,'hardware':checks,'checkedAt':time.time(),'durationMs':round((time.perf_counter()-started)*1000,3),
            'cpuPolicy':'CPU del hipervisor' if preferred=='whpx' else 'CPU del anfitrión' if preferred in ('kvm','hvf') else 'CPU emulada max',
            'scope':'Inicialización y prueba breve del firmware por QMP, sin disco, SO invitado ni programa del usuario. No certifica el arranque de todos los invitados. Resultado reutilizado hasta 60 segundos.'}

def detect(qemu):
    if not qemu:return {'preferred':'tcg','supported':[],'hardware':[],'scope':'QEMU no está instalado.'}
    try:stat=Path(qemu).stat()
    except OSError:return {'preferred':'tcg','supported':[],'hardware':[],'scope':'No se puede consultar el ejecutable QEMU.'}
    # Host access can change without replacing QEMU; don't cache forever.
    with DETECTION_LOCK:
        hits=_detect.cache_info().hits
        result=_detect(str(qemu),stat.st_mtime_ns,stat.st_size,platform.system(),platform.machine(),int(time.monotonic()//60))
        return {**result,'cached':_detect.cache_info().hits>hits,'cacheAgeMs':round(max(0,time.time()-result['checkedAt'])*1000,2)}
