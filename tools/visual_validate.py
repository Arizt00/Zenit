"""Geometry gates for canonical pillars; pixel similarity needs human review."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def validate(folder):
 data=json.loads((folder/'baseline.json').read_text(encoding='utf-8'));gold=json.loads((ROOT/'tests/visual/geometry.json').read_text());checks=[];failures=[]
 for view,targets in gold['screens'].items():
  for selector,expected in targets.items():
   actual=data['geometry'][view][selector];delta=[round(actual[key]-value,3) for key,value in zip(('x','y','width','height'),expected)]
   checks.append({'view':view,'selector':selector,'delta':delta,'withinTolerance':max(map(abs,delta))<=gold['tolerance']})
   if not checks[-1]['withinTolerance']:failures.append(checks[-1])
 if data['errors']:failures.append({'uncaughtJavaScript':data['errors']})
 result={'toleranceCssPixels':gold['tolerance'],'checks':checks,'failures':failures,'status':'pass' if not failures else 'fail','interpretation':'Only major composition bounds. Not a pixel fidelity certificate.'}
 (folder/'geometry-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');return result
def main():
 p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--matrix',action='store_true');a=p.parse_args()
 if a.matrix:
  data=json.loads((a.folder/'matrix.json').read_text());bad=[]
  for case in data['results']:
   if case['errors']:bad.append(case)
   for screen,state in case['overflow'].items():
    if any(state[k] for k in ('html','body','topbar')) or(screen=='editor' and state['editorWidth']<100):bad.append({'case':case['physical'],'scale':case['scale'],'screen':screen,'state':state})
  print(json.dumps({'cases':len(data['results']),'failures':bad},indent=2));raise SystemExit(bool(bad))
 result=validate(a.folder);print(json.dumps(result,indent=2));raise SystemExit(bool(result['failures']))
if __name__=='__main__':main()
