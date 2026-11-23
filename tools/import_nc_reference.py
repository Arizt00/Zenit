"""Extract declarations, never execute or modify the selected JetBrains distribution."""
import argparse,hashlib,io,json,zipfile,re,xml.etree.ElementTree as ET
from pathlib import Path

def extract(path):
    raw=Path(path).read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        name=next(n for n in archive.namelist() if re.search(r'/lib/nc-language-plugin-[^/]+\.jar$',n))
        jar=archive.read(name)
    with zipfile.ZipFile(io.BytesIO(jar)) as archive:root=ET.fromstring(archive.read('META-INF/plugin.xml'))
    return {'schema':1,'filename':Path(path).name,'sha256':hashlib.sha256(raw).hexdigest(),'jarSha256':hashlib.sha256(jar).hexdigest(),
        'id':root.findtext('id'),'version':root.findtext('version'),
        'declarations':[{'point':e.tag,**e.attrib} for e in root.find('extensions')],
        'actions':[{'id':e.get('id'),'text':e.get('text')} for e in root.findall('./actions/action')]}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('distribution');parser.add_argument('--output',required=True);args=parser.parse_args()
    Path(args.output).write_text(json.dumps(extract(args.distribution),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
