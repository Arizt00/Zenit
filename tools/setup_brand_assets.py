"""Pinned, integrity-checked language marks, loaded locally by Laboratory."""
import base64,hashlib,io,json,tarfile,urllib.request,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION='16.0.0'
ICONS={'python':'#3776ab','c':'#33699a','cplusplus':'#00599c','llvm':'#36364d','openjdk':'#007396','docker':'#2496ed','apachemaven':'#c71a36','gradle':'#02303a'}
def get(url,limit=12*1024**2):
 with urllib.request.urlopen(url,timeout=40) as response:
  raw=response.read(limit+1)
  if len(raw)>limit:raise ValueError('Asset download exceeded limit')
  return raw
def main():
 metadata=json.loads(get('https://registry.npmjs.org/simple-icons/'+VERSION));raw=get(metadata['dist']['tarball']);algorithm,value=metadata['dist']['integrity'].split('-',1)
 if algorithm!='sha512' or base64.b64encode(hashlib.sha512(raw).digest()).decode()!=value:raise ValueError('Asset integrity mismatch')
 target=ROOT/'web/assets/languages';target.mkdir(exist_ok=True);records=[]
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
  for name,color in ICONS.items():
   source=archive.extractfile('package/icons/'+name+'.svg').read();svg=ET.fromstring(source)
   if any(node.tag.split('}')[-1] not in ('svg','title','path') for node in svg.iter()):raise ValueError('Unexpected SVG content')
   text=source.decode().replace('<svg ','<svg fill="'+color+'" ',1)
   if name in ('python','openjdk'):
    colors=('#3776ab','#ffd43b') if name=='python' else ('#e35228','#007396')
    gradient=f'<defs><linearGradient id="brand" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="{colors[0]}"/><stop offset=".5" stop-color="{colors[0]}"/><stop offset=".5" stop-color="{colors[1]}"/><stop offset="1" stop-color="{colors[1]}"/></linearGradient></defs>'
    text=text.replace('fill="'+color+'"','fill="url(#brand)"',1);at=text.index('>')+1;text=text[:at]+gradient+text[at:]
   (target/(name+'.svg')).write_text(text,encoding='utf-8');records.append({'icon':name,'originalSha256':hashlib.sha256(source).hexdigest(),'source':metadata['dist']['tarball']})
  license_bytes=archive.extractfile('package/LICENSE.md').read()
 (ROOT/'licenses/simple-icons.txt').write_bytes(license_bytes)
 (target/'sources.json').write_text(json.dumps({'package':'simple-icons','version':VERSION,'integrity':metadata['dist']['integrity'],'use':'Descriptive marks for installed/detected tools; no brand endorsement. Colors applied locally.','icons':records},indent=2)+'\n',encoding='utf-8')
 print('Eight local language/tool marks verified.')
if __name__=='__main__':main()
