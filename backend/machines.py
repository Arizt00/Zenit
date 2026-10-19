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
from .foundation import inventory
from .preferences import atomic_json
from .runtime_paths import find_tool
from .terminals import child_environment

class Machines:
    def __init__(self,features):
        self.features=features;self.root=features.prefs.directory/'machines';self.root.mkdir(exist_ok=True)
        self.index=self.root/'profiles.json';self.lock=threading.RLock();self.active={}
        try:self.profiles=json.loads(self.index.read_text(encoding='utf-8'))
        except (ValueError,OSError):self.profiles=[]
        self.base_index=self.root/'vm-base.json'
        try:self.base_root=json.loads(self.base_index.read_text(encoding='utf-8')).get('directory')
        except (ValueError,OSError):self.base_root=None
    def vm_base(self,directory=None):
        root,data=inventory()
        if directory or self.base_root:
            root=Path(directory or self.base_root).resolve()
            data=json.loads((root/'tool-index.json').read_text(encoding='utf-8'))
        if not root:return {'qemu':None,'qimg':None,'image':None,'directory':None}
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
        return {'qemu':file(data.get('tools',{}).get('qemu-system-x86_64')) or find_tool('qemu-system-x86_64'),
                'qimg':file(data.get('tools',{}).get('qemu-img')) or find_tool('qemu-img'),
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
    def start(self,ws,key,profile=None):
        if not ws.trusted:raise PermissionError('Autoriza el proyecto antes de abrir su consola.')
        with self.lock:
            profile=profile or next((x for x in self.profiles if x['id']==key),None)
            if not profile:raise ValueError('Máquina desconocida.')
            old=self.active.get(key);session=self.features.terminals.sessions.get(old)
            if session and not session.closed:return {'id':session.id,'profile':session.profile,'kind':session.kind}
            if profile.get('mode')=='ssh':
                ssh=find_tool('ssh')
                if not ssh:raise ValueError('Instala OpenSSH para conectar esta máquina.')
                # SSH retains host-key verification and prompts in the real PTY.
                argv=[ssh,'-tt','-p',str(profile['port']),'-l',profile['user'],profile['host']]
            else:
                qemu=self.vm_base()['qemu']
                if not qemu:raise ValueError('Prepara QEMU en la base de Zénit.')
                with socket.socket() as probe:
                    probe.bind(('127.0.0.1',0));control_port=probe.getsockname()[1]
                argv=[qemu,'-machine','q35,hpet=off','-accel','tcg','-cpu','max','-m',str(profile['memory']),'-smp',str(profile['cpus']),'-display','none',
                      '-smbios','type=1,serial=ds=nocloud',
                      '-serial','--serial-placeholder','-monitor','none','-qmp',f'tcp:127.0.0.1:{control_port},server=on,wait=off',
                      '-drive','file='+profile['disk'].replace(',',',,')+',format=qcow2,if='+('ide' if profile.get('system','').startswith('windows') else 'virtio')+',cache=writethrough',
                      *(['-drive','file='+profile['seed'].replace(',',',,')+',format=raw,media=cdrom,readonly=on','-boot','once=d'] if profile.get('seed') else []),
                      '-netdev','user,id=net0','-device',('e1000' if profile.get('system','').startswith('windows') else 'virtio-net-pci')+',netdev=net0,mac=52:54:00:12:34:56']
                if profile.get('display')=='graphic':
                    # QEMU selects an available native graphical backend. The
                    # programmer explicitly requested a separate guest window.
                    index=argv.index('-display');del argv[index:index+2]
                from .foundation import python_command
                worker=Path(__file__).resolve().parents[1]/'tools/machine_console.py'
                argv=[*python_command(),str(worker),*argv]
            result=self.features.hacker._terminal(argv,profile['name']+' · consola',ws.root)
            if profile.get('mode')!='ssh':
                session=self.features.terminals.sessions[result['id']]
                session.before_close=lambda:self.poweroff(control_port,session)
            self.active[key]=result['id'];return result
    @staticmethod
    def poweroff(port,session):
        """ACPI shutdown, then QMP quit if needed: do not kill a writing qcow2."""
        if session.closed:return
        deadline=time.monotonic()+5;control=None
        while time.monotonic()<deadline and not session.closed:
            try:control=socket.create_connection(('127.0.0.1',port),timeout=2);break
            except OSError:time.sleep(.1)
        if control is None:
            if session.closed:return
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
                while not session.closed and time.monotonic()<deadline:time.sleep(.1)
                if not session.closed:
                    session._append('\r\nLa máquina no respondió al apagado ACPI; QEMU vaciará y cerrará su disco.\r\n')
                    command('quit')
                    deadline=time.monotonic()+5
                    while not session.closed and time.monotonic()<deadline:time.sleep(.1)
    def stop(self,key):
        terminal=self.active.get(key)
        if terminal:
            session=self.features.terminals.sessions.get(terminal)
            if session:session.close()
            self.active.pop(key,None)
        return self.snapshot()
