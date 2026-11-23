"""Opt-in real VS Code extension runner using a disposable profile."""
import argparse,json,os,subprocess,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--r17',action='store_true');args=parser.parse_args()
    code=Path(os.environ['LOCALAPPDATA'])/'Programs/Microsoft VS Code/Code.exe'
    with tempfile.TemporaryDirectory(prefix='zenit-vscode-team-',ignore_cleanup_errors=True) as temp:
        base=Path(temp);ws=base/'project';ws.mkdir();(ws/'main.py').write_text('print("team")\n',encoding='utf-8')
        app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True
        try:
            (ws/'library.py').write_text('VALUE=42\n');status=app.features.team.start(app.workspace,{'protocol':2 if args.r17 else 1,'shareProject':args.r17,'documents':[{'path':'main.py'}],'allowRun':True});report=ROOT/('qa-output/r17-vscode-team.json' if args.r17 else 'qa-output/r15-vscode-team.json');config=base/'test.json';config.write_text(json.dumps({'invitation':status['invitation'],'report':str(report),'protocol':2 if args.r17 else 1}),encoding='utf-8')
            if args.r17:
                def grant():
                    deadline=time.monotonic()+70
                    while time.monotonic()<deadline:
                        members=list(app.features.team.room.project.members.values())
                        if members:
                            app.features.team.request({'action':'permissions','participant':members[0]['id'],'role':'runner'});return
                        time.sleep(.1)
                threading.Thread(target=grant,daemon=True).start()
            profile=base/'vscode';(profile/'User').mkdir(parents=True);(profile/'User/settings.json').write_text(json.dumps({'telemetry.telemetryLevel':'off','update.mode':'none','workbench.startupEditor':'none'}),encoding='utf-8')
            result=subprocess.run([str(code),'--user-data-dir='+str(profile),'--extensions-dir='+str(base/'extensions'),'--extensionDevelopmentPath='+str(ROOT/'integrations/team-vscode'),'--extensionTestsPath='+str(ROOT/'tests/vscode_team_suite.cjs'),'--skip-welcome','--skip-release-notes','--disable-workspace-trust','--disable-updates','--disable-extensions','--disable-gpu'],env={**os.environ,'ZENIT_TEAM_TEST':str(config)},capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=100)
            print(result.stdout);print(result.stderr);assert result.returncode==0,result.returncode
            assert '# VS Code 🙂' in (ws/'main.py').read_text(encoding='utf-8');assert '# Zénit λ' in (ws/'main.py').read_text(encoding='utf-8');print(report.read_text(encoding='utf-8'))
        finally:app.features.shutdown();app.runner.shutdown()
if __name__=='__main__':main()
