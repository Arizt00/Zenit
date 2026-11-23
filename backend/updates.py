"""GitHub release checks and verified background downloads for Zénit desktop."""
import copy
import json
import re
import platform
import sys
import threading
import time
import urllib.request
from pathlib import Path
from .preferences import atomic_json

from .version import RELEASE_TAG,REPOSITORY
CURRENT=RELEASE_TAG
API='https://api.github.com/repos/'+REPOSITORY+'/releases?per_page=15'


def version_key(tag):
    m=re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)(?:-preview\.(\d+))?',str(tag))
    return (*map(int,m.groups()[:3]),int(m[4]) if m[4] else 1_000_000) if m else None


def package_matches(name, system=None, machine=None):
    """Never offer a Windows installer to Linux/macOS or the wrong CPU build."""
    system=system or sys.platform
    machine=(machine or platform.machine()).lower()
    architecture={'amd64':'x86_64','x64':'x86_64','aarch64':'arm64'}.get(machine,machine)
    if system=='win32':
        return architecture=='x86_64' and bool(re.fullmatch(r'(?:Zenit|Edryvo|LumenStudio)[-_].*(?:Setup|Installer|Instalador).*\.exe',name,re.I))
    if system=='darwin':
        return bool(re.fullmatch(r'(?:Zenit|Edryvo|LumenStudio)[-_].*-macOS-'+re.escape(architecture)+r'\.dmg',name,re.I))
    if system.startswith('linux'):
        arch={'x86_64':'amd64','arm64':'arm64'}.get(architecture,architecture)
        return bool(re.fullmatch(r'(?:Zenit|Edryvo|LumenStudio)[-_].*-Linux-'+re.escape(arch)+r'\.deb',name,re.I))
    return False


def update_asset(releases, current=CURRENT, system=None, machine=None, channel='preview'):
    if not isinstance(releases,list):raise ValueError('GitHub no devolvió una lista de versiones.')
    newer=[r for r in releases if isinstance(r,dict) and not r.get('draft') and version_key(r.get('tag_name')) and version_key(r['tag_name'])>version_key(current) and (channel=='preview' or not r.get('prerelease') and '-preview.' not in r['tag_name'])]
    for release in sorted(newer,key=lambda r:version_key(r['tag_name']),reverse=True):
        for asset in release.get('assets',[]):
            if isinstance(asset,dict) and isinstance(asset.get('name'),str) and package_matches(asset['name'],system,machine):
                digest=asset.get('digest','')
                url=asset.get('browser_download_url','')
                if not isinstance(digest,str) or not re.fullmatch(r'sha256:[a-f0-9]{64}',digest):continue
                if not isinstance(url,str) or not any(url.startswith('https://github.com/'+repo+'/releases/download/') for repo in (REPOSITORY,'Arizt00/Edryvo','Arizt00/LumenStudio')):continue
                if type(asset.get('size')) is not int or not 0<asset['size']<4_000_000_000:continue
                return {'version':release['tag_name'],'name':asset['name'],'url':url,'sha256':digest[7:],'size':asset['size'],'release':release.get('html_url',''),'notes':str(release.get('body') or '')[:16000]}
    return None


