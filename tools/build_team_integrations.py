"""Build local VSIX and JetBrains archives; never install or publish them."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SDK='252.28539.108'

def vscode(out):
    source=ROOT/'integrations/team-vscode';target=out/'zenit-team-0.2.2.vsix'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        for file in source.rglob('*'):
            if file.is_file():archive.write(file,'extension/'+file.relative_to(source).as_posix())
        archive.write(ROOT/'LICENSE','extension/LICENSE')
        archive.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="json" ContentType="application/json"/><Default Extension="cjs" ContentType="application/javascript"/><Default Extension="vsixmanifest" ContentType="text/xml"/></Types>')
        archive.writestr('extension.vsixmanifest','<?xml version="1.0"?><PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011"><Metadata><Identity Language="es-ES" Id="zenit-team" Version="0.2.2" Publisher="zenit"/><DisplayName>Co-Code</DisplayName><Description xml:space="preserve">Edición simultánea con Zénit.</Description></Metadata><Installation><InstallationTarget Id="Microsoft.VisualStudio.Code"/></Installation><Dependencies/><Assets><Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/></Assets></PackageManifest>')
    return target

def jetbrains(out):
    cache=ROOT/'qa-output/team-sdk';cache.mkdir(parents=True,exist_ok=True)
    names=['core','ide-core','ide','ui-jcef','util','util-ui','core-ui','util-rt','util-ex','extensions','project-model']
    def download(name):
        target=cache/(name+'.jar')
        if not target.exists():
            url=f'https://www.jetbrains.com/intellij-repository/releases/com/jetbrains/intellij/platform/{name}/{SDK}/{name}-{SDK}.jar'
            with urllib.request.urlopen(url,timeout=45) as response:target.write_bytes(response.read())
        return target
    with ThreadPoolExecutor(max_workers=4) as pool:jars=list(pool.map(download,names))
    annotations=cache/'annotations.jar'
    if not annotations.exists():
        with urllib.request.urlopen('https://repo.maven.apache.org/maven2/org/jetbrains/annotations/26.0.2/annotations-26.0.2.jar',timeout=30) as response:annotations.write_bytes(response.read())
    jars.append(annotations);classes=cache/'classes';classes.mkdir(exist_ok=True)
    source=ROOT/'integrations/team-jetbrains/src/main';subprocess.run(['javac','--release','21','-classpath',os.pathsep.join(map(str,jars)),'-d',str(classes),str(source/'java/studio/zenit/team/TeamToolWindow.java')],check=True)
    jar=cache/'zenit-team.jar'
    with zipfile.ZipFile(jar,'w',zipfile.ZIP_DEFLATED) as archive:
        for directory in [classes,source/'resources']:
            for path in directory.rglob('*'):
                if path.is_file():archive.write(path,path.relative_to(directory).as_posix())
        archive.write(ROOT/'LICENSE','META-INF/LICENSE')
    target=out/'zenit-team-jetbrains-0.1.0.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:archive.write(jar,'zenit-team/lib/zenit-team.jar')
    prebuilt=ROOT/'integrations/team-jetbrains/prebuilt';prebuilt.mkdir(exist_ok=True)
    (prebuilt/'zenit-team.jar').write_bytes(jar.read_bytes())
    sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}
    (prebuilt/'manifest.json').write_text(json.dumps({'sdk':SDK,'jarSha256':hashlib.sha256(jar.read_bytes()).hexdigest(),'sources':sources},indent=2),encoding='utf-8')
    (cache/'sdk-manifest.json').write_text(json.dumps({'sdk':SDK,'jars':[{'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in jars]},indent=2))
    return target

def validated_jetbrains(out):
    prebuilt=ROOT/'integrations/team-jetbrains/prebuilt';metadata=json.loads((prebuilt/'manifest.json').read_text(encoding='utf-8'));jar=prebuilt/'zenit-team.jar'
    actual={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'integrations/team-jetbrains/src/main').rglob('*') if p.is_file()}
    if metadata['sources']!=actual or hashlib.sha256(jar.read_bytes()).hexdigest()!=metadata['jarSha256']:
        raise ValueError('El conector JetBrains cambió. Recompila con --jetbrains antes de empaquetar.')
    target=out/'zenit-team-jetbrains-0.1.0.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:archive.write(jar,'zenit-team/lib/zenit-team.jar')
    return target


def build_all(recompile=False):
    out=ROOT/'dist/integrations';out.mkdir(parents=True,exist_ok=True)
    return [vscode(out),jetbrains(out) if recompile else validated_jetbrains(out)]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--jetbrains',action='store_true',help='Recompile against the pinned official SDK');args=parser.parse_args()
    for output in build_all(args.jetbrains):print(output,flush=True)

if __name__=='__main__':main()
