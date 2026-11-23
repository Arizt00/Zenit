"""Opt-in LAN and public HTTPS restart test; both stations use this machine."""
import argparse,json,shutil,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application
from backend.coco_tunnel import VERSION


def ready(team):
    deadline=time.monotonic()+100
    while time.monotonic()<deadline:
        status=team.status()
        if status['invitation'] and status['connection']['phase']=='ready':return status
        if status['connection']['phase']=='failed':raise AssertionError(status['connection']['error'])
        time.sleep(.15)
    raise TimeoutError('The fixture tunnel did not become ready')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--connector',type=Path,required=True);args=parser.parse_args();checks=[]
    with tempfile.TemporaryDirectory(prefix='zenit-restart-network-',ignore_cleanup_errors=True) as directory:
        base=Path(directory)
        for mode in ('lan','internet'):
            workspace=base/mode;workspace.mkdir();guest_workspace=base/(mode+'-guest');guest_workspace.mkdir();profile=base/(mode+'-profile');guest_profile=base/(mode+'-guest-profile')
            (workspace/'main.py').write_text('from pathlib import Path\np=Path("starts.txt")\np.write_text((p.read_text() if p.exists() else "")+"START\\n")\nprint("RESTART_NETWORK_OK")\n',encoding='utf-8')
            connector=profile/'tools/coco'/VERSION/'cloudflared-windows-amd64.exe';connector.parent.mkdir(parents=True);shutil.copy2(args.connector,connector)
            host=Application(ROOT,workspace,data_dir=profile);host.workspace.trusted=True
            guest=Application(ROOT,guest_workspace,data_dir=guest_profile);guest.workspace.trusted=True
            try:
                host.features.team.start(host.workspace,{'mode':mode,'protocol':2,'shareProject':True,'allowRun':True,'documents':[{'path':'main.py'}]});state=ready(host.features.team)
                guest.features.team.join(guest.workspace,state['invitation']);snapshot=guest.features.team.request({'action':'sync','vectors':{}});peer=snapshot['self']['id']
                host.features.team.request({'action':'permissions','participant':peer,'role':'runner'})
                run=guest.features.team.request({'action':'run','path':'main.py','requestId':'network-restart'});job=host.runner.jobs[run['job']];deadline=time.monotonic()+30
                while not job.done and time.monotonic()<deadline:time.sleep(.03)
                assert job.done and job.code==0;guest.features.team.request({'action':'job','job':run['job']})
                host.features.shutdown();host=Application(ROOT,workspace,data_dir=profile);host.workspace.trusted=True
                assert host.features.team.server is None;host.features.team.recover(host.workspace);recovered=ready(host.features.team)
                assert recovered['room']==state['room']
                guest.features.team.join(guest.workspace,recovered['invitation']);snapshot=guest.features.team.request({'action':'sync','vectors':{}})
                assert snapshot['self']['id']==peer and snapshot['self']['role']=='runner'
                checks.append(mode+': host restart and endpoint recovery retain the room, identity and permissions')
                retry=guest.features.team.request({'action':'run','path':'main.py','requestId':'network-restart'})
                assert retry['job']==run['job'] and not host.runner.jobs
                assert 'RESTART_NETWORK_OK' in guest.features.team.request({'action':'job','job':run['job']})['output']
                assert (workspace/'starts.txt').read_text()=='START\n';checks.append(mode+': retry reads the persisted output and never starts a second program')
                guest.features.shutdown();guest=Application(ROOT,guest_workspace,data_dir=guest_profile);guest.workspace.trusted=True
                guest.features.team.recover(guest.workspace);snapshot=guest.features.team.request({'action':'sync','vectors':{}})
                assert snapshot['self']['id']==peer and snapshot['self']['role']=='runner';checks.append(mode+': restarted native guest resumes the same participant')
            finally:guest.features.shutdown();host.features.shutdown()
    output=ROOT/'qa-output/coco-persistence-network.json';output.write_text(json.dumps({'checks':checks,'errors':[],'distinctPhysicalStations':False,'scope':'LAN interface and public HTTPS endpoint exercised by two clients on this station.'},indent=2),encoding='utf-8')
    for check in checks:print('PASS',check,flush=True)


if __name__=='__main__':main()
