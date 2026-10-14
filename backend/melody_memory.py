"""Bounded local conversation memory, isolated by workspace, file and provider."""
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time
from .preferences import atomic_json

def digest(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()
def scrub(text):return re.sub(r'(?:sk-[\w-]{8,}|AIza[\w-]{20,}|gh[pousr]_[\w]{20,})','[credential redacted]',text)

class MelodyMemory:
    def __init__(self,directory):
        self.file=directory/'melody-memory.json';self.lock=threading.RLock();self.epochs={};self.entries={}
        try:
            if self.file.stat().st_size<=3_000_000:
                data=json.loads(self.file.read_text(encoding='utf-8'))
                if data.get('schema')==1:self.entries={k:v for k,v in data.get('entries',{}).items() if isinstance(v,dict) and isinstance(v.get('turns'),list)}
        except (OSError,ValueError,TypeError):pass
    def key(self,workspace,path,provider):
        if not workspace or not path:return None
        target=Path(path) if Path(path).is_absolute() else Path(workspace)/path
        return digest(json.dumps([os.path.normcase(str(Path(workspace).resolve())),os.path.normcase(str(target.resolve())),provider]))
    def read(self,key):
        with self.lock:return json.loads(json.dumps(self.entries.get(key,{'turns':[]}))),self.epochs.get(key,0)
    def remember(self,key,epoch,path,question,answer,source_hash):
        if not key:return
        with self.lock:
            if self.epochs.get(key,0)!=epoch:return
            entry=self.entries.get(key,{'turns':[]})
            turns=entry['turns']+[{'question':scrub(question)[:6000],'answer':scrub(answer)[:12000]}]
            turns=turns[-6:]
            while len(turns)>1 and len(json.dumps(turns))>26000:turns.pop(0)
            self.entries[key]={'path':path,'updated':time.time(),'sourceHash':source_hash,'turns':turns}
            self.entries=dict(sorted(self.entries.items(),key=lambda x:x[1].get('updated',0))[-50:]);self.save()
    def forget(self,key):
        with self.lock:self.epochs[key]=self.epochs.get(key,0)+1;self.entries.pop(key,None);self.save()
    def save(self):atomic_json(self.file,{'schema':1,'entries':self.entries})
    def messages(self,key):
        entry,epoch=self.read(key);messages=[]
        for turn in entry['turns']:
            if not isinstance(turn,dict):continue
            for role,field in (('user','question'),('assistant','answer')):
                if isinstance(turn.get(field),str):messages.append({'role':role,'content':turn[field]})
        return messages,entry,epoch
