"""Prepare the Windows native tool dependency closure and corresponding sources."""
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,re,shutil,stat,urllib.request,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def fields(path):
    values={};key=None
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('%'):key=line.strip('%');values[key]=[]
        elif line and key:values[key].append(line)
    return values

def download(url,path):
    if not path.is_file():
        temp=path.with_suffix(path.suffix+'.part')
        with urllib.request.urlopen(url,timeout=90) as source,temp.open('wb') as out:shutil.copyfileobj(source,out)
        temp.replace(path)
    return {'file':path.name,'url':url,'sha256':hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),'bytes':path.stat().st_size}

def prepare(nc_root):
    base=ROOT/'sdk/foundation';target=base/'native-mingw';target.mkdir(exist_ok=True)
    packages={}
    for entry in Path('C:/msys64/var/lib/pacman/local').glob('mingw-w64-ucrt-x86_64-*'):
        data=fields(entry/'desc');packages[data['NAME'][0]]=(entry,data)
    for entry,data in list(packages.values()):
        for name in data.get('PROVIDES',[]):packages.setdefault(re.split('[<>=]',name)[0],(entry,data))
    names=['mingw-w64-ucrt-x86_64-'+x for x in ('gcc','gdb','cmake','ninja')];closure={}
    while names:
        name=names.pop()
        if name in closure:continue
        entry,data=packages[name];name=data['NAME'][0]
        if name in closure:continue
        closure[name]=(entry,data)
        names.extend(re.split('[<>=]',x)[0] for x in data.get('DEPENDS',[]) if x.startswith('mingw-w64-ucrt-x86_64-'))
    records=[];sources=base/'native-sources';sources.mkdir(exist_ok=True)
    for name,(entry,data) in sorted(closure.items()):
        count=0
        for relative in fields(entry/'files')['FILES']:
            if not relative.startswith('ucrt64/') or relative.endswith('/'):continue
            file=Path('C:/msys64')/relative
            if not file.is_file():continue
            destination=target/relative.removeprefix('ucrt64/');destination.parent.mkdir(parents=True,exist_ok=True)
            if not destination.is_file() or (destination.stat().st_size,destination.stat().st_mtime_ns)!=(file.stat().st_size,file.stat().st_mtime_ns):
                if destination.exists():destination.chmod(destination.stat().st_mode|stat.S_IWRITE)
                shutil.copy2(file,destination)
            count+=1
        records.append({'name':name,'base':data['BASE'][0],'version':data['VERSION'][0],'licenses':data.get('LICENSE',[]),'files':count})
    with urllib.request.urlopen('https://repo.msys2.org/mingw/sources/',timeout=60) as response:listing=response.read().decode()
    links=re.findall(r'href="([^"]+)"',listing)
    archives=[]
    for item in records:
        prefix=item['base']+'-'+item['version']+'.src.tar.'
        matches=[name for name in links if name.startswith(prefix) and not name.endswith('.sig')]
        if not matches:raise ValueError('Source archive unavailable: '+prefix)
        archives.append(matches[0])
    archives=sorted(set(archives))
    def fetch(name):
        result=download('https://repo.msys2.org/mingw/sources/'+name,sources/name);print('Source:',name,result['bytes'],flush=True);return result
    with ThreadPoolExecutor(max_workers=4) as pool:source_records=list(pool.map(fetch,archives))
    (sources/'PACKAGE_INVENTORY.json').write_text(json.dumps(records,indent=2),encoding='utf-8');(sources/'SOURCE_INDEX.json').write_text(json.dumps(source_records,indent=2),encoding='utf-8')
    llvm=base/'llvm';llvm.mkdir(exist_ok=True)
    download('https://raw.githubusercontent.com/llvm/llvm-project/llvmorg-22.1.6/LICENSE.TXT',llvm/'LICENSE.TXT')
    nasm=base/'nasm';nasm.mkdir(exist_ok=True)
    archive=sources/'nasm-2.16.03-win64.zip';record=download('https://www.nasm.us/pub/nasm/releasebuilds/2.16.03/win64/'+archive.name,archive)
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            if not member.is_dir():
                path=nasm/Path(member.filename).name;path.write_bytes(z.read(member))
    (nasm/'SOURCE.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    for name in ('LICENSE','LICENSE-MIT','LICENSE-APACHE','NOTICE'):
        if (nc_root/name).is_file():shutil.copy2(nc_root/name,base/'nc'/name)
    index=json.loads((base/'tool-index.json').read_text(encoding='utf-8'))
    for name in ('gcc','g++','gdb','cmake','ninja','as','ar'):index['tools'][name]='native-mingw/bin/'+name+'.exe'
    index['tools']['nasm']='nasm/nasm.exe';index['tools']['pylsp']='python/Scripts/pylsp.exe'
    index['components']=[x for x in index['components'] if x['id']!='nasm']+[{'id':'nasm','version':'2.16.03','license':'BSD-2-Clause','includes':['x86','x86_64']}]
    (base/'tool-index.json').write_text(json.dumps(index,indent=2),encoding='utf-8')
    print('Prepared',len(records),'native packages and',len(source_records),'source archives.',flush=True)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--nc-root',type=Path,required=True);prepare(parser.parse_args().nc_root)
