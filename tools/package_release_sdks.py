"""Optional prepared language components beside the lightweight application."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.package_sdk import GROUPS,package
from backend.version import RELEASE_TAG

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--components',default='gcc,llvm,nc,nasm,java,node');parser.add_argument('--source',type=Path,default=ROOT/'sdk/foundation');parser.add_argument('--output',type=Path,default=ROOT/'dist/sdk');args=parser.parse_args();components=args.components.split(',');rows=[]
 if len(components)!=len(set(components)) or set(components)-set(GROUPS):parser.error('Revisa los componentes SDK.')
 for component in components:
  row=package(args.source,component,args.output/f'Zenit-{RELEASE_TAG}-{sys.platform}-SDK-{component}.zip');digest=hashlib.sha256()
  with Path(row['path']).open('rb') as stream:
   for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
  row['sha256']=digest.hexdigest();row['filename']=Path(row.pop('path')).name;rows.append(row);print(json.dumps(row),flush=True)
 args.output.mkdir(parents=True,exist_ok=True);(args.output/'catalog.json').write_text(json.dumps({'schema':1,'release':RELEASE_TAG,'platform':sys.platform,'components':rows,'installation':'Laboratorio → SDK → Incorporar paquete. Los paquetes tienen manifiestos y hashes de todos sus archivos.'},ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
