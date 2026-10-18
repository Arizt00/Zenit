"""Produce optional SDK archives with exact file hashes for SDKManager."""
from __future__ import annotations
import argparse,hashlib,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GROUPS={'python':('python',),'gcc':('native-mingw','native-sources'),'llvm':('llvm',),'nc':('nc',),'nasm':('nasm',),'java':('java',),'node':('node',),'bash':('bash',),'docker':('docker',),'qemu':('qemu',),'arch':('images',),'mvn':('maven',),'gradle':('gradle',)}

def package(source,component,output):
 source=Path(source).resolve();data=json.loads((source/'tool-index.json').read_text(encoding='utf-8'));folders=GROUPS[component];selected=[x for x in data['components'] if x['id']==component]
 if not selected:raise ValueError('Componente no preparado: '+component)
 files={}
 for folder in folders:
  root=source/folder
  if not root.is_dir():raise ValueError('Falta '+str(root))
  for path in root.rglob('*'):
   if path.is_symlink() or getattr(path,'is_junction',lambda:False)():raise ValueError('Enlace no permitido: '+str(path))
   if path.is_file() and '__pycache__' not in path.parts and path.suffix!='.pyc':files[path.relative_to(source).as_posix()]=path
 tools={name:relative for name,relative in data['tools'].items() if relative.split('/')[0] in folders}
 index=json.dumps({'schema':1,'platform':data.get('platform',sys.platform),'components':selected,'tools':tools},indent=2).encode()
 hashes={'tool-index.json':hashlib.sha256(index).hexdigest()}
 for name,path in files.items():
  digest=hashlib.sha256()
  with path.open('rb') as stream:
   for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
  hashes[name]=digest.hexdigest()
 manifest={'schema':1,'platform':data.get('platform',sys.platform),'component':component,'files':hashes}
 output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as archive:
  archive.writestr('sdk-package.json',json.dumps(manifest,sort_keys=True));archive.writestr('tool-index.json',index)
  for name,path in files.items():archive.write(path,name)
 return {'component':component,'files':len(hashes),'path':str(output),'bytes':output.stat().st_size}

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=ROOT/'sdk/foundation');parser.add_argument('--component',choices=GROUPS,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();print(json.dumps(package(args.source,args.component,args.output)))
if __name__=='__main__':main()
