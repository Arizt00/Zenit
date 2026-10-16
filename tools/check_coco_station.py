"""Run a fixture-only CoCo acceptance test on separate OS stations.

Host: python tools/check_coco_station.py host --mode lan --exchange qa-output/lan
Peer: python tools/check_coco_station.py join --invitation-file invitation.json --report peer.json
The peer rejects this same computer unless --allow-same-station is explicit.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import time
import uuid
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.team import TeamService,encode,decode


def station_id():
    return hashlib.sha256((socket.gethostname()+':'+str(uuid.getnode())).encode()).hexdigest()[:24]


def write_report(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


def host(args):
    from backend.server import Application
    from backend.coco_tunnel import VERSION
    args.exchange.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='zenit-coco-station-probe-') as temp:
        base=Path(temp);ws=base/'fixture';ws.mkdir();documents=[]
        for name in ('station_a.py','station_b.py'):
            source=f'''# ZENIT_COCO_STATION_PROBE {station_id()}
import json,os,socket,time
from pathlib import Path
p=Path({(name+'.starts')!r})
with p.open('a') as f:f.write(str(os.getpid())+chr(10))
print(json.dumps(dict(marker='COCO_STATION_EXECUTION',station=socket.gethostname(),pid=os.getpid(),starts=len(p.read_text().splitlines()))),flush=True)
time.sleep(2)
'''
            (ws/name).write_text(source,encoding='utf-8');documents.append({'path':name,'text':'# HOST_UNSAVED\n'+source})
        app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True
        if args.connector:
            target=app.features.prefs.directory/'tools/coco'/VERSION/args.connector.name;target.parent.mkdir(parents=True);shutil.copy2(args.connector,target)
        report={'mode':args.mode,'hostStation':station_id(),'hostName':socket.gethostname(),'checks':[],'errors':[]}
        try:
            state=app.features.team.start(app.workspace,{'documents':documents,'mode':args.mode,'allowRun':True});deadline=time.monotonic()+100
            while state['connection']['phase'] not in ('ready','failed') and time.monotonic()<deadline:time.sleep(.2);state=app.features.team.status()
            if state['connection']['phase']!='ready':raise RuntimeError(state['connection'].get('error') or 'Transport not ready')
            write_report(args.exchange/'invitation.json',{'invitation':state['invitation'],'hostStation':station_id(),'mode':args.mode})
            print('READY: copy invitation.json to the other station; only fixture files are shared.',flush=True)
            print('Endpoint:',state['invitation'].split('#')[0],flush=True)
            deadline=time.monotonic()+args.seconds
            while time.monotonic()<deadline:
                if any(c['label']=='STATION_PROBE_COMPLETE' for c in app.features.team.room.checkpoints):break
                time.sleep(.2)
            else:raise TimeoutError('No completed peer proof received; this is not a two-station pass.')
            jobs=[app.runner.jobs[j] for j in app.features.team.room.jobs]
            if len(jobs)!=2 or not all(j.done and j.code==0 for j in jobs):raise AssertionError('Expected exactly two completed jobs, one per shared file.')
            for name in ('station_a.py','station_b.py'):
                if len((ws/(name+'.starts')).read_text().splitlines())!=1:raise AssertionError('Duplicate process: '+name)
                if '# PEER_UNICODE' not in (ws/name).read_text(encoding='utf-8'):raise AssertionError('Peer edit not saved on host: '+name)
            report.update(room=state['room'],processes=2,checks=['Two files saved on the host with concurrent Unicode edits','Eight run intents converged to one process per file','Completed run retries returned existing jobs'])
        except Exception as error:report['errors'].append(str(error));raise
        finally:
            app.features.shutdown();app.runner.shutdown();write_report(args.exchange/'host-report.json',report)


def join(args):
    from pycrdt import Doc,Text
    invitation=json.loads(args.invitation_file.read_text(encoding='utf-8'));url=urlsplit(invitation['invitation'])
    if url.scheme not in ('http','https') or not url.hostname or url.username or url.path not in ('','/') or not 32<=len(url.fragment)<=100:raise ValueError('Invalid fixture invitation')
    distinct=invitation['hostStation']!=station_id()
    if not distinct and not args.allow_same_station:raise ValueError('This is the host computer. Use a different station; same-station tests do not validate two machines.')
    wire=TeamService(None);remote=(url._replace(fragment='',path='/v1').geturl(),url.fragment);peer=uuid.uuid4().hex
    def request(body):return wire.contact(remote,{'peer':peer,'name':'Station acceptance probe','station':socket.gethostname(),'vectors':{},**body})
    result=request({'action':'sync'});room=result['room'];paths={'station_a.py','station_b.py'}
    if set(result['paths'])!=paths:raise ValueError('Use the fixture host command, not a session containing personal project files.')
    updates={}
    for path in paths:
        doc=Doc({'text':Text()});doc.apply_update(decode(result['updates'][path]))
        if '# ZENIT_COCO_STATION_PROBE '+invitation['hostStation'] not in str(doc['text']) or '# HOST_UNSAVED' not in str(doc['text']):raise ValueError('Unexpected fixture source')
        before=doc.get_state();doc['text'].insert(0,'# PEER_UNICODE 🙂 λ\n');updates[path]=encode(doc.get_update(before))
    synced=request({'action':'sync','updates':updates});assert synced['room']==room
    for path in paths:assert '# PEER_UNICODE' in request({'action':'save','path':path})['text']
    intents=[{'action':'run','path':path,'requestId':peer+':'+path+':'+str(i)} for path in sorted(paths) for i in range(4)]
    with ThreadPoolExecutor(max_workers=8) as pool:runs=list(pool.map(request,intents))
    jobs={path:{r['job'] for r in runs if r['path']==path} for path in paths};assert all(len(ids)==1 for ids in jobs.values())
    output={}
    for path,ids in jobs.items():
        identity=next(iter(ids));offset=0;text='';deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            data=request({'action':'job','job':identity,'offset':offset});text+=data['output'];offset=data['offset']
            if data['done'] and not data['more']:assert data['code']==0;break
            time.sleep(.1)
        else:raise TimeoutError('Host execution did not complete')
        assert 'COCO_STATION_EXECUTION' in text and '"starts": 1' in text;output[path]=text
    for intent,first in zip(intents,runs):assert request(intent)['job']==first['job']
    state=request({'action':'sync'});assert state['room']==room and all(state['executions'][p]['job']==next(iter(jobs[p])) for p in paths)
    request({'action':'checkpoint','label':'STATION_PROBE_COMPLETE'})
    write_report(args.report,{'room':room,'distinctStation':distinct,'scope':'Distinct OS stations; physical hardware inventory is not independently attested.' if distinct else 'Same-station development check; NOT a two-machine validation.','station':station_id(),'hostStation':invitation['hostStation'],'mode':invitation['mode'],'checks':['Same room and two shared files','Unicode edits and host-only saves','One host process per file under eight concurrent run intents','Retry after completion does not restart processes','Shared output and execution identities converge'],'output':output,'errors':[]})
    print('PASS fixture protocol; distinct station:',distinct,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    h=commands.add_parser('host');h.add_argument('--mode',choices=['lan','internet'],required=True);h.add_argument('--exchange',type=Path,required=True);h.add_argument('--connector',type=Path);h.add_argument('--seconds',type=int,default=300)
    p=commands.add_parser('join');p.add_argument('--invitation-file',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--allow-same-station',action='store_true')
    args=parser.parse_args()
    if args.command=='host' and not 10<=args.seconds<=3600:parser.error('seconds must be 10–3600')
    (host if args.command=='host' else join)(args)


if __name__=='__main__':main()
