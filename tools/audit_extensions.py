"""Audit installed packages in a disposable profile without copying credentials."""
import argparse,json,shutil,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--packages',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();rows=[]
 index=json.loads((args.packages/'installed.json').read_text('utf-8'));assert isinstance(index,dict) and len(index)<=100
 with tempfile.TemporaryDirectory(prefix='zenit-package-audit-',ignore_cleanup_errors=True) as temporary:
  base=Path(temporary);project=base/'project';project.mkdir();(project/'main.n').write_text('main :: in {\n println("Audit");\n}\n',encoding='utf-8');(project/'main.py').write_text('value = 42\n');(project/'Cargo.toml').write_text('[package]\nname="audit"\nversion="0.1.0"\n');destination=base/'profile/extensions';destination.mkdir(parents=True)
  for item in index.values():
   source=args.packages/item['directory'];assert source.resolve().parent==args.packages.resolve() and not source.is_symlink();shutil.copytree(source,destination/item['directory'])
  (destination/'installed.json').write_text(json.dumps(index),encoding='utf-8');app=Application(ROOT,project,data_dir=base/'profile');app.workspace.trusted=True;runtime=app.features.extension_runtime
  try:
   for identity in index:
    started=time.monotonic();item=index[identity];package=destination/item['directory']/'extension';manifest=json.loads((package/'package.json').read_text('utf-8-sig'));executable=manifest.get('main') or manifest.get('lumen',{}).get('main')
    row={'id':identity,'version':manifest['version'],'sha256':item.get('sha256'),'executable':bool(executable)}
    try:
     if executable:
      state=runtime.start(app.workspace,identity,True);host=next(h for h in state['hosts'] if h['id']==identity);row.update(state='activated',unsupportedApis=host.get('unsupportedApis',[]),commands=len(host.get('commands',[])),providers=len(host.get('providers',[])))
     else:row['state']='declarations-only'
    except Exception as error:row.update(state='activation-failed',error=str(error)[:1000])
    finally:runtime.stop(identity)
    row['elapsedMs']=round((time.monotonic()-started)*1000);rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
  finally:app.features.shutdown();app.runner.shutdown()
 result={'packages':rows,'scope':'Activation only in a disposable profile; runtime state, approvals and credentials were not copied. This does not certify every command or remote feature.'};args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 return int(any(row['state']=='activation-failed' for row in rows))
if __name__=='__main__':raise SystemExit(main())
