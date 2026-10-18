"""Opt-in real WSL file plans, entirely within a disposable mounted project."""
import argparse,json,sys,tempfile,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application
parser=argparse.ArgumentParser(description='Run real WSL plans in a disposable mounted project');parser.add_argument('--distribution',default='Ubuntu');parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
checks=[];errors=[];skipped=[]
if getattr(sys,'frozen',False):
 from backend import execution_targets
 assert Path(execution_targets.__file__).is_relative_to(sys._MEIPASS)
 checks.append('Execution targets are imported from the actual frozen R16 application')
try:
 with tempfile.TemporaryDirectory(prefix="zenit r16 ' WSL-",ignore_cleanup_errors=True) as tmp:
  root=Path(tmp);project=root/'project';project.mkdir();app=Application(Path(getattr(sys,'_MEIPASS',ROOT)),project,data_dir=root/'profile');app.workspace.trusted=True
  try:
   targets=app.features.execution.inventory(app.workspace)['targets'];ubuntu=next(t for t in targets if t.get('distribution')==args.distribution);app.features.execution.select(app.workspace,{'id':ubuntu['id']})
   (project/'main.py').write_text('import platform\nprint("R16_WSL_PYTHON",platform.system())\n',encoding='utf-8')
   (project/'main.c').write_text('#include <stdio.h>\nint main(){puts("R16_WSL_C");return 0;}\n')
   (project/'main.cpp').write_text('#include <iostream>\nint main(){std::cout<<"R16_WSL_CPP"<<std::endl;}\n')
   (project/'main.asm').write_text('global _start\nsection .text\n_start:\nmov rdi,8\nmov rax,60\nsyscall\n')
   checks.append('Actual WSL distribution discovered and selected through the shared backend target')
   for file,expected in [('main.py','R16_WSL_PYTHON Linux'),('main.c','R16_WSL_C'),('main.cpp','R16_WSL_CPP'),('main.asm',None)]:
    plan=app.features.runtimes.plan(app.workspace,file);task=app.runner.jobs[app.runner.start(plan['commands'],project,timeout=45)['job']];end=time.monotonic()+50
    while not task.done and time.monotonic()<end:time.sleep(.05)
    if task.code==127 and 'not found' in task.output:skipped.append({'file':file,'reason':task.output[-400:]});continue
    assert task.done and task.code==(8 if file.endswith('.asm') else 0),(file,task.code,task.output)
    if expected:assert expected in task.output,task.output
    checks.append(file+' builds/runs in the selected actual WSL distribution with quoted mounted paths and expected result')
   # Forge/Run uses the same plan through a genuine ConPTY session.
   result=app.features.hacker.start(app.workspace,'main.py','','file');terminal=app.features.terminals.get(result['terminal']['id']);end=time.monotonic()+20
   while not terminal.closed and time.monotonic()<end:time.sleep(.05)
   output=terminal.read()['data'];assert terminal.closed and terminal.code==0 and 'R16_WSL_PYTHON Linux' in output,(terminal.code,output);checks.append('Forge executes one real WSL process via its actual Windows PTY using the common destination')
   app.features.execution.select(app.workspace,{'id':'local'});assert app.features.execution.selected(app.workspace)['kind']=='local';checks.append('Returning to local target works after the real WSL runs')
  finally:app.features.shutdown()
except Exception:errors.append(traceback.format_exc())
report=args.report;report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps({'frozen':bool(getattr(sys,'frozen',False)),'distribution':args.distribution,'checks':checks,'errors':errors,'skipped':skipped},indent=2),encoding='utf-8');print(json.dumps({'checks':checks,'errors':errors,'skipped':skipped},indent=2));assert not errors
