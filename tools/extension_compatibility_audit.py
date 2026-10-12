"""Audit real installed packages in disposable trusted projects and profiles.

Activation and command registration are evidence, not complete compatibility.
Never load the user's runtime approvals, workspace, or account credentials.
"""
import argparse,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application
from backend.extension_runtime import Host
from backend.extension_lsp import PyreflyHost
from backend.runtime_paths import find_tool
from backend.extensions import localized_manifest

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--installed',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();results=[]
 for root in sorted(args.installed.glob('*/extension')):
  if not (root/'package.json').is_file():continue
  manifest=localized_manifest(root,'es');eid=manifest.get('publisher','')+'.'+manifest['name'];host=None
  result={'id':eid,'version':manifest['version'],'activation':'pending','commands':0,'providerCount':0,'capabilityCertification':False}
  with tempfile.TemporaryDirectory(prefix='zenit-compat-') as tmp:
   p=Path(tmp);ws=p/'project';ws.mkdir();(ws/'main.js').write_text('const x={a:1,b:2}\n',encoding='utf-8');(ws/'main.py').write_text('value: int = "text"\n',encoding='utf-8')
   app=Application(ROOT,ws,data_dir=p/'profile');app.workspace.trusted=True
   try:
    if eid.lower()=='meta.pyrefly':host=PyreflyHost(root,app.workspace);result['engine']='native-lsp'
    elif manifest.get('main'):
     entry=root/manifest['main'];entry=entry if entry.is_file() else entry.with_suffix('.js')
     options={'extensionId':eid,'manifest':manifest,'extensions':[{'id':eid,'root':str(root),'manifest':manifest}],'dependencies':[],'storage':str(p/'storage'),'locale':'es'}
     host=Host(find_tool('node'),root,entry,app.workspace,options,app.features.extension_services);result['engine']='node'
    else:result['activation']='declarative';continue
    result.update(activation='activated',commands=len(host.capabilities.get('commands',[])),providerCount=len(host.capabilities.get('providers',[])),unsupportedApis=host.capabilities.get('unsupportedApis',[]))
    if eid.lower()=='esbenp.prettier-vscode':
     edits=host.request({'method':'provide','kind':'format','document':{'path':'main.js','text':'const x={a:1,b:2}\n','language':'javascript','dirty':True},'options':{'tabSize':2,'insertSpaces':True}})['items'];result['realFormattingEdits']=len(edits)
    if result['commands']==0 and result['providerCount']==0:result['note']='Activation registered no observable commands/providers; do not certify functionality.'
   except Exception as error:result.update(activation='blocked',error=str(error))
   finally:
    if host:host.close()
    app.features.shutdown();app.runner.shutdown();results.append(result);print(json.dumps(result,ensure_ascii=True),flush=True)
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps({'method':'Isolated local package activation and selected real operations; no global parity percentage.','packages':results},ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
