"""Session-scoped HTTPS transport, prepared by Hilo without a system service."""
import hashlib
import os
from pathlib import Path
import platform
import re
import subprocess
import tempfile
import threading
import time
from urllib.request import Request,build_opener,ProxyHandler

VERSION='2026.10.1'
# Checksums published by cloudflare/cloudflared for this exact release.
ASSETS={
    ('Windows','AMD64'):('cloudflared-windows-amd64.exe','4d2490e74082c5d48dbfedaf92576fa5bd1702379ab88eb7faa0cfbe8dc891b6'),
    ('Linux','x86_64'):('cloudflared-linux-amd64','3bfc539f45d2620c71debb7a86be0efa737ed5ccbad9eb85c787116900e5c586'),
    ('Linux','aarch64'):('cloudflared-linux-arm64','2c65dfabf616c40efc7545d107d7a57ad5e21377e2964b7e88af19a238074a46'),
}


def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):value.update(chunk)
    return value.hexdigest()


class InternetTunnel:
    def __init__(self,features,local):
        self.features=features;self.local=local;self.lock=threading.RLock();self.cancelled=threading.Event()
        self.process=None;self.reader=None;self.endpoint=None;self.phase='preparing';self.error=None;self.tail=''
        self.directory=features.prefs.directory/'tools/coco'/VERSION

    def status(self):
        with self.lock:
            if self.phase=='ready' and self.process and self.process.poll() is not None:
                self.phase='failed';self.error='La conexión de Internet terminó. Puedes reintentarla sin perder el búfer compartido.'
            return {'kind':'internet','phase':self.phase,'provider':'Cloudflare · temporal','endpoint':self.endpoint if self.phase=='ready' else None,'error':self.error}

    def prepare(self,event):
        if event.is_set() or self.cancelled.is_set():raise ValueError('Conexión cancelada.')
        asset=ASSETS.get((platform.system(),platform.machine()))
        if not asset:raise ValueError('La conexión automática de Internet está disponible en Windows x64 y Linux x64/ARM64. En este equipo puedes usar una red privada entre estaciones.')
        name,expected=asset;self.directory.mkdir(parents=True,exist_ok=True)
        target=self.directory/name
        if target.is_symlink():raise ValueError('La ruta del conector no admite enlaces.')
        if target.is_file() and digest(target)==expected:return target
        self.features.hilo.report(event,'Descargando el conector HTTPS de CoCo')
        fd,temporary=tempfile.mkstemp(prefix='.cloudflared-',dir=self.directory)
        try:
            request=Request(f'https://github.com/cloudflare/cloudflared/releases/download/{VERSION}/{name}',headers={'User-Agent':'Zenit-CoCo'})
            with os.fdopen(fd,'wb') as output:
                fd=None
                with build_opener(ProxyHandler({})).open(request,timeout=30) as response:
                    total=0
                    while chunk:=response.read(1048576):
                        if event.is_set() or self.cancelled.is_set():raise ValueError('Conexión cancelada.')
                        total+=len(chunk)
                        if total>150_000_000:raise ValueError('El conector supera el tamaño permitido.')
                        output.write(chunk)
            if digest(Path(temporary))!=expected:raise ValueError('La huella del conector no coincide con la publicación oficial.')
            os.chmod(temporary,0o700);os.replace(temporary,target);return target
        finally:
            try:
                if fd is not None:os.close(fd)
            except OSError:pass
            if os.path.exists(temporary):os.unlink(temporary)

    def start(self,event):
        try:
            executable=self.prepare(event)
            with self.lock:
                if event.is_set() or self.cancelled.is_set():raise ValueError('Conexión cancelada.')
                # An explicit empty configuration keeps this session independent
                # from any cloudflared account or service configured by the user.
                config=self.directory/'coco-quick.yml';config.write_text('{}\n',encoding='utf-8')
                from .terminals import child_environment
                self.process=subprocess.Popen([str(executable),'tunnel','--config',str(config),'--no-autoupdate','--protocol','http2','--url',self.local,'--metrics','127.0.0.1:0'],cwd=self.directory,env=child_environment(),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                self.phase='connecting';process=self.process
            self.features.hilo.report(event,'Conectando las estaciones por HTTPS')
            def read():
                try:
                    for line in process.stdout:
                        with self.lock:
                            self.tail=(self.tail+line)[-6000:]
                            match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',line)
                            if match:self.endpoint=match.group()
                finally:process.stdout.close()
            self.reader=threading.Thread(target=read,name='coco-https-log',daemon=True);self.reader.start()
            deadline=time.monotonic()+75;opener=build_opener(ProxyHandler({}))
            while time.monotonic()<deadline and process.poll() is None:
                if event.is_set() or self.cancelled.is_set():raise ValueError('Conexión cancelada.')
                if self.endpoint:
                    try:
                        with opener.open(self.endpoint+'/',timeout=3) as response:ready=response.status==200 and b'team-peer.js' in response.read(50000)
                        if ready:
                            with self.lock:
                                if event.is_set() or self.cancelled.is_set():raise ValueError('Conexión cancelada.')
                                self.phase='ready'
                            return self.status()
                    except (OSError,ValueError):pass
                self.cancelled.wait(.4)
            raise ValueError('No se pudo establecer la dirección HTTPS. Revisa la conexión de Internet o utiliza una red privada entre estaciones.')
        except Exception as error:
            self.stop()
            with self.lock:self.phase='failed';self.error=str(error)
            raise

    def stop(self):
        self.cancelled.set()
        with self.lock:process=self.process;self.phase='off';self.endpoint=None
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
        if self.reader and self.reader is not threading.current_thread():self.reader.join(timeout=2)
