"""Explicit live test: local NIC and temporary public HTTPS, using fixture code."""
import argparse,json,shutil,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application
from backend.coco_tunnel import VERSION
from backend.team import encode,decode
from pycrdt import Doc,Text


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--connector',type=Path,required=True);parser.add_argument('--report',type=Path,required=True);args=parser.parse_args();checks=[]
    with tempfile.TemporaryDirectory(prefix='zenit-coco-stations-') as temp:
        base=Path(temp);ws=base/'host';ws.mkdir();(ws/'shared.py').write_text('print("COCO_NETWORK_EXECUTION")\n',encoding='utf-8');other=base/'guest';other.mkdir()
        host=Application(ROOT,ws,data_dir=base/'host-profile');guest=Application(ROOT,other,data_dir=base/'guest-profile');host.workspace.trusted=guest.workspace.trusted=True
        connector=host.features.prefs.directory/'tools/coco'/VERSION/'cloudflared-windows-amd64.exe';connector.parent.mkdir(parents=True);shutil.copy2(args.connector,connector)
        try:
            for mode in ('lan','internet'):
                state=host.features.team.start(host.workspace,{'documents':[{'path':'shared.py'}],'mode':mode,'allowRun':True});room=state['room'];deadline=time.monotonic()+100
                while state['connection']['phase'] not in ('ready','failed') and time.monotonic()<deadline:time.sleep(.2);state=host.features.team.status()
                assert state['connection']['phase']=='ready',state['connection']
                if mode=='internet':assert state['invitation'].startswith('https://')
                else:assert not state['invitation'].startswith('http://127.')
                guest.features.team.join(guest.workspace,state['invitation']);data=guest.features.team.request({'peer':'station-guest','name':'Estación invitada','vectors':{}});assert data['room']==room
                doc=Doc({'text':Text()});doc.apply_update(decode(data['updates']['shared.py']));before=doc.get_state();doc['text'].insert(0,'# '+mode+' 🙂\n')
                guest.features.team.request({'peer':'station-guest','vectors':{},'updates':{'shared.py':encode(doc.get_update(before))}});saved=guest.features.team.request({'action':'save','path':'shared.py'});assert '# '+mode+' 🙂' in saved['text'];assert not (other/'shared.py').exists()
                run=guest.features.team.request({'action':'run','path':'shared.py'});job=host.runner.jobs[run['job']]
                while not job.done and time.monotonic()<deadline:time.sleep(.05)
                assert job.code==0 and 'COCO_NETWORK_EXECUTION' in job.output
                peers=host.features.team.request({'peer':'station-host','vectors':{}})['peers'];assert any(p['station'] for p in peers if p['id']=='station-guest')
                tunnel=host.features.team.tunnel;host.features.team.stop();assert not tunnel or tunnel.process.poll() is not None
                try:guest.features.team.request({'peer':'revoked','vectors':{}})
                except (OSError,ValueError):pass
                else:raise AssertionError('The stopped session remained available')
                guest.features.team.stop();checks.append(mode+': same room, Unicode edits, host-only save, shared execution, station identity and revocation');print('PASS',checks[-1],flush=True)
        finally:guest.features.shutdown();guest.runner.shutdown();host.features.shutdown();host.runner.shutdown()
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps({'checks':checks,'errors':[],'scope':'Both clients run on this host; LAN uses its non-loopback interface and Internet crosses the public HTTPS tunnel.'},indent=2),encoding='utf-8')

if __name__=='__main__':main()
