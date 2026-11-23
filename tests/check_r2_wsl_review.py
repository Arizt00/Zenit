"""Opt-in real Linux runs on the selected WSL station, in disposable project copies."""
import json,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application
from backend.execution_readiness import inspect
from tests.test_hilo_tern import wait

checks=[]
with tempfile.TemporaryDirectory(prefix="zenit-reviewed ' WSL-",ignore_cleanup_errors=True) as tmp:
 base=Path(tmp);ws=base/'project';ws.mkdir();app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True;f=app.features
 try:
  f.execution.select(app.workspace,{'id':'wsl:Ubuntu'})
  samples={'main.py':('import platform\nprint("PY_WSL",platform.system())\n','PY_WSL Linux'),
   'main.c':('#include <stdio.h>\nint main(){puts("C_WSL");return 0;}','C_WSL'),
   'main.cpp':('#include <iostream>\nint main(){std::cout<<"CPP_WSL"<<std::endl;}','CPP_WSL'),
   'Main.java':('public class Main {public static void main(String[] a){System.out.println("JAVA_WSL");}}','JAVA_WSL'),
   'main.rs':('fn main(){println!("RUST_WSL");}','RUST_WSL'),
   'main.n':('use <io:output>;\nhello {\n fn:\n  run() -> bool {println("NC_WSL"); return true;}\n ref main ->> run;\n fa: return true;\n}\n','NC_WSL'),
   'main.asm':('global _start\nsection .text\n_start:\n mov rdi,0\n mov rax,60\n syscall\n','')}
  for path,(source,expected) in samples.items():(ws/path).write_text(source,encoding='utf-8')
  for path,(_,expected) in samples.items():
   report=inspect(f,app.workspace,path,threading.Event());assert report['ready'],report
   plan=f.runtimes.plan(app.workspace,path);task=app.runner.jobs[app.runner.start(plan['commands'],ws,timeout=45)['job']];deadline=time.monotonic()+50
   while not task.done and time.monotonic()<deadline:time.sleep(.05)
   assert task.done and task.code==0,(path,task.code,task.output)
   assert expected in task.stream_output,(path,task.stream_output)
   checks.append(path+' uses its actual WSL runtime and returns the expected result')
  saved='value=int(input())\nprint(value+1)\n';(ws/'cases.py').write_text(saved)
  matrix=f.lantern_matrix.plan(app.workspace,{'path':'cases.py','content':saved,'timeout':5,'cases':[{'name':'Positive','stdin':'4\n','expectedOutput':'5\n'},{'name':'Negative','stdin':'-2\n','expectedOutput':'-1\n'}]})
  result=wait(f.hilo,f.lantern_matrix.run(app.workspace,{'plan':matrix['id']})['job'],45);assert result['state']=='done',result;assert result['result']['passed']==2,result;assert result['result']['executionTarget']['id']=='wsl:Ubuntu'
  checks.append('The reviewed matrix executes both private copies sequentially in WSL, preserving inputs and exact outputs')
  counter=f.countercheck.plan(app.workspace,{'path':'cases.py','content':'value=int(input())\nprint(value+2)\n','stdin':'4\n','timeout':5})
  result=wait(f.hilo,f.countercheck.run(app.workspace,{'plan':counter['id']})['job'],45);assert result['state']=='done',result;assert [r['output'].strip() for r in result['result']['results']]==['5','6'];assert not result['result']['equivalent']
  assert (ws/'cases.py').read_text()==saved
  assert all(job.commands[0][0].lower().endswith('wsl.exe') for job in app.runner.jobs.values())
  checks.append('Countercheck uses the same WSL destination for both variants; original source stays unchanged and no local fallback process is started')
 finally:f.shutdown();app.runner.shutdown()
out=ROOT/'qa-output/r2-closure-wsl.json';out.write_text(json.dumps({'checks':checks,'passed':len(checks),'errors':[]},indent=2),encoding='utf-8');print(json.dumps({'passed':len(checks),'errors':[]}))
