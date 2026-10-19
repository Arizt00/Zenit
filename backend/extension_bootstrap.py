"""Bounded large activation metadata without relaxing ordinary RPC limits."""
from contextlib import contextmanager
import hashlib,json,os,tempfile
from pathlib import Path

@contextmanager
def activation_message(message,storage):
    raw=json.dumps(message,ensure_ascii=False).encode('utf-8')
    if len(raw)<=1_900_000:
        yield message
        return
    if len(raw)>20_000_000:raise ValueError('Los metadatos de activación superan 20 MB.')
    directory=Path(storage);directory.mkdir(parents=True,exist_ok=True)
    handle,name=tempfile.mkstemp(prefix='.activation-',suffix='.json',dir=directory)
    try:
        with os.fdopen(handle,'wb') as stream:stream.write(raw)
        yield {'method':'activateFromFile','file':str(Path(name).resolve()),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    finally:Path(name).unlink(missing_ok=True)
