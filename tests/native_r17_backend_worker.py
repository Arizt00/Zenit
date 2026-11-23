"""Execute with the frozen helper: real SDK, tests, collaboration and metadata."""
import argparse,json,sys,tempfile,time,threading
from pathlib import Path
from backend.server import Application
from backend.version import REVISION
from backend import foundation

def wait(app,identity,timeout=40):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  row=next(x for x in app.features.hilo.snapshot()['jobs'] if x['id']==identity)
  if row['state'] in ('done','failed','cancelled'):return row
  time.sleep(.05)
 raise AssertionError('Frozen task timed out')
def main():
 p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--sdk-package',type=Path,required=True);args=p.parse_args();root=Path(sys._MEIPASS);checks=[];assert getattr(sys,'frozen',False) and REVISION==17
 index=json.loads((Path(sys.executable).parent/'sdk/foundation/tool-index.json').read_text());assert {x['id'] for x in index['components']}=={'python'};assert not any(x in index['tools'] for x in ('gcc','nasm','clang'));checks.append('Frozen R17 core ships Python and excludes the optional native compiler payload')
 with tempfile.TemporaryDirectory(prefix='zenit-r17-frozen-') as tmp:
  base=Path(tmp);ws=base/'host';ws.mkdir();(ws/'main.py').write_text('import time\nprint("FROZEN_ONE_HOST",flush=True)\ntime.sleep(.5)\n');(ws/'test_actual.py').write_text('import unittest\nclass Actual(unittest.TestCase):\n def test_real(self):self.assertEqual(6*7,42)\n');app=Application(root,ws,data_dir=base/'profile');app.workspace.trusted=True;guests=[]
  try:
   app.features.sdk.install(str(args.sdk_package.resolve()));tool=foundation.bundled_tool('nasm');assert tool and Path(tool).is_relative_to(app.features.prefs.directory/'sdks');job=app.runner.jobs[app.runner.start([[tool,'-v']],ws)['job']];end=time.monotonic()+10
   while not job.done and time.monotonic()<end:time.sleep(.03)
   assert job.code==0 and 'NASM version' in job.output,job.output;checks.append('Optional NASM archive verifies, installs into a temporary profile and runs its actual executable')
   tests=app.features.tests;run=tests.start(app.workspace,{'framework':'unittest','consent':True});assert wait(app,run['job'])['state']=='done';result=tests.snapshot(app.workspace,run['run'])['runs'][0]['result'];assert result['summary']['passed']==1 and result['results'][0]['path']=='test_actual.py';assert (root/'backend/test_bridge.py').is_file();checks.append('Packaged test bridge executes a real unittest and returns its source result')
   t=app.features.tern;task=app.features.post('/lantern/environments/create',{'kind':'python','name':'Frozen environment','inherit':False});created=wait(app,task['job'],90);assert created['state']=='done',created;identity=created['result']['environment'];t.save(app.workspace,identity,'reproducible.tern');data=json.loads((ws/'reproducible.tern').read_text());assert data['schema']==2 and data['tools'][0]['version'];export=t.portability.export(app.workspace,{'file':'reproducible.tern'},threading.Event());assert export['report']['missing'];checks.append('Frozen Lantern captures exact interpreter metadata and reports missing offline resources')
   state=app.features.team.start(app.workspace,{'protocol':2,'shareProject':True,'allowRun':True,'documents':[{'path':'main.py'}]})
   for i in range(2):
    folder=base/('guest'+str(i));folder.mkdir();guest=Application(root,folder,data_dir=base/('guest-profile'+str(i)));guest.workspace.trusted=True;guest.features.team.join(guest.workspace,state['invitation']);person=guest.features.team.request({'action':'sync','vectors':{}});assert person['self']['role']=='viewer';app.features.team.request({'action':'permissions','participant':person['self']['id'],'role':'runner'});guests.append(guest)
   guests[0].features.team.request({'action':'project-create','path':'new.py','text':'VALUE=42\n'});guests[0].features.team.request({'action':'project-rename','path':'new.py','newPath':'renamed.py'});assert any(x['path']=='renamed.py' for x in guests[1].features.team.request({'vectors':{}})['documents']);checks.append('Packaged CoCo v2 applies actual guest permissions and shared file creation/rename')
   first=guests[0].features.team.request({'action':'run','path':'main.py','requestId':'frozen-idempotent'});second=guests[1].features.team.request({'action':'run','path':'main.py','requestId':'frozen-second'});assert first['job']==second['job'];assert all(not guest.runner.jobs for guest in guests);job=app.runner.jobs[first['job']];end=time.monotonic()+15
   while not job.done and time.monotonic()<end:time.sleep(.03)
   assert job.code==0 and 'FROZEN_ONE_HOST' in job.output;assert guests[0].features.team.request({'action':'run','path':'main.py','requestId':'frozen-idempotent'})['job']==first['job'];checks.append('Two frozen backend clients share one host process and retries do not launch it again')
   assert (root/'config/extension-compatibility.json').is_file();assert all((root/'web'/p).is_file() for p in ('coco-drafts.js','src/team-project.js','src/task-center.js','src/project-tests.js','src/git-conflicts.js'));checks.append('Frozen distribution contains R17 compatibility evidence and every new workflow resource')
  finally:
   for guest in guests:guest.features.shutdown();guest.runner.shutdown()
   app.features.shutdown();app.runner.shutdown();foundation.set_sdk_roots([])
 args.report.write_text(json.dumps({'revision':REVISION,'frozen':True,'checks':checks,'errors':[]},indent=2),encoding='utf-8');print('PASS',checks,flush=True)
if __name__=='__main__':main()
