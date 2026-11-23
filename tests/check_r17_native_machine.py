"""Inspect the actual paused native process, never the user's code."""
import json,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application

def main():
 checks=[]
 with tempfile.TemporaryDirectory(prefix='zenit-r17-native-machine-') as tmp:
  root=Path(tmp);ws=root/'project';ws.mkdir();(ws/'main.c').write_text('int marker=42;\nint main(void){\n int answer=marker+1;\n answer+=2;\n return answer==45?0:1;\n}\n');app=Application(ROOT,ws,data_dir=root/'profile');app.workspace.trusted=True;debug=app.features.debugger
  try:
   debug.start(app.workspace,'main.c',[4]);deadline=time.monotonic()+60
   while time.monotonic()<deadline:
    state=debug.snapshot()
    if state['status']=='paused' or state['status']=='error':break
    time.sleep(.05)
   assert state['status']=='paused',state;assert state['registers'],state;assert any('ip' in r['name'].lower() or r['name'].lower()=='pc' for r in state['registers']),state['registers'];checks.append('Actual LLDB native pause returns registers and stack with instruction pointer')
   reference=state['stack'][0]['instructionPointerReference'];assert reference,state
   pause=state['pauseHistory'][-1]['id'];code=debug.machine({'operation':'disassembly','reference':reference,'count':16});assert code['pause']==pause and code['result']['instructions'];checks.append('Native disassembly belongs to the same guarded pause as registers and stack')
   if state['machineCapabilities']['memory']:
    memory=debug.machine({'operation':'memory','reference':reference,'count':32});assert memory['pause']==pause and memory['result']['data'];checks.append('Actual process memory is read at the current instruction pointer')
   if not state.get('stepBackSupported'):
    try:debug.command('back')
    except ValueError:checks.append('Unsupported reverse execution is rejected without changing process state')
    else:raise AssertionError('Reverse falsely advertised')
   debug.command('next');deadline=time.monotonic()+10
   while time.monotonic()<deadline:
    next_state=debug.snapshot()
    if next_state['status'] in ('paused','error','finished'):break
    time.sleep(.05)
   assert next_state['status']=='paused' and next_state['pauseHistory'][-1]['id']!=pause,next_state;checks.append('A real step captures a new register/stack pause; previous machine data cannot be reused')
  finally:app.features.shutdown();app.runner.shutdown()
 report=ROOT/'qa-output/r17-native-machine.json';report.write_text(json.dumps({'checks':checks,'errors':[]},indent=2),encoding='utf-8');print('PASS',checks,flush=True)
if __name__=='__main__':main()