class Updates:
    def __init__(self,prefs,downloads):
        self.prefs=prefs;self.downloads=downloads;self.lock=threading.RLock();self.stop_event=threading.Event()
        self.data={'current':CURRENT,'status':'idle','available':None,'error':'','checkedAt':None,'download':None}
        self.index=Path(prefs.directory if prefs else downloads.root)/'updates/state.json'
        try:
            saved=json.loads(self.index.read_text('utf-8'))
            asset=saved.get('available')
            if asset and version_key(asset.get('version')) and version_key(asset['version'])>version_key(CURRENT):
                # Revalidate persisted metadata against the same release policy.
                valid=update_asset([{'tag_name':asset['version'],'assets':[{'name':asset['name'],'digest':'sha256:'+asset['sha256'],'browser_download_url':asset['url'],'size':asset['size']}]}],channel=prefs.get('updates.channel'))
                if valid:self.data.update(available={**valid,'notes':str(asset.get('notes',''))[:16000]},download=saved.get('download'),status='available',checkedAt=saved.get('checkedAt'))
        except (OSError,ValueError,TypeError,KeyError):pass
        self.busy=False

    def persist(self):atomic_json(self.index,{k:self.data[k] for k in ('available','download','checkedAt')})

    def snapshot(self):
        with self.lock:
            result=copy.deepcopy(self.data)
            result['channel']=self.prefs.get('updates.channel')
            if result['download']:
                with self.downloads.lock:item=copy.deepcopy(self.downloads.items.get(result['download']))
                result['transfer']=item
                if item and item['status']=='complete':result['status']='ready'
                elif item and item['status']=='error':result['status']='error';result['error']=item['error']
            return result

    def check(self,download=False):
        with self.lock:
            if self.busy:return self.snapshot()
            self.busy=True;self.data.update(status='checking',error='')
        def work():
            try:
                req=urllib.request.Request(API,headers={'User-Agent':'Zénit/'+CURRENT,'Accept':'application/vnd.github+json'})
                with urllib.request.urlopen(req,timeout=20) as response:raw=response.read(2_000_001)
                if len(raw)>2_000_000:raise ValueError('Respuesta de actualización demasiado grande.')
                releases=json.loads(raw);asset=update_asset(releases,channel=self.prefs.get('updates.channel'))
                with self.lock:
                    same=bool(asset and self.data['available'] and asset['sha256']==self.data['available']['sha256'])
                    if not same and self.data['download']:
                        with self.downloads.lock:previous=self.downloads.items.get(self.data['download'])
                        if previous and previous['status'] in ('downloading','verifying'):self.downloads.pause(previous['id'])
                    self.data.update(status='available' if asset else 'up_to_date',available=asset,checkedAt=time.time(),download=self.data['download'] if same else None);self.persist()
                if asset and download and not self.stop_event.is_set():self.download()
            except Exception as error:
                with self.lock:self.data.update(status='error',error=str(error)[:300])
            finally:
                with self.lock:self.busy=False
        threading.Thread(target=work,daemon=True,name='lumen-update-check').start()
        return self.snapshot()

    def download(self):
        with self.lock:
            asset=self.data['available']
            if not asset:raise ValueError('Comprueba primero si hay actualizaciones.')
            with self.downloads.lock:
                existing=next((x for x in self.downloads.items.values() if x['url']==asset['url'] and x['sha256']==asset['sha256']),None)
            if existing:
                key=existing['id']
                if existing['status'] in ('paused','error'):self.downloads.resume(key)
            else:
                state=self.downloads.start(asset['url'],asset['name'],asset['sha256'])
                key=next(x['id'] for x in state['items'] if x['url']==asset['url'] and x['sha256']==asset['sha256'])
            self.data.update(status='downloading',download=key)
            self.persist()
            return self.snapshot()

    def welcome(self,ack=False):
        file=Path(self.prefs.directory)/'updates/seen.json'
        try:seen=json.loads(file.read_text('utf-8')).get('version')
        except (OSError,ValueError):seen=None
        if ack:atomic_json(file,{'version':CURRENT,'seenAt':time.time()})
        return {'version':CURRENT,'show':not ack and seen!=CURRENT,'previous':seen,
                'items':['R7: nC · renombrado revisado entre módulos con comprobación NCC, deshacer y rehacer.',
                         'Consultas de extensiones cancelables al escribir; F2 conserva su proveedor al actualizar el estado.',
                         'Correcciones de fluidez en Melody, resultados de Lantern y gestión interna de recursos.',
                         'nC: parejas de corchetes, indentación y diagnósticos con el kit nativo o WSL elegido.',
                         'Inicio y actividad con iconos acotados, navegación y arrastre más fluidos.',
                         'Melody: Dossier de fallo, Huella de cambio y Contraprueba con evidencia revisable.',
                         'Lantern: casos guardados por archivo y referencia de comportamiento entre revisiones.',
                         'Laboratorio y depuración: seguimiento de instrucciones y referencias de variables.',
                         'Terminales de extensiones: perfil elegido, argumentos y eventos de interacción.',
                         'Paneles de documentación y acciones legibles, con superficie translúcida y tamaño adaptable.',
                         'Flujos de proyecto para Python, C, C++, Java, NASM y nC: plantillas, revisión de órdenes y recibos de ejecución.',
                         'Melody puede preparar tareas con archivos consultados, diagnósticos y resultados reales del proyecto.',
                         'Biblioteca de imágenes y clones QCOW2 ligeros para el laboratorio de máquinas.',
                         'Actualizaciones estables y preview: descarga verificada, instalación manual y recuperación de la sesión.']}

    def installer(self):
        state=self.snapshot()
        if state['status']!='ready':raise ValueError('La actualización aún no se ha descargado y verificado.')
        from pathlib import Path
        file=Path(state['transfer']['path']).resolve()
        if file.parent!=self.downloads.root.resolve() or not package_matches(file.name):raise ValueError('Instalador no válido para este sistema.')
        # Recheck before execution, even if the user modified the downloaded file.
        import hashlib
        digest=hashlib.sha256()
        with file.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
        sha=digest.hexdigest()
        if sha!=state['available']['sha256']:raise ValueError('El instalador no coincide con la versión publicada.')
        return file

    def start(self):
        def monitor():
            while not self.stop_event.is_set():
                if self.prefs.get('updates.automatic'):self.check(download=True)
                if self.stop_event.wait(6*3600):break
        threading.Thread(target=monitor,daemon=True,name='lumen-update-monitor').start()

    def shutdown(self):self.stop_event.set()
