"""Repeatable local journeys on disposable starter projects, never user sources.

Evidence is tied to the runtime configuration and executable identity. A declared
provider, a missing prerequisite and a successful behavior are separate states.
"""
import copy,hashlib,json,threading,time,tempfile,re
from pathlib import Path
from concurrent.futures import CancelledError
from .preferences import atomic_json
from .runtime_paths import find_tool
from .foundation import tool_environment
from .project_kits import KITS

STEPS=('project','navigation','rename','build','test','debug')
TOOLS=('gcc','g++','cmake','ninja','ctest','python','pylsp','clangd','rustc','cargo','rust-analyzer','nasm','asm-lsp','javac','java','jdtls','ncc','ncc-lsp','lldb-dap','node')
SERVERS={'c':('clangd',['--background-index=false']),'cpp':('clangd',['--background-index=false']),'python':('pylsp',[]),'rust':('rust-analyzer',[]),'java':('jdtls',[]),'asm':('asm-lsp',[]),'nc':('ncc-lsp',[])}

def signature(features):
    rows=[]
    for name in TOOLS:
        path=find_tool(name,features.runtimes.config.get('tools'))
        try:s=Path(path).stat();rows.append((name,path,s.st_size,s.st_mtime_ns))
        except (OSError,TypeError):rows.append((name,None))
    installed=features.extensions.installed
    packages=[(key,item.get('sha256'),item.get('version'),item.get('enabled')) for key,item in sorted(installed.items())]
    return hashlib.sha256(json.dumps([features.runtimes.config,rows,packages],sort_keys=True).encode()).hexdigest()

def reference(features):
    path=features.app.project/'config/nc-language-reference.json'
    data=json.loads(path.read_text(encoding='utf-8'));rows=[]
    equivalents={
      'fileType':('adapted','Familias e iconos del JAR seleccionado'),
      'lang.parserDefinition':('missing','El PSI de IntelliJ no se ejecuta en Monaco; la semántica se consulta a NCC'),
      'lang.syntaxHighlighterFactory':('adapted','Gramática y paleta exportadas del plugin'),
      'lang.braceMatcher':('adapted','Configuración de parejas de Monaco'),
      'colorSettingsPage':('adapted','Temas y estilos semánticos'),
      'completion.contributor':('adapted','Proveedor de la extensión nC'),
      'codeInsight.inlayProvider':('adapted','Proveedor de pistas en línea'),
      'lang.documentationProvider':('adapted','Documentación de la extensión'),
      'gotoDeclarationHandler':('adapted','Ámbitos locales y resolución de importaciones de la extensión; no equivale a semántica global de IntelliJ'),
      'annotator':('adapted','Diagnósticos mediante NCC y su broker'),
      'editorFactoryListener':('adapted','Edición y autoimportación de la extensión; requiere prueba específica'),
      'configurationType':('native','Perfil de ejecución de Zénit'),
      'runConfigurationProducer':('native','Plan de compilación NCC por proyecto'),
      'programRunner':('native','NCC y adaptador de depuración, según la familia'),
    }
    for item in data['declarations']:
        mode,route=equivalents.get(item['point'],('missing','Sin equivalente declarado'))
        rows.append({**item,'mode':mode,'route':route,'verification':'not-tested'})
    packages=[]
    for key,item in features.extensions.installed.items():
        if key.casefold()!='nc-lang.nc-language':continue
        try:
            manifest=json.loads((features.extensions.root/item['directory']/'extension/package.json').read_text(encoding='utf-8'))
            source=manifest.get('zenitJetBrainsVisual',{})
            packages.append({'id':key,'version':manifest.get('version'),'matchesReference':source.get('sha256')==data['sha256'] and source.get('jarSha256')==data['jarSha256'],'enabled':item.get('enabled',False)})
        except (OSError,ValueError):pass
    actions=[]
    for item in data.get('actions',[]):
        mode,route=('adapted','Selección del backend semántico en la extensión') if item['id']=='Nc.RouteLsp' else ('native',{'Nc.ResolveToolchain':'SDK y ruta del compilador NCC','Nc.RunActiveFile':'Destino común y plan de ejecución NCC','Nc.DebugActiveFile':'Sesión de depuración real de Zénit'}.get(item['id'],'Requiere revisión'))
        actions.append({**item,'mode':mode,'route':route,'verification':'not-tested'})
    return {**data,'declarations':rows,'actions':actions,'installed':packages,'notice':'Declaraciones del plugin elegido y su equivalente. Adaptado no significa verificado. El PSI y los servicios de IntelliJ no se ejecutan dentro de Zénit.'}

