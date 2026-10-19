"""Human-connected extension accounts. Tokens never enter profile JSON or status APIs."""
import hashlib
import json
import threading
import urllib.error
import urllib.request
import uuid
from .preferences import atomic_json
from .providers import CredentialVault, NoRedirect


class ExtensionAccounts:
    def __init__(self, prefs, changed=lambda: None):
        self.path=prefs.directory/'extension-accounts.json'
        self.service='Zenit.accounts:'+hashlib.sha256(str(prefs.directory.resolve()).encode()).hexdigest()[:16]
        self.changed=changed;self.lock=threading.RLock();self.token=None
        try:self.account=json.loads(self.path.read_text(encoding='utf-8')).get('github')
        except (OSError,ValueError,AttributeError):self.account=None
        if not isinstance(self.account,dict) or not all(k in self.account for k in ('id','account','scopes','remember')):self.account=None

    def _token(self):
        if self.token:return self.token
        if self.account and self.account.get('remember'):
            native=CredentialVault()._native()
            if native:
                try:return native.get_password(self.service,'github')
                except Exception:pass
        return None

    def snapshot(self):
        with self.lock:
            connected=bool(self.account and self._token())
            return {'github':{'connected':connected,'account':self.account['account'] if connected else None,
                'scopes':self.account['scopes'] if connected else [],'storage':('native-keyring' if self.account['remember'] else 'session') if connected else None}}

    def connect(self, body):
        if body.get('consent') is not True:raise PermissionError('Autoriza la conexión a GitHub.')
        token=body.get('token');remember=body.get('remember') is True
        if not isinstance(token,str) or not 8<=len(token)<=1000 or any(c.isspace() for c in token):raise ValueError('Token de GitHub no válido.')
        native=CredentialVault()._native()
        if remember and not native:raise ValueError('El almacén seguro no está disponible. Conecta solo para esta sesión.')
        request=urllib.request.Request('https://api.github.com/user',headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'Zenit-Extension-Accounts','X-GitHub-Api-Version':'2022-11-28'})
        try:
            with urllib.request.build_opener(NoRedirect()).open(request,timeout=20) as response:
                raw=response.read(500001)
                if len(raw)>500000:raise ValueError('La respuesta de GitHub es demasiado grande.')
                user=json.loads(raw);scopes=[s.strip() for s in response.headers.get('X-OAuth-Scopes','').split(',') if s.strip()]
        except urllib.error.HTTPError as error:raise ValueError('GitHub rechazó la conexión (HTTP '+str(error.code)+'). Comprueba el token y sus permisos.') from None
        except (urllib.error.URLError,TimeoutError):raise ValueError('No se pudo conectar con GitHub. Comprueba la red.') from None
        if not isinstance(user.get('id'),int) or not isinstance(user.get('login'),str):raise ValueError('GitHub no devolvió una cuenta válida.')
        # GitHub normalizes broader OAuth scopes; do not invent scopes for fine-grained tokens.
        implied={'user':['read:user','user:email','user:follow'],'repo':['repo:status','repo_deployment','public_repo','repo:invite','security_events']}
        scopes=sorted(set(scopes+[child for parent in scopes for child in implied.get(parent,[])]))
        account={'id':uuid.uuid4().hex,'account':{'id':str(user['id']),'label':user['login']},'scopes':scopes,'remember':remember}
        with self.lock:
            if remember:native.set_password(self.service,'github',token)
            elif native and native.get_password(self.service,'github') is not None:native.delete_password(self.service,'github')
            atomic_json(self.path,{'github':account});self.account=account;self.token=token
        self.changed();return self.snapshot()

    def disconnect(self):
        with self.lock:
            native=CredentialVault()._native()
            if native and native.get_password(self.service,'github') is not None:native.delete_password(self.service,'github')
            atomic_json(self.path,{});self.token=None;self.account=None
        self.changed();return self.snapshot()

    def sessions(self, scopes=(), account=None, create=False):
        if not isinstance(scopes,list) or len(scopes)>50 or any(not isinstance(s,str) or len(s)>100 for s in scopes):raise ValueError('Permisos de cuenta no válidos.')
        with self.lock:
            token=self._token();data=self.account
            valid=bool(data and token and all(s in data['scopes'] for s in scopes) and (not account or account.get('id')==data['account']['id']))
            if valid:return [{**{k:data[k] for k in ('id','account','scopes')},'accessToken':token}]
        if create:raise ValueError('Conecta una cuenta con los permisos solicitados en Ajustes → Conexiones → GitHub. Después vuelve a intentarlo.')
        return []
