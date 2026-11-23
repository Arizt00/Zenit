"""Crash-consistent CoCo checkpoints in the local profile, never in the project.

Only changed CRDT documents are serialized. Idle polls do not write the store.
SQLite FULL transactions acknowledge edits and reserve side effects durably.
Windows blobs use current-user DPAPI; POSIX uses a private directory/database.
"""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import secrets
import threading
import time
from contextlib import contextmanager


def protect(data, opening=False):
    if os.name != 'nt':
        return data
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    function = crypt.CryptUnprotectData if opening else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise OSError('No se pudo abrir el almacén privado de recuperación de CoCo.')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel.LocalFree(target.data)


class TeamStore:
    MAX_META = 40_000_000
    def __init__(self, directory):
        self.directory = Path(directory) / 'co-code'
        self.path = self.directory / 'recovery.sqlite3'
        self.lock = threading.RLock()
        self.leases = {}

    @contextmanager
    def connect(self):
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.directory, 0o700)
        connection = sqlite3.connect(self.path, timeout=10)
        os.chmod(self.path, 0o600)
        try:
            connection.execute('PRAGMA synchronous=FULL')
            connection.execute('PRAGMA secure_delete=ON')
            connection.executescript('''
            CREATE TABLE IF NOT EXISTS rooms (workspace TEXT PRIMARY KEY, updated REAL, data BLOB);
            CREATE TABLE IF NOT EXISTS documents (workspace TEXT, path TEXT, data BLOB, PRIMARY KEY(workspace,path));
            CREATE TABLE IF NOT EXISTS clients (workspace TEXT PRIMARY KEY, data BLOB);
            CREATE TABLE IF NOT EXISTS leases (workspace TEXT PRIMARY KEY, pid INTEGER, created REAL, identity TEXT);
            CREATE TABLE IF NOT EXISTS local_drafts (workspace TEXT, identity TEXT, bytes INTEGER, data BLOB, PRIMARY KEY(workspace,identity));
            ''')
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def key(workspace):
        return hashlib.sha256(os.path.normcase(str(Path(workspace).resolve())).encode()).hexdigest()

    def claim(self,workspace):
        import psutil
        key=self.key(workspace)
        with self.lock,self.connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            previous=connection.execute('SELECT pid,created,identity FROM leases WHERE workspace=?',(key,)).fetchone()
            if previous:
                if self.leases.get(key)==previous[2]:return
                try:
                    process=psutil.Process(previous[0])
                    if process.is_running() and abs(process.create_time()-previous[1])<.001:
                        raise ValueError('Otra instancia de Zénit ya está hospedando esta sesión. No se abrirá un segundo anfitrión.')
                except psutil.NoSuchProcess:pass
                except psutil.AccessDenied:raise ValueError('No se puede comprobar la otra instancia de CoCo; no se abrirá un segundo anfitrión.') from None
            identity=secrets.token_hex(24)
            connection.execute('INSERT OR REPLACE INTO leases VALUES (?,?,?,?)',
                               (key,os.getpid(),psutil.Process().create_time(),identity))
            self.leases[key]=identity

    def release(self,workspace):
        key=self.key(workspace)
        with self.lock:
            identity=self.leases.pop(key,None)
            if identity:
                with self.connect() as connection:
                    connection.execute('DELETE FROM leases WHERE workspace=? AND identity=?',(key,identity))

    @staticmethod
    def encode(value, limit=MAX_META):
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
        if len(raw) > limit:
            raise ValueError('El estado de recuperación de CoCo supera su presupuesto. Termina trabajos antiguos antes de continuar.')
        return protect(raw)

    @staticmethod
    def decode(value):
        return json.loads(protect(value, opening=True))

    def save(self, room, paths=()):
        from .team import encode
        project = room.project
        meta = {
            'schema': 1, 'workspace': str(room.workspace.root), 'id': room.id, 'token': room.token,
            'mode': room.mode, 'port': room.port, 'allowRun': room.allow_run,
            'revisions': room.revisions, 'checkpoints': room.checkpoints,
            'executions': room.executions, 'runRequests': list(room.run_requests.items()),
            'runSeen': [v.hex() for v in room.run_seen], 'evidence': list(room.evidence.items()),
            'operations': [[k.hex(), v] for k, v in room.operations.items()],
            'operationSeen': [v.hex() for v in room.operation_seen],
            'pendingOperations': room.pending_operations, 'archivedJobs': room.archived_jobs,
            'project': {key: getattr(project, key) for key in
                        ('protocol', 'shared', 'owner', 'document_ids', 'aliases', 'tree_version', 'tree', 'events', 'baselines')},
            'members': {key: {k: v for k, v in member.items() if k != 'seen'} for key, member in project.members.items()},
        }
        payload = self.encode(meta)
        documents = [(name, self.encode({'update': encode(room.documents[name].get_update())}, 6_000_000))
                     for name in set(paths) if name in room.documents]
        workspace = self.key(room.workspace.root)
        with self.lock, self.connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            lease=connection.execute('SELECT identity FROM leases WHERE workspace=?',(workspace,)).fetchone()
            if not lease or lease[0]!=self.leases.get(workspace):raise ValueError('CoCo no posee el bloqueo de esta sesión. Se ha detenido la confirmación del cambio.')
            connection.execute('INSERT OR REPLACE INTO rooms VALUES (?,?,?)', (workspace, time.time(), payload))
            for name, data in documents:
                connection.execute('INSERT OR REPLACE INTO documents VALUES (?,?,?)', (workspace, name, data))
            for (name,) in connection.execute('SELECT path FROM documents WHERE workspace=?', (workspace,)).fetchall():
                if name not in room.documents:
                    connection.execute('DELETE FROM documents WHERE workspace=? AND path=?', (workspace, name))

    def load(self, workspace):
        if not self.path.exists():
            return None
        with self.lock, self.connect() as connection:
            key = self.key(workspace)
            row = connection.execute('SELECT updated,data FROM rooms WHERE workspace=?', (key,)).fetchone()
            if row is None:
                return None
            meta = self.decode(row[1])
            if meta.get('schema') != 1 or Path(meta['workspace']).resolve() != Path(workspace).resolve():
                raise ValueError('El punto de recuperación de CoCo no corresponde a este proyecto.')
            meta['updated'] = row[0]
            meta['documents'] = {name: self.decode(data)['update'] for name, data in
                                 connection.execute('SELECT path,data FROM documents WHERE workspace=?', (key,))}
            return meta

    def forget(self, workspace):
        if not self.path.exists():
            return
        key=self.key(workspace);temporary=key not in self.leases
        self.claim(workspace)
        try:
            with self.lock, self.connect() as connection:
                connection.execute('DELETE FROM documents WHERE workspace=?', (key,))
                connection.execute('DELETE FROM rooms WHERE workspace=?', (key,))
        finally:
            if temporary:self.release(workspace)

    def client(self, workspace, data=None):
        if data is None and not self.path.exists():
            return {}
        with self.lock, self.connect() as connection:
            key = self.key(workspace)
            if data is not None:
                connection.execute('INSERT OR REPLACE INTO clients VALUES (?,?)', (key, self.encode(data, 100_000)))
                return data
            row = connection.execute('SELECT data FROM clients WHERE workspace=?', (key,)).fetchone()
            return self.decode(row[0]) if row else {}

    def local_drafts(self,workspace,body=None):
        if body is None and not self.path.exists():return []
        key=self.key(workspace)
        with self.lock,self.connect() as connection:
            if body and body.get('action')=='preserve':
                text=body.get('text');path=body.get('path');room=body.get('room');document=body.get('document')
                if not isinstance(text,str) or len(text.encode())>500000 or not all(isinstance(v,str) and 0<len(v)<=500 for v in (path,room,document)):
                    raise ValueError('El borrador local supera el presupuesto de CoCo.')
                identity=hashlib.sha256((room+'\0'+document+'\0'+text).encode()).hexdigest()
                row=connection.execute('SELECT data FROM local_drafts WHERE workspace=? AND identity=?',(key,identity)).fetchone()
                if row:return self.decode(row[0])
                count,size=connection.execute('SELECT count(*),coalesce(sum(bytes),0) FROM local_drafts WHERE workspace=?',(key,)).fetchone()
                if count>=128 or size+len(text.encode())>8000000:raise ValueError('Conserva o elimina copias locales antiguas antes de recuperar otros borradores; no se ha sustituido tu texto.')
                item={'id':identity,'room':room,'document':document,'path':path,'text':text,'created':time.time()}
                connection.execute('INSERT INTO local_drafts VALUES (?,?,?,?)',(key,identity,len(text.encode()),self.encode(item,600000)))
                return item
            if body:
                row=connection.execute('SELECT data FROM local_drafts WHERE workspace=? AND identity=?',(key,body.get('id'))).fetchone()
                if not row:raise ValueError('La copia local ya no está disponible.')
                item=self.decode(row[0])
                if body.get('action')=='discard':connection.execute('DELETE FROM local_drafts WHERE workspace=? AND identity=?',(key,item['id']))
                elif body.get('action')!='read':raise ValueError('Acción de borrador desconocida.')
                return item
            return [{k:v for k,v in self.decode(data).items() if k!='text'} for (data,) in
                    connection.execute('SELECT data FROM local_drafts WHERE workspace=?',(key,))]
