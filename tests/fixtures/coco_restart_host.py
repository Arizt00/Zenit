"""Private stdio control of a disposable real host process for crash acceptance."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from backend.server import Application

app=Application(ROOT,Path(sys.argv[1]),data_dir=Path(sys.argv[2]));app.workspace.trusted=True
team=app.features.team
for line in sys.stdin:
    try:
        body=json.loads(line);action=body.pop('command')
        if action=='start':result=team.start(app.workspace,{'protocol':2,'shareProject':True,'allowRun':True,'documents':[{'path':'main.py'}]})
        elif action=='recover':result=team.recover(app.workspace)
        elif action=='owner':result=team.request(body)
        elif action=='status':result=team.status()
        elif action=='close':app.features.shutdown();result={'closed':True}
        else:raise ValueError('Unknown fixture command')
        print(json.dumps({'result':result}),flush=True)
        if action=='close':break
    except Exception as error:print(json.dumps({'error':str(error)}),flush=True)
