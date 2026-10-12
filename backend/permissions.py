"""Durable local workspace decisions; explicit revocation overrides direct mode."""
import hashlib,json,os,threading
from pathlib import Path
from .preferences import atomic_json

class WorkspacePermissions:
    def __init__(self,directory):
        self.path=Path(directory)/'workspace-permissions.json';self.lock=threading.RLock();self.decisions={}
        try:
            data=json.loads(self.path.read_text(encoding='utf-8'))
            if data.get('version')==1 and isinstance(data.get('workspaces'),dict):
                self.decisions={k:v for k,v in data['workspaces'].items() if isinstance(k,str) and len(k)==64 and all(c in '0123456789abcdef' for c in k) and type(v) is bool}
        except (OSError,ValueError,AttributeError):pass
    @staticmethod
    def key(root):
        # Resolve aliases and case on Windows; grants apply to this exact folder.
        canonical=os.path.normcase(str(Path(root).expanduser().resolve()))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    def state(self,root,direct=False):
        with self.lock:decision=self.decisions.get(self.key(root))
        if decision is False:return {'trusted':False,'source':'revoked'}
        if decision is True:return {'trusted':True,'source':'remembered'}
        return {'trusted':bool(direct),'source':'direct' if direct else 'unapproved'}
    def set(self,root,trusted):
        if type(trusted) is not bool:raise ValueError('Decisión de confianza inválida.')
        with self.lock:
            decisions={**self.decisions,self.key(root):trusted}
            atomic_json(self.path,{'version':1,'workspaces':decisions});self.decisions=decisions