class LanguageVerification:
    def __init__(self,features):self.f=features;self.root=features.prefs.directory/'language-verification';self.lock=threading.RLock()

    def snapshot(self):
        current=signature(self.f);rows=[]
        for lang,item in KITS.items():
            file=self.root/(lang+'.json');report=None
            try:
                if file.is_file() and not file.is_symlink() and file.stat().st_size<200000:report=json.loads(file.read_text(encoding='utf-8'))
            except (OSError,ValueError):pass
            rows.append({'id':lang,'label':item['label'],'report':report,'stale':bool(report and report.get('signature')!=current)})
        return {'languages':rows,'nc':reference(self.f),'scope':'Este equipo · proyectos de muestra desechables. No certifica WSL, SSH, todas las arquitecturas ni el proyecto del usuario.'}

    def submit(self,ws,body):
        if not ws.trusted or body.get('consent') is not True:raise PermissionError('Revisa y autoriza el recorrido de muestra.')
        lang=body.get('language')
        if lang not in KITS:raise ValueError('Selecciona un lenguaje del catálogo.')
        self.f.execution.require_local(ws,'La comprobación del recorrido de lenguaje')
        stamp=signature(self.f);config=copy.deepcopy(self.f.runtimes.config)
        return self.f.hilo.submit('Verificar recorrido · '+KITS[lang]['label'],lambda event:self.verify(lang,config,stamp,event),workspace=ws.root,key='language-verification:'+lang,priority=2)

    def verify(self,lang,config,stamp,event):
        from .server import Application
        report={'schema':1,'language':lang,'checkedAt':time.time(),'signature':stamp,'steps':[], 'scope':'local-fixture','fixtureSha256':None}
        def record(name,status,detail,started=None):
            if any(s['id']==name for s in report['steps']):return
            report['steps'].append({'id':name,'status':status,'detail':str(detail)[:1800],'durationMs':round((time.perf_counter()-started)*1000,2) if started else 0})
        with tempfile.TemporaryDirectory(prefix='zenit-language-check-',ignore_cleanup_errors=True) as directory:
            root=Path(directory);project=root/'Project with spaces';project.mkdir();app=Application(self.f.app.project,project,data_dir=root/'profile');f=app.features;ws=app.workspace;ws.trusted=True
            # Only standard fixture profiles. A custom absolute build/run command
            # could write outside this disposable workspace, so never invoke it.
            f.runtimes.config={'tools':copy.deepcopy(config.get('tools',{})),'languages':{}}
            debugger=None
            def execute(commands,timeout=90):
                if event.is_set():raise CancelledError()
                task=app.runner.start(commands,project,timeout=timeout,env=tool_environment());job=app.runner.jobs[task['job']];deadline=time.monotonic()+timeout+5
                while not job.done:
                    if event.is_set() or time.monotonic()>deadline:job.cancel();raise CancelledError() if event.is_set() else ValueError('El ensayo excedió su presupuesto de tiempo.')
                    time.sleep(.025)
                if job.code:raise ValueError(job.output[-1600:] or 'La herramienta terminó con código '+str(job.code))
                return job.output
            try:
                started=time.perf_counter();kit=KITS[lang]
                if lang=='nc':
                    compiler=f.runtimes.executable('ncc');execute([[compiler,'package','init','sample','--path',str(project/'sample')]],30)
                    manifest=json.loads((project/'sample/ncc.package.json').read_text());entry='sample/'+manifest['targets']['main']
                else:
                    for name,text in kit['files'].items():file=project/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(text,encoding='utf-8',newline='')
                    entry=kit['entry']
                    # Several distinct executable lines make stepping observable.
                    if lang=='c':(project/entry).write_text('#include <stdio.h>\n#include "app.h"\nint main(void) {\n    int result = answer();\n    printf("%d\\n", result);\n    return 0;\n}\n')
                    elif lang=='cpp':(project/entry).write_text('#include <iostream>\n#include "app.hpp"\nint main() {\n    int result = zenit::answer();\n    std::cout << result << "\\n";\n    return 0;\n}\n')
                    elif lang=='java':
                        java=project/entry;java.write_text(java.read_text().replace('public static void main(String[] args) { System.out.println(answer()); }','public static void main(String[] args) {\n        int result = answer();\n        System.out.println(result);\n        result++;\n    }'))
                file=project/entry;source=file.read_text(encoding='utf-8');ws.read(entry)
                report['fixtureSha256']=hashlib.sha256(source.encode()).hexdigest();record('project','passed','Proyecto abierto y archivo leído con la estructura nativa de '+kit['label'],started)
                self.semantic(f,ws,lang,file,source,record,event)
                started=time.perf_counter();plan=f.runtimes.plan(ws,entry);output=execute(plan['commands']);record('build','passed','Compilación y ejecución correctas. '+output[-700:],started)
                started=time.perf_counter()
                try:
                    folder=project/plan['layout']['directory']
                    if lang in ('c','cpp'):
                        commands=[[f.runtimes.executable('cmake'),'--build',str(folder),'--parallel','2'],[f.runtimes.executable('ctest'),'--test-dir',str(folder),'--output-on-failure']]
                    elif lang=='python':commands=[[f.runtimes.executable('python'),'-m','unittest','discover','-s',str(project/'tests')]]
                    elif lang=='rust':commands=[[f.runtimes.executable('cargo'),'test','--manifest-path',str(project/'Cargo.toml'),'--target-dir',str(folder/'cargo-target'),'--tests','--config','build.rustc='+json.dumps(f.runtimes.executable('rustc')),'--color','never']]
                    elif lang=='java':
                        classes=folder/'test-classes';classes.mkdir(exist_ok=True)
                        commands=[[f.runtimes.executable('javac'),'-sourcepath',str(project/'src/main/java'),'-d',str(classes),str(file),str(project/'src/test/java/app/MainTest.java')],[f.runtimes.executable('java'),'-cp',str(classes),'app.MainTest']]
                    elif lang=='nc':commands=[[f.runtimes.executable('ncc'),'test',str(file),'--show-return']]
                    elif lang=='asm':commands=[[str(plan['target'])]]
                    else:commands=[]
                    if commands:record('test','passed',('Prueba de humo de salida correcta; no es una suite de aserciones. ' if lang in ('asm','nc') else '')+execute(commands)[-900:],started)
                    else:record('test','missing','No hay suite de aserciones integrada en esta muestra; ejecutar con código 0 no sustituye una prueba.',started)
                except (ValueError,OSError) as error:record('test','failed',error,started)
                started=time.perf_counter();debugger=f.debugger
                try:
                    points={'java':[5],'asm':[6]}.get(lang,[])
                    debugger.start(ws,entry,points);deadline=time.monotonic()+75;state=debugger.snapshot()
                    while state['status'] not in ('paused','error','finished','stopped') and time.monotonic()<deadline:
                        if event.is_set():raise CancelledError()
                        time.sleep(.05);state=debugger.snapshot()
                    if state['status']!='paused' or not state.get('stack'):raise ValueError(state.get('error') or 'El adaptador no confirmó una pausa con pila: '+state['status'])
                    before=len(state.get('pauseHistory',[]));debugger.command('next');deadline=time.monotonic()+10
                    while time.monotonic()<deadline:
                        if event.is_set():raise CancelledError()
                        state=debugger.snapshot()
                        if state['status']=='paused' and len(state.get('pauseHistory',[]))>before:break
                        if state['status'] in ('error','finished','stopped'):break
                        time.sleep(.04)
                    if state['status']!='paused' or len(state.get('pauseHistory',[]))<=before:raise ValueError('La pausa inicial existe, pero no se confirmó un segundo paso con pila.')
                    record('debug','passed','Pausa real, pila y paso confirmados por el depurador; sesión detenida al finalizar.',started)
                except (ValueError,OSError) as error:record('debug','failed',error,started)
                finally:debugger.stop()
            except CancelledError:raise
            except Exception as error:
                if not report['steps']:record('project','failed',error)
                else:record('build','failed',error)
            finally:
                if debugger:debugger.stop()
                f.shutdown();app.runner.shutdown()
        for name in STEPS:
            if not any(s['id']==name for s in report['steps']):record(name,'not-tested','No se llegó a este paso. Resuelve la preparación y repite el recorrido.')
        report['status']='passed' if all(s['status']=='passed' for s in report['steps']) else 'partial'
        report['stale']=signature(self.f)!=stamp
        if event.is_set():raise CancelledError()
        self.root.mkdir(parents=True,exist_ok=True);atomic_json(self.root/(lang+'.json'),report)
        return report

    def semantic(self,f,ws,lang,file,source,record,event):
        if lang=='nc':return self.nc_semantic(f,ws,record,event)
        from .lsp import LanguageSession
        name,args=SERVERS[lang];exe=find_tool(name,f.runtimes.config.get('tools'))
        if not exe:
            for step in ('navigation','rename'):record(step,'missing','Falta '+name+'. Las funciones anunciadas por una extensión se verifican por separado; no se presupone su resultado.')
            return
        # A controlled local variable has a declaration and at least two uses.
        snippets={'c':('int main(void) { int value = 42; return value + value; }\n','.c'),'cpp':('int main() { int value = 42; return value + value; }\n','.cpp'),'python':('value = 42\nprint(value + value)\n','.py'),'rust':('fn main() { let value = 42; println!("{}", value + value); }\n','.rs')}
        text,suffix=snippets.get(lang,(source,file.suffix))
        # rust-analyzer deliberately ignores a sibling orphan module that the
        # Cargo target never includes. This is already a disposable fixture:
        # probe its real crate entry and restore it before compiling/testing.
        probe=file if lang=='rust' else file.parent/('journey'+suffix);probe.write_text(text,encoding='utf-8');uri=probe.as_uri();offset=text.rfind('value');before=text[:offset];position={'line':before.count('\n'),'character':len(before.rsplit('\n',1)[-1].encode('utf-16-le'))//2+1};session=None
        try:
            started=time.perf_counter();session=LanguageSession({'id':'journey','languages':[lang],'argv':[exe,*args],'initializationTimeout':25},ws)
            session.notify('textDocument/didOpen',{'textDocument':{'uri':uri,'languageId':lang,'version':1,'text':text}})
            for step,method,extra in [('navigation','textDocument/definition',{}),('rename','textDocument/rename',{'newName':'verified_value'})]:
                began=time.perf_counter();result=None;error='Sin resultado semántico';deadline=time.monotonic()+15
                while time.monotonic()<deadline:
                    if event.is_set():raise CancelledError()
                    try:result=session.request(method,{'textDocument':{'uri':uri},'position':position,**extra},timeout=5)
                    except ValueError as failure:error=str(failure)
                    if result:break
                    time.sleep(.2)
                if step=='navigation':valid=bool(result) and uri.casefold() in json.dumps(result).casefold()
                else:
                    edits=[e for key,values in (result or {}).get('changes',{}).items() if key.casefold()==uri.casefold() for e in values]+[e for change in (result or {}).get('documentChanges',[]) if change.get('textDocument',{}).get('uri','').casefold()==uri.casefold() for e in change.get('edits',[])]
                    candidate=text;lines=text.splitlines(keepends=True)
                    def index(pos):return sum(len(line) for line in lines[:pos['line']])+pos['character']
                    for edit in sorted(edits,key=lambda e:index(e['range']['start']),reverse=True):
                        candidate=candidate[:index(edit['range']['start'])]+edit['newText']+candidate[index(edit['range']['end']):]
                    valid=bool(edits) and candidate==re.sub(r'\bvalue\b','verified_value',text)
                record(step,'passed' if valid else 'failed','Definición en el archivo correcto.' if valid and step=='navigation' else 'Renombrado devuelve la declaración y sus dos usos.' if valid else error,began)
        except (OSError,ValueError) as error:
            for step in ('navigation','rename'):record(step,'failed',str(error)+(' · '+session.stderr[-800:] if session else ''))
        finally:
            if session:session.close()
            if probe==file:probe.write_text(source,encoding='utf-8')
            else:probe.unlink(missing_ok=True)

    def nc_semantic(self,f,ws,record,event):
        from .extension_runtime import Host
        item=self.f.extensions.installed.get('nc-lang.nc-language');host=None
        if not item or not item.get('enabled'):
            for step in ('navigation','rename'):record(step,'missing','Activa el paquete nC adaptado del plugin seleccionado para comprobar sus proveedores.')
            return
        root=self.f.extensions.root/item['directory']/'extension';manifest=json.loads((root/'package.json').read_text(encoding='utf-8'))
        fixture=root/'test-fixtures/high_level.n';storage=f.prefs.directory/'nc-probe';storage.mkdir()
        atomic_json(storage/'configuration.json',{'nc.nccPath':f.runtimes.executable('ncc'),'nc.enableDiagnostics':False})
        try:
            sample=fixture.read_text(encoding='utf-8');text=sample+'\n'+sample.replace('vistaActual','otraVista');probe=ws.root/'journey.n';probe.write_text(text,encoding='utf-8');offset=text.rfind('valor');before=text[:offset]
            document={'path':str(probe),'text':text,'language':'nc'};position={'line':before.count('\n'),'character':len(before.rsplit('\n',1)[-1])+1}
            host=Host(f.runtimes.executable('node'),root,root/manifest['main'],ws,{'extensionId':'nc-lang.nc-language','manifest':manifest,'storage':str(storage),'locale':'es','extensions':[]})
            for step,kind in [('navigation','definition'),('rename','rename')]:
                if event.is_set():raise CancelledError()
                started=time.perf_counter();result=host.request({'method':'provide','kind':kind,'document':document,'position':position,'newName':'valorVerificado'})
                items=result.get('items',[]);second=text.index('otraVista');definition=text.index('valor',second);prefix=text[:definition];expected={'line':prefix.count('\n'),'character':len(prefix.rsplit('\n',1)[-1])}
                if kind=='definition':
                    valid=bool(items) and items[0].get('range',{}).get('start')==expected and 'journey.n' in json.dumps(items[0].get('uri'))
                    refs=host.request({'method':'provide','kind':'references','document':document,'position':position}).get('items',[])
                    valid=valid and len(refs)==2 and refs[0]['range']['start']==expected and all(r['range']['start']['line']>=expected['line'] for r in refs)
                else:
                    changes=(items[0].get('changes',[]) if items else []);edits=changes[0].get('edits',[]) if len(changes)==1 else []
                    def index(pos):
                        lines=text.splitlines(keepends=True);return sum(len(line) for line in lines[:pos['line']])+pos['character']
                    candidate=text
                    for edit in sorted(edits,key=lambda e:index(e['range']['start']),reverse=True):candidate=candidate[:index(edit['range']['start'])]+edit['newText']+candidate[index(edit['range']['end']):]
                    valid=len(edits)==2 and candidate==text[:second]+re.sub(r'\bvalor\b','valorVerificado',text[second:])
                record(step,'passed' if valid else 'failed','Proveedor adaptado '+manifest['version']+': '+('definición y dos referencias del contenedor correcto' if kind=='definition' else 'declaración y uso del segundo ámbito; el primero queda intacto') if valid else 'El proveedor mezcló ámbitos o no devolvió la definición y los cambios exactos esperados.',started)
        except (ValueError,OSError,KeyError) as error:
            for step in ('navigation','rename'):record(step,'failed',error)
        finally:
            if host:host.close()
            (ws.root/'journey.n').unlink(missing_ok=True)
