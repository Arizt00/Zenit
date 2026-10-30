"""Execute NCC's documented source smoke command and report each entry honestly."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time
ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]));sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workspace',required=True);parser.add_argument('--compiler',required=True);parser.add_argument('--output',required=True);parser.add_argument('--source',action='append',required=True)
    args=parser.parse_args();root=Path(args.workspace).resolve();items=[]
    for name in args.source:
        path=(root/name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.suffix.lower()!='.n':raise ValueError('Entrada NCC fuera del proyecto o no válida.')
        from backend.nc_project_bridge import has_project_imports,command as project_command
        started=time.perf_counter();command=project_command(args.compiler,root,path,'run',root/'build/nc/smoke.exe') if has_project_imports(path) else [args.compiler,'test',str(path),'--show-return'];code=1
        try:
            result=subprocess.run(command,cwd=root,input='',capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
            output=result.stdout+result.stderr;code=result.returncode
        except subprocess.TimeoutExpired:output='La prueba de humo NCC excedió 120 segundos.'
        except OSError as error:output=str(error)
        print(json.dumps(command,ensure_ascii=False),flush=True);print(output[-24000:],flush=True)
        match=re.search(r':(\d+):\d+:',output)
        items.append({'id':name+'::main','name':Path(name).name+' · main (humo NCC)','path':name,'line':int(match[1]) if match else 1,'status':'passed' if code==0 else 'failed','kind':'smoke','seconds':round(time.perf_counter()-started,3),'message':output[-12000:]})
    summary={state:sum(r['status']==state for r in items) for state in ('passed','failed','error','skipped')}
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps({'results':items,'summary':summary,'scope':'NCC source smoke: parser, tipos, contratos y main; no es una suite de aserciones.'},ensure_ascii=False),encoding='utf-8')
    return 1 if summary['failed'] else 0


if __name__=='__main__':sys.exit(main())
