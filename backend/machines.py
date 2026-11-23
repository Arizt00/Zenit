"""Persistent headless machines and SSH consoles; never invents a guest OS."""
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import threading
import time
import uuid
import hashlib
from .foundation import inventory
from .preferences import atomic_json
from .runtime_paths import find_tool
from .terminals import child_environment

class Machines:
    def __init__(self,features):
        self.features=features;self.root=features.prefs.directory/'machines';self.root.mkdir(exist_ok=True)
        self.index=self.root/'profiles.json';self.lock=threading.RLock();self.active={}
        self.boots={};self.metrics_root=self.root/'performance'
        try:self.profiles=json.loads(self.index.read_text(encoding='utf-8'))
        except (ValueError,OSError):self.profiles=[]
        self.base_index=self.root/'vm-base.json'
        try:self.base_root=json.loads(self.base_index.read_text(encoding='utf-8')).get('directory')
        except (ValueError,OSError):self.base_root=None
    def vm_base(self,directory=None):
        root,data=inventory()
        if directory or self.base_root:
            candidate=Path(directory or self.base_root).resolve()
            try:data=json.loads((candidate/'tool-index.json').read_text(encoding='utf-8'));root=candidate
            except (OSError,ValueError):
                if directory:raise
        tools=self.features.runtimes.config.get('tools',{})
        if not root:return {'qemu':find_tool('qemu-system-x86_64',tools),'qimg':find_tool('qemu-img',tools),'image':None,'directory':None}
        def file(relative):
            if not isinstance(relative,str):return None
            path=(root/relative).resolve()
            return str(path) if path.is_relative_to(root) and path.is_file() else None
        arch=next((x for x in data.get('components',[]) if x.get('id')=='arch'),{})
        image=file(arch.get('file'));image_root=root
        if not image and not directory and not self.base_root:
            # Optional image and QEMU components may be installed in either order.
            from .foundation import roots,read_index
            for candidate in roots():
                try:
                    candidate=candidate.resolve();index=read_index(candidate);resource=next((c for c in index.get('components',[]) if c.get('id')=='arch'),{}).get('file')
                    if not isinstance(resource,str):continue
                    target=(candidate/resource).resolve()
                    if target.is_relative_to(candidate) and target.is_file():image=str(target);image_root=candidate;break
                except (OSError,ValueError):continue
        return {'qemu':file(data.get('tools',{}).get('qemu-system-x86_64')) or find_tool('qemu-system-x86_64',tools),
                'qimg':file(data.get('tools',{}).get('qemu-img')) or find_tool('qemu-img',tools),
                'image':image,'directory':str(image_root)}
    def configure_base(self,directory):
        if not isinstance(directory,str) or not Path(directory).is_absolute():raise ValueError('Choose an absolute prepared SDK folder.')
        base=self.vm_base(directory)
        if not all(base[k] for k in ('qemu','qimg','image')):raise ValueError('This SDK needs QEMU, qemu-img and the Arch base image in tool-index.json.')
        atomic_json(self.base_index,{'directory':base['directory']});self.base_root=base['directory']
        return self.snapshot()
    def snapshot(self):
        try:base=self.vm_base()
        except (OSError,ValueError):base={'qemu':None,'qimg':None,'image':None,'directory':self.base_root}
        return {'profiles':self.profiles,'active':self.active,'qemu':base['qemu'],
                'archImage':base['image'],'baseDirectory':base['directory'],
                'templates':[{'id':'arch','name':'Arch Linux','mode':'Local · consola serie','available':bool(base['image'] and base['qemu'] and base['qimg'])},
                             {'id':'macos','name':'macOS','mode':'SSH a una máquina Mac','available':False,'note':'La virtualización macOS requiere hardware Apple; conecta un Mac o su VM por SSH.'},
                             {'id':'windows7','name':'Windows 7','mode':'SSH a una VM existente','available':False,'note':'Requiere una imagen con licencia y un servidor SSH configurado en la máquina.'}]}
    def create_arch(self, *, directory=None, identity=None, name="Arch Linux", persistent=True):
        with self.lock:
            existing=next((p for p in self.profiles if p['type']=='arch' and p.get('mode')!='ssh'),None)
            if existing and persistent:return self.snapshot()
            base=self.vm_base();image=base['image'];qimg=base['qimg']
            if not image or not Path(image).is_file() or not qimg:raise ValueError('La base de Zénit debe incluir QEMU y la imagen oficial de Arch.')
            directory=Path(directory) if directory is not None else self.root/'arch';directory.mkdir(parents=True,exist_ok=True);disk=directory/'disk.qcow2'
            if disk.exists():raise ValueError('Ya hay un disco Arch sin perfil; se conserva. Revisa la carpeta de máquinas.')
            result=subprocess.run([qimg,'create','-f','qcow2','-F','qcow2','-b',image,str(disk),'16G'],capture_output=True,timeout=30,
                                  env=child_environment(),creationflags=0x08000000 if os.name=='nt' else 0)
            if result.returncode:raise ValueError(result.stderr.decode('utf-8','replace'))
            # A NoCloud seed enables a local serial console. No shared host dirs,
            # remote password, fixed credential, SSH forwarding or exposed ports.
            seed=directory/'seed.iso'
            cloud='''#cloud-config
hostname: zenit-arch
locale: C.UTF-8
package_update: false
package_upgrade: false
users:
  - name: zenit
    groups: [wheel]
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL
    lock_passwd: true
ssh_pwauth: false
ssh_genkeytypes: [ed25519]
write_files:
  - path: /etc/systemd/system/serial-getty@ttyS0.service.d/autologin.conf
    content: |
      [Service]
      ExecStart=
      ExecStart=-/sbin/agetty --autologin zenit --noclear %I 115200 vt220
runcmd:
  - [systemctl, daemon-reload]
  - [systemctl, --no-block, restart, serial-getty@ttyS0.service]
'''
            network='''version: 2
ethernets:
  eth0:
    match:
      macaddress: "52:54:00:12:34:56"
    set-name: eth0
    addresses: [10.0.2.15/24]
    routes:
      - to: default
        via: 10.0.2.2
    nameservers:
      addresses: [10.0.2.3]
'''
            from .foundation import python_command
            worker=Path(__file__).resolve().parents[1]/'tools/machine_seed.py'
            result=subprocess.run([*python_command(),str(worker),str(seed)],input=json.dumps({'user-data':cloud,'meta-data':'instance-id: zenit-arch-1\nlocal-hostname: zenit-arch\n','network-config':network}).encode('utf-8'),
                                  capture_output=True,timeout=20,env=child_environment(),creationflags=0x08000000 if os.name=='nt' else 0)
            if result.returncode:
                raise ValueError('No se pudo preparar el arranque Arch. El runtime del SDK necesita pycdlib. '+result.stderr.decode('utf-8','replace')[-1000:])
            profile={'id':identity or uuid.uuid4().hex,'name':name,'type':'arch','disk':str(disk),'seed':str(seed),'memory':2048,'cpus':1}
            if not persistent:return profile
            candidate=[*self.profiles,profile];atomic_json(self.index,candidate);self.profiles=candidate
            return self.snapshot()
    def save_ssh(self,body):
        if len(self.profiles)>=12:raise ValueError('El laboratorio admite hasta 12 máquinas.')
        host=body.get('host','');user=body.get('user','');kind=body.get('type')
        if kind not in ('macos','windows7','windows11','arch','linux','kali','debian'):raise ValueError('Sistema desconocido.')
        if not isinstance(host,str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9.:-]{0,252}',host):raise ValueError('Dirección SSH no válida.')
        if not isinstance(user,str) or not re.fullmatch(r'[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,63}',user):raise ValueError('Usuario SSH no válido.')
        port=body.get('port',22)
        if type(port) is not int or not 1<=port<=65535:raise ValueError('Puerto SSH no válido.')
        profile={'id':uuid.uuid4().hex,'type':kind,'mode':'ssh','name':str(body.get('name',kind))[:60],'host':host,'user':user,'port':port}
        with self.lock:
            candidate=[*self.profiles,profile];atomic_json(self.index,candidate);self.profiles=candidate
        return self.snapshot()
    def readiness(self,profile):
        """Cheap explicit health checks; never boot or fetch a guest image."""
        if profile.get('mode')=='ssh':return {'ready':bool(find_tool('ssh')),'checks':[{'name':'OpenSSH','ok':bool(find_tool('ssh'))}]}
        checks=[];base=self.vm_base()
        checks.append({'name':'QEMU','ok':bool(base.get('qemu'))})
        for key,label in [('disk','Disco de la sesión'),('seed','Medio de arranque')]:
            value=profile.get(key)
            if value:checks.append({'name':label,'ok':Path(value).is_file() and not Path(value).is_symlink()})
            elif key=='disk':checks.append({'name':label,'ok':False})
        import psutil,shutil
        available=int(psutil.virtual_memory().available/1024**2)
        registry={p['id']:p for p in self.profiles}
        registry.update(getattr(getattr(self.features,'machine_images',None),'sessions',{}))
        registry.update({key:session.get('profile',{}) for key,session in getattr(getattr(self.features,'tern',None),'sessions',{}).items() if session.get('kind')=='arch'})
        reserved_memory=reserved_cpus=0
        for identity,terminal_id in list(self.active.items()):
            terminal=self.features.terminals.sessions.get(terminal_id);other=registry.get(identity,{})
            if identity==profile.get('id') or not terminal or terminal.closed or other.get('mode')=='ssh':continue
            reserved_memory+=other.get('memory',2048);reserved_cpus+=other.get('cpus',1)
        checks.append({'name':'RAM disponible y reservada por otras máquinas','ok':profile.get('memory',2048)+reserved_memory<=available*.8})
        checks.append({'name':'Presupuesto de CPU de las máquinas','ok':profile.get('cpus',1)+reserved_cpus<=(os.cpu_count() or 1)})
        disk=Path(profile.get('disk') or self.root);parent=disk.parent
        free=shutil.disk_usage(parent if parent.exists() else self.root).free
        checks.append({'name':'Espacio libre para el disco','ok':free>=64*1024**2})
        from .machine_acceleration import detect
        acceleration=detect(base.get('qemu'))
        checks.append({'name':'Aceleración · '+acceleration['preferred'].upper()+(' · software' if acceleration['preferred']=='tcg' else ' · inicialización comprobada'),'ok':bool(base.get('qemu'))})
        return {'ready':all(c['ok'] for c in checks),'checks':checks,'availableMemoryMiB':available,'freeDiskBytes':free,'reservedMemoryMiB':reserved_memory,'reservedCpus':reserved_cpus,'acceleration':acceleration}
    def start(self,ws,key,profile=None):
        if not ws.trusted:raise PermissionError('Autoriza el proyecto antes de abrir su consola.')
        with self.lock:
            profile=profile or next((x for x in self.profiles if x['id']==key),None)
            if not profile:raise ValueError('Máquina desconocida.')
            old=self.active.get(key);session=self.features.terminals.sessions.get(old)
            if session and not session.closed:return {'id':session.id,'profile':session.profile,'kind':session.kind}
            from .startup_metrics import StartupMetrics
            trace=StartupMetrics();record={'id':key,'name':profile['name'],'startedAt':time.time(),'trace':trace,'kind':profile.get('mode','qemu')};self.boots[key]=record
            while len(self.boots)>16:self.boots.pop(next(iter(self.boots)))
            if profile.get('mode')=='ssh':
                ssh=find_tool('ssh')
                if not ssh:raise ValueError('Instala OpenSSH para conectar esta máquina.')
                # SSH retains host-key verification and prompts in the real PTY.
                argv=[ssh,'-tt','-p',str(profile['port']),'-l',profile['user'],profile['host']]
            else:
                with trace.phase('machine-preflight'):health=self.readiness(profile)
                record['acceleration']=health.get('acceleration');record['memoryMiB']=profile.get('memory');record['cpus']=profile.get('cpus')
                if not health['ready']:raise ValueError('Revisa la máquina: '+', '.join(c['name'] for c in health['checks'] if not c['ok']))
                qemu=self.vm_base()['qemu']
                if not qemu:raise ValueError('Prepara QEMU en la base de Zénit.')
                with socket.socket() as probe:
                    probe.bind(('127.0.0.1',0));control_port=probe.getsockname()[1]
                from .machine_acceleration import cpu_arguments
                cache='writeback' if profile.get('type')=='arch' else 'writethrough'
                record['diskCache']=cache
                argv=[qemu,'-machine','q35,hpet=off','-accel',health['acceleration']['preferred'],*cpu_arguments(health['acceleration']['preferred']),'-m',str(profile['memory']),'-smp',str(profile['cpus']),'-display','none',
                      '-smbios','type=1,serial=ds=nocloud',
                      '-serial','--serial-placeholder','-monitor','none','-qmp',f'tcp:127.0.0.1:{control_port},server=on,wait=off',
                      '-drive','file='+profile['disk'].replace(',',',,')+',format=qcow2,if='+('ide' if profile.get('system','').startswith('windows') else 'virtio')+',cache='+cache,
                      *(['-drive','file='+profile['seed'].replace(',',',,')+',format=raw,media=cdrom,readonly=on','-boot','once=d'] if profile.get('seed') else []),
                      '-netdev','user,id=net0','-device',('e1000' if profile.get('system','').startswith('windows') else 'virtio-net-pci')+',netdev=net0,mac=52:54:00:12:34:56']
                if not profile.get('system','').startswith('windows'):
                    argv+=['-object','rng-builtin,id=zenit-rng','-device','virtio-rng-pci,rng=zenit-rng,max-bytes=1024,period=1000']
                if profile.get('display')=='graphic':
                    # QEMU selects an available native graphical backend. The
                    # programmer explicitly requested a separate guest window.
                    index=argv.index('-display');del argv[index:index+2]
                from .foundation import python_command
                worker=Path(__file__).resolve().parents[1]/'tools/machine_console.py'
                self.metrics_root.mkdir(parents=True,exist_ok=True)
                metrics=self.metrics_root/(hashlib.sha256(str(key).encode()).hexdigest()+'.json');metrics.unlink(missing_ok=True);record['metricsFile']=metrics
                argv=[*python_command(),str(worker),'--metrics',str(metrics),'--launch-clock',str(trace.started),*argv]
            # VM CPU/RAM reservations belong to readiness(). Generic tool
            # budgets may kill a process tree and must not own guest disks.
            with trace.phase('terminal-launch'):result=self.features.hacker._terminal(argv,profile['name']+' · consola',ws.root,managed=False)
            if profile.get('mode')!='ssh':
                session=self.features.terminals.sessions[result['id']]
                session.before_close=lambda:self.poweroff(control_port,session)
            self.active[key]=result['id'];return result

    def performance(self):
        records=[]
        for record in list(self.boots.values()):
            row={k:v for k,v in record.items() if k not in ('trace','metricsFile')};row['phases']=record['trace'].snapshot()['phases'];file=record.get('metricsFile')
            if file and file.is_file() and not file.is_symlink() and file.stat().st_size<32000:
                try:row['guest']=json.loads(file.read_text(encoding='utf-8'))
                except (OSError,ValueError):row['guest']={'state':'unavailable'}
            terminal=self.features.terminals.sessions.get(self.active.get(record['id']));row['terminalClosed']=terminal.closed if terminal else True;records.append(row)
        return records
    @staticmethod
    def poweroff(port,session):
        """ACPI shutdown, then QMP quit if needed: do not kill a writing qcow2."""
        finished=lambda:session.closed or session.has_exited()
        if finished():return
        deadline=time.monotonic()+5;control=None
        while time.monotonic()<deadline and not finished():
            try:control=socket.create_connection(('127.0.0.1',port),timeout=2);break
            except OSError:time.sleep(.1)
        if control is None:
            if finished():return
            raise ValueError('La máquina todavía no ofrece su canal de apagado. Intenta detenerla de nuevo.')
        with control:
            control.settimeout(3)
            with control.makefile('rb') as stream:
                def command(name):
                    control.sendall((json.dumps({'execute':name})+'\n').encode())
                    while line:=stream.readline(65536):
                        result=json.loads(line)
                        if 'error' in result:raise ValueError(str(result['error']))
                        if 'return' in result:return
                greeting=json.loads(stream.readline(65536))
                if 'QMP' not in greeting:raise ValueError('Canal de control QEMU no válido.')
                command('qmp_capabilities');command('system_powerdown')
                deadline=time.monotonic()+30
                while not finished() and time.monotonic()<deadline:time.sleep(.1)
                if not finished():
                    session._append('\r\nLa máquina no respondió al apagado ACPI; QEMU vaciará y cerrará su disco.\r\n')
                    command('quit')
                    deadline=time.monotonic()+5
                    while not finished() and time.monotonic()<deadline:time.sleep(.1)
                    if not finished():raise ValueError('QEMU no ha terminado de cerrar el disco. No se forzará el cierre; vuelve a detener la máquina.')
    def stop(self,key):
        terminal=self.active.get(key)
        if terminal:
            session=self.features.terminals.sessions.get(terminal)
            if session:session.close()
            self.active.pop(key,None)
        return self.snapshot()
